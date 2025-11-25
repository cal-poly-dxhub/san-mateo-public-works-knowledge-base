import json
import os
import boto3
from urllib.parse import unquote_plus
from doc_parser import extract_text

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    """Process S3 upload events and trigger lessons extraction if needed"""
    
    table_name = os.environ.get("PROJECT_DATA_TABLE_NAME")
    table = dynamodb.Table(table_name) if table_name else None
    
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        
        # Only process files in documents/
        if not key.startswith("documents/"):
            continue
        
        try:
            # Try to get metadata from DynamoDB
            extract_lessons = False
            project_name = None
            project_type = "other"
            
            if table:
                try:
                    response = table.get_item(
                        Key={
                            "project_id": "upload-metadata",
                            "item_id": f"file#{key}"
                        }
                    )
                    if "Item" in response:
                        item = response["Item"]
                        extract_lessons = item.get("extractLessons", False)
                        project_name = item.get("projectName")
                        project_type = item.get("projectType", "other")
                        
                        # Delete the metadata item after reading
                        table.delete_item(
                            Key={
                                "project_id": "upload-metadata",
                                "item_id": f"file#{key}"
                            }
                        )
                except Exception as e:
                    print(f"Could not read metadata from DynamoDB: {e}")
            
            if extract_lessons and project_name:
                # Get file content
                obj = s3.get_object(Bucket=bucket, Key=key)
                file_bytes = obj["Body"].read()
                content = extract_text(file_bytes, key)
                
                # Invoke async lessons processor
                lessons_lambda = os.environ.get("LESSONS_PROCESSOR_LAMBDA_NAME")
                if lessons_lambda:
                    lambda_client.invoke(
                        FunctionName=lessons_lambda,
                        InvocationType="Event",
                        Payload=json.dumps({
                            "content": content,
                            "filename": key,
                            "project_name": project_name,
                            "project_type": project_type,
                        }),
                    )
                    print(f"Triggered lessons extraction for {key}")
        
        except Exception as e:
            print(f"Error processing {key}: {e}")
            continue
    
    return {"statusCode": 200}
