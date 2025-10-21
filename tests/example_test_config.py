"""
Example Test Configuration for Meeting Automation Integration Tests
Copy this file to test_config.py and update with your actual values
"""

# API Configuration
API_URL = "https://your-api-gateway-url.execute-api.region.amazonaws.com/prod"
API_KEY = "your-api-key-here"
S3_BUCKET = "your-s3-bucket-name"

# Test Data
SAMPLE_MEETINGS = [
    {
        "filename": "test-discovery.txt",
        "meeting_type": "discovery",
        "date": "2025-01-08",
        "content": "Discovery meeting with client. Requirements: user authentication, product catalog, payment system. Team: Alice (frontend), Bob (backend), Charlie (DevOps).",
    },
    {
        "filename": "test-demo.txt",
        "meeting_type": "demo",
        "date": "2025-01-15",
        "content": "Sprint demo. Alice completed login UI, Bob implemented auth API, Charlie set up CI/CD. Next: Alice builds product pages, Bob adds cart API.",
    },
]

# Test Timeouts (seconds)
PROCESSING_WAIT_TIME = 30
ASSET_GENERATION_WAIT_TIME = 10
MAX_PROCESSING_TIMEOUT = 300  # 5 minutes max wait
POLLING_INTERVAL = 5  # Check every 5 seconds

# Expected File Patterns
EXPECTED_FILES = [
    "project_overview.json",
    "working_backwards.json",
    "assigned-students.json",
]

EXPECTED_TRANSCRIPT_PATTERN = "meeting-transcripts/{filename}"
EXPECTED_SUMMARY_PATTERN = "meeting-summaries/{filename_base}.json"
EXPECTED_ASSET_PATTERN = "assets/{asset_type}.md"
