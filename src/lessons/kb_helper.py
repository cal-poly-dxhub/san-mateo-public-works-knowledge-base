"""Knowledge Base operations for lessons learned"""

import json
import logging
import os
from typing import Any, Dict, List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")
bedrock_agent_client = boto3.client("bedrock-agent")
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime")


def trigger_vector_ingestion(bucket_name: str, s3_key: str):
    """Trigger Knowledge Base sync for an S3 object."""
    try:
        lambda_client.invoke(
            FunctionName=os.environ.get("ASYNC_LESSONS_PROCESSOR_NAME"),
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "Records": [
                        {
                            "s3": {
                                "bucket": {"name": bucket_name},
                                "object": {"key": s3_key},
                            }
                        }
                    ]
                }
            ),
        )
        logger.info(f"Triggered KB sync for {s3_key}")
    except Exception as e:
        logger.error(f"Error triggering KB sync for {s3_key}: {e}")


def trigger_project_lessons_ingestion(bucket_name: str, project_name: str):
    """Trigger KB sync for project lessons file."""
    s3_key = f"documents/projects/{project_name}/lessons-learned.json"
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        lessons_data = json.loads(response["Body"].read().decode("utf-8"))

        project_type = None
        try:
            metadata_response = s3_client.get_object(
                Bucket=bucket_name, Key=f"projects/{project_name}/metadata.json"
            )
            metadata = json.loads(metadata_response["Body"].read().decode("utf-8"))
            project_type = metadata.get("projectType")
        except:
            pass

        lambda_client.invoke(
            FunctionName=os.environ.get("ASYNC_LESSONS_PROCESSOR_NAME"),
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "sync_only": True,
                    "bucket_name": bucket_name,
                    "lessons_key": s3_key,
                    "lessons": lessons_data.get("lessons", []),
                    "project_name": project_name,
                    "project_type": project_type,
                }
            ),
        )
        logger.info(f"Triggered KB sync for {s3_key}")
    except Exception as e:
        logger.error(f"Error triggering KB sync for {s3_key}: {e}")


def trigger_type_lessons_ingestion(bucket_name: str, project_type: str):
    """Trigger KB sync for project type master lessons file."""
    s3_key = f"lessons-learned/{project_type}/lessons.json"
    trigger_vector_ingestion(bucket_name, s3_key)


def sync_lessons_to_kb(
    bucket_name: str,
    lessons_key: str,
    lessons: List[dict],
    project_name: str,
    project_type: str = None,
):
    """Sync lessons to Knowledge Base by uploading to S3 and triggering sync job."""
    try:
        kb_id = os.environ.get("KB_ID")
        docs_bucket = os.environ.get("BUCKET_NAME")

        if not kb_id or not docs_bucket:
            raise ValueError("KB_ID or BUCKET_NAME not configured")

        logger.info(f"Starting KB sync for {project_name}: {len(lessons)} lessons")

        text_content = (
            f"Project: {project_name}\nProject Type: {project_type or 'unknown'}\n\n"
        )

        for i, lesson in enumerate(lessons, 1):
            text_content += f"Lesson {i}: {lesson.get('title', 'Untitled')}\n"
            text_content += f"Description: {lesson.get('lesson', '')}\n"
            text_content += f"Impact: {lesson.get('impact', '')}\n"
            text_content += f"Recommendation: {lesson.get('recommendation', '')}\n"
            text_content += f"Severity: {lesson.get('severity', 'Unknown')}\n"
            text_content += f"Source: {lesson.get('source_document', '')}\n\n"

        lessons_s3_key = f"documents/projects/{project_name}/lessons-learned.txt"

        s3_client.put_object(
            Bucket=docs_bucket,
            Key=lessons_s3_key,
            Body=text_content,
            ContentType="text/plain",
        )

        logger.info(f"Uploaded lessons to s3://{docs_bucket}/{lessons_s3_key}")

        try:
            response = bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=kb_id, dataSourceId=get_data_source_id(kb_id)
            )
            logger.info(
                f"Started KB ingestion job: {response.get('ingestionJob', {}).get('ingestionJobId')}"
            )
        except Exception as e:
            logger.warning(
                f"Could not trigger KB sync: {e}. Sync will happen on schedule."
            )

        logger.info(f"Lessons sync completed for {project_name}")

    except Exception as e:
        logger.error(f"Error syncing lessons to KB: {str(e)}")
        raise


def get_data_source_id(kb_id: str) -> str:
    """Get the data source ID for the Knowledge Base."""
    response = bedrock_agent_client.list_data_sources(knowledgeBaseId=kb_id)
    data_sources = response.get("dataSourceSummaries", [])
    if not data_sources:
        raise ValueError("No data sources found for Knowledge Base")
    return data_sources[0]["dataSourceId"]


def query_kb_by_project(
    query: str, project_name: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Query Knowledge Base filtered by project name."""
    kb_id = os.environ.get("KB_ID")
    if not kb_id:
        raise ValueError("KB_ID environment variable not set")

    response = bedrock_agent_runtime_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": limit,
                "filter": {"equals": {"key": "project_name", "value": project_name}},
            }
        },
    )

    return [
        {
            "content": item.get("content", {}).get("text", ""),
            "metadata": item.get("metadata", {}),
            "score": item.get("score", 0.0),
        }
        for item in response.get("retrievalResults", [])
    ]


def query_kb_lessons_only(
    query: str, project_name: str = None, limit: int = 10
) -> List[Dict[str, Any]]:
    """Query Knowledge Base for lessons only, optionally filtered by project."""
    kb_id = os.environ.get("KB_ID")
    if not kb_id:
        raise ValueError("KB_ID environment variable not set")

    response = bedrock_agent_runtime_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": limit}
        },
    )

    return [
        {
            "content": item.get("content", {}).get("text", ""),
            "metadata": item.get("metadata", {}),
            "score": item.get("score", 0.0),
        }
        for item in response.get("retrievalResults", [])
    ]


def query_kb_by_type(
    query: str, project_type: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Query Knowledge Base filtered by project type."""
    kb_id = os.environ.get("KB_ID")
    if not kb_id:
        raise ValueError("KB_ID environment variable not set")

    response = bedrock_agent_runtime_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": limit,
                "filter": {"equals": {"key": "project_type", "value": project_type}},
            }
        },
    )

    return [
        {
            "content": item.get("content", {}).get("text", ""),
            "metadata": item.get("metadata", {}),
            "score": item.get("score", 0.0),
        }
        for item in response.get("retrievalResults", [])
    ]
