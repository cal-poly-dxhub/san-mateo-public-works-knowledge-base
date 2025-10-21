# Project Knowledge Integration Test Suite

python -m pytest tests/ -v

This test suite provides comprehensive integration testing for the DPW Project Knowledge Management system, covering all API endpoints and functionality.

## Test Coverage

### API Endpoints Tested
- **Projects API**: Create, list, get details, delete projects
- **Document Upload API**: Upload project documents
- **Generate Assets API**: Create executive summaries and web stories
- **Dashboard API**: Get models, retrieve asset files
- **Search API**: Global and project-specific search
- **Timeline API**: Get project timeline

### Functionality Tested
- Project creation and management
- Project document processing
- AI-generated knowledge extraction
- S3 file storage and retrieval
- JSON structure validation
- Search functionality
- Asset generation

## Running Tests

### Prerequisites
```bash
pip install requests boto3
```

### Run All Tests
```bash
python run_tests.py
```

### Run Specific Test
```bash
python -m pytest tests/test_meeting_automation.py::test_01_create_project -v
```

## Test Structure

Tests are numbered and run sequentially:

1. **test_01_create_project** - Creates test project
2. **test_02_get_projects_list** - Validates project listing
3. **test_03_batch_upload_documents** - Uploads test documents
4. **test_04_wait_for_processing** - Allows Lambda processing time
5. **test_05_get_project_details** - Retrieves project information
6. **test_06_validate_knowledge_extraction** - Validates knowledge extraction JSON
7. **test_07_get_available_models** - Tests model endpoint
8. **test_08_search_global** - Tests global search
9. **test_09_search_project_specific** - Tests project search
10. **test_10_generate_executive_summary** - Tests asset generation
11. **test_11_generate_webstory** - Tests asset generation
12. **test_12_race_condition** - Tests sequential processing
13. **test_13_update_project_progress** - Tests progress updates
14. **test_16_timeline_api** - Tests timeline functionality
15. **test_17_delete_project** - Tests project deletion and cleanup

## LLM Response Validation

For AI-generated content, tests validate:
- JSON can be loaded without errors
- Content is non-empty
- Basic structure is present
- Lessons learned are extracted

## Test Data

Tests create a unique project with timestamp to avoid conflicts:
- Project name: `test-project-{timestamp}`
- Sample documents with realistic DPW project content
- Test data is cleaned up after tests complete

## Configuration

Edit `test_config.py` to modify:
- API endpoints
- Test data
- Timeout values
- Expected file patterns

## Troubleshooting

### Common Issues
- **Authentication errors**: Check API key in frontend/.env
- **Timeout errors**: Increase wait times in test_config.py
- **S3 access errors**: Verify AWS credentials
- **Lambda processing delays**: Increase PROCESSING_WAIT_TIME

### Debug Mode
Add print statements or use Python debugger:
```python
import pdb; pdb.set_trace()
```

## Expected Output

Successful test run shows:
```
🧪 Project Knowledge Integration Test Suite
============================================================
Started at: 2025-01-16 14:30:00
============================================================

test_01_create_project ... ok
test_02_get_projects_list ... ok
...
test_17_delete_project ... ok

============================================================
TEST SUMMARY
============================================================
Tests run: 15
Failures: 0
Errors: 0
Success rate: 100.0%
Total time: 95.23 seconds

✅ All tests passed!
```
