import json
import os
import sys
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeSerializer

from db_utils import query_all_items

dynamodb = boto3.resource("dynamodb")
dynamodb_client = boto3.client("dynamodb")
serializer = TypeSerializer()


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
            return sync_to_all_projects()

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
                    "required": item["taskData"].get("required", True),
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


def sync_to_all_projects():
    """Sync global checklist changes to all projects with optimizations"""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])

        # Get global tasks for both types
        global_response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
            ExpressionAttributeValues={":pid": "__GLOBAL__", ":task": "task#"},
        )

        global_tasks = {item["item_id"]: item for item in global_response["Items"]}
        if not global_tasks:
            return cors_response(200, {"message": "No global tasks to sync", "updates": 0})
        
        global_version = global_response["Items"][0]["version"]

        # Get all projects with pagination
        projects = []
        last_key = None
        while True:
            query_params = {
                "IndexName": "item_id-index",
                "KeyConditionExpression": "item_id = :config",
                "ExpressionAttributeValues": {":config": "config"}
            }
            if last_key:
                query_params["ExclusiveStartKey"] = last_key
            
            response = table.query(**query_params)
            projects.extend([p["project_id"] for p in response.get("Items", []) if p["project_id"] != "__GLOBAL__"])
            
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break

        updated_count = 0
        
        def parse_task_id(task_id):
            try:
                return [int(x) for x in task_id.split(".")]
            except:
                return [999, 999]

        for project_id in projects:
            # Get project tasks - only query if needed
            project_tasks_response = table.query(
                KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
                ExpressionAttributeValues={":pid": project_id, ":task": "task#"}
            )
            
            project_tasks = project_tasks_response.get("Items", [])
            if not project_tasks and not global_tasks:
                continue  # Skip if no tasks to sync
            
            project_tasks_map = {item["item_id"]: item for item in project_tasks}

            # Find highest completed task per type
            highest_completed = {"design": None, "construction": None}
            for item_id, item in project_tasks_map.items():
                if item.get("status") == "completed":
                    parts = item_id.split("#")
                    if len(parts) == 3:
                        checklist_type = parts[1]
                        task_num = parts[2]
                        if checklist_type in highest_completed:
                            if not highest_completed[checklist_type] or parse_task_id(task_num) > parse_task_id(highest_completed[checklist_type]):
                                highest_completed[checklist_type] = task_num

            # Batch delete and put operations
            batch_items = []
            
            # Delete tasks not in global (if unchecked)
            for item_id, task_item in project_tasks_map.items():
                if item_id not in global_tasks and task_item.get("status") != "completed":
                    batch_items.append({
                        "DeleteRequest": {
                            "Key": {
                                "project_id": {"S": project_id},
                                "item_id": {"S": item_id}
                            }
                        }
                    })
                    updated_count += 1

            # Add/update tasks from global
            for item_id, global_task in global_tasks.items():
                parts = item_id.split("#")
                if len(parts) != 3:
                    continue
                checklist_type = parts[1]
                task_num = parts[2]

                # Skip adding new tasks with IDs lower than highest completed
                if item_id not in project_tasks_map and highest_completed.get(checklist_type):
                    if parse_task_id(task_num) < parse_task_id(highest_completed[checklist_type]):
                        continue

                item_data = {
                    "project_id": project_id,
                    "item_id": item_id,
                    "taskData": global_task["taskData"],
                    "global_version": global_version,
                }
                
                if item_id in project_tasks_map:
                    # Skip completed tasks - don't update them
                    if project_tasks_map[item_id].get("status") == "completed":
                        continue
                    
                    # Update unchecked task
                    item_data["status"] = project_tasks_map[item_id].get("status", "not_started")
                    batch_items.append({
                        "PutRequest": {
                            "Item": {k: serializer.serialize(v) for k, v in item_data.items()}
                        }
                    })
                    updated_count += 1
                else:
                    # Add new task
                    item_data["status"] = "not_started"
                    item_data["createdDate"] = datetime.utcnow().isoformat()
                    batch_items.append({
                        "PutRequest": {
                            "Item": {k: serializer.serialize(v) for k, v in item_data.items()}
                        }
                    })
                    updated_count += 1
            
            # Write in batches of 25
            for i in range(0, len(batch_items), 25):
                batch = batch_items[i:i+25]
                if batch:
                    dynamodb_client.batch_write_item(
                        RequestItems={table.table_name: batch}
                    )

        return cors_response(
            200,
            {
                "message": f"Synced {len(projects)} projects",
                "updates": updated_count,
            },
        )

    except Exception as e:
        print(f"Error syncing to projects: {str(e)}")
        raise


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
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }
