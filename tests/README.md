# API Test Suite

Comprehensive integration tests for the DXHub Meeting Automation API.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
export API_URL="https://your-api-gateway-url.execute-api.us-west-2.amazonaws.com/prod"
export API_KEY="your-api-key"
export S3_BUCKET="dpw-project-mgmt-data"
export VECTOR_BUCKET="dpw-project-mgmt-vectors"
export DYNAMODB_TABLE="dpw-project-data"
export INDEX_NAME="project-mgmt-index"
```

Or create a `.env` file with these values.

## Running Tests

Run all tests:
```bash
pytest test_api_comprehensive.py -v
```

Run specific test:
```bash
pytest test_api_comprehensive.py::test_01_get_project_types -v
```

Run with coverage:
```bash
pytest test_api_comprehensive.py --cov --cov-report=html
```

## Test Coverage

### 1. Project Management (Tests 1-6)
- Get project types configuration
- Create new project
- Setup project with wizard (AI-generated config)
- List all projects
- Get project details
- Update project progress

### 2. Task Management (Tests 7-9)
- Get all tasks for a project
- Create new task
- Update task status

### 3. Checklist API (Tests 10-12)
- Get project checklist with progress
- Update checklist metadata
- Update individual checklist tasks

### 4. Files API (Tests 13-14)
- Get presigned upload URL
- Retrieve file content

### 5. Lessons Learned (Tests 15-19)
- Upload document with lesson extraction
- Wait for async processing
- Get project-specific lessons
- Get master project types
- Get aggregated lessons by type

### 6. Search (Tests 20-21)
- Semantic vector search
- RAG search with AI-generated answers

### 7. AI Assistant (Tests 22-24)
- Q&A functionality
- Template generation
- Proactive alerts

### 8. Dashboard (Tests 25-26)
- Get available AI models
- Retrieve project assets

### 9. Vector Storage (Test 27)
- Validate vectors created in S3 vector store

### 10. Race Conditions (Test 28)
- Concurrent lesson processing without data corruption

### 11. Cleanup (Test 29)
- Project deletion with complete cleanup verification

## Test Workflows

The tests follow realistic user workflows:

1. **Project Creation Flow**: Create → Setup Wizard → Verify
2. **Task Management Flow**: List → Create → Update → Check Progress
3. **Lessons Flow**: Upload Docs → Extract → Review → Aggregate
4. **Search Flow**: Vector Search → RAG Answer → AI Follow-up

## Notes

- Tests run sequentially to maintain state
- Each test creates unique project names with timestamps
- Cleanup test ensures no orphaned resources
- Race condition test validates concurrent processing
- All tests include proper assertions and error handling
