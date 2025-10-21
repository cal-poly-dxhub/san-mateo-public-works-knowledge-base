import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")


def handler(event, context):
    try:
        bucket_name = os.getenv("BUCKET_NAME")

        # Handle API Gateway event
        if "body" in event:
            import json

            body = json.loads(event["body"])
            project_name = body["project_name"]
            project_description = body.get("project_description", "")
        else:
            # Direct invocation
            project_name = event["project_name"]
            project_description = event.get("project_description", "")

        create_project_folder(bucket_name, project_name, project_description)

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps(
                {"message": f"Project '{project_name}' created successfully"}
            ),
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps({"error": f"Error creating project: {str(e)}"}),
        }


def create_project_folder(bucket_name, project_name, project_description=""):
    project_name = project_name.strip("/")
    logger.info(f"Creating project folder: {project_name}")

    # Create main project folder
    project_path = f"projects/{project_name}/"
    s3_client.put_object(Bucket=bucket_name, Key=project_path)

    # Create subfolders
    subfolders = [
        f"projects/{project_name}/meeting-videos/",
        f"projects/{project_name}/meeting-transcripts/",
        f"projects/{project_name}/meeting-summaries/",
    ]

    for folder in subfolders:
        s3_client.put_object(Bucket=bucket_name, Key=folder)

    # Create project_overview.json file
    overview_template = load_template("project_overview.txt")
    overview_content = overview_template.format(project_name=project_name)

    # Add description if provided
    if project_description:
        overview_content = overview_content.replace('""', f'"{project_description}"')

    overview_path = f"projects/{project_name}/project_overview.json"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=overview_path,
        Body=overview_content.encode("utf-8"),
        ContentType="application/json",
    )

    # Create working_backwards.json file
    working_backwards_template = load_template("working_backwards.txt")
    working_backwards_content = working_backwards_template.format(
        project_name=project_name
    )

    working_backwards_path = f"projects/{project_name}/working_backwards.json"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=working_backwards_path,
        Body=working_backwards_content.encode("utf-8"),
        ContentType="application/json",
    )

    logger.info(f"Project folder '{project_name}' created successfully")


def load_template(template_name):
    """Load template from local file"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", template_name)
    try:
        with open(template_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading template {template_name}: {str(e)}")
        return f"Error loading template: {template_name}"
