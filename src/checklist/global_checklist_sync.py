import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import boto3
from boto3.dynamodb.types import TypeSerializer

dynamodb = boto3.resource("dynamodb")
dynamodb_client = boto3.client("dynamodb")
serializer = TypeSerializer()

MAX_WORKERS = 10


def handler(event, context):
    """Async handler for syncing global checklist to all projects"""
    try:
        return perform_sync_to_all_projects()
    except Exception as e:
        print(f"Error in sync: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def perform_sync_to_all_projects():
    """Sync global checklist changes to all projects with parallel processing."""
    try:
        table = dynamodb.Table(os.environ["PROJECT_DATA_TABLE_NAME"])
        table_name = table.table_name

        # Get global tasks
        global_response = table.query(
            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
            ExpressionAttributeValues={":pid": "__GLOBAL__", ":task": "task#"},
        )
        global_tasks = {item["item_id"]: item for item in global_response["Items"]}
        if not global_tasks:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No global tasks to sync", "updates": 0})
            }
        
        global_version = global_response["Items"][0]["version"]

        # Get all projects
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

        if not projects:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No projects to sync", "updates": 0})
            }

        def sync_project(project_id):
            """Sync a single project - runs in thread pool."""
            project_tasks_response = table.query(
                KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
                ExpressionAttributeValues={":pid": project_id, ":task": "task#"}
            )
            project_tasks_map = {item["item_id"]: item for item in project_tasks_response.get("Items", [])}
            
            # Find highest completed task per type
            highest_completed = {"design": None, "construction": None}
            for item_id, item in project_tasks_map.items():
                if item.get("status") == "completed":
                    parts = item_id.split("#")
                    if len(parts) == 3:
                        ctype, task_num = parts[1], parts[2]
                        if ctype in highest_completed:
                            if not highest_completed[ctype] or _parse_task_id(task_num) > _parse_task_id(highest_completed[ctype]):
                                highest_completed[ctype] = task_num

            batch_items = []
            
            # Delete tasks not in global (if unchecked)
            for item_id, task_item in project_tasks_map.items():
                if item_id not in global_tasks and task_item.get("status") != "completed":
                    batch_items.append({"DeleteRequest": {"Key": {"project_id": {"S": project_id}, "item_id": {"S": item_id}}}})

            # Add/update tasks from global
            for item_id, global_task in global_tasks.items():
                parts = item_id.split("#")
                if len(parts) != 3:
                    continue
                ctype, task_num = parts[1], parts[2]

                if item_id not in project_tasks_map:
                    # Skip new tasks below highest completed
                    if highest_completed.get(ctype) and _parse_task_id(task_num) < _parse_task_id(highest_completed[ctype]):
                        continue
                    item_data = {"project_id": project_id, "item_id": item_id, "taskData": global_task["taskData"],
                                 "global_version": global_version, "status": "not_started", "createdDate": datetime.utcnow().isoformat()}
                    batch_items.append({"PutRequest": {"Item": {k: serializer.serialize(v) for k, v in item_data.items()}}})
                elif project_tasks_map[item_id].get("status") != "completed":
                    item_data = {"project_id": project_id, "item_id": item_id, "taskData": global_task["taskData"],
                                 "global_version": global_version, "status": project_tasks_map[item_id].get("status", "not_started")}
                    batch_items.append({"PutRequest": {"Item": {k: serializer.serialize(v) for k, v in item_data.items()}}})

            # Write batches
            for i in range(0, len(batch_items), 25):
                batch = batch_items[i:i+25]
                if batch:
                    dynamodb_client.batch_write_item(RequestItems={table_name: batch})
            
            return len(batch_items)

        # Process projects in parallel
        total_updates = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(sync_project, pid): pid for pid in projects}
            for future in as_completed(futures):
                try:
                    total_updates += future.result()
                except Exception as e:
                    print(f"Error syncing project {futures[future]}: {e}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Synced {len(projects)} projects", "updates": total_updates})
        }

    except Exception as e:
        print(f"Error syncing to projects: {str(e)}")
        raise


def _parse_task_id(task_id):
    try:
        return [int(x) for x in task_id.split(".")]
    except:
        return [999, 999]
