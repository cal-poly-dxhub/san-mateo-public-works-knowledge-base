import json
import os
from collections import defaultdict

import boto3

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    """Handle lessons learned master API requests"""
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, X-Api-Key",
                },
                "body": "",
            }

        if "/project-types" in path and method == "GET":
            return get_project_types()

        elif "/by-type/" in path and method == "GET":
            project_type = event["pathParameters"]["project_type"]
            return get_lessons_by_type(project_type)

        elif method == "PUT":
            lesson_id = event["pathParameters"]["lesson_id"]
            body = json.loads(event.get("body", "{}"))
            return update_lesson(lesson_id, body)

        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Not found"}),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_project_types():
    """Get all project types with lesson counts"""
    try:
        bucket_name = os.environ.get("BUCKET_NAME")
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        print(f"Scanning table: {os.environ['PROJECT_DATA_TABLE_NAME']}")
        print(f"Using bucket: {bucket_name}")

        # Get all projects and their types
        response = table.scan(
            FilterExpression="item_id = :config",
            ExpressionAttributeValues={":config": "config"},
        )

        print(f"Found {len(response['Items'])} projects")

        project_types = defaultdict(lambda: {"count": 0, "projects": []})

        for item in response["Items"]:
            project_type = item.get("projectType", "Unknown")
            project_name = item.get("projectName", "Unknown")
            project_types[project_type]["projects"].append(project_name)
            print(f"Project: {project_name}, Type: {project_type}")

        # Count lessons for each project type
        for project_type, data in project_types.items():
            lesson_count = 0
            for project_name in data["projects"]:
                try:
                    # Count lessons in S3 for this project
                    prefix = f"lessons-learned/{project_name}/"
                    print(f"Checking S3 prefix: {prefix}")

                    s3_response = s3.list_objects_v2(
                        Bucket=bucket_name, Prefix=prefix
                    )

                    lesson_files = [
                        obj
                        for obj in s3_response.get("Contents", [])
                        if obj["Key"].endswith(".json")
                    ]
                    lesson_count += len(lesson_files)

                    print(
                        f"Found {len(lesson_files)} lessons for {project_name}"
                    )

                except Exception as e:
                    print(f"Error checking lessons for {project_name}: {e}")

            project_types[project_type]["count"] = lesson_count
            print(f"Total lessons for {project_type}: {lesson_count}")

        # Convert to list format - show all project types
        result = [
            {
                "type": project_type,
                "count": data["count"],
                "projects": data["projects"],
            }
            for project_type, data in project_types.items()
        ]

        # Sort by lesson count descending, then by name
        result.sort(key=lambda x: (-x["count"], x["type"]))

        print(f"Returning {len(result)} project types")

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"projectTypes": result}),
        }

    except Exception as e:
        print(f"Error getting project types: {str(e)}")
        raise


def get_lessons_by_type(project_type):
    """Get all lessons for a specific project type"""
    try:
        bucket_name = os.environ.get("BUCKET_NAME")
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Get all projects of this type
        response = table.scan(
            FilterExpression="item_id = :config AND projectType = :ptype",
            ExpressionAttributeValues={
                ":config": "config",
                ":ptype": project_type,
            },
        )

        lessons = []

        for item in response["Items"]:
            project_name = item.get("projectName", "")

            try:
                # Get lessons from S3 for this project
                prefix = f"lessons-learned/{project_name}/"
                s3_response = s3.list_objects_v2(
                    Bucket=bucket_name, Prefix=prefix
                )

                for obj in s3_response.get("Contents", []):
                    if obj["Key"].endswith(".json"):
                        # Get lesson content
                        lesson_response = s3.get_object(
                            Bucket=bucket_name, Key=obj["Key"]
                        )
                        lesson_data = json.loads(lesson_response["Body"].read())

                        # Add metadata
                        lesson_data["id"] = (
                            obj["Key"].split("/")[-1].replace(".json", "")
                        )
                        lesson_data["projectName"] = project_name

                        lessons.append(lesson_data)

            except Exception as e:
                print(f"Error loading lessons for project {project_name}: {e}")
                continue

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"lessons": lessons}),
        }

    except Exception as e:
        print(f"Error getting lessons by type: {str(e)}")
        raise


def update_lesson(lesson_id, lesson_data):
    """Update a lesson learned"""
    try:
        bucket_name = os.environ.get("BUCKET_NAME")
        project_name = lesson_data.get("projectName")

        if not project_name:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Project name required"}),
            }

        # Remove metadata fields that shouldn't be stored
        lesson_content = {
            k: v
            for k, v in lesson_data.items()
            if k not in ["id", "projectName"]
        }

        # Save updated lesson to S3
        s3_key = f"lessons-learned/{project_name}/{lesson_id}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(lesson_content, indent=2),
            ContentType="application/json",
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Lesson updated successfully"}),
        }

    except Exception as e:
        print(f"Error updating lesson: {str(e)}")
        raise
