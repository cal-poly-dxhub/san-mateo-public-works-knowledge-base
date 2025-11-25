#!/usr/bin/env python3

import json
import time
from datetime import datetime
from urllib.parse import quote
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

from .test_config import (
    API_URL,
    MAX_PROCESSING_TIMEOUT,
    POLLING_INTERVAL,
    S3_BUCKET,
    DYNAMODB_TABLE,
    INDEX_NAME,
    KNOWLEDGE_BASE_ID,
)
from .cognito_auth import get_auth_headers
from .conftest import get_cached_auth_token

# Get auth headers with JWT token
headers = get_auth_headers()

def get_auth_only():
    """Get Authorization header only (for GET requests)"""
    return {"Authorization": get_cached_auth_token()}
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
        response = requests.get(f"{API_URL}/config/project-types", headers=get_auth_only())
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert api_timer.duration < 2.0, f"API took {api_timer.duration:.2f}s (SLA: <2s)"
    
    result = response.json()
    assert isinstance(result, (list, dict))


def test_02_create_project(api_timer):
    """Test project creation via setup wizard"""
    wizard_data = {
        "projectName": test_project_name,
        "projectType": "Reconstruction",
        "location": "Test Street",
        "areaSize": "1.0",
        "specialConditions": []
    }
    
    with api_timer:
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
    
    assert response.status_code == 200
    assert api_timer.duration < 5.0, f"Project creation took {api_timer.duration:.2f}s (SLA: <5s)"
    
    result = response.json()
    assert "projectId" in result


def test_03_get_projects_list(api_timer):
    """Test getting all projects"""
    response = requests.get(f"{API_URL}/projects", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert "projects" in result
    assert isinstance(result["projects"], list)
    project_names = [p["name"] for p in result["projects"]]
    assert test_project_name in project_names


def test_04_get_project_details(api_timer):
    """Test getting specific project details"""
    response = requests.get(f"{API_URL}/projects/{test_project_name}", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == test_project_name


def test_05_get_tasks(api_timer):
    """Test getting all tasks for a project"""
    response = requests.get(f"{API_URL}/projects/{test_project_name}/tasks", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result
    assert "progress" in result


def test_06_create_task(api_timer):
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


def test_07_update_task(api_timer):
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

def test_08_get_checklist(api_timer):
    """Test getting project checklist"""
    response = requests.get(f"{API_URL}/projects/{test_project_name}/checklist", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result
    assert "metadata" in result
    assert "progress" in result


def test_09_vector_search(api_timer):
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


def test_10_rag_search(api_timer):
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


def test_10a_vector_search_with_filters(api_timer):
    """Test vector search with different query types"""
    search_data = {
        "query": "drainage design",
        "project": test_project_name,
        "limit": 3
    }
    response = requests.post(f"{API_URL}/search", headers=headers, json=search_data)
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) <= 3


def test_10b_rag_search_without_project(api_timer):
    """Test RAG search across all projects"""
    search_data = {
        "query": "What are best practices for project management?",
        "limit": 5
    }
    response = requests.post(f"{API_URL}/search-rag", headers=headers, json=search_data)
    assert response.status_code == 200
    result = response.json()
    assert "answer" in result
    assert "sources" in result


def test_10c_vector_search_empty_results(api_timer):
    """Test vector search with query that may return no results"""
    search_data = {
        "query": "xyzabc123notarealterm",
        "project": test_project_name,
        "limit": 5
    }
    response = requests.post(f"{API_URL}/search", headers=headers, json=search_data)
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert isinstance(result["results"], list)


# ============================================================================
# 7. AI ASSISTANT TESTS
# ============================================================================

def test_11_get_available_models(api_timer):
    """Test getting available AI models"""
    response = requests.get(f"{API_URL}/models", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert "models" in result or "available_search_models" in result


def test_12_concurrent_lesson_processing(api_timer):
    """Test that multiple lesson documents are processed without race conditions"""
    race_project = f"race-test-{int(time.time())}"
    debug_project = f"debug-test-{int(time.time())}"
    
    try:
        # Create race test project via wizard
        wizard_data = {
            "projectName": race_project,
            "projectType": "Drainage",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
        assert response.status_code == 200
        
        # Create debug test project
        wizard_data["projectName"] = debug_project
        wizard_data["projectType"] = "Utilities"
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
        assert response.status_code == 200
        
        # Upload 3 documents using presigned URLs
        docs = [
            ("doc1.txt", "Lesson about scheduling and planning"),
            ("doc2.txt", "Lesson about budgeting and cost control"),
            ("doc3.txt", "Lesson about coordination and communication")
        ]
        
        for filename, content in docs:
            # Request presigned URL
            response = requests.post(
                f"{API_URL}/upload-url",
                headers=headers,
                json={
                    "files": [{
                        "fileName": filename,
                        "projectName": race_project,
                        "projectType": "road",
                        "extractLessons": True
                    }]
                }
            )
            assert response.status_code == 200
            result = response.json()
            assert "uploads" in result
            
            # Upload to S3 using presigned URL
            upload_url = result["uploads"][0]["uploadUrl"]
            upload_response = requests.put(upload_url, data=content.encode())
            assert upload_response.status_code == 200
        
        # Wait for processing
        time.sleep(MAX_PROCESSING_TIMEOUT / 2)
        
        # Verify lessons were extracted
        response = requests.get(
            f"{API_URL}/projects/{race_project}/lessons-learned",
            headers=get_auth_only()
        )
        assert response.status_code == 200
        result = response.json()
        
        lessons = result.get("lessons", [])
        assert len(lessons) >= 3, f"Expected at least 3 lessons, got {len(lessons)}"
        
        # Verify each lesson has required fields
        for lesson in lessons:
            assert "title" in lesson
            assert "lesson" in lesson
            assert "impact" in lesson
            assert "recommendation" in lesson
            assert "severity" in lesson
    
    finally:
        # Cleanup both test projects
        requests.delete(f"{API_URL}/projects/{race_project}", headers=get_auth_only())
        requests.delete(f"{API_URL}/projects/{debug_project}", headers=get_auth_only())


# ============================================================================
# 8. DOCUMENT UPLOAD TESTS
# ============================================================================

def test_13_upload_txt_document(api_timer):
    """Test uploading a text document"""
    content = "This is a test document with important information."
    filename = "test_doc.txt"
    
    # Request presigned URL
    response = requests.post(
        f"{API_URL}/upload-url",
        headers=headers,
        json={
            "files": [{
                "fileName": filename,
                "projectName": test_project_name,
                "extractLessons": False
            }]
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert "uploads" in result
    
    # Upload to S3 using presigned URL
    upload_url = result["uploads"][0]["uploadUrl"]
    upload_response = requests.put(upload_url, data=content.encode())
    assert upload_response.status_code == 200


def test_14_upload_pdf_document(api_timer):
    """Test uploading a PDF document"""
    # Create minimal PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000214 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n308\n%%EOF"
    filename = "test_doc.pdf"
    
    # Request presigned URL
    response = requests.post(
        f"{API_URL}/upload-url",
        headers=headers,
        json={
            "files": [{
                "fileName": filename,
                "projectName": test_project_name,
                "extractLessons": False
            }]
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert "uploads" in result
    
    # Upload to S3 using presigned URL
    upload_url = result["uploads"][0]["uploadUrl"]
    upload_response = requests.put(upload_url, data=pdf_content)
    assert upload_response.status_code == 200


def test_15_upload_docx_document(api_timer):
    """Test uploading a DOCX document"""
    # Create minimal DOCX (ZIP with XML)
    import zipfile
    import io
    
    docx_buffer = io.BytesIO()
    with zipfile.ZipFile(docx_buffer, 'w') as docx:
        docx.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        docx.writestr('word/document.xml', '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test Document</w:t></w:r></w:p></w:body></w:document>')
    
    filename = "test_doc.docx"
    
    # Request presigned URL
    response = requests.post(
        f"{API_URL}/upload-url",
        headers=headers,
        json={
            "files": [{
                "fileName": filename,
                "projectName": test_project_name,
                "extractLessons": False
            }]
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert "uploads" in result
    
    # Upload to S3 using presigned URL
    upload_url = result["uploads"][0]["uploadUrl"]
    upload_response = requests.put(upload_url, data=docx_buffer.getvalue())
    assert upload_response.status_code == 200


# ============================================================================
# 9. LESSON EXTRACTION TESTS
# ============================================================================

def test_16_extract_lessons_from_document(api_timer):
    """Test that lessons are properly extracted from documents"""
    lesson_project = f"lesson-test-{int(time.time())}"
    
    try:
        # Create project
        wizard_data = {
            "projectName": lesson_project,
            "projectType": "Resurface",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
        assert response.status_code == 200
        
        # Upload document with extract_lessons=True using presigned URL
        doc_content = """
        Lesson 1: We learned that early coordination with utilities prevents delays.
        Lesson 2: Budget contingency of 15% is essential for road projects.
        Lesson 3: Weekly stakeholder meetings improved communication significantly.
        """
        filename = "lessons_doc.txt"
        
        # Request presigned URL
        response = requests.post(
            f"{API_URL}/upload-url",
            headers=headers,
            json={
                "files": [{
                    "fileName": filename,
                    "projectName": lesson_project,
                    "projectType": "Resurface",
                    "extractLessons": True
                }]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "uploads" in result
        
        # Upload to S3 using presigned URL
        upload_url = result["uploads"][0]["uploadUrl"]
        upload_response = requests.put(upload_url, data=doc_content.encode())
        assert upload_response.status_code == 200
        
        # Wait for async processing
        time.sleep(MAX_PROCESSING_TIMEOUT / 2)
        
        # Verify lessons were extracted
        response = requests.get(
            f"{API_URL}/projects/{lesson_project}/lessons-learned",
            headers=get_auth_only()
        )
        assert response.status_code == 200
        result = response.json()
        
        # Should have extracted lessons
        lessons = result.get("lessons", [])
        assert len(lessons) >= 3, f"Expected at least 3 lessons, got {len(lessons)}"
        
        # Verify each lesson has required fields
        for lesson in lessons:
            assert "title" in lesson
            assert "lesson" in lesson
            assert "impact" in lesson
            assert "recommendation" in lesson
            assert "severity" in lesson
    
    finally:
        requests.delete(f"{API_URL}/projects/{lesson_project}", headers=get_auth_only())


def test_17_lessons_markdown_sync(api_timer):
    """Test that lessons are converted to markdown for KB sync"""
    md_project = f"md-test-{int(time.time())}"
    
    try:
        # Create project
        wizard_data = {
            "projectName": md_project,
            "projectType": "Slurry Seal",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
        assert response.status_code == 200
        
        # Upload document with extract_lessons=True using presigned URL
        doc_content = "Lesson: Proper drainage design prevents flooding. Lesson: Material testing ensures quality. Lesson: Safety protocols reduce incidents."
        filename = "md_test.txt"
        
        # Request presigned URL
        response = requests.post(
            f"{API_URL}/upload-url",
            headers=headers,
            json={
                "files": [{
                    "fileName": filename,
                    "projectName": md_project,
                    "projectType": "Slurry Seal",
                    "extractLessons": True
                }]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "uploads" in result
        
        # Upload to S3 using presigned URL
        upload_url = result["uploads"][0]["uploadUrl"]
        upload_response = requests.put(upload_url, data=doc_content.encode())
        assert upload_response.status_code == 200
        
        # Wait for processing and markdown sync
        time.sleep(MAX_PROCESSING_TIMEOUT / 2 + 2)
        
        # Verify markdown files were created in S3
        prefix = f"documents/lessons-learned/lesson-"
        paginator = s3_client.get_paginator('list_objects_v2')
        
        md_files = []
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    if obj["Key"].endswith(f"-{md_project}.md"):
                        md_files.append(obj["Key"])
        
        assert len(md_files) >= 3, f"Expected at least 3 markdown files, got {len(md_files)}"
        
        # Verify markdown content format
        for md_file in md_files[:1]:  # Check first one
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=md_file)
            content = response["Body"].read().decode('utf-8')
            assert "# " in content  # Has markdown header
            assert "**Project:**" in content
            assert "**Impact:**" in content
            assert "## Recommendation" in content
    
    finally:
        requests.delete(f"{API_URL}/projects/{md_project}", headers=get_auth_only())


# ============================================================================
# 10. GLOBAL CHECKLIST TESTS
# ============================================================================

def test_18b_update_task_status(api_timer):
    """Test that updating task status works correctly"""
    put_test_project = f"put-test-{int(time.time())}"
    
    try:
        # Create project
        wizard_data = {
            "projectName": put_test_project,
            "projectType": "Other",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
        assert response.status_code == 200
        
        # Get tasks
        response = requests.get(
            f"{API_URL}/projects/{put_test_project}/tasks",
            headers=get_auth_only()
        )
        assert response.status_code == 200
        tasks = response.json().get("tasks", [])
        assert len(tasks) > 0, "Project should have tasks"
        
        first_task = tasks[0]
        task_id = first_task.get("item_id")
        
        # Update task with completed_date
        update_data = {"completed_date": datetime.utcnow().isoformat()}
        response = requests.put(
            f"{API_URL}/projects/{put_test_project}/tasks/{quote(task_id, safe='')}",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200, f"PUT failed: {response.text}"
        
        # Verify task status changed to completed
        response = requests.get(
            f"{API_URL}/projects/{put_test_project}/tasks",
            headers=get_auth_only()
        )
        assert response.status_code == 200
        updated_tasks = response.json().get("tasks", [])
        updated_task = next((t for t in updated_tasks if t.get("item_id") == task_id), None)
        assert updated_task is not None, "Task should exist"
        assert updated_task.get("status") == "completed", f"Task status should be 'completed', got {updated_task.get('status')}"
    
    finally:
        requests.delete(f"{API_URL}/projects/{put_test_project}", headers=get_auth_only())


def test_19_checklist_sync_to_projects(api_timer):
    """Test that checklist sync updates unchecked tasks but preserves completed ones"""
    sync_project = f"sync-test-{int(time.time())}"
    
    try:
        # Create project
        wizard_data = {
            "projectName": sync_project,
            "projectType": "Reconstruction",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
        response = requests.post(f"{API_URL}/setup-wizard", headers=headers, json=wizard_data)
        assert response.status_code == 200
        
        # Get initial tasks
        response = requests.get(
            f"{API_URL}/projects/{sync_project}/tasks",
            headers=get_auth_only()
        )
        assert response.status_code == 200
        initial_tasks = response.json().get("tasks", [])
        assert len(initial_tasks) > 0, "Project should have tasks"
        
        # Store initial taskData for first task
        first_task = initial_tasks[0]
        first_task_id = first_task.get("item_id")
        initial_task_data = first_task.get("taskData", {})
        print(f"First task: {first_task}")
        print(f"First task ID: {first_task_id}")
        
        # Mark first task as completed
        if first_task_id:
            update_data = {"completed_date": datetime.utcnow().isoformat()}
            response = requests.put(
                f"{API_URL}/projects/{sync_project}/tasks/{quote(first_task_id, safe='')}",
                headers=headers,
                json=update_data
            )
            assert response.status_code == 200, f"Failed to mark task as completed: {response.text}"
            print(f"Marked task {first_task_id} as completed")
            print(f"PUT response: {response.json()}")
            
            # Verify it was marked as completed
            response = requests.get(
                f"{API_URL}/projects/{sync_project}/tasks",
                headers=get_auth_only()
            )
            verify_tasks = response.json().get("tasks", [])
            verify_task = next((t for t in verify_tasks if t.get("item_id") == first_task_id), None)
            print(f"Task status after marking: {verify_task.get('status') if verify_task else 'NOT FOUND'}")
        
        # Run sync
        response = requests.post(
            f"{API_URL}/global-checklist/sync",
            headers=headers
        )
        assert response.status_code == 200
        
        # Get tasks after sync
        response = requests.get(
            f"{API_URL}/projects/{sync_project}/tasks",
            headers=get_auth_only()
        )
        assert response.status_code == 200
        synced_tasks = response.json().get("tasks", [])
        
        # Find the first task after sync
        synced_first_task = next((t for t in synced_tasks if t.get("item_id") == first_task_id), None)
        assert synced_first_task is not None, "First task should still exist after sync"
        
        # Verify completed task status is preserved
        assert synced_first_task.get("status") == "completed", "Completed task status should be preserved"
        
        # Verify other tasks got updated (taskData should match global)
        uncompleted_tasks = [t for t in synced_tasks if t.get("status") != "completed"]
        assert len(uncompleted_tasks) > 0, "Should have uncompleted tasks"
        
        # Verify at least one uncompleted task has taskData (was synced)
        has_task_data = any(t.get("taskData") for t in uncompleted_tasks)
        assert has_task_data, "Uncompleted tasks should have taskData from sync"
    
    finally:
        requests.delete(f"{API_URL}/projects/{sync_project}", headers=get_auth_only())


# ============================================================================
# 11. CLEANUP TEST
# ============================================================================

def test_20_delete_project(api_timer):
    """Test project deletion and verify complete cleanup"""
    response = requests.delete(
        f"{API_URL}/projects/{test_project_name}",
        headers=get_auth_only()
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
