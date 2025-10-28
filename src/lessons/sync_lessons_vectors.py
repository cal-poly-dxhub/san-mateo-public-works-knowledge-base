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
    bucket_name: str, lessons_key: str, lessons: List[dict], project_name: str
):
    """
    Sync lessons to vector store
    - Deletes all existing lesson vectors for the project
    - Adds each lesson as individual vector with lesson ID
    """
    try:
        vector_bucket = os.environ.get("VECTOR_BUCKET_NAME", "dxhub-meeting-kb-vectors")
        index_name = os.environ.get("INDEX_NAME", "meeting-kb-index")
        embedding_model = os.environ["EMBEDDING_MODEL_ID"]

        # Delete all existing lesson vectors for this project
        delete_lesson_vectors_by_metadata(vector_bucket, index_name, project_name, lessons_key)

        if not lessons:
            logger.info(f"No lessons to sync for {project_name}")
            return

        # Add each lesson as vector using lesson ID
        for lesson in lessons:
            try:
                # Create searchable content
                content = f"{lesson.get('title', '')} {lesson.get('lesson', '')} {lesson.get('recommendation', '')}"
                
                # Generate embedding
                embedding = get_embedding(content, embedding_model)

                # Create metadata with lesson ID reference
                metadata = {
                    "lesson_id": lesson["id"],
                    "s3_key": lessons_key,
                    "project_name": project_name,
                    "title": lesson.get("title", "")[:500],
                    "severity": lesson.get("severity", "Medium"),
                    "is_lesson": "true",
                }

                # Use lesson ID in vector key for easy correlation
                vector_id = f"{project_name}_{lesson['id']}"

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

                logger.info(f"Added lesson vector {lesson['id']} for {project_name}")

            except Exception as e:
                logger.error(f"Error adding lesson {lesson.get('id')}: {e}")

        logger.info(f"Synced {len(lessons)} lessons for {project_name}")

    except Exception as e:
        logger.error(f"Error syncing lessons to vectors: {e}")
        raise


def delete_lesson_vectors_by_metadata(
    vector_bucket: str, index_name: str, project_name: str, lessons_key: str
):
    """Delete all lesson vectors for a project using metadata query"""
    try:
        logger.info(f"Deleting existing lesson vectors for {project_name}")

        # Query vectors by metadata
        response = s3vectors_client.query_vectors(
            vectorBucketName=vector_bucket,
            indexName=index_name,
            metadataFilters={
                "project_name": {"equals": project_name},
                "s3_key": {"equals": lessons_key},
                "is_lesson": {"equals": "true"}
            },
            maxResults=1000
        )

        vector_keys = [v["key"] for v in response.get("vectors", [])]

        if vector_keys:
            s3vectors_client.delete_vectors(
                vectorBucketName=vector_bucket,
                indexName=index_name,
                vectorKeys=vector_keys
            )
            logger.info(f"Deleted {len(vector_keys)} existing lesson vectors")
        else:
            logger.info(f"No existing lesson vectors found for {project_name}")

    except Exception as e:
        logger.warning(f"Error deleting lesson vectors: {e}")


def get_embedding(text: str, model_id: str) -> List[float]:
    """Generate embedding using Bedrock"""
    response = bedrock_client.invoke_model(
        modelId=model_id, body=json.dumps({"inputText": text})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]

