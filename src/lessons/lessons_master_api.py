import json
import os
from urllib.parse import unquote

import boto3
from kb_helper import trigger_type_lessons_ingestion

s3 = boto3.client("s3")


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
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, X-Api-Key",
                },
                "body": "",
            }

        if "/project-types" in path and method == "GET":
            return get_project_types()

        elif "/conflicts/resolve/" in path and method == "POST":
            conflict_id = unquote(event["pathParameters"]["conflict_id"])
            return resolve_master_conflict(event, conflict_id)

        elif "/conflicts/by-type/" in path and method == "GET":
            project_type = unquote(event["pathParameters"]["project_type"])
            return get_master_conflicts(project_type)

        elif "/by-type/" in path and method == "GET":
            project_type = unquote(event["pathParameters"]["project_type"])
            return get_lessons_by_type(project_type)

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
    """Get all project types with lesson counts from master files"""
    try:
        bucket_name = os.environ.get("BUCKET_NAME")

        # List all master lesson files in lessons-learned/
        response = s3.list_objects_v2(
            Bucket=bucket_name, Prefix="lessons-learned/", Delimiter="/"
        )

        project_types = []

        # Get each project type folder
        for prefix in response.get("CommonPrefixes", []):
            project_type = prefix["Prefix"].replace("lessons-learned/", "").rstrip("/")

            # Try to get lessons file
            try:
                lessons_key = f"lessons-learned/{project_type}/lessons.json"
                obj = s3.get_object(Bucket=bucket_name, Key=lessons_key)
                data = json.loads(obj["Body"].read())
                lesson_count = len(data.get("lessons", []))

                # Extract unique project names from lessons
                projects = list(
                    set(
                        lesson.get("projectName", "")
                        for lesson in data.get("lessons", [])
                        if lesson.get("projectName")
                    )
                )

                project_types.append(
                    {"type": project_type, "count": lesson_count, "projects": projects}
                )
            except:
                # No lessons file yet
                project_types.append({"type": project_type, "count": 0, "projects": []})

        project_types.sort(key=lambda x: (-x["count"], x["type"]))

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"projectTypes": project_types}),
        }

    except Exception as e:
        print(f"Error getting project types: {str(e)}")
        raise


def get_lessons_by_type(project_type):
    """Get aggregated lessons for a specific project type"""
    try:
        bucket_name = os.environ.get("BUCKET_NAME")
        lessons_key = f"lessons-learned/{project_type}/lessons.json"

        try:
            response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
            data = json.loads(response["Body"].read())

            return {
                "statusCode": 200,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps(data),
            }
        except s3.exceptions.NoSuchKey:
            return {
                "statusCode": 200,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps(
                    {"projectType": project_type, "lastUpdated": "", "lessons": []}
                ),
            }

    except Exception as e:
        print(f"Error getting lessons by type: {str(e)}")
        raise


def get_master_conflicts(project_type):
    """Get pending conflicts for a project type's master lessons"""
    try:
        bucket_name = os.environ["BUCKET_NAME"]
        conflicts_key = f"lessons-learned/{project_type}/lessons-conflicts.json"

        try:
            response = s3.get_object(Bucket=bucket_name, Key=conflicts_key)
            conflicts = json.loads(response["Body"].read().decode("utf-8"))
            # Filter only pending conflicts
            pending = [c for c in conflicts if c.get("status") == "pending"]
        except s3.exceptions.NoSuchKey:
            pending = []

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"conflicts": pending}),
        }

    except Exception as e:
        print(f"Error getting master conflicts: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def resolve_master_conflict(event, conflict_id):
    """Resolve a master lesson conflict with user decision"""
    try:
        print(f"Received conflict_id: {conflict_id}")
        print(f"Event pathParameters: {event.get('pathParameters')}")

        body = json.loads(event.get("body", "{}"))
        decision = body.get(
            "decision"
        )  # "keep_new", "keep_existing", "keep_both", "delete_both"
        project_type = body.get("project_type")

        print(f"Decision: {decision}, Project Type: {project_type}")

        if not project_type:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "project_type required"}),
            }

        bucket_name = os.environ["BUCKET_NAME"]
        conflicts_key = f"lessons-learned/{project_type}/lessons-conflicts.json"
        lessons_key = f"lessons-learned/{project_type}/lessons.json"

        # Load conflicts
        response = s3.get_object(Bucket=bucket_name, Key=conflicts_key)
        conflicts = json.loads(response["Body"].read().decode("utf-8"))

        print(f"Loaded {len(conflicts)} conflicts")
        print(f"Conflict IDs: {[c.get('id') for c in conflicts[:3]]}")

        # Find the conflict
        conflict = next((c for c in conflicts if c["id"] == conflict_id), None)
        if not conflict:
            print(f"Conflict {conflict_id} not found in conflicts")
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Conflict not found"}),
            }

        # Load lessons
        lessons_response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
        lessons_data = json.loads(lessons_response["Body"].read().decode("utf-8"))
        lessons = lessons_data.get("lessons", [])

        # Apply decision
        new_id = conflict["new_lesson"]["id"]
        existing_id = conflict["existing_lesson"]["id"]

        if decision == "keep_new":
            lessons = [l for l in lessons if l["id"] != existing_id]
        elif decision == "keep_existing":
            lessons = [l for l in lessons if l["id"] != new_id]
        elif decision == "delete_both":
            lessons = [l for l in lessons if l["id"] not in [new_id, existing_id]]
        # keep_both: do nothing

        # Save updated lessons
        lessons_data["lessons"] = lessons
        s3.put_object(
            Bucket=bucket_name,
            Key=lessons_key,
            Body=json.dumps(lessons_data, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        # Mark conflict as resolved
        for c in conflicts:
            if c["id"] == conflict_id:
                c["status"] = "resolved"
                c["decision"] = decision

        s3.put_object(
            Bucket=bucket_name,
            Key=conflicts_key,
            Body=json.dumps(conflicts, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        # Trigger vector sync for updated lessons
        try:
            trigger_type_lessons_ingestion(bucket_name, project_type)
            print(
                f"Triggered sync for {project_type} lessons after conflict resolution"
            )
        except Exception as e:
            print(f"Warning: Failed to trigger sync: {e}")

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Conflict resolved"}),
        }

    except Exception as e:
        print(f"Error resolving master conflict: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }

    except Exception as e:
        print(f"Error resolving master conflict: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
