import json
import os
import boto3

ssm_client = boto3.client("ssm")
s3_client = boto3.client("s3")


def handler(event, context):
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")
        path_parameters = event.get("pathParameters") or {}

        # Models endpoint
        if path == "/models" and method == "GET":
            return get_available_models()

        # Assets endpoint
        elif "/assets/" in path and method == "GET":
            project_name = path_parameters.get("project_name")
            filename = path_parameters.get("filename")

            if not project_name or not filename:
                return {
                    "statusCode": 400,
                    "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                    "body": json.dumps({"error": "Missing project name or filename"}),
                }

            return get_asset_file(project_name, filename)

        elif method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
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


def get_asset_file(project_name, filename):
    """Get asset file content from S3"""
    try:
        bucket_name = os.environ["BUCKET_NAME"]
        key = f"projects/{project_name}/assets/{filename}"

        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        content = response["Body"].read().decode("utf-8")

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true",
                "Content-Type": "text/plain",
            },
            "body": content,
        }
    except s3_client.exceptions.NoSuchKey:
        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": "Asset not found"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": str(e)}),
        }


def get_available_models():
    """Get available AI models"""
    try:
        response = ssm_client.get_parameter(Name="/project-management/available-models")
        models = json.loads(response["Parameter"]["Value"])

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps(models),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": str(e)}),
        }
