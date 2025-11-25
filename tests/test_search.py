#!/usr/bin/env python3
"""Search and Knowledge Base Tests"""

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


def test_vector_search():
    """Test semantic vector search"""
    response = requests.post(
        f"{API_URL}/search",
        headers=get_auth_headers(),
        json={
            "query": "utility coordination timeline",
            "limit": 5
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert isinstance(result["results"], list)


def test_rag_search():
    """Test RAG search with AI-generated answer"""
    response = requests.post(
        f"{API_URL}/search-rag",
        headers=get_auth_headers(),
        json={
            "query": "What are best practices for utility coordination?",
            "limit": 10
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "answer" in result
    assert "sources" in result
    assert "type" in result
    assert result["type"] == "rag"


def test_get_available_models():
    """Test getting available AI models"""
    response = requests.get(f"{API_URL}/models", headers=get_auth_only())
    
    assert response.status_code == 200
    result = response.json()
    assert "models" in result or "available_search_models" in result


def test_trigger_kb_sync():
    """Test triggering manual Knowledge Base sync"""
    response = requests.post(
        f"{API_URL}/sync/knowledge-base",
        headers=get_auth_headers()
    )
    
    # Should succeed or indicate sync already in progress
    assert response.status_code in [200, 409]
    
    if response.status_code == 200:
        result = response.json()
        assert "job_id" in result or "jobId" in result or "message" in result


def test_get_kb_sync_status():
    """Test getting Knowledge Base sync status"""
    response = requests.get(
        f"{API_URL}/sync/knowledge-base/status",
        headers=get_auth_only()
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "status" in result or "state" in result or "message" in result
