import json
import os
import boto3
from urllib.parse import unquote_plus

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")


def handler(event, context):
    """Process S3 upload events and trigger lessons extraction if needed"""
    
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        
        # Only process files in documents/
        if not key.startswith("documents/"):
            continue
        
        try:
            # Get object metadata
            response = s3.head_object(Bucket=bucket, Key=key)
            metadata = response.get("Metadata", {})
            
            extract_lessons = metadata.get("extract-lessons") == "true"
            project_name = metadata.get("project-name")
            project_type = metadata.get("project-type", "other")
            
            if extract_lessons and project_name:
                # Get file content
                obj = s3.get_object(Bucket=bucket, Key=key)
                content = obj["Body"].read().decode("utf-8")
                
                # Invoke async lessons processor
                lessons_lambda = os.environ.get("LESSONS_PROCESSOR_LAMBDA_NAME")
                if lessons_lambda:
                    lambda_client.invoke(
                        FunctionName=lessons_lambda,
                        InvocationType="Event",
                        Payload=json.dumps({
                            "content": content,
                            "filename": key.split("/")[-1],
                            "project_name": project_name,
                            "project_type": project_type,
                        }),
                    )
                    print(f"Triggered lessons extraction for {key}")
        
        except Exception as e:
            print(f"Error processing {key}: {e}")
            continue
    
    return {"statusCode": 200}
