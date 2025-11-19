import json
import os
import sys

import boto3

from db_utils import list_all_s3_objects, query_all_items

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")
        bucket_name = os.environ["BUCKET_NAME"]

        if path == "/config/project-types" and method == "GET":
            return get_project_types(bucket_name)

        if path == "/projects" and method == "GET":
            query_params = event.get("queryStringParameters") or {}
            checklist_type = query_params.get("type", "design")
            return get_projects_list(bucket_name, checklist_type)

        elif path == "/documents/upload" and method == "POST":
            return upload_general_document(event, bucket_name)

        elif method == "POST" and "/documents" in path:
            parts = path.split("/")
            if len(parts) >= 3 and parts[1] == "projects":
                project_name = parts[2]
                return upload_document(event, bucket_name, project_name)

        elif path.startswith("/projects/") and method == "GET":
            project_name = event.get("pathParameters", {}).get("project_name")
            if not project_name:
                project_name = path.split("/")[2]
            return get_project_detail(bucket_name, project_name)

        elif (
            path.startswith("/projects/") or path.startswith("/delete-project/")
        ) and method == "DELETE":
            project_name = path.split("/")[-1]
            return delete_project(project_name, bucket_name)

        elif path.startswith("/create-project") and method == "POST":
            return create_project(event, bucket_name)

        elif method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                },
                "body": "",
            }

        return {
            "statusCode": 404,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Not found"}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_projects_list(bucket_name, checklist_type="design"):
    """Get list of all projects with task progress"""
    try:
        table_name = os.environ.get("PROJECT_DATA_TABLE_NAME")
        table = dynamodb.Table(table_name) if table_name else None

        response = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix="projects/", Delimiter="/"
        )
        projects = []

        for prefix in response.get("CommonPrefixes", []):
            project_name = prefix["Prefix"].replace("projects/", "").rstrip("/")
            if project_name:
                project_data = {"name": project_name}

                # Get task progress from DynamoDB filtered by checklist type
                if table:
                    try:
                        # Query for tasks of the specified type for this project
                        task_prefix = f"task#{checklist_type}#"
                        db_response = table.query(
                            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
                            ExpressionAttributeValues={
                                ":pid": project_name,
                                ":task": task_prefix,
                            },
                        )

                        tasks = db_response.get("Items", [])
                        total_tasks = len(tasks)
                        completed_tasks = sum(
                            1 for t in tasks if t.get("status") == "completed"
                        )

                        project_data["task_count"] = total_tasks
                        project_data["task_progress"] = {
                            "completed": completed_tasks,
                            "total": total_tasks,
                        }

                        # Get next incomplete task
                        incomplete_tasks = [
                            t for t in tasks if t.get("status") != "completed"
                        ]
                        if incomplete_tasks:
                            # Sort by task_id numerically (e.g., 3.2, 7.1, 10.1)
                            def parse_task_id(task):
                                task_id = task.get("taskData", {}).get(
                                    "task_id", "999.999"
                                )
                                try:
                                    parts = task_id.split(".")
                                    return (
                                        int(parts[0]),
                                        int(parts[1]) if len(parts) > 1 else 0,
                                    )
                                except:
                                    return (999, 999)

                            incomplete_tasks.sort(key=parse_task_id)
                            next_task = incomplete_tasks[0]
                            task_data = next_task.get("taskData", {})
                            project_data["next_task"] = {
                                "number": task_data.get("task_id", ""),
                                "text": task_data.get("description", ""),
                                "projected_date": task_data.get("projected_date", ""),
                            }
                    except Exception as e:
                        print(f"Error fetching tasks for {project_name}: {e}")
                        project_data["task_count"] = 0
                        project_data["task_progress"] = {"completed": 0, "total": 0}

                projects.append(project_data)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(projects),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_project_detail(bucket_name, project_name):
    """Get detailed project information"""
    try:
        # First try to find project by name in DynamoDB
        table_name = os.environ.get("PROJECT_DATA_TABLE_NAME")
        project_id = project_name

        if table_name:
            table = dynamodb.Table(table_name)
            # Use GSI instead of scan
            response = table.query(
                IndexName="projectName-index",
                KeyConditionExpression="projectName = :name AND item_id = :config",
                ExpressionAttributeValues={":name": project_name, ":config": "config"},
            )
            if response.get("Items"):
                project_id = response["Items"][0]["project_id"]

        project_detail = {
            "name": project_name,
            "project_id": project_id,
            "meeting_summaries": [],
            "action_items_detail": [],
            "generated_assets": [],
        }

        # Get meeting summaries
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=f"projects/{project_name}/meeting-summaries/",
            )
            for obj in response.get("Contents", []):
                if obj["Key"].endswith(".json"):
                    try:
                        summary_response = s3_client.get_object(
                            Bucket=bucket_name, Key=obj["Key"]
                        )
                        summary_data = json.loads(
                            summary_response["Body"].read().decode("utf-8")
                        )
                        filename = obj["Key"].split("/")[-1].replace(".json", "")
                        project_detail["meeting_summaries"].append(
                            {
                                "title": filename,
                                "date": obj["LastModified"].strftime("%Y-%m-%d"),
                                "summary": summary_data.get("summary", "")[:500] + "..."
                                if len(summary_data.get("summary", "")) > 500
                                else summary_data.get("summary", ""),
                                "meeting_date": summary_data.get("meeting_date"),
                            }
                        )
                    except:
                        pass
        except:
            pass

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(project_detail),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def delete_project(project_name, bucket_name):
    """Delete a project and all its files. KB will auto-sync when S3 files are deleted."""
    try:
        # Delete all DynamoDB items for this project
        try:
            table_name = os.environ.get("PROJECT_DATA_TABLE_NAME")
            if table_name:
                table = dynamodb.Table(table_name)

                # Get project_id from project name using GSI
                response = table.query(
                    IndexName="projectName-index",
                    KeyConditionExpression="projectName = :pname AND item_id = :config",
                    ExpressionAttributeValues={
                        ":pname": project_name,
                        ":config": "config",
                    },
                )

                if response["Items"]:
                    project_id = response["Items"][0]["project_id"]

                    # Query all items for this project_id with pagination
                    items = query_all_items(
                        table,
                        KeyConditionExpression="project_id = :pid",
                        ExpressionAttributeValues={":pid": project_id},
                    )

                    # Delete all items
                    with table.batch_writer() as batch:
                        for item in items:
                            batch.delete_item(
                                Key={
                                    "project_id": item["project_id"],
                                    "item_id": item["item_id"],
                                }
                            )

                    print(
                        f"Deleted {len(items)} DynamoDB items for project: {project_name}"
                    )
        except Exception as e:
            print(f"Warning: Could not delete DynamoDB items: {e}")

        # List all objects with the project prefix
        response = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=f"projects/{project_name}/"
        )

        # Delete all objects
        objects_to_delete = []
        for obj in response.get("Contents", []):
            objects_to_delete.append({"Key": obj["Key"]})

        if objects_to_delete:
            s3_client.delete_objects(
                Bucket=bucket_name, Delete={"Objects": objects_to_delete}
            )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {"message": f"Project {project_name} deleted successfully"}
            ),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def create_project(event, bucket_name):
    """Create a new project"""
    try:
        body = json.loads(event.get("body", "{}"))
        project_name = body.get("project_name")
        description = body.get("project_description", "")

        if not project_name:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "project_name is required"}),
            }

        # Call project setup wizard Lambda to create folder structure
        lambda_client = boto3.client("lambda")
        setup_payload = {
            "body": json.dumps(
                {
                    "projectName": project_name,
                    "projectType": "Other",
                    "location": "TBD",
                    "areaSize": "0",
                    "specialConditions": [],
                }
            )
        }

        lambda_client.invoke(
            FunctionName=os.environ.get("PROJECT_WIZARD_LAMBDA_NAME"),
            InvocationType="RequestResponse",
            Payload=json.dumps(setup_payload),
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {"message": f"Project {project_name} created successfully"}
            ),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_project_types(bucket_name):
    """Get project types from S3"""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key="project-types.json")
        data = json.loads(response["Body"].read().decode("utf-8"))
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(data),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def upload_document(event, bucket_name, project_name):
    """Upload document to project and optionally extract lessons"""
    try:
        body = json.loads(event.get("body", "{}"))
        filename = body.get("filename")
        content = body.get("content")
        extract_lessons = body.get("extract_lessons", False)
        project_type = body.get("project_type", "")

        if not filename or not content:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "filename and content are required"}),
            }

        # Save document to S3
        s3_key = f"documents/projects/{project_name}/{filename}"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content.encode("utf-8") if isinstance(content, str) else content,
        )

        # If extract_lessons is enabled, invoke lessons processor
        if extract_lessons:
            try:
                lessons_lambda = os.environ.get("LESSONS_PROCESSOR_LAMBDA_NAME")
                if lessons_lambda:
                    lambda_client.invoke(
                        FunctionName=lessons_lambda,
                        InvocationType="Event",
                        Payload=json.dumps(
                            {
                                "s3_key": s3_key,
                                "project_name": project_name,
                                "project_type": project_type,
                            }
                        ),
                    )
            except Exception as e:
                print(f"Warning: Could not invoke lessons processor: {e}")

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "message": f"Document {filename} uploaded successfully",
                    "s3_key": s3_key,
                }
            ),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def upload_general_document(event, bucket_name):
    """Upload document directly to documents/ folder"""
    try:
        body = json.loads(event.get("body", "{}"))
        filename = body.get("filename")
        content = body.get("content")

        if not filename or not content:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "filename and content are required"}),
            }

        s3_key = f"documents/{filename}"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content.encode("utf-8") if isinstance(content, str) else content,
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "message": f"Document {filename} uploaded successfully",
                    "s3_key": s3_key,
                }
            ),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
