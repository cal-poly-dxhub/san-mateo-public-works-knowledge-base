# API Test Suite

Integration tests for the Project Management API.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `tests/.env`:
```bash
API_URL=https://your-api-gateway-url.execute-api.us-west-2.amazonaws.com/prod
USER_POOL_ID=us-west-2_xxxxxxxx
USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
TEST_USERNAME=your-test-user@example.com
TEST_PASSWORD=your-test-password
S3_BUCKET=your-s3-bucket-name
DYNAMODB_TABLE=your-dynamodb-table-name
KNOWLEDGE_BASE_ID=your-knowledge-base-id
```

## Running Tests

Run all tests:
```bash
cd tests
pytest -v
```

Run a specific test file:
```bash
pytest test_projects.py -v
pytest test_lessons.py -v
pytest test_checklist.py -v
pytest test_search.py -v
pytest test_uploads.py -v
```

Run a specific test:
```bash
pytest test_projects.py::test_create_project -v
```

Run with coverage:
```bash
pytest --cov --cov-report=html
```

## Test Suites

| File | Description |
|------|-------------|
| `test_projects.py` | Project CRUD operations, setup wizard |
| `test_lessons.py` | Lessons learned extraction, sync, conflicts |
| `test_checklist.py` | Checklist retrieval and task updates |
| `test_search.py` | Vector search and RAG queries |
| `test_uploads.py` | File upload presigned URLs and processing |

## Configuration

Test configuration is in `test_config.py`. All values are read from environment variables with no defaults for sensitive data.

## Notes

- Tests require valid Cognito credentials
- Some tests create/delete resources - use a test environment
- Async operations (lessons extraction) have configurable timeouts
