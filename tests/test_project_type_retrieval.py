"""Test project_type retrieval when adding single lessons"""
import json
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Add layer path for db_utils import
layer_path = os.path.join(os.path.dirname(__file__), "..", "layers", "common", "python")
if layer_path not in sys.path:
    sys.path.insert(0, layer_path)


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table"""
    table = MagicMock()
    table.query.return_value = {
        "Items": [
            {
                "project_id": "test-project",
                "item_id": "config",
                "projectName": "Test Project",
                "projectType": "reconstruction",
            }
        ]
    }
    return table


@pytest.fixture
def mock_event():
    """Mock API Gateway event for document upload"""
    return {
        "httpMethod": "POST",
        "path": "/projects/test-project/documents",
        "pathParameters": {"project_name": "test-project"},
        "body": json.dumps({
            "filename": "lesson-123.txt",
            "content": "Test lesson content",
            "extract_lessons": True,
            # Note: project_type is NOT provided
        }),
    }


def test_project_type_retrieved_from_dynamodb(mock_event, mock_dynamodb_table):
    """Test that project_type is fetched from DynamoDB when not provided"""
    with patch("src.projects.projects_api.s3_client") as mock_s3, \
         patch("src.projects.projects_api.lambda_client") as mock_lambda, \
         patch("src.projects.projects_api.dynamodb") as mock_dynamodb, \
         patch.dict(os.environ, {"PROJECT_DATA_TABLE_NAME": "test-table", "LESSONS_PROCESSOR_LAMBDA_NAME": "test-lambda"}):
        
        # Setup DynamoDB mock
        mock_dynamodb.Table.return_value = mock_dynamodb_table
        
        # Import after patching
        from src.projects.projects_api import upload_document
        
        # Call the function
        result = upload_document(mock_event, "test-bucket", "test-project")
        
        # Verify DynamoDB was queried
        mock_dynamodb_table.query.assert_called_once_with(
            IndexName="projectName-index",
            KeyConditionExpression="projectName = :name AND item_id = :config",
            ExpressionAttributeValues={":name": "test-project", ":config": "config"},
        )
        
        # Verify Lambda was invoked with correct project_type
        mock_lambda.invoke.assert_called_once()
        call_args = mock_lambda.invoke.call_args
        payload = json.loads(call_args[1]["Payload"])
        
        assert payload["project_type"] == "reconstruction"
        assert payload["project_name"] == "test-project"
        assert payload["content"] == "Test lesson content"


def test_project_type_uses_provided_value(mock_event):
    """Test that provided project_type is used instead of querying DynamoDB"""
    # Add project_type to event
    body = json.loads(mock_event["body"])
    body["project_type"] = "resurface"
    mock_event["body"] = json.dumps(body)
    
    with patch("src.projects.projects_api.s3_client") as mock_s3, \
         patch("src.projects.projects_api.lambda_client") as mock_lambda, \
         patch("src.projects.projects_api.dynamodb") as mock_dynamodb, \
         patch.dict(os.environ, {"LESSONS_PROCESSOR_LAMBDA_NAME": "test-lambda"}):
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        from src.projects.projects_api import upload_document
        
        result = upload_document(mock_event, "test-bucket", "test-project")
        
        # Verify DynamoDB was NOT queried
        mock_table.query.assert_not_called()
        
        # Verify Lambda was invoked with provided project_type
        mock_lambda.invoke.assert_called_once()
        call_args = mock_lambda.invoke.call_args
        payload = json.loads(call_args[1]["Payload"])
        
        assert payload["project_type"] == "resurface"


def test_project_type_defaults_to_other_on_error(mock_event):
    """Test that project_type defaults to 'other' if DynamoDB query fails"""
    with patch("src.projects.projects_api.s3_client") as mock_s3, \
         patch("src.projects.projects_api.lambda_client") as mock_lambda, \
         patch("src.projects.projects_api.dynamodb") as mock_dynamodb, \
         patch.dict(os.environ, {"PROJECT_DATA_TABLE_NAME": "test-table", "LESSONS_PROCESSOR_LAMBDA_NAME": "test-lambda"}):
        
        mock_table = MagicMock()
        # Simulate DynamoDB error
        mock_table.query.side_effect = Exception("DynamoDB error")
        mock_dynamodb.Table.return_value = mock_table
        
        from src.projects.projects_api import upload_document
        
        result = upload_document(mock_event, "test-bucket", "test-project")
        
        # Verify Lambda was invoked with 'other' as fallback
        mock_lambda.invoke.assert_called_once()
        call_args = mock_lambda.invoke.call_args
        payload = json.loads(call_args[1]["Payload"])
        
        assert payload["project_type"] == "other"
