import json
import os
import boto3
from urllib.parse import unquote

s3_client = boto3.client("s3")


def handler(event, context):
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")
        bucket_name = os.environ["BUCKET_NAME"]

        if path.startswith("/file/"):
            file_path = path.replace("/file/", "")
            return get_file_content(bucket_name, file_path)

        elif path.startswith("/upload-url") and method == "POST":
            return generate_upload_url(event, bucket_name)

        elif method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                },
                "body": "",
            }

        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Not found"}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_file_content(bucket_name, file_path):
    """Get file content from S3"""
    try:
        # Decode URL-encoded path
        file_path = unquote(file_path)

        # Get file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
        content = response["Body"].read()

        # Determine content type
        content_type = "text/plain"
        if file_path.endswith(".json"):
            content_type = "application/json"
        elif file_path.endswith(".md"):
            content_type = "text/markdown"
        elif file_path.endswith(".html"):
            content_type = "text/html"

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": "*",
            },
            "body": content.decode("utf-8"),
        }
    except s3_client.exceptions.NoSuchKey:
        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "File not found"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def generate_upload_url(event, bucket_name):
    """Generate presigned URL for file upload"""
    try:
        body = json.loads(event.get("body", "{}"))
        file_name = body.get("fileName")
        project_name = body.get("projectName")

        if not file_name or not project_name:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "fileName and projectName are required"}),
            }

        # Generate S3 key
        s3_key = f"projects/{project_name}/documents/{file_name}"

        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket_name, "Key": s3_key},
            ExpiresIn=3600,  # 1 hour
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"uploadUrl": presigned_url, "s3Key": s3_key}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
