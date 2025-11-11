import json
import logging
import os
from typing import List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
bedrock_agent_client = boto3.client("bedrock-agent")


def truncate_lesson_fields(
    lessons: List[dict], max_field_length: int = 200
) -> List[dict]:
    """Truncate lesson text fields to prevent S3 Vectors metadata size errors"""
    truncated_lessons = []
    text_fields = ["lesson", "recommendation", "impact", "title"]

    for lesson in lessons:
        truncated_lesson = lesson.copy()
        for field in text_fields:
            if field in truncated_lesson and isinstance(
                truncated_lesson[field], str
            ):
                if len(truncated_lesson[field]) > max_field_length:
                    truncated_lesson[field] = (
                        truncated_lesson[field][:max_field_length] + "..."
                    )
        truncated_lessons.append(truncated_lesson)

    return truncated_lessons


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

        # Convert lessons to plain text format
        text_content = f"Project: {project_name}\nProject Type: {project_type or 'unknown'}\n\n"
        
        for i, lesson in enumerate(lessons, 1):
            text_content += f"Lesson {i}: {lesson.get('title', 'Untitled')}\n"
            text_content += f"Description: {lesson.get('lesson', '')}\n"
            text_content += f"Impact: {lesson.get('impact', '')}\n"
            text_content += f"Recommendation: {lesson.get('recommendation', '')}\n"
            text_content += f"Severity: {lesson.get('severity', 'Unknown')}\n"
            text_content += f"Source: {lesson.get('source_document', '')}\n\n"

        # Upload lessons as plain text
        lessons_s3_key = f"documents/projects/{project_name}/lessons-learned.txt"

        # Upload to S3 with no metadata
        s3_client.put_object(
            Bucket=docs_bucket,
            Key=lessons_s3_key,
            Body=text_content,
            ContentType="text/plain",
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
