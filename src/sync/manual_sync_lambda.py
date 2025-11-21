import json
import os
import boto3
from botocore.exceptions import ClientError

bedrock_agent = boto3.client("bedrock-agent")

KB_ID = os.environ["KB_ID"]
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID")


def handler(event, context):
    """Manual Knowledge Base sync trigger with status checking."""
    
    cors_headers = {
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization",
    }
    
    # Get data source ID if not in env
    data_source_id = DATA_SOURCE_ID
    if not data_source_id:
        try:
            response = bedrock_agent.list_data_sources(knowledgeBaseId=KB_ID)
            data_source_id = response["dataSourceSummaries"][0]["dataSourceId"]
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": cors_headers,
                "body": json.dumps({"error": f"Failed to get data source: {str(e)}"})
            }
    
    # Check current sync status
    try:
        ds_response = bedrock_agent.get_data_source(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id
        )
        status = ds_response["dataSource"]["status"]
        
        # If sync in progress, return stats
        if status in ["SYNCING", "DELETING"]:
            # Get latest ingestion job stats
            jobs_response = bedrock_agent.list_ingestion_jobs(
                knowledgeBaseId=KB_ID,
                dataSourceId=data_source_id,
                maxResults=1
            )
            
            job_stats = {}
            if jobs_response.get("ingestionJobSummaries"):
                job = jobs_response["ingestionJobSummaries"][0]
                job_stats = {
                    "status": job["status"],
                    "startedAt": job.get("startedAt", "").isoformat() if job.get("startedAt") else None,
                    "statistics": job.get("statistics", {})
                }
            
            return {
                "statusCode": 409,
                "headers": cors_headers,
                "body": json.dumps({
                    "message": "Sync already in progress",
                    "syncInProgress": True,
                    "dataSourceStatus": status,
                    "currentJob": job_stats
                })
            }
        
        # Start new sync
        sync_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id
        )
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "message": "Sync started successfully",
                "syncInProgress": False,
                "jobId": sync_response["ingestionJob"]["ingestionJobId"],
                "status": sync_response["ingestionJob"]["status"]
            })
        }
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ConflictException":
            return {
                "statusCode": 409,
                "headers": cors_headers,
                "body": json.dumps({
                    "message": "Sync already in progress",
                    "syncInProgress": True
                })
            }
        
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Failed to sync: {str(e)}"})
        }
