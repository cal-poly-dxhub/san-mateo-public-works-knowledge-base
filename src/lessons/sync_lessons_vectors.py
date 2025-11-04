import json
import logging
import os
from typing import List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime")
s3vectors_client = boto3.client("s3vectors")


def sync_lessons_to_vectors(
    bucket_name: str, lessons_key: str, lessons: List[dict], project_name: str, project_type: str = None
):
    """
    Sync lessons to vector store
    - Deletes all existing lesson vectors for the project
    - Adds each lesson as individual vector with lesson ID
    """
    try:
        vector_bucket = os.environ.get("VECTOR_BUCKET_NAME", "dpw-project-mgmt-vectors")
        index_name = os.environ.get("INDEX_NAME", "project-mgmt-index")
        embedding_model = os.environ.get("EMBEDDING_MODEL_ID")
        
        if not embedding_model:
            logger.error("EMBEDDING_MODEL_ID environment variable not set")
            raise ValueError("EMBEDDING_MODEL_ID not configured")

        logger.info(f"Starting vector sync for {project_name}: {len(lessons)} lessons")
        logger.info(f"Vector bucket: {vector_bucket}, Index: {index_name}")

        # Delete all existing lesson vectors for this project
        delete_lesson_vectors_by_metadata(vector_bucket, index_name, project_name, lessons_key)

        if not lessons:
            logger.info(f"No lessons to sync for {project_name}")
            return

        # Add each lesson as vector using lesson ID
        for lesson in lessons:
            try:
                # Create searchable content with project type context
                content_parts = []
                if project_type:
                    content_parts.append(f"Lessons learned for {project_type} projects")
                content_parts.extend([
                    lesson.get('title', ''),
                    lesson.get('lesson', ''),
                    lesson.get('recommendation', '')
                ])
                content = ' '.join(content_parts)
                
                logger.info(f"Generating embedding for lesson {lesson['id']}")
                # Generate embedding
                embedding = get_embedding(content, embedding_model)

                # Create searchable content for display (truncated to 1800 chars like regular docs)
                display_content = f"Title: {lesson.get('title', 'Untitled')}\n"
                display_content += f"Lesson: {lesson.get('lesson', '')}\n"
                display_content += f"Impact: {lesson.get('impact', '')}\n"
                display_content += f"Recommendation: {lesson.get('recommendation', '')}\n"
                display_content += f"Severity: {lesson.get('severity', 'Unknown')}"
                truncated_content = display_content[:1800] if len(display_content) > 1800 else display_content

                # Create metadata with lesson ID reference
                metadata = {
                    "lesson_id": lesson["id"],
                    "s3_key": lessons_key,
                    "project_name": project_name,
                    "file_name": lesson.get("source_document", "master-lessons.json"),
                    "title": lesson.get("title", "")[:500],
                    "severity": lesson.get("severity", "Medium"),
                    "is_lesson": "true",
                    "content": truncated_content,  # Add content field for search display
                    "chunk_index": "0",
                    "total_chunks": "1",
                }

                # Use lesson ID in vector key for easy correlation
                vector_id = f"{project_name}_{lesson['id']}"

                logger.info(f"Inserting vector {vector_id}")
                # Insert into vector index
                s3vectors_client.put_vectors(
                    vectorBucketName=vector_bucket,
                    indexName=index_name,
                    vectors=[
                        {
                            "key": vector_id,
                            "data": {"float32": embedding},
                            "metadata": metadata,
                        }
                    ],
                )

                logger.info(f"✓ Added lesson vector {lesson['id']} for {project_name}")

            except Exception as e:
                logger.error(f"✗ Error adding lesson {lesson.get('id')}: {e}", exc_info=True)
                raise

        logger.info(f"✓ Successfully synced {len(lessons)} lessons for {project_name}")

    except Exception as e:
        logger.error(f"✗ FATAL: Error syncing lessons to vectors: {e}", exc_info=True)
        raise


def delete_lesson_vectors_by_metadata(
    vector_bucket: str, index_name: str, project_name: str, lessons_key: str
):
    """Delete all lesson vectors for a project by listing and filtering"""
    try:
        logger.info(f"Deleting existing lesson vectors for {project_name} from {lessons_key}")

        # List all vectors with pagination
        vector_keys = []
        next_token = None
        
        while True:
            params = {
                "vectorBucketName": vector_bucket,
                "indexName": index_name,
                "returnMetadata": True,
                "maxResults": 500
            }
            if next_token:
                params["nextToken"] = next_token
                
            response = s3vectors_client.list_vectors(**params)

            # Filter vectors by metadata
            for v in response.get("vectors", []):
                metadata = v.get("metadata", {})
                if (metadata.get("project_name") == project_name and 
                    metadata.get("s3_key") == lessons_key and
                    metadata.get("is_lesson") == "true"):
                    vector_keys.append(v["key"])
            
            next_token = response.get("nextToken")
            if not next_token:
                break

        if vector_keys:
            # Delete in batches of 100
            for i in range(0, len(vector_keys), 100):
                batch = vector_keys[i:i+100]
                s3vectors_client.delete_vectors(
                    vectorBucketName=vector_bucket,
                    indexName=index_name,
                    keys=batch
                )
            logger.info(f"Deleted {len(vector_keys)} existing lesson vectors")
        else:
            logger.info(f"No existing lesson vectors found for {project_name}")

    except Exception as e:
        logger.error(f"Error deleting lesson vectors: {e}", exc_info=True)
        raise



def get_embedding(text: str, model_id: str) -> List[float]:
    """Generate embedding using Bedrock"""
    response = bedrock_client.invoke_model(
        modelId=model_id, body=json.dumps({"inputText": text})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]

