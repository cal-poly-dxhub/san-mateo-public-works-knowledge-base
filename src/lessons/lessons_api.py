import base64
import json
import os
from datetime import datetime

import boto3

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")


def handler(event, context):
    """Handle lessons learned document upload and extraction"""

    path = event.get("path", "")
    method = event.get("httpMethod", "")

    if method == "POST" and "/documents" in path:
        return upload_and_extract(event)
    elif method == "GET" and "/lessons-learned" in path:
        return get_lessons(event)

    return {
        "statusCode": 404,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": "Not found"}),
    }


def upload_and_extract(event):
    """Upload document and extract lessons learned"""
    try:
        body = json.loads(event.get("body", "{}"))
        project_name = event["pathParameters"]["project_name"]

        file_content = body.get("content")
        filename = body.get("filename")
        extract_lessons = body.get("extract_lessons", False)

        if not file_content or not filename:
            return error_response("Missing file content or filename")

        # Decode base64 content if needed
        try:
            content_text = base64.b64decode(file_content).decode("utf-8")
        except:
            content_text = file_content

        bucket_name = os.environ["BUCKET_NAME"]
        project_type = body.get("project_type", "other")

        # Upload document to S3
        doc_key = f"projects/{project_name}/documents/{filename}"
        s3.put_object(
            Bucket=bucket_name, Key=doc_key, Body=content_text.encode("utf-8")
        )

        if extract_lessons:
            # Trigger async processing
            lambda_client = boto3.client('lambda')
            lambda_client.invoke(
                FunctionName=os.environ.get('ASYNC_LESSONS_PROCESSOR_NAME'),
                InvocationType='Event',  # Async
                Payload=json.dumps({
                    'project_name': project_name,
                    'project_type': project_type,
                    'content': content_text,
                    'filename': filename
                })
            )
            
            return {
                "statusCode": 202,  # Accepted
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": "Document uploaded successfully. Lessons extraction in progress.",
                    "status": "processing"
                })
            }

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Document uploaded successfully"}),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e))


def extract_lessons_from_document(content, project_name, date):
    """Extract lessons learned from document using LLM"""

    prompt = f"""Extract lessons learned from this document for project "{project_name}".
Date: {date}

Return ONLY a JSON array of lessons in this exact format:
[
  {{
    "title": "Brief title of the lesson",
    "dateEntered": "{date}T00:00:00Z",
    "lesson": "The core lesson learned",
    "details": "Full description and context of what happened",
    "impact": "What this lesson affected (cost, timeline, quality, etc.)",
    "recommendation": "What to do differently in future projects",
    "severity": "Low|Medium|High"
  }}
]

Extract 3-5 key lessons. Focus on actionable insights for future projects.

Document Content:
{content}

Return only the JSON array, no other text."""

    try:
        response = bedrock.invoke_model(
            modelId=os.environ.get(
                "LESSONS_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        response_body = json.loads(response["body"].read())
        lessons_text = response_body["content"][0]["text"]

        # Extract JSON from response
        start = lessons_text.find("[")
        end = lessons_text.rfind("]") + 1
        if start >= 0 and end > start:
            lessons_array = json.loads(lessons_text[start:end])
            return lessons_array

        return []

    except Exception as e:
        print(f"Error extracting lessons: {str(e)}")
        return [
            {
                "title": "Document uploaded",
                "dateEntered": f"{date}T00:00:00Z",
                "lesson": "Automatic extraction failed",
                "details": "Document was uploaded but lesson extraction encountered an error",
                "impact": "No automated insights generated",
                "recommendation": "Review document manually for lessons learned",
                "severity": "Low",
            }
        ]


def append_to_project_lessons(bucket_name, project_name, new_lessons):
    """Merge lessons with project's lessons-learned.json file using LLM"""

    lessons_key = f"projects/{project_name}/lessons-learned.json"

    try:
        # Get existing lessons
        response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
        existing_data = json.loads(response["Body"].read().decode("utf-8"))
    except:
        existing_data = {
            "projectName": project_name,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "lessons": [],
        }

    # Merge using LLM
    merged_data = merge_project_lessons_json(
        existing_data, new_lessons, project_name
    )

    s3.put_object(
        Bucket=bucket_name,
        Key=lessons_key,
        Body=json.dumps(merged_data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def merge_project_lessons_json(existing_data, new_lessons, project_name):
    """Merge new lessons with existing project lessons JSON"""

    existing_lessons = existing_data.get("lessons", [])

    prompt = f"""Merge these new lessons with existing lessons for project "{project_name}".

Rules:
1. Deduplicate similar lessons (keep most comprehensive version)
2. If lessons contradict, keep the most recent one
3. Order by severity: High, Medium, Low
4. Preserve all required fields

New Lessons:
{json.dumps(new_lessons, indent=2)}

Existing Lessons:
{json.dumps(existing_lessons, indent=2)}

Return ONLY a JSON array of the merged lessons, no other text."""

    try:
        response = bedrock.invoke_model(
            modelId=os.environ.get(
                "LESSONS_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        response_body = json.loads(response["body"].read())
        merged_text = response_body["content"][0]["text"]

        # Extract JSON from response
        start = merged_text.find("[")
        end = merged_text.rfind("]") + 1
        if start >= 0 and end > start:
            merged_lessons = json.loads(merged_text[start:end])
        else:
            merged_lessons = existing_lessons + new_lessons

        return {
            "projectName": project_name,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "lessons": merged_lessons,
        }

    except Exception as e:
        print(f"Error merging project lessons: {str(e)}")
        # Fallback: just append
        return {
            "projectName": project_name,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "lessons": existing_lessons + new_lessons,
        }


def update_master_lessons(bucket_name, project_type, project_name, new_lessons):
    """Update master lessons learned file with LLM merge"""

    # Get current master file
    master_folder = f"lessons-learned/{project_type}"

    try:
        # List existing master files
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=master_folder)

        if "Contents" in response and response["Contents"]:
            # Get most recent master file
            latest_file = sorted(response["Contents"], key=lambda x: x["Key"])[
                -1
            ]
            master_response = s3.get_object(
                Bucket=bucket_name, Key=latest_file["Key"]
            )
            existing_master = json.loads(
                master_response["Body"].read().decode("utf-8")
            )
        else:
            existing_master = {
                "projectType": project_type.title(),
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "lessons": [],
            }
    except:
        existing_master = {
            "projectType": project_type.title(),
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "lessons": [],
        }

    # Add project name to new lessons
    new_lessons_with_project = []
    for lesson in new_lessons:
        lesson_with_project = lesson.copy()
        lesson_with_project["projectName"] = project_name
        new_lessons_with_project.append(lesson_with_project)

    # Merge using LLM
    merged_lessons = merge_master_lessons_json(
        existing_master, new_lessons_with_project, project_type
    )

    # Save new versioned master file
    today = datetime.now().strftime("%Y-%m-%d")
    new_master_key = f"{master_folder}/master-{today}.json"

    s3.put_object(
        Bucket=bucket_name,
        Key=new_master_key,
        Body=json.dumps(merged_lessons, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def merge_master_lessons_json(existing_master, new_lessons, project_type):
    """Merge new lessons with existing master using LLM"""

    existing_lessons = existing_master.get("lessons", [])

    prompt = f"""Merge these new lessons with the existing master lessons for {project_type} projects.

Rules:
1. Deduplicate similar lessons (keep most comprehensive version)
2. If lessons contradict, keep the most recent one
3. Order by severity: High, Medium, Low
4. Each lesson must include projectName field
5. Preserve all required fields

New Lessons:
{json.dumps(new_lessons, indent=2)}

Existing Master Lessons:
{json.dumps(existing_lessons, indent=2)}

Return ONLY a JSON array of the merged lessons, no other text."""

    try:
        response = bedrock.invoke_model(
            modelId=os.environ.get(
                "LESSONS_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        response_body = json.loads(response["body"].read())
        merged_text = response_body["content"][0]["text"]

        # Extract JSON from response
        start = merged_text.find("[")
        end = merged_text.rfind("]") + 1
        if start >= 0 and end > start:
            merged_lessons = json.loads(merged_text[start:end])
        else:
            merged_lessons = existing_lessons + new_lessons

        return {
            "projectType": project_type.title(),
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "lessons": merged_lessons,
        }

    except Exception as e:
        print(f"Error merging master lessons: {str(e)}")
        # Fallback: just append
        return {
            "projectType": project_type.title(),
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "lessons": existing_lessons + new_lessons,
        }


def get_lessons(event):
    """Get project lessons learned"""
    try:
        project_name = event["pathParameters"]["project_name"]
        bucket_name = os.environ["BUCKET_NAME"]
        lessons_key = f"projects/{project_name}/lessons-learned.json"

        try:
            response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
            lessons_data = json.loads(response["Body"].read().decode("utf-8"))
        except:
            lessons_data = {
                "projectName": project_name,
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "lessons": [],
            }

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(lessons_data),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e))


def error_response(message):
    return {
        "statusCode": 500,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message}),
    }
