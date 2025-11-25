#!/usr/bin/env python3
"""Task Management Tests"""

import time
import requests
from .test_config import API_URL
from .conftest import get_cached_auth_token


def get_auth_only():
    return {"Authorization": get_cached_auth_token()}


def get_auth_headers():
    return {
        "Authorization": get_cached_auth_token(),
        "Content-Type": "application/json"
    }


def test_get_tasks():
    """Test getting all tasks for a project"""
    project_name = f"test-tasks-{int(time.time())}"
    
    # Create project
    requests.post(
        f"{API_URL}/setup-wizard",
        headers=get_auth_headers(),
        json={
            "projectName": project_name,
            "projectType": "Other",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
    )
    
    # Get tasks
    response = requests.get(
        f"{API_URL}/projects/{project_name}/tasks",
        headers=get_auth_only()
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result
    assert "progress" in result
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_create_task():
    """Test creating a new task"""
    project_name = f"test-create-task-{int(time.time())}"
    
    # Create project
    requests.post(
        f"{API_URL}/setup-wizard",
        headers=get_auth_headers(),
        json={
            "projectName": project_name,
            "projectType": "Other",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
    )
    
    # Create task
    response = requests.post(
        f"{API_URL}/projects/{project_name}/tasks",
        headers=get_auth_headers(),
        json={
            "title": "Test Task",
            "description": "Task description",
            "assignee": "test-user"
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "taskId" in result
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_update_task():
    """Test updating task status"""
    project_name = f"test-update-task-{int(time.time())}"
    
    # Create project
    requests.post(
        f"{API_URL}/setup-wizard",
        headers=get_auth_headers(),
        json={
            "projectName": project_name,
            "projectType": "Other",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
    )
    
    # Create task
    create_response = requests.post(
        f"{API_URL}/projects/{project_name}/tasks",
        headers=get_auth_headers(),
        json={
            "title": "Task to Update",
            "description": "Will be updated",
            "assignee": "test-user"
        }
    )
    
    task_id = create_response.json()["taskId"]
    
    # Update task
    response = requests.put(
        f"{API_URL}/projects/{project_name}/tasks/{task_id}",
        headers=get_auth_headers(),
        json={
            "status": "completed",
            "notes": "Task completed"
        }
    )
    
    assert response.status_code == 200
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())
