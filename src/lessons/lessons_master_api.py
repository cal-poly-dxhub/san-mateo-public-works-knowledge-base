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
