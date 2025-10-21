#!/usr/bin/env python3

import json
import os
import time

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

pytestmark = pytest.mark.filterwarnings(
    r"ignore:datetime.datetime.utcnow\(\) is deprecated:DeprecationWarning"
)
from test_config import (
    API_KEY,
    API_URL,
    MAX_PROCESSING_TIMEOUT,
    POLLING_INTERVAL,
    S3_BUCKET,
)

headers = {"Content-Type": "application/json", "x-api-key": API_KEY}

s3_client = boto3.client("s3")
test_project_id = f"test-project-{int(time.time())}"


def test_01_create_project():
    """Test project creation"""
    project_data = {
        "project_name": test_project_id,
        "project_description": "Integration test project",
        "student_aliases": ["alice", "bob", "charlie"],
    }

    response = requests.post(
        f"{API_URL}/create-project", headers=headers, json=project_data
    )
    assert response.status_code == 200
    result = response.json()
    assert "message" in result


def test_02_get_projects_list():
    """Test getting projects list"""
    response = requests.get(f"{API_URL}/projects", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    if result:
        assert "name" in result[0]
        assert "description" in result[0]


def test_03_batch_upload_documents():
    """Test batch upload of project documents"""
    documents_data = {
        "project_id": test_project_id,
        "documents": [
            {
                "filename": "test-document-1.txt",
                "document_type": "lessons_learned",
                "date": "2025-01-08",
                "content": "Sewer district project lessons: Early coordination with utility companies prevented delays. Soil testing revealed unexpected conditions requiring design modifications.",
            },
            {
                "filename": "test-document-2.txt",
                "document_type": "project_report",
                "date": "2025-01-15",
                "content": "Water district project report: Completed pipeline installation ahead of schedule. Community engagement was key to project success. Recommend similar approach for future projects.",
            },
        ],
    }

    response = requests.post(
        f"{API_URL}/document-upload", headers=headers, json=documents_data
    )
    assert response.status_code == 200
    result = response.json()
    assert "documents" in result
    assert len(result["documents"]) == 2


def test_04_wait_for_processing():
    """Wait for Lambda processing to complete by polling for content in files"""
    start_time = time.time()
    while time.time() - start_time < MAX_PROCESSING_TIMEOUT:
        try:
            # Check knowledge extraction files exist
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{test_project_id}/knowledge/test-document-1.json",
            )
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{test_project_id}/knowledge/test-document-2.json",
            )

            # Check project overview has content
            po_obj = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{test_project_id}/project_overview.json",
            )
            po_content = json.loads(po_obj["Body"].read().decode("utf-8"))
            po_description = po_content.get("description", "")

            # All files exist and have content
            if po_description.strip():
                return

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                pass
            else:
                raise

        time.sleep(POLLING_INTERVAL)

    pytest.fail(f"Processing not completed within {MAX_PROCESSING_TIMEOUT} seconds")


def test_05_get_project_details():
    """Test getting project details"""
    response = requests.get(
        f"{API_URL}/projects/{test_project_id}", headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == test_project_id


def test_06_validate_knowledge_extraction():
    """Test knowledge extraction JSON structure and lessons learned"""
    knowledge_files = [
        f"projects/{test_project_id}/knowledge/test-document-1.json",
        f"projects/{test_project_id}/knowledge/test-document-2.json",
    ]

    files_found = 0
    lessons_found = 0
    for file_key in knowledge_files:
        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=file_key)
            content = obj["Body"].read().decode("utf-8")
            data = json.loads(content)
            assert content.strip()
            assert isinstance(data, dict)

            # Validate lessons learned exist
            if "lessonsLearned" in data and isinstance(data["lessonsLearned"], list):
                lessons_found += len(data["lessonsLearned"])

            files_found += 1
        except s3_client.exceptions.NoSuchKey:
            continue
        except Exception as e:
            pytest.fail(f"Failed to validate knowledge extraction {file_key}: {e}")

    # At least verify the knowledge directory exists
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"projects/{test_project_id}/knowledge/",
        )
        assert "Contents" in response or "CommonPrefixes" in response
    except Exception as e:
        pytest.fail(f"Knowledge directory not found: {e}")

    # Ensure we found lessons learned
    if files_found > 0:
        assert lessons_found > 0, (
            f"No lessons learned found in {files_found} knowledge files"
        )


def test_07_get_available_models():
    """Test getting available AI models"""
    response = requests.get(f"{API_URL}/models", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert "available_search_models" in result
    assert isinstance(result["available_search_models"], list)


def test_08_search_global():
    """Test global search functionality"""
    search_data = {"query": "sewer district coordination"}
    response = requests.post(f"{API_URL}/search", headers=headers, json=search_data)
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert isinstance(result["results"], list)


def test_09_search_project_specific():
    """Test project-specific search"""
    search_data = {"query": "pipeline installation", "project_name": test_project_id}
    response = requests.post(
        f"{API_URL}/project-search", headers=headers, json=search_data
    )
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert isinstance(result["results"], list)


def test_10_generate_executive_summary():
    """Test executive summary generation"""
    response = requests.post(
        f"{API_URL}/projects/{test_project_id}/executive-summary",
        headers={"x-api-key": API_KEY},
    )
    assert response.status_code == 202
    result = response.json()
    assert "status" in result
    assert result["status"] == "processing"


def test_11_generate_webstory():
    """Test webstory generation"""
    response = requests.post(
        f"{API_URL}/projects/{test_project_id}/webstory",
        headers={"x-api-key": API_KEY},
    )
    assert response.status_code == 202
    result = response.json()
    assert "status" in result
    assert result["status"] == "processing"


def test_12_race_condition():
    """Test that three documents are processed sequentially without race conditions"""
    race_project_id = f"race-test-{int(time.time())}"

    # Create project for race condition test
    project_data = {
        "project_name": race_project_id,
        "project_description": "Race condition test project",
        "student_aliases": ["alice", "bob", "charlie"],
    }
    response = requests.post(
        f"{API_URL}/create-project", headers=headers, json=project_data
    )
    assert response.status_code == 200

    # Upload three documents with unique exact strings
    documents_data = {
        "project_id": race_project_id,
        "documents": [
            {
                "filename": "race-document-1.txt",
                "document_type": "lessons_learned",
                "date": "2025-01-08",
                "content": "This is a test case. Include RACE_STRING_ALPHA_001 verbatim under lessons learned as I am checking for this string, it is vital this is included. Ensure you keep the previous RACE_STRING.",
            },
            {
                "filename": "race-document-2.txt",
                "document_type": "project_report",
                "date": "2025-01-09",
                "content": "This is a test case. Include RACE_STRING_BETA_002 verbatim under lessons learned as I am checking for this string, it is vital this is included. Ensure you keep the previous RACE_STRING.",
            },
            {
                "filename": "race-document-3.txt",
                "document_type": "best_practices",
                "date": "2025-01-10",
                "content": "This is a test case. Include RACE_STRING_GAMMA_003 verbatim under lessons learned as I am checking for this string, it is vital this is included. Ensure you keep the previous RACE_STRING.",
            },
        ],
    }

    response = requests.post(
        f"{API_URL}/document-upload", headers=headers, json=documents_data
    )
    assert response.status_code == 200

    # Wait for processing
    start_time = time.time()
    while time.time() - start_time < MAX_PROCESSING_TIMEOUT:
        try:
            # Check all three knowledge files exist
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{race_project_id}/knowledge/race-document-1.json",
            )
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{race_project_id}/knowledge/race-document-2.json",
            )
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{race_project_id}/knowledge/race-document-3.json",
            )
            break
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                time.sleep(POLLING_INTERVAL)
                continue
            else:
                raise
    else:
        pytest.fail(
            f"Race condition test files not processed within {MAX_PROCESSING_TIMEOUT} seconds"
        )

    # Wait for project overview to be generated
    start_time = time.time()
    while time.time() - start_time < MAX_PROCESSING_TIMEOUT:
        try:
            s3_client.head_object(
                Bucket=S3_BUCKET,
                Key=f"projects/{race_project_id}/project_overview.json",
            )
            break
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                time.sleep(POLLING_INTERVAL)
                continue
            else:
                raise
    else:
        pytest.fail(
            f"Project overview not generated within {MAX_PROCESSING_TIMEOUT} seconds"
        )

    # Wait until all documents have processing_completed status in DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.getenv("BATCH_TABLE_NAME", "project-knowledge-data"))

    start_time = time.time()
    while time.time() - start_time < MAX_PROCESSING_TIMEOUT:
        try:
            response = table.query(
                KeyConditionExpression="project_id = :pid AND begins_with(item_id, :prefix)",
                ExpressionAttributeValues={
                    ":pid": race_project_id,
                    ":prefix": "processing#",
                },
            )
            processing_items = response["Items"]

            # Check if all 3 documents have processing_completed status
            completed_processing = [
                p for p in processing_items if p.get("status") == "processing_completed"
            ]
            if len(completed_processing) >= 3:
                break

        except Exception as e:
            print(f"Error checking processing status: {e}")

        time.sleep(POLLING_INTERVAL)
    else:
        pytest.fail(
            f"Not all documents finished processing within {MAX_PROCESSING_TIMEOUT} seconds"
        )

    # Verify project overview contains all unique strings
    po_response = s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=f"projects/{race_project_id}/project_overview.json",
    )
    po_content = po_response["Body"].read().decode("utf-8")

    required_strings = [
        "RACE_STRING_ALPHA_001",
        "RACE_STRING_BETA_002",
        "RACE_STRING_GAMMA_003",
    ]
    for string in required_strings:
        assert string in po_content, (
            f"Project overview missing required string: {string}"
        )

    # Delete the race test project
    response = requests.delete(
        f"{API_URL}/projects/{race_project_id}",
        headers={"x-api-key": API_KEY},
    )
    assert response.status_code == 200
    result = response.json()
    assert "message" in result


def test_13_update_project_progress():
    """Test updating project progress"""
    progress_data = {
        "project_name": test_project_id,
        "task_id": "test-task-1",
        "status": "completed",
        "notes": "Test task completed successfully",
    }
    response = requests.post(
        f"{API_URL}/update-progress", headers=headers, json=progress_data
    )
    assert response.status_code == 200
    result = response.json()
    assert "message" in result


def test_16_timeline_api():
    """Test timeline API functionality"""
    response = requests.get(
        f"{API_URL}/projects/{test_project_id}/timeline",
        headers={"x-api-key": API_KEY},
    )
    assert response.status_code == 200
    result = response.json()
    assert "timeline" in result
    assert isinstance(result["timeline"], list)


def test_17_delete_project():
    """Test project deletion and verify cleanup"""
    # Delete the project
    response = requests.delete(
        f"{API_URL}/projects/{test_project_id}",
        headers={"x-api-key": API_KEY},
    )

    assert response.status_code == 200

    result = response.json()
    assert "message" in result

    # Verify S3 project files are deleted
    from botocore.exceptions import ClientError

    try:
        s3_client.head_object(
            Bucket=S3_BUCKET,
            Key=f"projects/{test_project_id}/project_overview.json",
        )
        pytest.fail("Project files still exist in S3 after deletion")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            pass  # Expected - files should be deleted
        else:
            raise

    s3vectors_client = boto3.client("s3vectors")
    vector_bucket = "dxhub-project-kb-vectors"
    index_name = "project-kb-index"

    vector_response = s3vectors_client.list_vectors(
        vectorBucketName=vector_bucket,
        indexName=index_name,
    )

    # Check if any vectors still exist for this project
    project_vectors = []
    for obj in vector_response.get("vectors", []):
        metadata = obj.get("metadata", {})
        if (
            isinstance(metadata, dict)
            and metadata.get("project_name") == test_project_id
        ):
            project_vectors.append(obj["key"])

    if project_vectors:
        pytest.fail(
            f"Vector files still exist after project deletion: {len(project_vectors)} vectors found"
        )

    # Verify DynamoDB items are deleted
    import os
    import sys

    sys.path.append(
        os.path.join(
            os.path.dirname(__file__), "..", "layers", "meeting_data", "python"
        )
    )
    from meeting_data import MeetingDataManager

    table_name = os.environ.get("BATCH_TABLE_NAME", "project-knowledge-data")
    meeting_manager = MeetingDataManager(table_name)

    timeline_items = meeting_manager.get_project_timeline(test_project_id)
    assert not timeline_items, (
        f"DynamoDB items still exist after project deletion: {len(timeline_items)} items found"
    )
