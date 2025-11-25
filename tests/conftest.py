import time
import pytest
import json
import os
from typing import Dict
from datetime import datetime
import boto3
from .test_config import API_URL, TEST_PASSWORD, DYNAMODB_TABLE
from .cognito_auth import get_auth_token

dynamodb = boto3.resource("dynamodb")

# Store timing results
timing_results: Dict[str, float] = {}

# Cache auth token to avoid repeated Cognito calls
_cached_token = None
_token_timestamp = 0
TOKEN_CACHE_DURATION = 3000  # 50 minutes (tokens valid for 1 hour)

def get_cached_auth_token():
    """Get cached auth token or fetch new one if expired"""
    global _cached_token, _token_timestamp
    
    current_time = time.time()
    if _cached_token and (current_time - _token_timestamp) < TOKEN_CACHE_DURATION:
        return _cached_token
    
    _cached_token = get_auth_token()
    _token_timestamp = current_time
    return _cached_token


@pytest.fixture(scope="session", autouse=True)
def initialize_global_checklist():
    """Initialize global checklist before tests and cleanup after"""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    # Check if already initialized
    response = table.query(
        KeyConditionExpression="project_id = :pid",
        ExpressionAttributeValues={":pid": "__GLOBAL__"},
        Limit=1
    )
    
    if not response["Items"]:
        # Initialize global checklist
        version = datetime.utcnow().isoformat()
        
        # Load design checklist
        design_path = os.path.join(
            os.path.dirname(__file__),
            "../src/checklist/design_checklist.json"
        )
        
        with open(design_path, "r") as f:
            design_checklist = json.load(f)
        
        for item in design_checklist["document"]["checklist_items"]:
            for task in item["tasks"]:
                table.put_item(Item={
                    "project_id": "__GLOBAL__",
                    "item_id": f"task#design#{task['task_id']}",
                    "taskData": task,
                    "version": version,
                    "lastUpdated": version
                })
        
        # Load construction checklist if exists
        construction_path = os.path.join(
            os.path.dirname(__file__),
            "../src/checklist/construction_checklist.json"
        )
        
        if os.path.exists(construction_path):
            with open(construction_path, "r") as f:
                construction_checklist = json.load(f)
            
            for item in construction_checklist["document"]["checklist_items"]:
                for task in item["tasks"]:
                    table.put_item(Item={
                        "project_id": "__GLOBAL__",
                        "item_id": f"task#construction#{task['task_id']}",
                        "taskData": task,
                        "version": version,
                        "lastUpdated": version
                    })
    
    yield
    
    # Cleanup: Delete all global checklist items
    response = table.query(
        KeyConditionExpression="project_id = :pid",
        ExpressionAttributeValues={":pid": "__GLOBAL__"}
    )
    
    for item in response["Items"]:
        table.delete_item(
            Key={"project_id": "__GLOBAL__", "item_id": item["item_id"]}
        )


@pytest.fixture(autouse=True)
def measure_test_time(request):
    """Automatically measure test execution time"""
    start = time.time()
    yield
    duration = time.time() - start
    
    test_name = request.node.name
    timing_results[test_name] = duration
    
    # Log if test is slow (>5 seconds)
    if duration > 5.0:
        print(f"\n⚠️  SLOW TEST: {test_name} took {duration:.2f}s")


@pytest.fixture(scope="session", autouse=True)
def print_timing_summary(request):
    """Print timing summary after all tests"""
    def finalizer():
        if not timing_results:
            return
            
        print("\n" + "="*70)
        print("API CALL PERFORMANCE REPORT")
        print("="*70)
        
        sorted_times = sorted(timing_results.items(), 
                             key=lambda x: x[1], reverse=True)
        
        print(f"\n{'Test Name':<50} {'Duration':>10}")
        print("-"*70)
        
        for test_name, duration in sorted_times[:15]:
            print(f"{test_name:<50} {duration:>9.2f}s")
        
        if len(sorted_times) > 15:
            print(f"... and {len(sorted_times) - 15} more tests")
        
        total = sum(timing_results.values())
        avg = total / len(timing_results) if timing_results else 0
        
        print("-"*70)
        print(f"Total: {total:.2f}s | Average: {avg:.2f}s | Tests: {len(timing_results)}")
        print("="*70 + "\n")
    
    request.addfinalizer(finalizer)


@pytest.fixture
def api_timer():
    """Context manager for measuring API call duration"""
    class APITimer:
        def __init__(self):
            self.start = None
            self.end = None
            self.calls = []
            
        def __enter__(self):
            self.start = time.time()
            return self
            
        def __exit__(self, *args):
            self.end = time.time()
            
        @property
        def duration(self):
            return self.end - self.start if self.end else 0
        
        def mark(self, label: str):
            """Mark a checkpoint in timing"""
            if self.start:
                elapsed = time.time() - self.start
                self.calls.append((label, elapsed))
    
    return APITimer()


# Skip integration tests if config is missing
pytestmark = pytest.mark.skipif(
    not API_URL or not TEST_PASSWORD,
    reason="API_URL and TEST_PASSWORD environment variables required for integration tests"
)
