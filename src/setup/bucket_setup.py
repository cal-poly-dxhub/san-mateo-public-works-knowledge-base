import json
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")


def handler(event, context):
    try:
        request_type = event["RequestType"]
        bucket_name = event["ResourceProperties"]["BucketName"]

        if request_type == "Create":
            setup_base_structure(bucket_name)

        return {
            "Status": "SUCCESS",
            "PhysicalResourceId": f"bucket-setup-{bucket_name}",
            "Data": {},
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "Status": "FAILED",
            "Reason": str(e),
            "PhysicalResourceId": context.log_stream_name,
            "Data": {},
        }


def setup_base_structure(bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except s3_client.exceptions.NoSuchBucket:
        s3_client.create_bucket(Bucket=bucket_name)

    base_folders = ["new-meeting-videos/", "projects/"]

    for folder in base_folders:
        s3_client.put_object(Bucket=bucket_name, Key=folder)
        logger.info(f"Created folder: {folder}")

    project_types = {
        "project_types": [
            "Reconstruction",
            "Resurface",
            "Slurry Seal",
            "Drainage",
            "Utilities",
            "Other",
        ]
    }

    s3_client.put_object(
        Bucket=bucket_name,
        Key="project-types.json",
        Body=json.dumps(project_types, indent=2),
        ContentType="application/json",
    )
    logger.info("Created project-types.json")
