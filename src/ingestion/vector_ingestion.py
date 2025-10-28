import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime")
s3vectors_client = boto3.client("s3vectors")
dynamodb_client = boto3.client("dynamodb")
ssm_client = boto3.client("ssm")


def handler(event, context):
    """Lambda handler for automatic vector ingestion"""
    try:
        logger.info(
            f"Vector ingestion triggered with {len(event['Records'])} records"
        )

        for record in event["Records"]:
            bucket_name = record["s3"]["bucket"]["name"]
            object_key = record["s3"]["object"]["key"]

            # Skip lessons files - they're synced directly by lessons_processor
            if "lessons-learned" in object_key and object_key.endswith(".json"):
                logger.info(f"Skipping lesson file (synced by processor): {object_key}")
                continue

            # Process text files in documents folder
            is_document = (
                object_key.endswith(".txt") and "documents" in object_key
            )

            if not is_document:
                logger.info(f"Skipping non-document file: {object_key}")
                continue

            logger.info(
                f"Processing document for vector ingestion: {object_key}"
            )

            # Extract project name from path
            project_name = extract_project_name(object_key)
            if not project_name:
                logger.warning(
                    f"Could not extract project name from {object_key}"
                )
                continue

            # Get file metadata
            file_last_modified = record["s3"]["object"].get(
                "lastModified", datetime.now(timezone.utc).isoformat()
            )

            # Check if file needs processing
            if should_process_file(object_key, file_last_modified):
                ingest_file_to_vector_index(
                    bucket_name,
                    object_key,
                    project_name,
                    file_last_modified,
                    is_lesson=False,
                )
            else:
                logger.info(f"File {object_key} already processed, skipping")

        return {"statusCode": 200, "body": "Vector ingestion completed"}

    except Exception as e:
        logger.error(f"Error in vector ingestion: {str(e)}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}


def extract_project_name(object_key: str) -> str:
    """Extract project name from S3 object key"""
    # Expected format: projects/{project_name}/documents/{filename}
    parts = object_key.split("/")
    if len(parts) >= 3 and parts[0] == "projects":
        return parts[1]
    return ""


def delete_existing_vectors_for_file(
    vector_bucket_name: str,
    index_name: str,
    project_name: str,
    file_key: str
):
    """Delete all existing vectors for a file before re-ingesting"""
    try:
        filename = file_key.split("/")[-1]
        vector_keys = []
        next_token = None
        
        # Paginate through all vectors
        while True:
            params = {
                "vectorBucketName": vector_bucket_name,
                "indexName": index_name,
                "returnMetadata": True,
                "maxResults": 500
            }
            if next_token:
                params["nextToken"] = next_token
                
            response = s3vectors_client.list_vectors(**params)
            
            # Filter by project_name and file_name
            for v in response.get("vectors", []):
                metadata = v.get("metadata", {})
                if (metadata.get("project_name") == project_name and 
                    metadata.get("file_name") == filename):
                    vector_keys.append(v["key"])
            
            next_token = response.get("nextToken")
            if not next_token:
                break
        
        if vector_keys:
            # Delete in batches of 100
            for i in range(0, len(vector_keys), 100):
                batch = vector_keys[i:i+100]
                s3vectors_client.delete_vectors(
                    vectorBucketName=vector_bucket_name,
                    indexName=index_name,
                    keys=batch
                )
            logger.info(f"Deleted {len(vector_keys)} existing vectors for {file_key}")
        else:
            logger.info(f"No existing vectors found for {file_key}")
            
    except Exception as e:
        logger.warning(f"Error deleting existing vectors for {file_key}: {e}")


def load_config():
    """Load vector ingestion configuration from SSM"""
    chunk_size = ssm_client.get_parameter(
        Name="/project-management/vector-ingestion/chunk-size-tokens"
    )
    overlap = ssm_client.get_parameter(
        Name="/project-management/vector-ingestion/overlap-tokens"
    )
    bucket_name = ssm_client.get_parameter(
        Name="/project-management/vector-ingestion/vector-bucket-name"
    )
    index_name = ssm_client.get_parameter(
        Name="/project-management/vector-ingestion/index-name"
    )

    return {
        "chunk_size_tokens": int(chunk_size["Parameter"]["Value"]),
        "overlap_tokens": int(overlap["Parameter"]["Value"]),
        "vector_bucket_name": bucket_name["Parameter"]["Value"],
        "index_name": index_name["Parameter"]["Value"],
    }


def should_process_file(file_key: str, file_last_modified: str) -> bool:
    """Check if file needs processing using DynamoDB cache"""
    try:
        response = dynamodb_client.get_item(
            TableName="vector-ingestion-cache",
            Key={"file_key": {"S": file_key}},
        )

        if "Item" not in response:
            return True

        cached_modified = response["Item"]["last_modified"]["S"]
        return file_last_modified > cached_modified

    except Exception as e:
        logger.error(f"Error checking cache for {file_key}: {e}")
        return True


def update_cache(file_key: str, file_last_modified: str, vector_ids: List[str]):
    """Update DynamoDB cache with processed file info"""
    try:
        dynamodb_client.put_item(
            TableName="vector-ingestion-cache",
            Item={
                "file_key": {"S": file_key},
                "last_modified": {"S": file_last_modified},
                "processed_at": {"S": datetime.now(timezone.utc).isoformat()},
                "chunks_ingested": {"N": str(len(vector_ids))},
                "vector_ids": {"SS": vector_ids},
            },
        )
    except Exception as e:
        logger.error(f"Error updating cache for {file_key}: {e}")


def chunk_text(
    text: str, chunk_size_tokens: int, overlap_tokens: int
) -> List[str]:
    """Chunk text with fixed size and overlap"""
    chunk_size_chars = chunk_size_tokens * 4
    overlap_chars = overlap_tokens * 4

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size_chars
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap_chars
        if start >= len(text):
            break

    return chunks


def get_embedding(text: str, model_id: str) -> List[float]:
    """Generate embedding using Bedrock"""
    response = bedrock_client.invoke_model(
        modelId=model_id, body=json.dumps({"inputText": text})
    )

    result = json.loads(response["body"].read())
    return result["embedding"]


def get_project_metadata(bucket_name: str, project_name: str) -> Dict[str, Any]:
    """Get project metadata from DynamoDB"""
    try:
        response = dynamodb_client.get_item(
            TableName=os.environ.get("PROJECTS_TABLE", "projects"),
            Key={"project_name": {"S": project_name}},
        )

        if "Item" not in response:
            logger.warning(f"No metadata found for project {project_name}")
            return {}

        item = response["Item"]
        return {
            "project_type": item.get("project_type", {}).get("S", ""),
            "project_description": item.get("description", {}).get("S", ""),
            "status": item.get("status", {}).get("S", ""),
        }
    except Exception as e:
        logger.warning(
            f"Could not load project metadata for {project_name}: {e}"
        )
        return {}


def ingest_file_to_vector_index(
    bucket_name: str,
    file_key: str,
    project_name: str,
    file_last_modified: str,
    is_lesson: bool = False,
):
    """Ingest a single file into the vector index with project metadata"""
    logger.info(f"Starting vector ingestion for {file_key}")

    # Load configuration
    config = load_config()

    # DELETE EXISTING VECTORS FOR THIS FILE FIRST
    delete_existing_vectors_for_file(
        config["vector_bucket_name"],
        config["index_name"],
        project_name,
        file_key
    )

    # Get file content
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        raw_content = response["Body"].read().decode("utf-8")

        # Handle JSON lessons files - each lesson becomes its own chunk
        if is_lesson:
            lessons_data = json.loads(raw_content)
            lessons_list = lessons_data.get("lessons", [])
            logger.info(
                f"Processing {len(lessons_list)} individual lessons from {file_key}"
            )
        else:
            content = raw_content
            lessons_list = None

    except Exception as e:
        logger.error(f"Error reading {file_key}: {e}")
        return

    # Get project metadata
    project_metadata = get_project_metadata(bucket_name, project_name)

    # Extract filename for metadata
    filename = file_key.split("/")[-1]

    # Chunk the content
    if is_lesson and lessons_list:
        # Each lesson is its own chunk - store lesson data for metadata
        chunks = []
        lesson_metadata_list = []
        for lesson in lessons_list:
            lesson_text = f"Title: {lesson.get('title', 'Untitled')}\n"
            lesson_text += f"Lesson: {lesson.get('lesson', '')}\n"
            lesson_text += f"Impact: {lesson.get('impact', '')}\n"
            lesson_text += (
                f"Recommendation: {lesson.get('recommendation', '')}\n"
            )
            lesson_text += f"Severity: {lesson.get('severity', 'Unknown')}"
            chunks.append(lesson_text)
            # Store source document name and lesson ID
            lesson_metadata_list.append(
                {
                    "source_document": lesson.get("source_document", "Unknown"),
                    "lesson_id": lesson.get("id", ""),
                }
            )
        logger.info(f"Created {len(chunks)} lesson chunks for {filename}")
    else:
        chunks = chunk_text(
            content, config["chunk_size_tokens"], config["overlap_tokens"]
        )
        lesson_metadata_list = None
        logger.info(f"Created {len(chunks)} chunks for {filename}")

    vector_ids = []
    embedding_model_id = os.environ["EMBEDDING_MODEL_ID"]

    # Process each chunk
    for i, chunk in enumerate(chunks):
        try:
            # Generate embedding
            embedding = get_embedding(chunk, embedding_model_id)

            # Create metadata with project context
            truncated_content = chunk[:1800] if len(chunk) > 1800 else chunk

            # For lessons, use source_document if available
            if (
                is_lesson
                and lesson_metadata_list
                and i < len(lesson_metadata_list)
            ):
                source_doc = lesson_metadata_list[i].get(
                    "source_document", filename
                )
            else:
                source_doc = filename

            metadata = {
                "project_name": project_name,
                "file_name": source_doc,  # Use source document name for lessons
                "chunk_index": str(i),
                "total_chunks": str(len(chunks)),
                "content": truncated_content,
                "is_lesson": "true" if is_lesson else "false",
                **project_metadata,  # Include project metadata
            }

            # Generate unique vector ID
            vector_id = f"{project_name}_{filename}_{i}"
            vector_ids.append(vector_id)

            # Insert into vector index
            s3vectors_client.put_vectors(
                vectorBucketName=config["vector_bucket_name"],
                indexName=config["index_name"],
                vectors=[
                    {
                        "key": vector_id,
                        "data": {"float32": embedding},
                        "metadata": metadata,
                    }
                ],
            )

            logger.info(f"Ingested chunk {i + 1}/{len(chunks)} from {filename}")

        except Exception as e:
            logger.error(f"Error processing chunk {i} from {filename}: {e}")

    # Update cache
    update_cache(file_key, file_last_modified, vector_ids)
    logger.info(
        f"Completed vector ingestion for {file_key} - {len(vector_ids)} chunks processed"
    )
