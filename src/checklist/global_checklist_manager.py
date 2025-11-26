import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeSerializer

dynamodb = boto3.resource("dynamodb")
dynamodb_client = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")
serializer = TypeSerializer()

MAX_WORKERS = 10  # Parallel threads for project sync


def handler(event, context):
    """Manage global checklist CRUD operations"""
    try:
        method = event.get("httpMethod", "")
        path = event.get("path", "")

        if method == "OPTIONS":
            return cors_response(200, "")

        if method == "GET" and "/global-checklist" in path:
            query_params = event.get("queryStringParameters") or {}
            checklist_type = query_params.get("type", "design")
            return get_global_checklist(checklist_type)

        elif method == "PUT" and "/global-checklist" in path:
            body = json.loads(event.get("body", "{}"))
            query_params = event.get("queryStringParameters") or {}
            checklist_type = query_params.get("type", "design")
            return update_global_checklist(body, checklist_type)

        elif method == "POST" and "/global-checklist/sync" in path:
            return trigger_async_sync()

        elif method == "POST" and "/global-checklist/initialize" in path:
            return initialize_global_checklist()

        return cors_response(404, {"error": "Not found"})

    except Exception as e:
        print(f"Error: {str(e)}")
        return cors_response(500, {"error": str(e)})


def get_global_checklist(checklist_type="design"):
    """Get global checklist from DynamoDB"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        task_prefix = f"task#{checklist_type}#"
        response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
            ExpressionAttributeValues={":pid": "__GLOBAL__", ":task": task_prefix},
        )

        tasks = []
        for item in response["Items"]:
            tasks.append(
                {
                    "task_id": item["taskData"]["task_id"],
                    "description": item["taskData"]["description"],
                    "notes": item["taskData"].get("notes", ""),
                    "projected_date": item["taskData"].get("projected_date", ""),
                    "version": item.get("version", ""),
                }
            )

        # Sort by task_id
        tasks.sort(
            key=lambda x: [
                int(n) if n.isdigit() else n for n in x["task_id"].split(".")
            ]
        )

        return cors_response(200, {"tasks": tasks})

    except Exception as e:
        print(f"Error getting global checklist: {str(e)}")
        raise


def update_global_checklist(body, checklist_type="design"):
    """Update global checklist tasks"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])
        tasks = body.get("tasks", [])
        version = datetime.utcnow().isoformat()

        task_prefix = f"task#{checklist_type}#"

        # Get existing tasks for this checklist type
        response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
            ExpressionAttributeValues={":pid": "__GLOBAL__", ":task": task_prefix},
        )
        existing_item_ids = {item["item_id"] for item in response["Items"]}
        new_item_ids = {f"{task_prefix}{task['task_id']}" for task in tasks}

        # Delete removed tasks
        for item_id in existing_item_ids - new_item_ids:
            table.delete_item(Key={"project_id": "__GLOBAL__", "item_id": item_id})

        # Update/create tasks
        for task in tasks:
            table.put_item(
                Item={
                    "project_id": "__GLOBAL__",
                    "item_id": f"{task_prefix}{task['task_id']}",
                    "taskData": task,
                    "version": version,
                    "lastUpdated": version,
                }
            )

        return cors_response(
            200, {"message": "Global checklist updated", "version": version}
        )

    except Exception as e:
        print(f"Error updating global checklist: {str(e)}")
        raise


def trigger_async_sync():
    """Trigger async sync and return immediately"""
    try:
        lambda_client.invoke(
            FunctionName=os.environ["SYNC_LAMBDA_NAME"],
            InvocationType="Event",
            Payload=json.dumps({})
        )
        return cors_response(200, {"message": "Global sync started"})
    except Exception as e:
        print(f"Error triggering async sync: {str(e)}")
        raise


def perform_sync_to_all_projects():
    """Deprecated - sync now handled by separate lambda"""
    return cors_response(400, {"error": "Use async sync endpoint"})


def initialize_global_checklist():
    """Initialize global checklist from design_checklist.json and construction_checklist.json"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Check if already initialized
        response = table.query(
            KeyConditionExpression="project_id = :pid",
            ExpressionAttributeValues={":pid": "__GLOBAL__"},
            Limit=1,
        )

        if response["Items"]:
            return cors_response(400, {"error": "Global checklist already initialized"})

        version = datetime.utcnow().isoformat()

        # Load and store design checklist
        design_path = "/var/task/design_checklist.json"
        with open(design_path, "r") as f:
            design_checklist = json.load(f)

        for item in design_checklist["document"]["checklist_items"]:
            for task in item["tasks"]:
                table.put_item(
                    Item={
                        "project_id": "__GLOBAL__",
                        "item_id": f"task#design#{task['task_id']}",
                        "taskData": task,
                        "version": version,
                        "lastUpdated": version,
                    }
                )

        # Load and store construction checklist
        construction_path = "/var/task/construction_checklist.json"
        with open(construction_path, "r") as f:
            construction_checklist = json.load(f)

        for item in construction_checklist["document"]["checklist_items"]:
            for task in item["tasks"]:
                table.put_item(
                    Item={
                        "project_id": "__GLOBAL__",
                        "item_id": f"task#construction#{task['task_id']}",
                        "taskData": task,
                        "version": version,
                        "lastUpdated": version,
                    }
                )

        return cors_response(
            200,
            {
                "message": "Global checklists initialized (design and construction)",
                "version": version,
            },
        )

    except Exception as e:
        print(f"Error initializing global checklist: {str(e)}")
        raise


def cors_response(status_code, body):
    """Return CORS-enabled response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
            "Access-Control-Allow-Methods": "GET, PUT, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": json.dumps(body),
    }
