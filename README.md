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
- Docker
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
## Configuration

### config.yaml

The `config.yaml` file is the central configuration for all AI models, prompts, and system behavior. Edit this file to customize the system without changing code.

**Models Section**
- `primary_llm`: Main AI model for project setup and assistance (Claude Sonnet 4)
- `lessons_extractor`: Fast model for extracting lessons from documents (Llama 4 Maverick)
- `conflict_detector`: Model for detecting conflicting lessons (Claude Sonnet 4)
- `embeddings`: Model for vector embeddings (Titan Embed v2, 1024 dimensions)
- `available_search_models`: Models users can select in search UI (Haiku, Sonnet, Llama, Nova)

**S3 Paths Section**
Defines all S3 key patterns used throughout the system:
- `documents_prefix`: "documents/projects" - Knowledge Base document storage
- `project_documents`: "documents/projects/{project_name}" - Project-specific documents
- `project_lessons_json/txt`: Lessons learned files in both formats
- `projects_prefix`: "projects" - Project metadata (separate from documents)
- `project_metadata`: "projects/{project_name}/metadata.json"
- `project_checklist`: "projects/{project_name}/checklist.json"
- `master_lessons_prefix`: "lessons-learned" - Aggregated lessons by type
- `master_lessons_by_type`: "lessons-learned/{project_type}/lessons.json"
- `master_conflicts_by_type`: Conflict tracking for master lessons

**Important**: `documents/projects/` (Knowledge Base) and `projects/` (metadata) are different paths.

**Knowledge Base Section**
- `name`: "dpw-project-management-kb" - Knowledge Base identifier
- `data_source_name`: "project-documents" - S3 data source name
- `chunk_size_tokens`: 512 - Document chunk size for vector search
- `overlap_tokens`: 64 - Overlap between chunks for context
- `vector_dimension`: 1024 - Must match embedding model (Titan v2 = 1024)
- Supported formats: .txt, .md, .html, .doc, .docx, .csv, .xls, .xlsx, .pdf

**API Gateway Section**
- `throttle`: Rate limiting (500 req/sec, 1000 burst)
- `quota`: Daily request limits (100,000 per day)

**Project Section**
- `max_document_length`: 100,000 characters
- `types`: Reconstruction, Resurface, Slurry Seal, Drainage, Utilities, Other
- `special_conditions`: Near coast, NFO area, Federal funding, Environmental sensitive, High traffic

**Prompts Section**
Customizable prompts for all AI interactions:
- `retrieve_and_generate`: RAG search responses
- `project_setup_wizard`: New project configuration generation
- `generate_task_checklist`: Task list generation
- `ai_assistant_response`: General Q&A responses
- `generate_document_template`: Document generation
- `proactive_alert_check`: Issue detection and alerts
- `estimate_timeline`: Timeline estimation

Use `{variable}` or `$variable` syntax for dynamic values in prompts.

**Templates Section**
JSON templates for project configuration and task structure.

### Environment Variables

See `ENV_VAR.md` for complete documentation of environment variables.

Key variables set by CDK deployment:
- `BUCKET_NAME`: S3 bucket for documents
- `PROJECT_DATA_TABLE_NAME`: DynamoDB table name
- `KB_ID`: Bedrock Knowledge Base ID
- Model IDs for various AI tasks (from config.yaml)

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

**Supported Document Types for Lessons Extraction**
- PDF (.pdf)
- Microsoft Word (.doc, .docx)
- Microsoft Excel (.xls, .xlsx)
- Plain text (.txt, .md, .html, .csv, and other text formats)

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
│   ├── checklist/          # Checklist definitions
│   │   ├── design_checklist.json       # Design phase checklist
│   │   └── construction_checklist.json # Construction phase checklist
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

### Checklists

Initial checklists are stored in `src/checklist/` as JSON files. After deployment, checklists are saved globally in DynamoDB and can be edited and saved in the app.

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

## Support

For issues or questions, contact [Your Contact Info]
