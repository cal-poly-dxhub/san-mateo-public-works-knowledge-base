import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def handler(event, context):
    """Handle task management operations"""
    try:
        http_method = event.get("httpMethod")
        body = json.loads(event.get("body", "{}")) if event.get("body") else {}
        path_params = event.get("pathParameters", {})
        project_name = path_params.get("project_name")
        task_id = path_params.get("task_id")

        if http_method == "GET":
            return get_tasks(project_name)
        elif http_method == "PUT":
            return update_task(project_name, task_id, body)
        elif http_method == "POST":
            return create_task(project_name, body)
        else:
            return {
                "statusCode": 405,
                "body": json.dumps({"error": "Method not allowed"}),
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_tasks(project_name):
    """Get all tasks for a project"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Use project name directly as project_id
        project_id = project_name.lower().replace(" ", "-")

        response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :prefix)",
            ExpressionAttributeValues={":pid": project_id, ":prefix": "task#"},
        )

        tasks = response.get("Items", [])

        # Calculate progress
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
        progress = (
            round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "tasks": tasks,
                    "progress": progress,
                    "totalTasks": total_tasks,
                    "completedTasks": completed_tasks,
                },
                default=decimal_default,
            ),
        }

    except Exception as e:
        print(f"Error in get_tasks: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def update_task(project_name, task_id, body):
    """Update task status"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Use project name directly as project_id
        project_id = project_name.lower().replace(" ", "-")

        # Build update expression
        update_expr = "SET "
        expr_values = {}
        expr_names = {}

        for key, value in body.items():
            safe_key = f"#{key}"
            value_key = f":{key}"
            update_expr += f"{safe_key} = {value_key}, "
            expr_values[value_key] = value
            expr_names[safe_key] = key

        update_expr += "#lastUpdated = :lastUpdated"
        expr_values[":lastUpdated"] = datetime.utcnow().isoformat()
        expr_names["#lastUpdated"] = "lastUpdated"

        table.update_item(
            Key={"project_id": project_id, "item_id": f"task#{task_id}"},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Task updated successfully"}),
        }

    except Exception as e:
        print(f"Error in update_task: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def create_task(project_name, body):
    """Create a new task"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        import uuid

        task_id = str(uuid.uuid4())

        item = {
            "project_id": project_name,
            "item_id": f"task#{task_id}",
            "status": "not_started",
            "createdDate": datetime.utcnow().isoformat(),
            "lastUpdated": datetime.utcnow().isoformat(),
        }
        item.update(body)

        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"taskId": task_id, "message": "Task created successfully"}
            ),
        }

    except Exception as e:
        print(f"Error in create_task: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
