# Knowledge Base Manual Sync Button

## Overview
Added a manual sync button to the project page that allows users to trigger Knowledge Base synchronization on-demand. This helps manage KB sync load during testing and provides visibility into sync status.

## Implementation

### Backend

**Lambda Function**: `src/sync/manual_sync_lambda.py`
- Checks if sync is already in progress
- Returns sync status with statistics if running
- Starts new sync if none in progress
- Handles ConflictException gracefully

**API Endpoint**: `POST /sync/knowledge-base`
- Added to `infrastructure/api.py`
- Protected with Cognito authentication

**Permissions**: Added to `infrastructure/iam.py`
- `bedrock:StartIngestionJob`
- `bedrock:GetDataSource`
- `bedrock:ListDataSources`
- `bedrock:ListIngestionJobs`

**Infrastructure**: Added to `infrastructure/compute.py`
- Lambda function definition with KB_ID environment variable

### Frontend

**Component**: `frontend/components/KBSyncButton.tsx`
- Simple button with loading state
- Shows sync status messages
- Auto-dismisses messages after 5 seconds
- Displays sync statistics when available

**Integration**: Added to `frontend/app/project/[name]/page.tsx`
- Placed in header next to "Add Lesson" and "Upload Documents" buttons

## API Response Format

### Success (200)
```json
{
  "message": "Sync started successfully",
  "syncInProgress": false,
  "jobId": "abc123",
  "status": "STARTING"
}
```

### Sync In Progress (409)
```json
{
  "message": "Sync already in progress",
  "syncInProgress": true,
  "dataSourceStatus": "SYNCING",
  "currentJob": {
    "status": "IN_PROGRESS",
    "startedAt": "2025-11-20T08:30:00Z",
    "statistics": {
      "numberOfDocumentsScanned": 42,
      "numberOfDocumentsIndexed": 38
    }
  }
}
```

### Error (500)
```json
{
  "error": "Failed to sync: <error message>"
}
```

## Usage

1. Navigate to any project page
2. Click "Sync Knowledge Base" button in the header
3. Button shows:
   - "✓ Sync started successfully" - New sync initiated
   - "⏳ Sync already in progress (X docs scanned)" - Sync running
   - "✗ Error: <message>" - Sync failed

## Benefits for Load Testing

- **Manual control**: Disable auto-sync, let users upload, then sync once
- **Status visibility**: See if sync is running and progress stats
- **No conflicts**: Prevents multiple sync attempts from conflicting
- **User feedback**: Clear messaging about sync state

## Deployment

```bash
cdk deploy
```

The sync button will appear on all project pages after deployment.
