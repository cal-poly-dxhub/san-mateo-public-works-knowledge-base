import json
import os
import sys
from datetime import datetime
from decimal import Decimal

import boto3

from db_utils import query_all_items

dynamodb = boto3.resource("dynamodb")


def decimal_to_number(obj):
    """Convert Decimal to int or float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def handler(event, context):
    """Handle checklist requests"""
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, PUT, POST, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
                "body": "",
            }

        # Check /checklist/task paths BEFORE /checklist to avoid incorrect matching
        if "/checklist/task" in path and method == "POST":
            project_name = event["pathParameters"]["project_name"]
            body = json.loads(event.get("body", "{}"))
            return add_task(project_name, body)

        elif "/checklist/task" in path and method == "DELETE":
            project_name = event["pathParameters"]["project_name"]
            body = json.loads(event.get("body", "{}"))
            return delete_task(project_name, body.get("task_id"))

        elif "/checklist/task" in path and method == "PUT":
            project_name = event["pathParameters"]["project_name"]
            body = json.loads(event.get("body", "{}"))
            return edit_task(project_name, body)

        elif "/metadata" in path and method == "PUT":
            project_name = event["pathParameters"]["project_name"]
            body = json.loads(event.get("body", "{}"))
            return update_metadata(project_name, body)

        elif "/checklist" in path and method == "GET":
            project_name = event["pathParameters"]["project_name"]
            query_params = event.get("queryStringParameters") or {}
            checklist_type = query_params.get("type", "design")
            return get_checklist(project_name, checklist_type)

        elif "/checklist" in path and method == "PUT":
            project_name = event["pathParameters"]["project_name"]
            body = json.loads(event.get("body", "{}"))
            task_id = body.get("task_id")
            completed_date = body.get("completed_date")
            projected_date = body.get("projected_date")
            actual_date = body.get("actual_date")
            return update_task(
                project_name,
                task_id,
                completed_date,
                projected_date,
                actual_date,
            )

        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": "Not found"}),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"error": str(e)}),
        }


def get_checklist(project_name, checklist_type="design"):
    """Get all tasks for a project from DynamoDB"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Get project config directly
        config_response = table.get_item(
            Key={"project_id": project_name, "item_id": "config"}
        )

        if "Item" not in config_response:
            return {
                "statusCode": 200,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {
                        "tasks": [],
                        "progress": {
                            "total": 0,
                            "completed": 0,
                            "percentage": 0,
                        },
                    }
                ),
            }

        config_item = config_response["Item"]

        # Extract metadata from config
        project_config = config_item.get("config", {})
        metadata = project_config.get(
            "metadata",
            {
                "date": "",
                "project": "",
                "work_authorization": "",
                "office_plans_file_no": "",
                "design_engineer": "",
                "survey_books": "",
                "project_manager": "",
            },
        )

        # Get all tasks for this project filtered by checklist type
        task_prefix = f"task#{checklist_type}#"
        response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
            ExpressionAttributeValues={":pid": project_name, ":task": task_prefix},
        )

        tasks = []
        completed_count = 0

        for item in response["Items"]:
            task_data = item.get("taskData", {})
            completed_date = item.get("completed_date") or task_data.get("actual_date")

            task = {
                "task_id": item["item_id"],
                "checklist_task_id": task_data.get("task_id", ""),
                "description": task_data.get("description", ""),
                "projected_date": task_data.get("projected_date", ""),
                "actual_date": completed_date or "",
                "required": task_data.get("required", True),
                "notes": task_data.get("notes", ""),
                "status": "completed"
                if completed_date
                else item.get("status", "not_started"),
            }

            if completed_date:
                completed_count += 1

            tasks.append(task)

        # Calculate progress
        total = len(tasks)
        percentage = int((completed_count / total * 100)) if total > 0 else 0

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps(
                {
                    "tasks": tasks,
                    "metadata": metadata,
                    "progress": {
                        "total": total,
                        "completed": completed_count,
                        "percentage": percentage,
                    },
                }
            ),
        }

    except Exception as e:
        print(f"Error getting checklist: {str(e)}")
        raise


def update_task(
    project_name, task_id, completed_date, projected_date=None, actual_date=None
):
    """Update task completion status and dates"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Get project_id using GSI
        response = table.query(
            IndexName="projectName-index",
            KeyConditionExpression="projectName = :pname AND item_id = :config",
            ExpressionAttributeValues={":pname": project_name, ":config": "config"},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Project not found"}),
            }

        project_id = response["Items"][0]["project_id"]

        # Get current task to update taskData
        task_response = table.get_item(
            Key={"project_id": project_id, "item_id": task_id}
        )

        if "Item" not in task_response:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Task not found"}),
            }

        task_data = task_response["Item"].get("taskData", {})

        # Update taskData fields only if valid dates provided
        if projected_date is not None and is_valid_date(projected_date):
            task_data["projected_date"] = projected_date
        if actual_date is not None:
            if is_valid_date(actual_date):
                task_data["actual_date"] = actual_date
            elif actual_date == "":
                task_data["actual_date"] = ""

        # Build update expression
        update_expr = "SET #status = :status, taskData = :taskData"
        expr_values = {
            ":status": "completed"
            if (completed_date or actual_date)
            else "not_started",
            ":taskData": task_data,
        }
        expr_names = {"#status": "status"}

        if completed_date or actual_date:
            update_expr += ", completed_date = :date"
            expr_values[":date"] = completed_date or actual_date
        elif "completed_date" in task_response["Item"]:
            update_expr += " REMOVE completed_date"

        table.update_item(
            Key={"project_id": project_id, "item_id": task_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"message": "Task updated"}),
        }

    except Exception as e:
        print(f"Error updating task: {str(e)}")
        raise


def is_valid_date(date_str):
    """Check if string is valid YYYY-MM-DD date"""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False


def is_valid_task_id(task_id):
    """Check if task ID contains only valid characters"""
    if not task_id:
        return False
    # Allow alphanumeric, dashes, underscores, and periods
    import re

    return bool(re.match(r"^[a-zA-Z0-9._-]+$", task_id))


def update_metadata(project_name, metadata):
    """Update project metadata"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        response = table.query(
            IndexName="projectName-index",
            KeyConditionExpression="projectName = :pname AND item_id = :config",
            ExpressionAttributeValues={":pname": project_name, ":config": "config"},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Project not found"}),
            }

        project_id = response["Items"][0]["project_id"]
        config = response["Items"][0].get("config", {})
        config["metadata"] = metadata

        table.update_item(
            Key={"project_id": project_id, "item_id": "config"},
            UpdateExpression="SET config = :config",
            ExpressionAttributeValues={":config": config},
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"message": "Metadata updated"}),
        }

    except Exception as e:
        print(f"Error updating metadata: {str(e)}")
        raise


def add_task(project_name, task_data):
    """Add a new task to the checklist"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        response = table.query(
            IndexName="projectName-index",
            KeyConditionExpression="projectName = :pname AND item_id = :config",
            ExpressionAttributeValues={":pname": project_name, ":config": "config"},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Project not found"}),
            }

        project_id = response["Items"][0]["project_id"]
        task_number = task_data.get("checklist_task_id", "").strip()
        checklist_type = task_data.get("checklist_type", "design")

        if not task_number:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Task ID is required"}),
            }

        if not is_valid_task_id(task_number):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {
                        "error": "Task ID must contain only letters, numbers, dashes, underscores, and periods"
                    }
                ),
            }

        task_id = f"task#{checklist_type}#{task_number}"

        existing_task = table.get_item(
            Key={"project_id": project_id, "item_id": task_id}
        )

        if "Item" in existing_task:
            return {
                "statusCode": 409,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {"error": f"Task ID '{task_number}' already exists"}
                ),
            }

        projected_date = task_data.get("projected_date", "")
        if projected_date and not is_valid_date(projected_date):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {"error": "Projected date must be in YYYY-MM-DD format"}
                ),
            }

        table.put_item(
            Item={
                "project_id": project_id,
                "item_id": task_id,
                "taskData": {
                    "task_id": task_number,
                    "description": task_data.get("description", "").strip(),
                    "projected_date": projected_date,
                    "required": task_data.get("required", True),
                    "notes": task_data.get("notes", "").strip(),
                },
                "status": "not_started",
                "createdDate": datetime.utcnow().isoformat(),
            }
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"message": "Task added", "task_id": task_id}),
        }
    except Exception as e:
        print(f"Error adding task: {str(e)}")
        raise


def delete_task(project_name, task_id):
    """Delete a task from the checklist"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        response = table.query(
            IndexName="projectName-index",
            KeyConditionExpression="projectName = :pname AND item_id = :config",
            ExpressionAttributeValues={":pname": project_name, ":config": "config"},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Project not found"}),
            }

        project_id = response["Items"][0]["project_id"]

        # Validate task exists
        existing = table.get_item(Key={"project_id": project_id, "item_id": task_id})

        if "Item" not in existing:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Task not found"}),
            }

        table.delete_item(Key={"project_id": project_id, "item_id": task_id})

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"message": "Task deleted"}),
        }
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        raise


def edit_task(project_name, task_data):
    """Edit task details"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        response = table.query(
            IndexName="projectName-index",
            KeyConditionExpression="projectName = :pname AND item_id = :config",
            ExpressionAttributeValues={":pname": project_name, ":config": "config"},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Project not found"}),
            }

        project_id = response["Items"][0]["project_id"]
        task_id = task_data.get("task_id")
        new_task_number = task_data.get("checklist_task_id", "").strip()
        checklist_type = task_data.get("checklist_type", "design")

        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Task ID is required"}),
            }

        existing_task = table.get_item(
            Key={"project_id": project_id, "item_id": task_id}
        )

        if "Item" not in existing_task:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Task not found"}),
            }

        if not new_task_number:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps({"error": "Task ID is required"}),
            }

        if not is_valid_task_id(new_task_number):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {
                        "error": "Task ID must contain only letters, numbers, dashes, underscores, and periods"
                    }
                ),
            }

        new_task_id = f"task#{checklist_type}#{new_task_number}"

        # Check if changing to a different task ID that already exists
        if new_task_id != task_id:
            duplicate_check = table.get_item(
                Key={"project_id": project_id, "item_id": new_task_id}
            )
            if "Item" in duplicate_check:
                return {
                    "statusCode": 409,
                    "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                    "body": json.dumps(
                        {"error": f"Task ID '{new_task_number}' already exists"}
                    ),
                }

        # Validate dates
        projected_date = task_data.get("projected_date", "")
        actual_date = task_data.get("actual_date", "")

        if projected_date and not is_valid_date(projected_date):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {"error": "Projected date must be in YYYY-MM-DD format"}
                ),
            }

        if actual_date and not is_valid_date(actual_date):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
                "body": json.dumps(
                    {"error": "Actual date must be in YYYY-MM-DD format"}
                ),
            }

        # If task ID changed, delete old and create new
        if new_task_id != task_id:
            old_task = existing_task["Item"]

            table.delete_item(Key={"project_id": project_id, "item_id": task_id})

            table.put_item(
                Item={
                    "project_id": project_id,
                    "item_id": new_task_id,
                    "taskData": {
                        "task_id": new_task_number,
                        "description": task_data.get("description", "").strip(),
                        "projected_date": projected_date,
                        "required": task_data.get("required", True),
                        "notes": task_data.get("notes", "").strip(),
                    },
                    "status": old_task.get("status", "not_started"),
                    "completed_date": old_task.get("completed_date", ""),
                    "createdDate": old_task.get(
                        "createdDate", datetime.utcnow().isoformat()
                    ),
                }
            )
        else:
            # Just update the task data
            table.update_item(
                Key={"project_id": project_id, "item_id": task_id},
                UpdateExpression="SET taskData = :taskData",
                ExpressionAttributeValues={
                    ":taskData": {
                        "task_id": new_task_number,
                        "description": task_data.get("description", "").strip(),
                        "projected_date": projected_date,
                        "required": task_data.get("required", True),
                        "notes": task_data.get("notes", "").strip(),
                    }
                },
            )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"), "Access-Control-Allow-Credentials": "true"},
            "body": json.dumps({"message": "Task updated", "task_id": new_task_id}),
        }
    except Exception as e:
        print(f"Error editing task: {str(e)}")
        raise
