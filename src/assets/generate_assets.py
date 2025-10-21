import json
import os

import boto3

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")


def load_prompt(prompt_name):
    """Load prompt from file"""
    prompt_path = os.path.join(
        os.path.dirname(__file__), "prompts", f"{prompt_name}.txt"
    )
    with open(prompt_path, "r") as f:
        return f.read()


def lambda_handler(event, context):
    try:
        # Parse the request
        path = event.get("path", "")
        project_name = event.get("pathParameters", {}).get("project_name")

        if not project_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Project name is required"}),
            }

        bucket_name = os.environ["BUCKET_NAME"]

        # Determine asset type from path
        if "executive-summary" in path:
            asset_type = "executive_summary"
        elif "webstory" in path:
            asset_type = "webstory"
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid asset type"}),
            }

        payload = {
            "project_name": project_name,
            "asset_type": asset_type,
            "bucket_name": bucket_name,
        }

        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=os.environ["ASYNC_ASSET_PROCESSOR_NAME"],
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(payload),
        )

        return {
            "statusCode": 202,  # Accepted
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, x-api-key",
            },
            "body": json.dumps(
                {
                    "message": f"{asset_type.replace('_', ' ').title()} generation started",
                    "status": "processing",
                }
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
