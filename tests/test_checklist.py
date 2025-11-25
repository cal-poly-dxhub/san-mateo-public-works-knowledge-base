#!/usr/bin/env python3
"""Checklist Management Tests"""

import json
import time
from datetime import datetime
import pytest
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


def test_get_checklist():
    """Test getting project checklist"""
    project_name = f"test-checklist-{int(time.time())}"
    
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
    
    # Get checklist
    response = requests.get(
        f"{API_URL}/projects/{project_name}/checklist",
        headers=get_auth_only()
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result
    assert "metadata" in result
    assert "progress" in result
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_add_custom_task():
    """Test adding custom task to checklist"""
    project_name = f"test-add-task-{int(time.time())}"
    
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
    
    # Add custom task - API expects checklist_task_id and description
    response = requests.post(
        f"{API_URL}/projects/{project_name}/checklist/task",
        headers=get_auth_headers(),
        json={
            "checklist_task_id": "CUSTOM-001",
            "description": "Custom task description",
            "checklist_type": "design"
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "task_id" in result or "taskId" in result or "item_id" in result
    
    # Verify task was added - checklist returns task_id field
    checklist_response = requests.get(
        f"{API_URL}/projects/{project_name}/checklist?type=design",
        headers=get_auth_only()
    )
    tasks = checklist_response.json().get("tasks", [])
    custom_task = next((t for t in tasks if "CUSTOM-001" in t.get("task_id", "")), None)
    assert custom_task is not None
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_edit_custom_task():
    """Test editing custom task"""
    project_name = f"test-edit-task-{int(time.time())}"
    
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
    
    # Add custom task
    add_response = requests.post(
        f"{API_URL}/projects/{project_name}/checklist/task",
        headers=get_auth_headers(),
        json={
            "checklist_task_id": "EDIT-001",
            "description": "Original description",
            "checklist_type": "design"
        }
    )
    
    task_id = (add_response.json().get("task_id") or 
               add_response.json().get("taskId") or 
               add_response.json().get("item_id"))
    
    # Edit task - frontend sends task_id (full) and checklist_task_id (short)
    response = requests.put(
        f"{API_URL}/projects/{project_name}/checklist/task",
        headers=get_auth_headers(),
        json={
            "task_id": task_id,
            "checklist_task_id": "EDIT-001",
            "description": "Updated description",
            "checklist_type": "design"
        }
    )
    
    assert response.status_code == 200
    
    # Verify changes
    checklist_response = requests.get(
        f"{API_URL}/projects/{project_name}/checklist?type=design",
        headers=get_auth_only()
    )
    tasks = checklist_response.json().get("tasks", [])
    updated_task = next((t for t in tasks if t.get("task_id") == task_id), None)
    assert updated_task is not None
    assert updated_task.get("description") == "Updated description"
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_delete_custom_task():
    """Test deleting custom task"""
    project_name = f"test-delete-task-{int(time.time())}"
    
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
    
    # Add custom task
    add_response = requests.post(
        f"{API_URL}/projects/{project_name}/checklist/task",
        headers=get_auth_headers(),
        json={
            "checklist_task_id": "DELETE-001",
            "description": "Will be deleted",
            "checklist_type": "design"
        }
    )
    
    task_id = (add_response.json().get("task_id") or 
               add_response.json().get("taskId") or 
               add_response.json().get("item_id"))
    
    # Delete task
    response = requests.delete(
        f"{API_URL}/projects/{project_name}/checklist/task",
        headers=get_auth_headers(),
        json={"task_id": task_id}
    )
    
    assert response.status_code == 200
    
    # Verify task is gone
    checklist_response = requests.get(
        f"{API_URL}/projects/{project_name}/checklist?type=design",
        headers=get_auth_only()
    )
    tasks = checklist_response.json().get("tasks", [])
    deleted_task = next((t for t in tasks if t.get("item_id") == task_id), None)
    assert deleted_task is None
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_get_global_checklist():
    """Test getting global checklist"""
    response = requests.get(
        f"{API_URL}/global-checklist?type=design",
        headers=get_auth_only()
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "tasks" in result


def test_update_global_checklist():
    """Test updating global checklist"""
    # Get current checklist
    response = requests.get(
        f"{API_URL}/global-checklist?type=design",
        headers=get_auth_only()
    )
    assert response.status_code == 200
    result = response.json()
    tasks = result.get("tasks", [])
    
    if tasks:
        tasks[0]["description"] = f"Updated at {int(time.time())}"
    
    # Update checklist
    update_response = requests.put(
        f"{API_URL}/global-checklist?type=design",
        headers=get_auth_headers(),
        json={"tasks": tasks}
    )
    
    assert update_response.status_code == 200


def test_sync_global_checklist():
    """Test syncing global checklist to projects"""
    response = requests.post(
        f"{API_URL}/global-checklist/sync",
        headers=get_auth_headers()
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result.get("message") == "Global sync started"
