# Meeting Automation Integration Test Suite

python -m pytest tests/ -v

This test suite provides comprehensive integration testing for the Meeting Automation system, covering all API endpoints and functionality.

## Test Coverage

### API Endpoints Tested
- **Projects API**: Create, list, get details, delete projects
- **Batch Upload API**: Upload meeting transcripts
- **Generate Assets API**: Create executive summaries and web stories
- **Dashboard API**: Get models, retrieve asset files
- **Search API**: Global and project-specific search
- **Timeline API**: Get project timeline and action items

### Functionality Tested
- Project creation and management
- Meeting transcript processing
- AI-generated summaries and assets
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
python -m unittest test_meeting_automation.MeetingAutomationIntegrationTests.test_01_create_project -v
```

## Test Structure

Tests are numbered and run sequentially:

1. **test_01_create_project** - Creates test project
2. **test_02_get_projects_list** - Validates project listing
3. **test_03_batch_upload_meetings** - Uploads test meetings
4. **test_04_wait_for_processing** - Allows Lambda processing time
5. **test_05_get_project_details** - Retrieves project information
6. **test_06_check_s3_files_exist** - Verifies S3 file creation
7. **test_07_validate_project_overview** - Validates JSON structure
8. **test_08_validate_working_backwards** - Validates JSON structure
9. **test_09_validate_meeting_summaries** - Validates summary JSON
10. **test_10_get_available_models** - Tests model endpoint
11. **test_11_search_global** - Tests global search
12. **test_12_search_project_specific** - Tests project search
13. **test_13_generate_executive_summary** - Tests asset generation
14. **test_14_generate_webstory** - Tests asset generation
15. **test_15_get_asset_file** - Tests asset retrieval
16. **test_16_update_project_progress** - Tests progress updates
17. **test_17_timeline_api** - Tests timeline functionality

## LLM Response Validation

For AI-generated content, tests validate:
- JSON can be loaded without errors
- Content is non-empty
- Basic structure is present

## Test Data

Tests create a unique project with timestamp to avoid conflicts:
- Project name: `test-project-{timestamp}`
- Sample meetings with realistic content
- Test data is left in system for inspection

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
🧪 Meeting Automation Integration Test Suite
============================================================
Started at: 2025-01-16 14:30:00
============================================================

test_01_create_project ... ok
test_02_get_projects_list ... ok
...
test_17_timeline_api ... ok

============================================================
TEST SUMMARY
============================================================
Tests run: 17
Failures: 0
Errors: 0
Success rate: 100.0%
Total time: 95.23 seconds

✅ All tests passed!
```
