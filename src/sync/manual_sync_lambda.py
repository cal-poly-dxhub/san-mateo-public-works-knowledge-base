import json
import os
import time
import boto3
from botocore.exceptions import ClientError

bedrock_agent = boto3.client("bedrock-agent")
dynamodb = boto3.resource("dynamodb")

KB_ID = os.environ["KB_ID"]
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID")
SYNC_JOBS_TABLE = os.environ.get("SYNC_JOBS_TABLE", "kb-sync-jobs")

sync_jobs_table = dynamodb.Table(SYNC_JOBS_TABLE)


def handler(event, context):
    """Manual Knowledge Base sync trigger with async status tracking."""
    
    cors_headers = {
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization",
    }
    
    method = event.get("httpMethod", "POST")
    path = event.get("path", "")
    
    # GET /sync/knowledge-base/status - Check status
    if method == "GET" or "status" in path:
        return get_sync_status(cors_headers)
    
    # POST /sync/knowledge-base - Start sync
    return start_sync(cors_headers)


def get_sync_status(cors_headers):
    """Get current sync job status and progress."""
    try:
        # Get latest job from DynamoDB
        response = sync_jobs_table.scan(Limit=1)
        items = sorted(response.get("Items", []), key=lambda x: x.get("started_at", ""), reverse=True)
        
        if not items:
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({"status": "idle", "message": "No sync jobs found"})
            }
        
        job = items[0]
        job_id = job["job_id"]
        
        # Get fresh status from Bedrock
        data_source_id = DATA_SOURCE_ID or get_data_source_id()
        
        try:
            job_response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=KB_ID,
                dataSourceId=data_source_id,
                ingestionJobId=job_id
            )
            
            ingestion_job = job_response["ingestionJob"]
            stats = ingestion_job.get("statistics", {})
            
            # Update DynamoDB with latest stats
            sync_jobs_table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #status = :status, statistics = :stats, updated_at = :updated",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": ingestion_job["status"].lower(),
                    ":stats": {
                        "documentsScanned": stats.get("numberOfDocumentsScanned", 0),
                        "documentsModified": stats.get("numberOfModifiedDocuments", 0),
                        "documentsFailed": stats.get("numberOfDocumentsFailed", 0)
                    },
                    ":updated": int(time.time())
                }
            )
            
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({
                    "status": ingestion_job["status"].lower(),
                    "jobId": job_id,
                    "statistics": {
                        "documentsScanned": stats.get("numberOfDocumentsScanned", 0),
                        "documentsModified": stats.get("numberOfModifiedDocuments", 0),
                        "documentsFailed": stats.get("numberOfDocumentsFailed", 0),
                    },
                    "startedAt": job.get("started_at"),
                    "message": get_status_message(ingestion_job["status"], stats)
                })
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Job completed and cleaned up
                stats = job.get("statistics", {})
                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps({
                        "status": job.get("status", "complete").lower(),
                        "jobId": job_id,
                        "statistics": {
                            "documentsScanned": stats.get("documentsScanned", 0),
                            "documentsModified": stats.get("documentsModified", 0),
                            "documentsFailed": stats.get("documentsFailed", 0)
                        },
                        "message": "Sync completed"
                    })
                }
            raise
            
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Failed to get status: {str(e)}"})
        }


def start_sync(cors_headers):
    """Start a new Knowledge Base sync job."""
    data_source_id = DATA_SOURCE_ID or get_data_source_id()
    
    # Check if sync already in progress
    try:
        ds_response = bedrock_agent.get_data_source(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id
        )
        status = ds_response["dataSource"]["status"]
        
        if status in ["SYNCING", "DELETING"]:
            # Get current job info
            jobs_response = bedrock_agent.list_ingestion_jobs(
                knowledgeBaseId=KB_ID,
                dataSourceId=data_source_id,
                maxResults=1
            )
            
            if jobs_response.get("ingestionJobSummaries"):
                job = jobs_response["ingestionJobSummaries"][0]
                stats = job.get("statistics", {})
                
                return {
                    "statusCode": 409,
                    "headers": cors_headers,
                    "body": json.dumps({
                        "message": "Sync already in progress",
                        "status": "in_progress",
                        "jobId": job["ingestionJobId"],
                        "statistics": {
                            "documentsScanned": stats.get("numberOfDocumentsScanned", 0),
                            "documentsModified": stats.get("numberOfModifiedDocuments", 0),
                            "documentsFailed": stats.get("numberOfDocumentsFailed", 0),
                        }
                    })
                }
        
        # Start new sync
        sync_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id
        )
        
        job_id = sync_response["ingestionJob"]["ingestionJobId"]
        
        # Store job in DynamoDB
        sync_jobs_table.put_item(
            Item={
                "job_id": job_id,
                "status": "starting",
                "started_at": int(time.time()),
                "updated_at": int(time.time()),
                "statistics": {
                    "documentsScanned": 0,
                    "documentsModified": 0,
                    "documentsFailed": 0
                },
                "ttl": int(time.time()) + 86400  # 24 hours
            }
        )
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "message": "Sync started successfully",
                "status": "starting",
                "jobId": job_id,
                "statistics": {
                    "documentsScanned": 0,
                    "documentsModified": 0,
                    "documentsFailed": 0
                }
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
                    "status": "in_progress"
                })
            }
        
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Failed to sync: {str(e)}"})
        }


def get_data_source_id():
    """Get data source ID from Knowledge Base."""
    response = bedrock_agent.list_data_sources(knowledgeBaseId=KB_ID)
    return response["dataSourceSummaries"][0]["dataSourceId"]


def get_status_message(status, stats):
    """Generate user-friendly status message."""
    scanned = stats.get("numberOfDocumentsScanned", 0)
    modified = stats.get("numberOfModifiedDocuments", 0)
    failed = stats.get("numberOfDocumentsFailed", 0)
    
    if status == "STARTING":
        return "Sync is starting..."
    elif status == "IN_PROGRESS":
        return f"Syncing... {scanned} documents scanned, {modified} indexed"
    elif status == "COMPLETE":
        return f"Sync complete! {modified} documents indexed"
    elif status == "FAILED":
        return f"Sync failed. {failed} documents had errors"
    else:
        return f"Status: {status}"
