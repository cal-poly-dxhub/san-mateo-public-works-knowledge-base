import json
import os
import uuid
from datetime import datetime

import boto3

bedrock = boto3.client("bedrock-runtime")
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Load design checklist template
CHECKLIST_PATH = os.path.join(
    os.path.dirname(__file__), "design_checklist.json"
)
with open(CHECKLIST_PATH, "r") as f:
    DESIGN_CHECKLIST = json.load(f)


def handler(event, context):
    """Handle project setup wizard requests"""
    try:
        body = json.loads(event.get("body", "{}"))

        project_name = body.get("projectName")
        project_type = body.get("projectType")
        location = body.get("location")
        area_size = body.get("areaSize")
        special_conditions = body.get("specialConditions", [])

        # Load tasks from design checklist
        project_config = {
            "metadata": DESIGN_CHECKLIST["document"]["metadata"].copy(),
            "tasks": [],
        }

        # Add project creation fields to metadata
        project_config["metadata"].update(
            {
                "project_type": project_type,
                "location": location,
                "area_size": area_size,
                "special_conditions": special_conditions,
            }
        )

        # Convert checklist items to tasks
        for item in DESIGN_CHECKLIST["document"]["checklist_items"]:
            for task in item["tasks"]:
                project_config["tasks"].append(
                    {
                        "task_id": task["task_id"],
                        "description": task["description"],
                        "required": task.get("required", True),
                        "projected_date": task.get("projected_date", ""),
                        "actual_date": task.get("actual_date", ""),
                        "notes": task.get("notes", ""),
                    }
                )

        # Use project name as project_id (slugified)
        project_id = project_name.lower().replace(" ", "-")
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Check if project already exists
        try:
            existing = table.get_item(
                Key={"project_id": project_id, "item_id": "config"}
            )
            if "Item" in existing:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type",
                    },
                    "body": json.dumps(
                        {"error": f'Project "{project_name}" already exists'}
                    ),
                }
        except:
            pass  # Project doesn't exist, continue

        table.put_item(
            Item={
                "project_id": project_id,
                "item_id": "config",
                "projectName": project_name,
                "projectType": project_type,
                "location": location,
                "areaSize": area_size,
                "specialConditions": special_conditions,
                "config": project_config,
                "status": "active",
                "createdDate": datetime.utcnow().isoformat(),
                "lastUpdated": datetime.utcnow().isoformat(),
            }
        )

        # Create S3 folder structure
        bucket_name = os.environ.get("BUCKET_NAME")
        if bucket_name:
            folders = [
                f"projects/{project_name}/",
                f"projects/{project_name}/documents/",
            ]
            for folder in folders:
                s3.put_object(Bucket=bucket_name, Key=folder)

            # Create initial lessons-learned.md file
            lessons_content = f"# Lessons Learned - {project_name}\n\nNo lessons learned yet. Upload documents with 'Extract Lessons Learned' enabled to populate this file.\n"
            s3.put_object(
                Bucket=bucket_name,
                Key=f"projects/{project_name}/lessons-learned.md",
                Body=lessons_content.encode("utf-8"),
                ContentType="text/markdown",
            )

        # Store tasks separately for easier querying
        for task in project_config.get("tasks", []):
            task_id = str(uuid.uuid4())
            table.put_item(
                Item={
                    "project_id": project_id,
                    "item_id": f"task#{task_id}",
                    "taskData": task,
                    "status": "not_started",
                    "createdDate": datetime.utcnow().isoformat(),
                }
            )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps(
                {"projectId": project_id, "config": project_config}
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps({"error": str(e)}),
        }


def generate_project_config(
    project_type, location, area_size, special_conditions
):
    """Generate project configuration using AI"""

    prompt = f"""Based on the following project information, generate a complete project configuration.

Project Information:
- Project Type: {project_type}
- Location: {location}
- Work Area Size: {area_size} acres
- Special Conditions: {", ".join(special_conditions) if special_conditions else "None"}

Generate a comprehensive project setup including tasks, stakeholders, permits, timeline, and budget estimate.

Return JSON in this format:
{{
  "projectConfig": {{
    "tasks": [{{"phase": "Survey", "task": "Initial site survey", "description": "Details", "estimatedDays": 5, "dependencies": [], "required": true}}],
    "stakeholders": [{{"name": "PG&E", "type": "utility", "contactReason": "Gas line coordination", "timing": "At 60% design"}}],
    "permits": [{{"name": "Encroachment Permit", "agency": "County", "estimatedTime": "2-3 weeks", "required": true}}],
    "timeline": {{"totalEstimatedDays": 365, "milestones": [{{"name": "Design Complete", "estimatedDay": 90}}]}},
    "budgetEstimate": {{"low": 100000, "high": 150000, "basis": "Similar projects"}}
  }}
}}"""

    try:
        response = bedrock.invoke_model(
            modelId=os.environ["PROJECT_SETUP_MODEL_ID"],
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        response_body = json.loads(response["body"].read())
        content = response_body["content"][0]["text"]

        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])["projectConfig"]

        return generate_default_config(project_type)

    except Exception as e:
        print(f"Error generating config: {str(e)}")
        return generate_default_config(project_type)


def generate_default_config(project_type):
    """Generate a basic default configuration"""
    return {
        "tasks": [
            {
                "phase": "Survey",
                "task": "Initial site survey",
                "description": "Conduct field survey",
                "estimatedDays": 5,
                "dependencies": [],
                "required": True,
            },
            {
                "phase": "Design",
                "task": "30% design",
                "description": "Preliminary design",
                "estimatedDays": 20,
                "dependencies": ["Initial site survey"],
                "required": True,
            },
        ],
        "stakeholders": [
            {
                "name": "Local utilities",
                "type": "utility",
                "contactReason": "Coordination",
                "timing": "At 60% design",
            }
        ],
        "permits": [
            {
                "name": "Encroachment Permit",
                "agency": "County",
                "estimatedTime": "2-3 weeks",
                "required": True,
            }
        ],
        "timeline": {
            "totalEstimatedDays": 365,
            "milestones": [{"name": "Design Complete", "estimatedDay": 90}],
        },
        "budgetEstimate": {
            "low": 100000,
            "high": 200000,
            "basis": "Typical range for project type",
        },
    }
