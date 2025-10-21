import json
import os
from urllib.parse import unquote
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from Lambda layer
from meeting_data import MeetingDataManager


def handler(event, context):
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")

        if path.startswith("/projects/") and "/timeline" in path and method == "GET":
            project_name = path.split("/")[2]
            return get_project_timeline(project_name)

        elif path.startswith("/projects/") and "/meetings/" in path and path.endswith("/summary") and method == "GET":
            # Parse: /projects/{project}/meetings/{meeting_id}/summary
            parts = path.split("/")
            project_name = parts[2]
            meeting_id = unquote(parts[4])  # URL decode the meeting_id
            return get_meeting_summary(project_name, meeting_id)

        elif (
            path.startswith("/projects/")
            and path.endswith("/action-items")
            and method == "POST"
        ):
            # Parse: /projects/{project}/action-items
            project_name = path.split("/")[2]
            body = json.loads(event.get("body", "{}"))
            return create_action_item(project_name, body)

        elif (
            path.startswith("/projects/")
            and "/action-items/" in path
            and method == "PUT"
        ):
            # Parse: /projects/{project}/action-items/{item_id}
            parts = path.split("/action-items/")
            project_name = parts[0].split("/")[2]  # /projects/{project}
            action_item_id = unquote(
                parts[1]
            )  # Everything after /action-items/, URL decoded
            body = json.loads(event.get("body", "{}"))
            return update_action_item(project_name, action_item_id, body)

        elif (
            path.startswith("/projects/")
            and "/action-items" in path
            and method == "POST"
        ):
            project_name = path.split("/")[2]
            body = json.loads(event.get("body", "{}"))
            return create_action_item(project_name, body)

        elif (
            path.startswith("/projects/")
            and "/action-items/" in path
            and method == "DELETE"
        ):
            # Parse: /projects/{project}/action-items/{item_id}
            parts = path.split("/action-items/")
            project_name = parts[0].split("/")[2]  # /projects/{project}
            action_item_id = unquote(
                parts[1]
            )  # Everything after /action-items/, URL decoded
            return delete_action_item(project_name, action_item_id)

        elif method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
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


def fetch_summary_for_meeting(s3_client, bucket_name, project_name, item):
    """Fetch summary for a single meeting item"""
    if item.get("item_type") != "meeting" or not item.get("filename"):
        return item
    
    # Extract base filename without extension
    base_filename = item["filename"].replace(".txt", "").replace(".vtt", "")
    summary_key = f"projects/{project_name}/meeting-summaries/{base_filename}.json"
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=summary_key)
        summary_data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Extract summary structure that matches frontend expectations
        if "summary" in summary_data:
            item["summary"] = {
                "overview": summary_data["summary"].get("overview"),
                "participants": summary_data["summary"].get("participants", []),
                "key_points": summary_data["summary"].get("keyPoints", []),
                "direct_quotes": summary_data["summary"].get("directQuotes", []),
                "next_steps": summary_data["summary"].get("nextSteps", [])
            }
    except Exception as e:
        print(f"Could not fetch summary for {summary_key}: {str(e)}")
        # Continue without summary - frontend will show "No summary available"
    
    return item


def get_meeting_summary(project_name, meeting_id):
    """Get summary for a specific meeting"""
    try:
        # Find the meeting to get its filename
        meeting_manager = MeetingDataManager(os.environ.get("MEETING_DATA_TABLE_NAME"))
        timeline_items = meeting_manager.get_project_timeline(project_name)
        
        # Find the meeting item
        meeting_item = None
        for item in timeline_items:
            if item.get("item_id") == meeting_id and item.get("item_type") == "meeting":
                meeting_item = item
                break
        
        if not meeting_item or not meeting_item.get("filename"):
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Meeting not found"}),
            }
        
        # Fetch summary from S3
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get("BUCKET_NAME")
        
        base_filename = meeting_item["filename"].replace(".txt", "").replace(".vtt", "")
        summary_key = f"projects/{project_name}/meeting-summaries/{base_filename}.json"
        
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=summary_key)
            summary_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Extract summary structure that matches frontend expectations
            summary = {}
            if "summary" in summary_data:
                summary = {
                    "overview": summary_data["summary"].get("overview"),
                    "participants": summary_data["summary"].get("participants", []),
                    "key_points": summary_data["summary"].get("keyPoints", []),
                    "direct_quotes": summary_data["summary"].get("directQuotes", []),
                    "next_steps": summary_data["summary"].get("nextSteps", [])
                }
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"summary": summary}),
            }
            
        except Exception as e:
            print(f"Could not fetch summary for {summary_key}: {str(e)}")
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Summary not found"}),
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }


def get_project_timeline(project_name):
    """Get project timeline using meeting data structure"""
    try:
        meeting_manager = MeetingDataManager(os.environ.get("MEETING_DATA_TABLE_NAME"))
        timeline_items = meeting_manager.get_project_timeline(project_name)
        
        # Don't fetch summaries initially - only return meeting names and action items
        # Summaries will be loaded on-demand when user clicks dropdown
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"timeline": timeline_items}, default=str),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }


def create_action_item(project_name, item_data):
    """Create new action item using MeetingDataManager"""
    try:
        meeting_manager = MeetingDataManager(os.environ.get("MEETING_DATA_TABLE_NAME"))

        action_uuid = meeting_manager.create_action_item(
            project_id=project_name,
            meeting_uuid=item_data.get("meeting_uuid", ""),
            meeting_date=item_data.get("meeting_date"),
            title=item_data["title"],
            assignee=item_data.get("assignee", ""),
            action_status=item_data.get("action_status", "open"),
        )

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"message": "Action item created", "action_uuid": action_uuid}
            ),
        }
    except Exception as e:
        print(f"Error creating action item: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }


def update_action_item(project_name, action_item_id, body):
    """Update action item status/details"""
    try:
        meeting_manager = MeetingDataManager(os.environ.get("MEETING_DATA_TABLE_NAME"))

        meeting_manager.update_action_item(
            project_id=project_name,
            item_id=action_item_id,
            title=body.get("title"),
            assignee=body.get("assignee"),
            action_status=body.get("action_status"),
            meeting_item_id=body.get("meeting_item_id"),
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Action item updated"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }


def delete_action_item(project_name, action_item_id):
    """Delete action item"""
    try:
        meeting_manager = MeetingDataManager(os.environ.get("MEETING_DATA_TABLE_NAME"))

        # Direct table delete call
        meeting_manager.table.delete_item(
            Key={"project_id": project_name, "item_id": action_item_id}
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Action item deleted"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
