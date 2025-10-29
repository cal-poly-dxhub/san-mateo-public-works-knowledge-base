import json
import os

import boto3

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

        elif "/by-type/" in path and method == "GET":
            project_type = event["pathParameters"]["project_type"]
            return get_lessons_by_type(project_type)

        elif "/conflicts/resolve/" in path and method == "POST":
            conflict_id = event["pathParameters"]["conflict_id"]
            return resolve_master_conflict(event, conflict_id)

        elif "/conflicts/by-type/" in path and method == "GET":
            project_type = event["pathParameters"]["project_type"]
            return get_master_conflicts(project_type)

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
            Bucket=bucket_name,
            Prefix="lessons-learned/",
            Delimiter="/"
        )
        
        project_types = []
        
        # Get each project type folder
        for prefix in response.get("CommonPrefixes", []):
            project_type = prefix["Prefix"].replace("lessons-learned/", "").rstrip("/")
            
            # Try to get master lessons file
            try:
                master_key = f"lessons-learned/{project_type}/master-lessons.json"
                obj = s3.get_object(Bucket=bucket_name, Key=master_key)
                data = json.loads(obj["Body"].read())
                lesson_count = len(data.get("lessons", []))
                
                project_types.append({
                    "type": project_type,
                    "count": lesson_count
                })
            except:
                # No master file yet
                project_types.append({
                    "type": project_type,
                    "count": 0
                })
        
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
        master_key = f"lessons-learned/{project_type}/master-lessons.json"
        
        try:
            response = s3.get_object(Bucket=bucket_name, Key=master_key)
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
                "body": json.dumps({
                    "projectType": project_type,
                    "lastUpdated": "",
                    "lessons": []
                }),
            }

    except Exception as e:
        print(f"Error getting lessons by type: {str(e)}")
        raise



def get_master_conflicts(project_type):
    """Get pending conflicts for a project type's master lessons"""
    try:
        bucket_name = os.environ["BUCKET_NAME"]
        conflicts_key = f"lessons-learned/{project_type}/master-lessons-conflicts.json"

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
        body = json.loads(event.get("body", "{}"))
        keep_new = body.get("keepNew", True)

        bucket_name = os.environ["BUCKET_NAME"]

        # Find which project type this conflict belongs to
        # We need to search through all project types
        project_types = ["Reconstruction", "Resurface", "Slurry Seal", "Drainage", "Utilities", "Other"]
        
        conflict = None
        project_type = None
        conflicts_key = None
        
        for pt in project_types:
            try:
                key = f"lessons-learned/{pt}/master-lessons-conflicts.json"
                response = s3.get_object(Bucket=bucket_name, Key=key)
                conflicts = json.loads(response["Body"].read().decode("utf-8"))
                
                found = next((c for c in conflicts if c["id"] == conflict_id), None)
                if found:
                    conflict = found
                    project_type = pt
                    conflicts_key = key
                    break
            except s3.exceptions.NoSuchKey:
                continue

        if not conflict:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Conflict not found"}),
            }

        # Load master lessons
        lessons_key = f"lessons-learned/{project_type}/master-lessons.json"
        lessons_response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
        lessons = json.loads(lessons_response["Body"].read().decode("utf-8"))

        # Apply decision
        new_id = conflict["new_lesson"]["id"]
        existing_id = conflict["existing_lesson"]["id"]

        if keep_new:
            # Remove existing, keep new
            lessons = [l for l in lessons if l["id"] != existing_id]
        else:
            # Remove new, keep existing
            lessons = [l for l in lessons if l["id"] != new_id]

        # Save updated lessons
        s3.put_object(
            Bucket=bucket_name,
            Key=lessons_key,
            Body=json.dumps(lessons, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        # Mark conflict as resolved
        response = s3.get_object(Bucket=bucket_name, Key=conflicts_key)
        all_conflicts = json.loads(response["Body"].read().decode("utf-8"))
        
        for c in all_conflicts:
            if c["id"] == conflict_id:
                c["status"] = "resolved"
                c["decision"] = "keep_new" if keep_new else "keep_existing"

        s3.put_object(
            Bucket=bucket_name,
            Key=conflicts_key,
            Body=json.dumps(all_conflicts, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

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
