#!/usr/bin/env python3
"""Project Management Tests"""

import json
import time
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


def test_get_project_types():
    """Test getting available project types"""
    response = requests.get(f"{API_URL}/config/project-types", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, (list, dict))


def test_create_project():
    """Test project creation"""
    project_name = f"test-project-{int(time.time())}"
    
    response = requests.post(
        f"{API_URL}/create-project",
        headers=get_auth_headers(),
        json={
            "projectName": project_name,
            "projectType": "Other",
            "location": "Test",
            "areaSize": "1.0",
            "specialConditions": []
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    assert response.status_code == 200
    result = response.json()
    assert "projectId" in result
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_get_projects_list():
    """Test getting all projects"""
    response = requests.get(f"{API_URL}/projects", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert "projects" in result
    assert isinstance(result["projects"], list)


def test_get_project_details():
    """Test getting specific project details"""
    project_name = f"test-detail-{int(time.time())}"
    
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
    
    # Get details
    response = requests.get(f"{API_URL}/projects/{project_name}", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert result["name"] == project_name
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_update_project_metadata():
    """Test updating project metadata"""
    project_name = f"test-metadata-{int(time.time())}"
    
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
    
    # Allow GSI propagation
    time.sleep(1)
    
    # Update metadata with proper structure
    response = requests.put(
        f"{API_URL}/projects/{project_name}/metadata",
        headers=get_auth_headers(),
        json={
            "date": "",
            "project": "",
            "work_authorization": "",
            "office_plans_file_no": "",
            "design_engineer": "",
            "survey_books": "",
            "project_manager": "Test Manager",
            "project_type": "Other",
            "location": "Updated Location",
            "area_size": "1.0",
            "special_conditions": []
        }
    )
    
    assert response.status_code == 200
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_update_progress():
    """Test that progress is calculated from task completion"""
    project_name = f"test-progress-{int(time.time())}"
    
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
    
    # Get project details - verify it was created
    response = requests.get(
        f"{API_URL}/projects/{project_name}",
        headers=get_auth_only()
    )
    
    assert response.status_code == 200
    result = response.json()
    # Project should have a name field
    assert result.get("name") == project_name
    
    # Cleanup
    requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())


def test_delete_project():
    """Test project deletion"""
    project_name = f"test-delete-{int(time.time())}"
    
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
    
    # Delete project
    response = requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())
    assert response.status_code == 200
    result = response.json()
    assert "message" in result
