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
    """Process asset generation asynchronously"""
    try:
        project_name = event["project_name"]
        asset_type = event["asset_type"]
        bucket_name = event["bucket_name"]

        # Get project data
        project_data = get_project_data(bucket_name, project_name)

        # Generate asset
        asset_content = generate_asset(asset_type, project_data)

        # Save to S3
        asset_key = f"projects/{project_name}/assets/{asset_type}.md"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=asset_key,
            Body=asset_content,
            ContentType="text/markdown",
        )

        print(f"Successfully generated {asset_type} for {project_name}")
        return {"statusCode": 200}

    except Exception as e:
        print(f"Error in async processing: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500}


def get_project_data(bucket_name, project_name):
    """Get all project data for asset generation"""
    data = {}

    # Get project overview
    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=f"projects/{project_name}/project_overview.json",
        )
        data["project_overview"] = json.loads(
            response["Body"].read().decode("utf-8")
        )
    except:
        data["project_overview"] = {}

    # Get working backwards
    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=f"projects/{project_name}/working_backwards.json",
        )
        data["working_backwards"] = json.loads(
            response["Body"].read().decode("utf-8")
        )
    except:
        data["working_backwards"] = {}

    # Get meeting summaries
    data["meeting_summaries"] = []
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=f"projects/{project_name}/meeting-summaries/",
        )
        for obj in response.get("Contents", []):
            if obj["Key"].endswith(".json"):
                summary_response = s3_client.get_object(
                    Bucket=bucket_name, Key=obj["Key"]
                )
                summary = json.loads(
                    summary_response["Body"].read().decode("utf-8")
                )
                data["meeting_summaries"].append(summary)
    except:
        pass

    return data


def generate_asset(asset_type, project_data):
    """Generate asset content using Bedrock"""
    prompt_template = load_prompt(asset_type)

    # Replace placeholders in prompt
    prompt = prompt_template.replace(
        "{project_overview}",
        json.dumps(project_data.get("project_overview", {}), indent=2),
    )
    prompt = prompt.replace(
        "{working_backwards}",
        json.dumps(project_data.get("working_backwards", {}), indent=2),
    )
    prompt = prompt.replace(
        "{meeting_summaries}",
        json.dumps(project_data.get("meeting_summaries", []), indent=2),
    )

    response = bedrock_client.invoke_model(
        modelId=os.getenv("ASSET_MODEL_ID"),
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
