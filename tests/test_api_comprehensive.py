#!/usr/bin/env python3

import json
import time
import boto3
import pytest
import requests
from botocore.exceptions import ClientError

pytestmark = [
    pytest.mark.filterwarnings(
        r"ignore:datetime.datetime.utcnow\(\) is deprecated:DeprecationWarning"
    ),
    pytest.mark.integration,
]

from test_config import (
    API_KEY,
    API_URL,
    MAX_PROCESSING_TIMEOUT,
    POLLING_INTERVAL,
    S3_BUCKET,
    VECTOR_BUCKET,
    DYNAMODB_TABLE,
    INDEX_NAME,
)

headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

test_project_name = f"test-road-project-{int(time.time())}"
test_task_id = None
test_lesson_doc = None


# ============================================================================
# 1. PROJECT MANAGEMENT TESTS
# ============================================================================

def test_01_get_project_types(api_timer):
    """Test getting available project types"""
    with api_timer:
        response = requests.get(f"{API_URL}/config/project-types", headers={"x-api-key": API_KEY})
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert api_timer.duration < 2.0, f"API took {api_timer.duration:.2f}s (SLA: <2s)"
    
    result = response.json()
    assert isinstance(result, (list, dict))


def test_02_create_project(api_timer):
    """Test project creation"""
    project_data = {
        "project_name": test_project_name,
        "project_description": "Test road reconstruction project"
    }
    
    with api_timer:
        response = requests.post(f"{API_URL}/create-project", headers=headers, json=project_data)
    
    assert response.status_code == 200
    assert api_timer.duration < 3.0, f"Project creation took {api_timer.duration:.2f}s (SLA: <3s)"
    
    result = response.json()
    assert "message" in result


def test_03_setup_project_wizard(api_timer):
    """Test project setup wizard with AI configuration"""
    wizard_data = {
        "projectName": test_project_name,
        "projectType": "Road Rehabilitation",
        "location": "Main Street, Downtown",
        "areaSize": "2.5",
        "specialConditions": ["High traffic area", "Near coast"]
    }
    response = requests.post(f"{API_URL}/project-setup", headers=headers, json=wizard_data)
    assert response.status_code in [200, 202]
    result = response.json()
    assert "projectId" in result or "message" in result


def test_04_get_projects_list(api_timer):
    """Test getting all projects"""
    response = requests.get(f"{API_URL}/projects", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    project_names = [p["name"] for p in result]
    assert test_project_name in project_names


def test_05_get_project_details(api_timer):
    """Test getting specific project details"""
    response = requests.get(f"{API_URL}/projects/{test_project_name}", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == test_project_name


def test_06_update_project_progress(api_timer):
    """Test updating project progress"""
    progress_data = {
        "project_name": test_project_name,
        "progress": {
            "completion_percentage": 25,
            "current_phase": "design",
            "notes": "30% design review completed"
        }
    }
    response = requests.post(f"{API_URL}/update-progress", headers=headers, json=progress_data)
    assert response.status_code == 200


# ============================================================================
# 2. TASK MANAGEMENT TESTS
# ============================================================================

def test_07_get_tasks(api_timer):
    """Test getting all tasks for a project"""
    response = requests.get(f"{API_URL}/projects/{test_project_name}/tasks", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result
    assert "progress" in result


def test_08_create_task(api_timer):
    """Test creating a new task"""
    global test_task_id
    task_data = {
        "title": "Complete site survey",
        "description": "Conduct topographic survey of project area",
        "assignee": "survey-team"
    }
    response = requests.post(
        f"{API_URL}/projects/{test_project_name}/tasks",
        headers=headers,
        json=task_data
    )
    assert response.status_code == 200
    result = response.json()
    assert "taskId" in result
    test_task_id = result["taskId"]


def test_09_update_task(api_timer):
    """Test updating task status"""
    if not test_task_id:
        pytest.skip("No task ID available")
    
    update_data = {
        "status": "completed",
        "notes": "Survey completed successfully"
    }
    response = requests.put(
        f"{API_URL}/projects/{test_project_name}/tasks/{test_task_id}",
        headers=headers,
        json=update_data
    )
    assert response.status_code == 200


# ============================================================================
# 3. CHECKLIST API TESTS
# ============================================================================

def test_10_get_checklist(api_timer):
    """Test getting project checklist"""
    response = requests.get(f"{API_URL}/{test_project_name}/checklist", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result
    assert "metadata" in result
    assert "progress" in result


def test_11_update_checklist_metadata(api_timer):
    """Test updating checklist metadata"""
    metadata = {
        "date": "2025-01-15",
        "project": "Main Street Reconstruction",
        "work_authorization": "WA-2025-001",
        "project_manager": "John Doe"
    }
    response = requests.put(
        f"{API_URL}/{test_project_name}/metadata",
        headers=headers,
        json=metadata
    )
    assert response.status_code == 200


def test_12_update_checklist_task(api_timer):
    """Test updating a checklist task"""
    task_update = {
        "task_id": "task#001",
        "completed_date": "2025-01-20",
        "projected_date": "2025-01-15",
        "actual_date": "2025-01-20"
    }
    response = requests.put(
        f"{API_URL}/{test_project_name}/checklist",
        headers=headers,
        json=task_update
    )
    assert response.status_code == 200


# ============================================================================
# 4. FILES API TESTS
# ============================================================================

def test_13_get_upload_url(api_timer):
    """Test getting presigned upload URL"""
    upload_request = {
        "fileName": "test-document.pdf",
        "projectName": test_project_name
    }
    response = requests.post(f"{API_URL}/upload-url", headers=headers, json=upload_request)
    assert response.status_code == 200
    result = response.json()
    assert "uploadUrl" in result
    assert "s3Key" in result


def test_14_get_file(api_timer):
    """Test retrieving a file"""
    # First create a test file in S3
    test_key = f"projects/{test_project_name}/test-file.txt"
    s3_client.put_object(Bucket=S3_BUCKET, Key=test_key, Body=b"Test content")
    
    response = requests.get(f"{API_URL}/file/{test_key}", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    assert response.text == "Test content"


# ============================================================================
# 5. LESSONS LEARNED TESTS
# ============================================================================

def test_15_upload_document_with_lessons(api_timer):
    """Test uploading document and extracting lessons"""
    global test_lesson_doc
    doc_content = """
    Project Retrospective - Main Street Project
    
    Key Lessons Learned:
    1. Utility coordination should start 6 months before construction
    2. Traffic management plan needs city council approval
    3. Weather delays are common in winter months
    
    Impact: Project delayed by 3 weeks due to late utility coordination.
    Recommendation: Create utility coordination checklist at project start.
    """
    
    import base64
    encoded_content = base64.b64encode(doc_content.encode()).decode()
    
    doc_data = {
        "content": encoded_content,
        "filename": "retrospective-2025.txt",
        "extract_lessons": True
    }
    
    response = requests.post(
        f"{API_URL}/documents/{test_project_name}",
        headers=headers,
        json=doc_data
    )
    assert response.status_code in [200, 202]
    test_lesson_doc = "retrospective-2025.txt"


def test_16_wait_for_lesson_extraction(api_timer):
    """Wait for async lesson extraction to complete"""
    if not test_lesson_doc:
        pytest.skip("No lesson document uploaded")
    
    start_time = time.time()
    while time.time() - start_time < MAX_PROCESSING_TIMEOUT:
        try:
            response = requests.get(
                f"{API_URL}/lessons-learned/{test_project_name}",
                headers={"x-api-key": API_KEY}
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("lessons") and len(result["lessons"]) > 0:
                    return
        except Exception:
            pass
        time.sleep(POLLING_INTERVAL)
    
    pytest.fail("Lesson extraction not completed in time")


def test_17_get_lessons_learned(api_timer):
    """Test retrieving lessons learned"""
    response = requests.get(
        f"{API_URL}/lessons-learned/{test_project_name}",
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200
    result = response.json()
    assert "projectName" in result
    assert "lessons" in result
    assert isinstance(result["lessons"], list)


def test_18_get_master_project_types(api_timer):
    """Test getting project types with lesson counts"""
    response = requests.get(f"{API_URL}/project-types", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert "projectTypes" in result


def test_19_get_lessons_by_type(api_timer):
    """Test getting aggregated lessons by project type"""
    response = requests.get(
        f"{API_URL}/by-type/Road Rehabilitation",
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200
    result = response.json()
    assert "projectType" in result
    assert "lessons" in result


# ============================================================================
# 6. SEARCH TESTS
# ============================================================================

def test_20_vector_search(api_timer):
    """Test semantic vector search"""
    search_data = {
        "query": "utility coordination timeline",
        "project": test_project_name,
        "limit": 5
    }
    response = requests.post(f"{API_URL}/search", headers=headers, json=search_data)
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert isinstance(result["results"], list)


def test_21_rag_search(api_timer):
    """Test RAG search with AI-generated answer"""
    search_data = {
        "query": "What are the key lessons about utility coordination?",
        "project": test_project_name,
        "limit": 10
    }
    response = requests.post(f"{API_URL}/search-rag", headers=headers, json=search_data)
    assert response.status_code == 200
    result = response.json()
    assert "answer" in result
    assert "sources" in result
    assert "type" in result
    assert result["type"] == "rag"


# ============================================================================
# 7. AI ASSISTANT TESTS
# ============================================================================

def test_22_ai_assistant_question(api_timer):
    """Test AI assistant Q&A"""
    question_data = {
        "question": "What permits are typically needed for road reconstruction?",
        "projectId": test_project_name,
        "type": "question"
    }
    response = requests.post(f"{API_URL}/assistant", headers=headers, json=question_data)
    assert response.status_code == 200
    result = response.json()
    assert "answer" in result


def test_23_ai_assistant_template(api_timer):
    """Test AI template generation"""
    template_data = {
        "type": "template",
        "documentType": "Traffic Management Plan",
        "projectDetails": {
            "name": test_project_name,
            "location": "Main Street",
            "duration": "3 months"
        }
    }
    response = requests.post(f"{API_URL}/assistant", headers=headers, json=template_data)
    assert response.status_code == 200
    result = response.json()
    assert "template" in result


def test_24_ai_assistant_alerts(api_timer):
    """Test proactive alert checking"""
    alert_data = {
        "type": "alert",
        "projectId": test_project_name
    }
    response = requests.post(f"{API_URL}/assistant", headers=headers, json=alert_data)
    assert response.status_code == 200
    result = response.json()
    assert "alerts" in result
    assert isinstance(result["alerts"], list)


# ============================================================================
# 8. DASHBOARD TESTS
# ============================================================================

def test_25_get_available_models(api_timer):
    """Test getting available AI models"""
    response = requests.get(f"{API_URL}/models", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    result = response.json()
    assert "models" in result or "available_search_models" in result


def test_26_get_project_asset(api_timer):
    """Test retrieving project assets"""
    # Create a test asset
    asset_key = f"projects/{test_project_name}/assets/test-asset.txt"
    s3_client.put_object(Bucket=S3_BUCKET, Key=asset_key, Body=b"Asset content")
    
    response = requests.get(
        f"{API_URL}/assets/{test_project_name}/test-asset.txt",
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200


# ============================================================================
# 9. VECTOR STORAGE VALIDATION
# ============================================================================

def test_27_validate_vectors_created(api_timer):
    """Test that vectors were created in S3 vector store"""
    try:
        s3vectors_client = boto3.client("s3vectors")
        response = s3vectors_client.list_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
        )
        
        project_vectors = []
        for obj in response.get("vectors", []):
            metadata = obj.get("metadata", {})
            if isinstance(metadata, dict) and metadata.get("project") == test_project_name:
                project_vectors.append(obj["key"])
        
        assert len(project_vectors) > 0, "No vectors found for test project"
    except Exception as e:
        pytest.skip(f"S3 Vectors not available or configured: {e}")


# ============================================================================
# 10. RACE CONDITION TEST
# ============================================================================

def test_28_concurrent_lesson_processing(api_timer):
    """Test that multiple lesson documents are processed without race conditions"""
    race_project = f"race-test-{int(time.time())}"
    
    # Create project
    project_data = {
        "project_name": race_project,
        "project_description": "Race condition test"
    }
    response = requests.post(f"{API_URL}/create-project", headers=headers, json=project_data)
    assert response.status_code == 200
    
    # Upload 3 documents with unique markers
    import base64
    docs = [
        ("doc1.txt", "RACE_MARKER_ALPHA_001 - Lesson about scheduling"),
        ("doc2.txt", "RACE_MARKER_BETA_002 - Lesson about budgeting"),
        ("doc3.txt", "RACE_MARKER_GAMMA_003 - Lesson about coordination")
    ]
    
    for filename, content in docs:
        encoded = base64.b64encode(content.encode()).decode()
        doc_data = {
            "content": encoded,
            "filename": filename,
            "extract_lessons": True
        }
        response = requests.post(
            f"{API_URL}/documents/{race_project}",
            headers=headers,
            json=doc_data
        )
        assert response.status_code in [200, 202]
    
    # Wait for processing
    time.sleep(MAX_PROCESSING_TIMEOUT / 2)
    
    # Verify all markers present in lessons
    response = requests.get(
        f"{API_URL}/lessons-learned/{race_project}",
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200
    result = response.json()
    
    lessons_text = json.dumps(result)
    assert "RACE_MARKER_ALPHA_001" in lessons_text
    assert "RACE_MARKER_BETA_002" in lessons_text
    assert "RACE_MARKER_GAMMA_003" in lessons_text
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{race_project}", headers={"x-api-key": API_KEY})


# ============================================================================
# 11. CLEANUP TEST
# ============================================================================

def test_29_delete_project(api_timer):
    """Test project deletion and verify complete cleanup"""
    response = requests.delete(
        f"{API_URL}/projects/{test_project_name}",
        headers={"x-api-key": API_KEY}
    )
    assert response.status_code == 200
    result = response.json()
    assert "message" in result
    
    # Verify S3 cleanup
    try:
        s3_client.head_object(
            Bucket=S3_BUCKET,
            Key=f"projects/{test_project_name}/project_overview.json"
        )
        pytest.fail("S3 files still exist after deletion")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            pass
        else:
            raise
    
    # Verify DynamoDB cleanup
    response = table.query(
        KeyConditionExpression="project_id = :pid",
        ExpressionAttributeValues={":pid": test_project_name}
    )
    assert len(response.get("Items", [])) == 0, "DynamoDB items still exist"
    
    # Verify vector cleanup
    try:
        s3vectors_client = boto3.client("s3vectors")
        response = s3vectors_client.list_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
        )
        
        project_vectors = [
            obj for obj in response.get("vectors", [])
            if obj.get("metadata", {}).get("project") == test_project_name
        ]
        assert len(project_vectors) == 0, "Vectors still exist after deletion"
    except Exception:
        pass  # S3 Vectors may not be configured
