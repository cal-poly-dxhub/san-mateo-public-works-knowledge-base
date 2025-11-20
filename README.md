# AI-Powered Project Management for Public Works

AWS-powered project management system for the Department of Public Works that automates project setup, tracks progress through interactive checklists, and provides AI-powered guidance for civil infrastructure projects.

## Three Core Features

### 1. Smart Project Setup Wizard
- 5-7 question questionnaire to configure new projects
- Automatically generates task checklists, stakeholder lists, document templates, timelines, and permit requirements
- Reduces project setup from 2-3 days to 15 minutes

### 2. Interactive Project Roadmap & Checklist
- Living checklist with 60+ phases and 200+ tasks
- Smart task management with dependencies and progress tracking
- Real-time visibility for leadership
- Collaboration features with task assignments and notifications

### 3. AI Knowledge Assistant
- Plain English Q&A about projects, regulations, and procedures
- Automatic template generation with pre-filled project details
- Historical insights from past projects
- Proactive alerts for potential issues

## Architecture

### AWS Services Used
- **Amazon Bedrock**: AI models for project setup, lessons extraction, and conflict detection
- **Amazon Bedrock Knowledge Base**: Vector search for lessons learned
- **AWS Lambda**: Serverless compute for API handlers and processing
- **Amazon S3**: Document storage and project data
- **Amazon DynamoDB**: Project metadata and status tracking
- **Amazon API Gateway**: REST API endpoints
- **AWS CDK**: Infrastructure as code

### System Components

```
Frontend (Next.js)
    ↓
API Gateway
    ↓
Lambda Functions
    ├── Project Management (CRUD operations)
    ├── Lessons Processing (extract, sync, conflict detection)
    ├── Search & RAG (Knowledge Base queries)
    └── Project Setup Wizard
    ↓
Storage Layer
    ├── S3 (documents, lessons, metadata)
    ├── DynamoDB (project data)
    └── Bedrock Knowledge Base (vector search)
```

## Setup

### Prerequisites
- AWS Account with appropriate permissions
- Node.js 18+ and npm
- Python 3.9+
- AWS CDK CLI (`npm install -g aws-cdk`)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dxhub-meeting-automation
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure settings**
   
   Edit `config.yaml` to customize:
   - AI model selections
   - Project types and special conditions
   - Prompts for AI interactions
   - S3 path patterns

5. **Deploy AWS infrastructure**
   ```bash
   cdk bootstrap  # First time only
   cdk deploy
   ```

6. **Configure frontend environment**
   
   Create `frontend/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=<your-api-gateway-url>
   NEXT_PUBLIC_API_KEY=<your-api-key>
   ```

7. **Initialize Knowledge Base**
   ```bash
   python scripts/trigger_kb_creation.py
   ```

8. **Start the frontend**
   ```bash
   cd frontend
   npm run dev
   ```

## Configuration

### config.yaml

The `config.yaml` file controls all AI models, prompts, and system behavior:

**Models Section**
- `primary_llm`: Main AI model for project setup and assistance
- `lessons_extractor`: Fast model for extracting lessons from documents
- `conflict_detector`: Model for detecting conflicting lessons
- `embeddings`: Model for vector embeddings (used by Knowledge Base)
- `available_search_models`: Models users can select in search UI

**Knowledge Base Section**
- `name`: Knowledge Base name (used to derive vector bucket and index names)
- `data_source_name`: Name for the S3 data source
- `chunk_size_tokens`: Token size for document chunking (default: 512)
- `overlap_tokens`: Overlap between chunks (default: 64)
- `vector_dimension`: Vector dimension (must match embedding model, Titan v2 = 1024)

**S3 Paths Section**
- Defines all S3 key patterns used throughout the system
- **Important**: `documents/projects/` (for Knowledge Base) vs `projects/` (for metadata)
- `documents_prefix`: Used by Knowledge Base for document ingestion

**Project Section**
- `types`: Available project types
- `special_conditions`: Special conditions that can apply to projects
- `max_document_length`: Maximum document size for processing

**Prompts Section**
- Customizable prompts for all AI interactions
- Use `{variable}` syntax for dynamic values

### Environment Variables

See `ENV_VAR.md` for complete documentation of environment variables and consolidation opportunities.

Key variables:
- `BUCKET_NAME`: S3 bucket for documents
- `PROJECT_DATA_TABLE_NAME`: DynamoDB table name
- `KB_ID`: Bedrock Knowledge Base ID
- Model IDs for various AI tasks

## Usage

### Creating a New Project

1. Click "Create New Project" in the dashboard
2. Answer 5-7 questions about the project:
   - Project name and type
   - Location and area size
   - Special conditions
3. System automatically generates:
   - Task checklist with dependencies
   - Stakeholder contact list
   - Required permits
   - Timeline with milestones
   - Budget estimate

### Managing Project Tasks

- View all tasks organized by phase
- Check off completed tasks
- Add notes and actual completion dates
- Track overall progress percentage
- Edit or add custom tasks

### Lessons Learned

**Project-Level Lessons**
- Upload documents to extract lessons automatically
- Review and edit extracted lessons
- Resolve conflicts with existing lessons
- Lessons are synced to Knowledge Base for search

**Master Lessons by Type**
- View aggregated lessons across all projects of a type
- Resolve conflicts between project lessons
- Search across all lessons using natural language

### AI Search & Assistance

- Ask questions in plain English
- Search across all project documents and lessons
- Get AI-generated answers with source citations
- Select different AI models for different use cases

## Project Structure

```
.
├── infrastructure/          # AWS CDK infrastructure code
│   ├── api.py              # API Gateway definitions
│   ├── compute.py          # Lambda functions and layers
│   ├── storage.py          # S3 and DynamoDB resources
│   └── knowledge_base.py   # Bedrock Knowledge Base setup
├── src/                    # Lambda function source code
│   ├── lessons/            # Lessons processing and API
│   │   ├── kb_helper.py    # Knowledge Base operations
│   │   ├── lessons_api.py  # Project lessons API
│   │   ├── lessons_master_api.py  # Master lessons API
│   │   ├── lessons_processor.py   # Extract lessons from docs
│   │   └── lessons_sync_lambda.py # Sync to Knowledge Base
│   ├── projects/           # Project management
│   └── search/             # Search and RAG functionality
├── frontend/               # Next.js web application
│   ├── app/               # Next.js app router pages
│   ├── components/        # React components
│   ├── lib/               # Utilities and API client
│   └── types/             # TypeScript type definitions
├── scripts/               # Utility scripts
│   └── trigger_kb_creation.py
├── config.yaml            # System configuration
├── ENV_VAR.md            # Environment variables documentation
└── README.md             # This file
```

## API Endpoints

### Projects
- `GET /projects` - List all projects
- `POST /projects` - Create new project
- `GET /projects/{name}` - Get project details
- `PUT /projects/{name}` - Update project
- `DELETE /projects/{name}` - Delete project

### Checklists
- `GET /projects/{name}/checklist` - Get project checklist
- `PUT /projects/{name}/checklist` - Update checklist

### Lessons (Project-Level)
- `GET /projects/{name}/lessons` - Get project lessons
- `POST /projects/{name}/lessons` - Add lesson
- `PUT /projects/{name}/lessons/{id}` - Update lesson
- `DELETE /projects/{name}/lessons/{id}` - Delete lesson
- `GET /projects/{name}/conflicts` - Get pending conflicts
- `POST /projects/{name}/conflicts/{id}/resolve` - Resolve conflict

### Lessons (Master by Type)
- `GET /lessons/project-types` - List all project types with counts
- `GET /lessons/by-type/{type}` - Get master lessons for type
- `GET /lessons/conflicts/by-type/{type}` - Get conflicts for type
- `POST /lessons/conflicts/resolve/{id}` - Resolve master conflict

### Search
- `POST /search` - Search Knowledge Base with RAG
- `GET /search/models` - Get available AI models

### Documents
- `POST /projects/{name}/documents` - Upload document
- `GET /projects/{name}/documents` - List documents

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
ruff format src/ infrastructure/
```

### Linting
```bash
ruff check src/ infrastructure/
```

### Local Development
```bash
# Backend (Lambda functions)
# Use AWS SAM or Lambda local testing

# Frontend
cd frontend
npm run dev
```

## Project Types Supported

- **Reconstruction**: Full street reconstruction projects
- **Resurface**: Street resurfacing and overlay projects
- **Slurry Seal**: Slurry seal maintenance projects
- **Drainage**: Drainage improvement projects
- **Utilities**: Utility coordination and installation
- **Other**: Custom infrastructure projects

## Troubleshooting

### Knowledge Base Not Syncing
1. Check `KB_ID` environment variable is set
2. Verify S3 bucket permissions
3. Run `python scripts/trigger_kb_creation.py`
4. Check CloudWatch logs for sync Lambda

### API Errors
1. Verify API Gateway URL in frontend `.env.local`
2. Check API key is valid
3. Review Lambda function logs in CloudWatch
4. Ensure DynamoDB table exists

### Frontend Not Loading
1. Check `NEXT_PUBLIC_API_URL` is set correctly
2. Verify CORS settings in API Gateway
3. Check browser console for errors
4. Ensure API key is configured

## Contributing

1. Create a feature branch
2. Make changes and test thoroughly
3. Run code formatting: `ruff format`
4. Run linting: `ruff check`
5. Submit pull request

## License

[Your License Here]

## Support

For issues or questions, contact [Your Contact Info]
