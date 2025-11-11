import json
import logging
import os
from typing import List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
bedrock_agent_client = boto3.client("bedrock-agent")


def sync_lessons_to_vectors(
    bucket_name: str,
    lessons_key: str,
    lessons: List[dict],
    project_name: str,
    project_type: str = None,
):
    """
    Sync lessons to Knowledge Base by uploading to S3 and triggering sync job
    """
    try:
        kb_id = os.environ.get("KB_ID")
        docs_bucket = os.environ.get("BUCKET_NAME")

        if not kb_id:
            logger.error("KB_ID environment variable not set")
            raise ValueError("KB_ID not configured")

        if not docs_bucket:
            logger.error("BUCKET_NAME environment variable not set")
            raise ValueError("BUCKET_NAME not configured")

        logger.info(
            f"Starting KB sync for {project_name}: {len(lessons)} lessons"
        )

        # Upload lessons to docs bucket with metadata
        lessons_s3_key = f"documents/projects/{project_name}/lessons-learned.json"

        # Create lessons file content
        lessons_content = json.dumps(lessons, indent=2)

        # Upload to S3 with metadata
        s3_client.put_object(
            Bucket=docs_bucket,
            Key=lessons_s3_key,
            Body=lessons_content,
            ContentType="application/json",
            Metadata={
                "project_name": project_name,
                "project_type": project_type or "unknown",
                "content_type": "lesson",
                "lesson_count": str(len(lessons)),
            },
        )

        logger.info(f"Uploaded lessons to s3://{docs_bucket}/{lessons_s3_key}")

        # Trigger Knowledge Base sync job
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
    """Get the data source ID for the Knowledge Base"""
    try:
        response = bedrock_agent_client.list_data_sources(knowledgeBaseId=kb_id)
        data_sources = response.get("dataSourceSummaries", [])
        if data_sources:
            return data_sources[0]["dataSourceId"]
        raise ValueError("No data sources found for Knowledge Base")
    except Exception as e:
        logger.error(f"Error getting data source ID: {e}")
        raise
