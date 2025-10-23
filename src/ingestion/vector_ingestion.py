import json
import logging
import os
import boto3
from typing import List, Dict, Any
from datetime import datetime, timezone

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
        logger.info(f"Vector ingestion triggered with {len(event['Records'])} records")

        for record in event["Records"]:
            bucket_name = record["s3"]["bucket"]["name"]
            object_key = record["s3"]["object"]["key"]

            # Only process text files in documents folder
            if not (
                object_key.endswith(".txt") and "documents" in object_key
            ):
                logger.info(f"Skipping non-document file: {object_key}")
                continue

            logger.info(f"Processing document for vector ingestion: {object_key}")

            # Extract project name from path
            project_name = extract_project_name(object_key)
            if not project_name:
                logger.warning(f"Could not extract project name from {object_key}")
                continue

            # Get file metadata
            file_last_modified = record["s3"]["object"].get(
                "lastModified", datetime.now(timezone.utc).isoformat()
            )

            # Check if file needs processing
            if should_process_file(object_key, file_last_modified):
                ingest_file_to_vector_index(
                    bucket_name, object_key, project_name, file_last_modified
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


def load_config():
    """Load vector ingestion configuration from SSM"""
    try:
        chunk_size = ssm_client.get_parameter(
            Name="/meeting-automation/vector-ingestion/chunk-size-tokens"
        )
        overlap = ssm_client.get_parameter(
            Name="/meeting-automation/vector-ingestion/overlap-tokens"
        )
        bucket_name = ssm_client.get_parameter(
            Name="/meeting-automation/vector-ingestion/vector-bucket-name"
        )
        index_name = ssm_client.get_parameter(
            Name="/meeting-automation/vector-ingestion/index-name"
        )

        return {
            "chunk_size_tokens": int(chunk_size["Parameter"]["Value"]),
            "overlap_tokens": int(overlap["Parameter"]["Value"]),
            "vector_bucket_name": bucket_name["Parameter"]["Value"],
            "index_name": index_name["Parameter"]["Value"],
        }
    except Exception as e:
        logger.error(f"Error loading config from SSM: {e}")
        # Fallback defaults
        return {
            "chunk_size_tokens": 512,
            "overlap_tokens": 64,
            "vector_bucket_name": "dxhub-meeting-kb-vectors",
            "index_name": "meeting-kb-index",
        }


def should_process_file(file_key: str, file_last_modified: str) -> bool:
    """Check if file needs processing using DynamoDB cache"""
    try:
        response = dynamodb_client.get_item(
            TableName="vector-ingestion-cache", Key={"file_key": {"S": file_key}}
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


def chunk_text(text: str, chunk_size_tokens: int, overlap_tokens: int) -> List[str]:
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
    """Get project metadata from S3"""
    try:
        # Try to get project overview
        overview_key = f"projects/{project_name}/project-overview.json"
        response = s3_client.get_object(Bucket=bucket_name, Key=overview_key)
        overview = json.loads(response["Body"].read().decode("utf-8"))

        return {
            "project_description": overview.get("description", ""),
            "project_goals": overview.get("goals", []),
            "team_members": overview.get("team_members", []),
        }
    except Exception as e:
        logger.warning(f"Could not load project metadata for {project_name}: {e}")
        return {}


def ingest_file_to_vector_index(
    bucket_name: str, file_key: str, project_name: str, file_last_modified: str
):
    """Ingest a single file into the vector index with project metadata"""
    logger.info(f"Starting vector ingestion for {file_key}")

    # Load configuration
    config = load_config()

    # Get file content
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        content = response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error(f"Error reading {file_key}: {e}")
        return

    # Get project metadata
    project_metadata = get_project_metadata(bucket_name, project_name)

    # Extract filename for metadata
    filename = file_key.split("/")[-1]

    # Chunk the content
    chunks = chunk_text(content, config["chunk_size_tokens"], config["overlap_tokens"])
    logger.info(f"Created {len(chunks)} chunks for {filename}")

    vector_ids = []
    embedding_model_id = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

    # Process each chunk
    for i, chunk in enumerate(chunks):
        try:
            # Generate embedding
            embedding = get_embedding(chunk, embedding_model_id)

            # Create metadata with project context
            truncated_content = chunk[:1800] if len(chunk) > 1800 else chunk
            metadata = {
                "project_name": project_name,
                "file_name": filename,
                "chunk_index": str(i),
                "total_chunks": str(len(chunks)),
                "content": truncated_content,
                "is_lesson": "false",
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
