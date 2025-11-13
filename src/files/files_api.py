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

        # Check API key for file access
        if path.startswith("/file/"):
            api_key = event.get("headers", {}).get("x-api-key") or event.get(
                "headers", {}
            ).get("X-Api-Key")
            if not api_key:
                return {
                    "statusCode": 401,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": "API key required"}),
                }
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
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"url": presigned_url}),
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
        project_id = body.get("projectId") or body.get("projectName")

        if not file_name or not project_id:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "fileName and projectId are required"}),
            }

        # Generate S3 key with new path structure
        s3_key = f"documents/projects/{project_id}/{file_name}"

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
