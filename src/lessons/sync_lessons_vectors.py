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
    bucket_name: str, project_name: str, project_type: str
):
    """
    Sync lessons learned to vector store
    - Deletes all existing lesson vectors for the project
    - Adds each lesson as individual vector chunk
    """
    try:
        # Load config
        vector_bucket = os.environ.get(
            "VECTOR_BUCKET_NAME", "dxhub-meeting-kb-vectors"
        )
        index_name = os.environ.get("INDEX_NAME", "meeting-kb-index")
        embedding_model = os.environ["EMBEDDING_MODEL_ID"]

        # Delete existing lesson vectors for this project
        delete_lesson_vectors(vector_bucket, index_name, project_name)

        # Load lessons from S3
        lessons_key = f"projects/{project_name}/lessons-learned.md"
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=lessons_key)
            lessons_content = response["Body"].read().decode("utf-8")
        except:
            logger.warning(f"No lessons file found for {project_name}")
            return

        # Parse lessons by category
        lessons = parse_lessons_markdown(lessons_content)

        if not lessons:
            logger.info(f"No lessons to sync for {project_name}")
            return

        # Add each lesson as vector
        vector_ids = []
        for i, lesson in enumerate(lessons):
            try:
                # Generate embedding
                embedding = get_embedding(lesson["content"], embedding_model)

                # Create metadata
                metadata = {
                    "project_name": project_name,
                    "project_type": project_type,
                    "file_name": "lessons-learned.md",
                    "category": lesson["category"],
                    "content": lesson["content"][:1800],
                    "is_lesson": "true",
                    "chunk_index": str(i),
                    "total_chunks": str(len(lessons)),
                }

                # Generate vector ID
                vector_id = f"{project_name}_lesson_{i}"
                vector_ids.append(vector_id)

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

                logger.info(
                    f"Added lesson vector {i + 1}/{len(lessons)} for {project_name}"
                )

            except Exception as e:
                logger.error(f"Error adding lesson {i}: {e}")

        logger.info(f"Synced {len(vector_ids)} lessons for {project_name}")

    except Exception as e:
        logger.error(f"Error syncing lessons to vectors: {e}")
        raise


def delete_lesson_vectors(
    vector_bucket: str, index_name: str, project_name: str
):
    """Delete all lesson vectors for a project"""
    try:
        # Query for all lesson vectors for this project
        # Note: S3 Vectors doesn't have a direct delete by filter, so we need to list and delete
        # For now, we'll use a naming convention: {project_name}_lesson_{index}

        # We'll delete by pattern - this is a simplified approach
        # In production, you might want to track vector IDs in DynamoDB
        logger.info(f"Deleting existing lesson vectors for {project_name}")

        # Delete up to 1000 potential lesson vectors (should be more than enough)
        for i in range(1000):
            try:
                vector_id = f"{project_name}_lesson_{i}"
                s3vectors_client.delete_vectors(
                    vectorBucketName=vector_bucket,
                    indexName=index_name,
                    vectorKeys=[vector_id],
                )
            except:
                # Vector doesn't exist, we're done
                break

    except Exception as e:
        logger.warning(f"Error deleting lesson vectors: {e}")


def parse_lessons_markdown(content: str) -> List[dict]:
    """Parse lessons learned markdown into individual lessons"""
    lessons = []
    current_category = "General"

    lines = content.split("\n")
    for line in lines:
        line = line.strip()

        # Detect category headers
        if line.startswith("##") and not line.startswith("###"):
            current_category = line.replace("#", "").strip()
            continue

        # Detect individual lessons (bullet points)
        if line.startswith("-") or line.startswith("*"):
            lesson_text = line.lstrip("-*").strip()
            if lesson_text:
                lessons.append(
                    {
                        "category": current_category,
                        "content": f"{current_category}: {lesson_text}",
                    }
                )

    return lessons


def get_embedding(text: str, model_id: str) -> List[float]:
    """Generate embedding using Bedrock"""
    response = bedrock_client.invoke_model(
        modelId=model_id, body=json.dumps({"inputText": text})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]
