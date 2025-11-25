#!/usr/bin/env python3
"""Document Upload Tests - Large files and batch uploads"""

import time
import requests
import boto3
import pytest
from .test_config import API_URL, S3_BUCKET
from .conftest import get_cached_auth_token

s3_client = boto3.client("s3")

LARGE_PDF_URL = "https://dot.ca.gov/-/media/dot-media/programs/design/documents/2025-standard-plans-locked.pdf"


def get_auth_headers():
    return {
        "Authorization": get_cached_auth_token(),
        "Content-Type": "application/json"
    }


def get_auth_only():
    return {"Authorization": get_cached_auth_token()}


def test_large_pdf_upload():
    """Test uploading a large PDF (~50MB) and verify it reaches S3"""
    project_name = f"test-large-pdf-{int(time.time())}"
    filename = "2025-standard-plans-locked.pdf"
    
    try:
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
        
        # Download the large PDF
        print(f"Downloading large PDF from {LARGE_PDF_URL}...")
        pdf_response = requests.get(LARGE_PDF_URL, timeout=120)
        assert pdf_response.status_code == 200, f"Failed to download PDF: {pdf_response.status_code}"
        pdf_content = pdf_response.content
        pdf_size = len(pdf_content)
        print(f"Downloaded PDF: {pdf_size / (1024*1024):.2f} MB")
        
        # Request presigned URL
        response = requests.post(
            f"{API_URL}/upload-url",
            headers=get_auth_headers(),
            json={
                "files": [{
                    "fileName": filename,
                    "projectName": project_name,
                    "extractLessons": False
                }]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "uploads" in result
        
        upload_url = result["uploads"][0]["uploadUrl"]
        s3_key = result["uploads"][0]["s3Key"]
        
        # Upload to S3 (no Content-Type header - presigned URL doesn't include it)
        print(f"Uploading {pdf_size / (1024*1024):.2f} MB to S3...")
        upload_response = requests.put(upload_url, data=pdf_content, timeout=300)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.status_code} - {upload_response.text}"
        
        # Verify file exists in S3
        head_response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        assert head_response["ContentLength"] == pdf_size, "S3 file size mismatch"
        print(f"Verified: File in S3 with size {head_response['ContentLength']} bytes")
        
    finally:
        # Cleanup
        requests.delete(f"{API_URL}/projects/{project_name}", headers=get_auth_only())
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=f"documents/{filename}")
        except:
            pass


def test_batch_upload_10_documents():
    """Test uploading 10 documents concurrently with mixed extractLessons settings"""
    project_a = f"test-batch-a-{int(time.time())}"
    project_b = f"test-batch-b-{int(time.time())}"
    
    try:
        # Create both projects
        for proj in [project_a, project_b]:
            requests.post(
                f"{API_URL}/setup-wizard",
                headers=get_auth_headers(),
                json={
                    "projectName": proj,
                    "projectType": "Other",
                    "location": "Test",
                    "areaSize": "1.0",
                    "specialConditions": []
                }
            )
        
        # Define 10 files with mixed settings
        files = [
            {"fileName": f"batch_doc_{i}.txt", "projectName": project_a if i < 5 else project_b, "extractLessons": i % 2 == 0, "projectType": "Other"}
            for i in range(10)
        ]
        
        # Request presigned URLs for all 10
        response = requests.post(
            f"{API_URL}/upload-url",
            headers=get_auth_headers(),
            json={"files": files}
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["uploads"]) == 10
        
        # Upload all 10 files
        uploaded_keys = []
        for i, upload_info in enumerate(result["uploads"]):
            content = f"Document {i} content. Lesson: Testing batch upload {i}."
            upload_response = requests.put(upload_info["uploadUrl"], data=content.encode())
            assert upload_response.status_code == 200, f"Upload {i} failed"
            uploaded_keys.append(upload_info["s3Key"])
        
        # Verify all 10 exist in S3
        for key in uploaded_keys:
            head_response = s3_client.head_object(Bucket=S3_BUCKET, Key=key)
            assert head_response["ContentLength"] > 0
        
        print(f"All 10 documents uploaded and verified in S3")
        
    finally:
        # Cleanup
        for proj in [project_a, project_b]:
            requests.delete(f"{API_URL}/projects/{proj}", headers=get_auth_only())
        for i in range(10):
            try:
                s3_client.delete_object(Bucket=S3_BUCKET, Key=f"documents/batch_doc_{i}.txt")
            except:
                pass
