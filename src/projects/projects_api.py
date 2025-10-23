import json
import os
from datetime import datetime

import boto3

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
            return get_projects_list(bucket_name)

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

        elif path.startswith("/update-progress") and method == "POST":
            return update_project_progress(event, bucket_name)

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


def get_projects_list(bucket_name):
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
                
                # Get project overview if exists
                try:
                    overview_response = s3_client.get_object(
                        Bucket=bucket_name,
                        Key=f"projects/{project_name}/project_overview.json",
                    )
                    overview_data = json.loads(
                        overview_response["Body"].read().decode("utf-8")
                    )
                    project_data["description"] = overview_data.get(
                        "description", "No description available"
                    )
                    project_data["status"] = overview_data.get("status", "active")
                except:
                    project_data["description"] = "No description available"
                    project_data["status"] = "active"
                
                # Get task progress from DynamoDB
                if table:
                    try:
                        # Query for all tasks for this project
                        db_response = table.query(
                            KeyConditionExpression="project_id = :pid AND begins_with(item_id, :task)",
                            ExpressionAttributeValues={
                                ":pid": project_name,
                                ":task": "task#"
                            }
                        )
                        
                        tasks = db_response.get("Items", [])
                        total_tasks = len(tasks)
                        completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
                        
                        project_data["task_count"] = total_tasks
                        project_data["task_progress"] = {
                            "completed": completed_tasks,
                            "total": total_tasks
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
            # Scan for project with matching name
            response = table.scan(
                FilterExpression="item_id = :config AND projectName = :name",
                ExpressionAttributeValues={
                    ":config": "config",
                    ":name": project_name
                }
            )
            if response.get('Items'):
                project_id = response['Items'][0]['project_id']
        
        project_detail = {
            "name": project_name,
            "project_id": project_id,
            "description": "No description available",
            "meeting_summaries": [],
            "action_items_detail": [],
            "generated_assets": [],
        }

        # Get project overview
        try:
            overview_response = s3_client.get_object(
                Bucket=bucket_name,
                Key=f"projects/{project_name}/project_overview.json",
            )
            overview_data = json.loads(overview_response["Body"].read().decode("utf-8"))
            project_detail.update(overview_data)
        except:
            pass

        # Get working backwards data
        try:
            wb_response = s3_client.get_object(
                Bucket=bucket_name,
                Key=f"projects/{project_name}/working_backwards.json",
            )
            wb_data = json.loads(wb_response["Body"].read().decode("utf-8"))
            project_detail["working_backwards"] = wb_data.get(
                "workingBackwards", wb_data
            )
        except:
            pass

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
    """Delete a project and all its files"""
    try:
        # Delete vectors from S3 vector bucket
        try:
            s3vectors_client = boto3.client("s3vectors")
            vector_bucket = os.environ.get(
                "VECTOR_BUCKET_NAME", "dxhub-meeting-kb-vectors"
            )
            index_name = os.environ.get("INDEX_NAME", "meeting-kb-index")

            vector_keys = []
            next_token = None

            # Paginate through all vectors
            while True:
                params = {
                    "vectorBucketName": vector_bucket,
                    "indexName": index_name,
                }
                if next_token:
                    params["nextToken"] = next_token

                vector_response = s3vectors_client.list_vectors(**params)

                for obj in vector_response.get("vectors", []):
                    metadata = obj.get("metadata", {})
                    if (
                        isinstance(metadata, dict)
                        and metadata.get("project_name") == project_name
                    ):
                        vector_keys.append(obj["key"])

                next_token = vector_response.get("nextToken")
                if not next_token:
                    break

            if vector_keys:
                # Delete in batches of 500
                batch_size = 500
                total_deleted = 0
                for i in range(0, len(vector_keys), batch_size):
                    batch = vector_keys[i : i + batch_size]
                    s3vectors_client.delete_vectors(
                        vectorBucketName=vector_bucket,
                        indexName=index_name,
                        keys=batch,
                    )
                    total_deleted += len(batch)
                print(f"Deleted {total_deleted} S3 vectors for project: {project_name}")
        except Exception as e:
            print(f"Warning: Could not delete vectors: {e}")

        # Delete all DynamoDB items for this project
        try:
            table_name = os.environ.get("PROJECT_DATA_TABLE_NAME")
            if table_name:
                table = dynamodb.Table(table_name)
                
                # Get project_id from project name
                response = table.scan(
                    FilterExpression='projectName = :pname',
                    ExpressionAttributeValues={':pname': project_name}
                )
                
                if response['Items']:
                    project_id = response['Items'][0]['project_id']
                    
                    # Query all items for this project_id
                    items_response = table.query(
                        KeyConditionExpression='project_id = :pid',
                        ExpressionAttributeValues={':pid': project_id}
                    )
                    
                    # Delete all items
                    with table.batch_writer() as batch:
                        for item in items_response['Items']:
                            batch.delete_item(
                                Key={
                                    'project_id': item['project_id'],
                                    'item_id': item['item_id']
                                }
                            )
                    
                    print(f"Deleted {len(items_response['Items'])} DynamoDB items for project: {project_name}")
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
            "body": json.dumps({
                "projectName": project_name,
                "projectType": "Other",
                "location": "TBD",
                "areaSize": "0",
                "specialConditions": []
            })
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


def update_project_progress(event, bucket_name):
    """Update project progress"""
    try:
        body = json.loads(event.get("body", "{}"))
        project_name = body.get("project_name")
        progress_data = body.get("progress", {})

        if not project_name:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "project_name is required"}),
            }

        # Get existing project overview
        try:
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=f"projects/{project_name}/project_overview.json",
            )
            project_data = json.loads(response["Body"].read().decode("utf-8"))
        except:
            project_data = {"name": project_name}

        # Update with progress data
        project_data.update(progress_data)
        project_data["updated_at"] = datetime.utcnow().isoformat()

        # Save back to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=f"projects/{project_name}/project_overview.json",
            Body=json.dumps(project_data, indent=2),
            ContentType="application/json",
        )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Progress updated successfully"}),
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
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key="project-types.json"
        )
        data = json.loads(response["Body"].read().decode("utf-8"))
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(data)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
