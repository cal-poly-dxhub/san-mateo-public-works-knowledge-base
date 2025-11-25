import json
import os
import boto3
import time
from urllib.parse import unquote

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")
        bucket_name = os.environ["BUCKET_NAME"]

        # Cognito authorization is handled by API Gateway
        if path.startswith("/file/"):
            file_path = path.replace("/file/", "", 1)
            return get_file_content(bucket_name, file_path)

        elif path.startswith("/upload-url") and method == "POST":
            return generate_upload_url(event, bucket_name)

        elif method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization",
                },
                "body": "",
            }

        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": "Not found"}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": str(e)}),
        }


def get_file_content(bucket_name, file_path):
    """Generate presigned URL for S3 file"""
    try:
        # Decode URL-encoded path
        file_path = unquote(file_path)

        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": file_path},
            ExpiresIn=3600,
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps({"url": presigned_url}),
        }
    except s3_client.exceptions.NoSuchKey:
        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": "File not found"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": str(e)}),
        }


def generate_upload_url(event, bucket_name):
    """Generate presigned URLs for file uploads (supports batch)"""
    try:
        body = json.loads(event.get("body", "{}"))
        files = body.get("files", [])
        
        if not files:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "files array is required"}),
            }

        table_name = os.environ.get("PROJECT_DATA_TABLE_NAME")
        table = dynamodb.Table(table_name) if table_name else None

        upload_urls = []
        for file_info in files:
            file_name = file_info.get("fileName")
            project_name = file_info.get("projectName")
            extract_lessons = file_info.get("extractLessons", False)
            project_type = file_info.get("projectType", "other")
            
            if not file_name:
                continue
            
            s3_key = f"documents/{file_name}"
            
            # Generate presigned URL without metadata
            print(f"Generating presigned URL for: {s3_key}")
            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket_name, "Key": s3_key},
                ExpiresIn=3600,
            )
            print(f"Generated URL: {presigned_url[:100]}...")
            
            # Store metadata in DynamoDB for S3 processor to retrieve
            if table and (project_name or extract_lessons):
                table.put_item(
                    Item={
                        "project_id": "upload-metadata",
                        "item_id": f"file#{s3_key}",
                        "projectName": project_name or "",
                        "extractLessons": extract_lessons,
                        "projectType": project_type,
                        "ttl": int(time.time()) + 7200,  # 2 hour TTL
                    }
                )
            
            upload_urls.append({
                "fileName": file_name,
                "uploadUrl": presigned_url,
                "s3Key": s3_key,
            })

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps({"uploads": upload_urls}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": str(e)}),
        }
