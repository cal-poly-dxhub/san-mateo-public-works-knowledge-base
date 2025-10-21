"""
Example Test Configuration for Project Knowledge Integration Tests
Copy this file to test_config.py and update with your actual values
"""

# API Configuration
API_URL = "https://your-api-gateway-url.execute-api.region.amazonaws.com/prod"
API_KEY = "your-api-key-here"
S3_BUCKET = "your-s3-bucket-name"

# Test Data
SAMPLE_DOCUMENTS = [
    {
        "filename": "test-lessons-learned.txt",
        "document_type": "lessons_learned",
        "date": "2025-01-08",
        "content": "Sewer district project lessons: Early coordination with utility companies prevented delays. Soil testing revealed unexpected conditions requiring design modifications.",
    },
    {
        "filename": "test-project-report.txt",
        "document_type": "project_report",
        "date": "2025-01-15",
        "content": "Water district project report: Completed pipeline installation ahead of schedule. Community engagement was key to project success. Recommend similar approach for future projects.",
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
]

EXPECTED_DOCUMENT_PATTERN = "documents/{filename}"
EXPECTED_KNOWLEDGE_PATTERN = "knowledge/{filename_base}.json"
EXPECTED_ASSET_PATTERN = "assets/{asset_type}.md"
