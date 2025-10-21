import json
import os
from datetime import datetime

import boto3

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")


def handler(event, context):
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")
        bucket_name = os.environ["BUCKET_NAME"]

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
    """Get list of all projects"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix="projects/", Delimiter="/"
        )
        projects = []

        for prefix in response.get("CommonPrefixes", []):
            project_name = prefix["Prefix"].replace("projects/", "").rstrip("/")
            if project_name:
                # Get project overview if exists
                try:
                    overview_response = s3_client.get_object(
                        Bucket=bucket_name,
                        Key=f"projects/{project_name}/project_overview.json",
                    )
                    overview_data = json.loads(
                        overview_response["Body"].read().decode("utf-8")
                    )
                    description = overview_data.get(
                        "description", "No description available"
                    )
                except:
                    description = "No description available"

                projects.append({"name": project_name, "description": description})

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
        project_detail = {
            "name": project_name,
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
            import sys

            sys.path.append("/opt/python")
            from meeting_data import MeetingDataManager

            meeting_manager = MeetingDataManager(
                os.environ.get("MEETING_DATA_TABLE_NAME")
            )
            meeting_manager.delete_project(project_name)
            print(f"Deleted DynamoDB items for project: {project_name}")
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

        # Call project setup Lambda to create folder structure
        lambda_client = boto3.client("lambda")
        setup_payload = {
            "project_name": project_name,
            "project_description": description,
        }

        lambda_client.invoke(
            FunctionName=os.environ.get("PROJECT_SETUP_LAMBDA_NAME"),
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
