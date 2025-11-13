"""
Lambda function to sync lessons JSON files to markdown files for Bedrock KB.
Triggered by S3 events on projects/*/lessons.json changes.
"""

import json
import os
import boto3
from urllib.parse import unquote_plus

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
BUCKET_NAME = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ.get("PROJECT_DATA_TABLE_NAME", "project-management-data")


def lambda_handler(event, context):
    """Sync lessons JSON to markdown files"""
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        # Only process projects/*/lessons.json files
        if not key.startswith("projects/") or not key.endswith("/lessons.json"):
            continue

        # Extract project name from path: projects/project-name/lessons.json
        project_name = key.split("/")[1]

        # Handle delete events
        if record["eventName"].startswith("ObjectRemoved"):
            delete_project_lessons(project_name)
            continue

        # Read lessons JSON
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            lessons_data = json.loads(response["Body"].read())
        except s3.exceptions.NoSuchKey:
            delete_project_lessons(project_name)
            continue

        # Get project type from DynamoDB
        project_type = get_project_type(project_name)

        # Sync lessons to markdown
        sync_lessons_to_markdown(
            project_name, project_type, lessons_data.get("lessons", [])
        )

    return {"statusCode": 200}


def get_project_type(project_name):
    """Get project type from DynamoDB"""
    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={"project_id": project_name, "item_id": "config"})
        item = response.get("Item", {})
        # Try nested config.metadata.project_type, top-level projectType, or project_type
        project_type = (
            item.get("config", {}).get("metadata", {}).get("project_type")
            or item.get("projectType")
            or item.get("project_type")
        )

        if not project_type or project_type == "Unknown":
            # Try to extract from lessons-learned path in S3
            try:
                prefix = f"lessons-learned/"
                paginator = s3.get_paginator("list_objects_v2")
                for page in paginator.paginate(
                    Bucket=BUCKET_NAME, Prefix=prefix, Delimiter="/"
                ):
                    for common_prefix in page.get("CommonPrefixes", []):
                        folder = common_prefix["Prefix"].replace(prefix, "").rstrip("/")
                        # Check if this folder contains lessons for this project
                        lessons_key = f"{common_prefix['Prefix']}lessons.json"
                        try:
                            lessons_obj = s3.get_object(
                                Bucket=BUCKET_NAME, Key=lessons_key
                            )
                            lessons_data = json.loads(lessons_obj["Body"].read())
                            for lesson in lessons_data.get("lessons", []):
                                if lesson.get("project_name") == project_name:
                                    print(
                                        f"Found project type '{folder}' for {project_name} from lessons-learned folder"
                                    )
                                    return folder
                        except:
                            continue
            except Exception as e:
                print(f"Error searching for project type in lessons-learned: {e}")

        return project_type if project_type and project_type != "Unknown" else "General"
    except Exception as e:
        print(f"Error getting project type for {project_name}: {e}")
        return "General"


def sync_lessons_to_markdown(project_name, project_type, lessons):
    """Create/update markdown files for lessons"""
    # Get current lesson IDs
    current_ids = {lesson["id"] for lesson in lessons}

    # Source document path
    source_doc_key = f"projects/{project_name}/lessons_learned.txt"

    # Create/update markdown for each lesson
    for lesson in lessons:
        lesson_id = lesson["id"]
        md_key = f"documents/lessons-learned/lesson-{lesson_id}-{project_name}.md"

        content = f"""# {lesson["title"]}

**Project:** {project_name}
**Project Type:** {project_type}
**Impact:** {lesson["impact"]}
**Severity:** {lesson["severity"]}

## {project_type} Lesson Learned

{lesson["lesson"]}

## Recommendation
{lesson["recommendation"]}

---
*Source: {lesson.get("source_document", "N/A")}*
*Created: {lesson.get("created_at", "N/A")}*
"""

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=md_key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown",
            Metadata={
                "project-name": project_name,
                "project-type": project_type,
                "lesson-id": lesson_id,
                "source-document": source_doc_key,
            },
        )

    # Delete markdown files for removed lessons
    delete_orphaned_lessons(project_name, current_ids)


def delete_orphaned_lessons(project_name, current_ids):
    """Delete markdown files for lessons no longer in JSON"""
    prefix = f"documents/lessons-learned/lesson-"

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]
            # Check if this file belongs to this project
            if not key.endswith(f"-{project_name}.md"):
                continue

            # Extract lesson ID from filename: lesson-{id}-{project}.md
            filename = key.split("/")[-1]
            lesson_id = filename.replace("lesson-", "").replace(
                f"-{project_name}.md", ""
            )

            if lesson_id not in current_ids:
                s3.delete_object(Bucket=BUCKET_NAME, Key=key)


def delete_project_lessons(project_name):
    """Delete all markdown files for a project"""
    prefix = f"documents/lessons-learned/"
    suffix = f"-{project_name}.md"

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            if obj["Key"].endswith(suffix):
                s3.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])
