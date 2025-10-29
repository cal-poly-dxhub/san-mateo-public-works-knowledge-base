import json
import os
from datetime import datetime
from decimal import Decimal

import boto3

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
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, X-Api-Key",
                },
                "body": "",
            }

        if "/metadata" in path and method == "PUT":
            project_name = event["pathParameters"]["project_name"]
            body = json.loads(event.get("body", "{}"))
            return update_metadata(project_name, body)

        elif "/checklist" in path and method == "GET":
            project_name = event["pathParameters"]["project_name"]
            return get_checklist(project_name)

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


def get_checklist(project_name):
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
                "headers": {"Access-Control-Allow-Origin": "*"},
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

        # Get all tasks for this project
        response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
            ExpressionAttributeValues={":pid": project_name, ":task": "task#"},
        )

        tasks = []
        completed_count = 0

        for item in response["Items"]:
            task_data = item.get("taskData", {})
            completed_date = item.get("completed_date") or task_data.get(
                "actual_date"
            )

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
            "headers": {"Access-Control-Allow-Origin": "*"},
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

        # Get project_id
        response = table.scan(
            FilterExpression="projectName = :pname",
            ExpressionAttributeValues={":pname": project_name},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
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
                "headers": {"Access-Control-Allow-Origin": "*"},
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
            "headers": {"Access-Control-Allow-Origin": "*"},
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


def update_metadata(project_name, metadata):
    """Update project metadata"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        response = table.scan(
            FilterExpression="projectName = :pname",
            ExpressionAttributeValues={":pname": project_name},
        )

        if not response["Items"]:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
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
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Metadata updated"}),
        }

    except Exception as e:
        print(f"Error updating metadata: {str(e)}")
        raise
