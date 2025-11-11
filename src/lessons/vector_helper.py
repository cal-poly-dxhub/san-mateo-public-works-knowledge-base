"""Reusable helper for Knowledge Base operations across the codebase"""

import json
import os
from typing import Any, Dict, List

import boto3

lambda_client = boto3.client("lambda")
bedrock_agent_client = boto3.client("bedrock-agent-runtime")


def trigger_vector_ingestion(bucket_name: str, s3_key: str):
    """
    Trigger Knowledge Base sync for an S3 object.
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key (e.g., "projects/my-project/lessons-learned.json")
    """
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
        print(f"Triggered KB sync for {s3_key}")
    except Exception as e:
        print(f"Error triggering KB sync for {s3_key}: {e}")


def trigger_project_lessons_ingestion(bucket_name: str, project_name: str):
    """Trigger KB sync for project lessons file by invoking async processor"""
    s3_key = f"documents/projects/{project_name}/lessons-learned.json"
    try:
        s3_client = boto3.client("s3")
        
        # Read lessons from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        lessons_data = json.loads(response["Body"].read().decode("utf-8"))
        
        # Try to get project type from project metadata
        project_type = None
        try:
            metadata_response = s3_client.get_object(Bucket=bucket_name, Key=f"projects/{project_name}/metadata.json")
            metadata = json.loads(metadata_response["Body"].read().decode("utf-8"))
            project_type = metadata.get("projectType")
        except:
            pass

        # Invoke async processor with a sync-only event
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
        print(f"Triggered KB sync for {s3_key}")
    except Exception as e:
        print(f"Error triggering KB sync for {s3_key}: {e}")


def trigger_type_lessons_ingestion(bucket_name: str, project_type: str):
    """Trigger KB sync for project type master lessons file"""
    s3_key = f"documents/lessons-learned/{project_type}/master-lessons.json"
    trigger_vector_ingestion(bucket_name, s3_key)


def query_kb_by_project(query: str, project_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query Knowledge Base filtered by project name.
    
    Args:
        query: Search query text
        project_name: Project name to filter by
        limit: Maximum number of results
        
    Returns:
        List of search results with content and metadata
    """
    try:
        kb_id = os.environ.get("KB_ID")
        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": limit,
                    "filter": {
                        "equals": {
                            "key": "project_name",
                            "value": project_name
                        }
                    }
                }
            }
        )

        results = []
        for item in response.get("retrievalResults", []):
            results.append({
                "content": item.get("content", {}).get("text", ""),
                "metadata": item.get("metadata", {}),
                "score": item.get("score", 0.0)
            })
        
        return results

    except Exception as e:
        print(f"Error querying KB by project: {e}")
        return []


def query_kb_lessons_only(query: str, project_name: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query Knowledge Base for lessons only, optionally filtered by project.
    
    Args:
        query: Search query text
        project_name: Optional project name to filter by
        limit: Maximum number of results
        
    Returns:
        List of lesson results
    """
    try:
        kb_id = os.environ.get("KB_ID")
        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        # Query KB without any filtering
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": limit
                }
            }
        )

        results = []
        for item in response.get("retrievalResults", []):
            results.append({
                "content": item.get("content", {}).get("text", ""),
                "metadata": item.get("metadata", {}),
                "score": item.get("score", 0.0)
            })
        
        return results

    except Exception as e:
        print(f"Error querying KB for lessons: {e}")
        return []


def query_kb_by_type(query: str, project_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query Knowledge Base filtered by project type.
    
    Args:
        query: Search query text
        project_type: Project type to filter by
        limit: Maximum number of results
        
    Returns:
        List of search results
    """
    try:
        kb_id = os.environ.get("KB_ID")
        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": limit,
                    "filter": {
                        "equals": {
                            "key": "project_type",
                            "value": project_type
                        }
                    }
                }
            }
        )

        results = []
        for item in response.get("retrievalResults", []):
            results.append({
                "content": item.get("content", {}).get("text", ""),
                "metadata": item.get("metadata", {}),
                "score": item.get("score", 0.0)
            })
        
        return results

    except Exception as e:
        print(f"Error querying KB by type: {e}")
        return []
