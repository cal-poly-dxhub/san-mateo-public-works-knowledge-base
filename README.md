# AI-Powered Project Management for Public Works

AWS-powered project management system for the Department of Public Works that automates project setup, tracks progress through interactive checklists, and provides AI-powered guidance for civil infrastructure projects.

## Core Features

### 1. Interactive Project Roadmap & Checklist
- Living checklist with editable tasks at both project and global level
- Smart task management with progress tracking
- Real-time visibility for leadership

### 2. AI Knowledge Assistant
- Plain English Q&A about projects, regulations, and procedures
- Automatic template generation with pre-filled project details
- Historical insights from past projects
- Proactive alerts for potential issues

Example questions:
- I'm starting a new Slurry Seal project, is there anything I should keep in mind?
- What is a prebid outreach meeting?
- How much of a project site needs stormwater treatment?

### 3. Lessons Learned Knowledge Base
- Automatically extract lessons learned from documents
- Quickly jot down lessons with Add Lesson button
- Review and search over lessons in order to inform future projects.

# Collaboration
Thanks for your interest in our solution.  Having specific examples of replication and cloning allows us to continue to grow and scale our work. If you clone or download this repository, kindly shoot us a quick email to let us know you are interested in this work!

[wwps-cic@amazon.com]

# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document.**

**This document:**

(a) is for informational purposes only,

(b) represents current AWS product offerings and practices, which are subject to change without notice, and

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers.

(d) is not to be considered a recommendation or viewpoint of AWS

**Additionally, all prototype code and associated assets should be considered:**

(a) as-is and without warranties

(b) not suitable for production environments

(d) to include shortcuts in order to support rapid prototyping such as, but not limitted to, relaxed authentication and authorization and a lack of strict adherence to security best practices

**All work produced is open source. More information can be found in the GitHub repo.**

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
   git clone https://github.com/cal-poly-dxhub/san-mateo-public-works-knowledge-base
   cd san-mateo-public-works-knowledge-base
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

4. **Deploy AWS infrastructure**
   ```bash
   cdk bootstrap  # First time only
   cdk deploy
   ```

Look for the cloudfront URL among the cdk outputs.

5. **Create a Cognito user to access the application**
   - Go to Amazon Cognito in the AWS Console
   - Find the user pool named `project-management-users`
   - Click "Users" → "Create user"
   - Enter username (email), email address, and temporary password
   - User will need to change password on first login

## Configuration

### config.yaml

The `config.yaml` file is the central configuration for all AI models, prompts, and system behavior. Edit this file to customize the system without changing code. For changes to take effect, re-run `cdk deploy`.

## Usage

### Upload Initial Knowledge Base Files

It is reccomended that any documentation that is not specific to a singular project be uploaded using the "Upload Files" button.
This will place the file into the general knowledge base for RAG search.

1. Click on "Upload Files" button at top of page.
2. Upload files.

### Creating a New Project

1. Click "Create New Project" in the dashboard
2. Answer 5-7 questions about the project:
   - Project name and type
   - Location and area size
   - Special conditions

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
- View aggregated lessons across all projects of a type on Lessons Learned page
- Resolve conflicts between project lessons

### AI Search & Assistance

- Ask questions in plain English
- Search across all project documents and lessons
- Get AI-generated answers with source citations
- Select different AI models for speed vs answer quality

### Checklists

Initial checklists are stored in `src/checklist/` as JSON files. After deployment, checklists are saved globally in DynamoDB and can be edited and saved in the app.

## Project Types Supported
These can be updated before deployment inside `config.yaml`.
- **Reconstruction**: Full street reconstruction projects
- **Resurface**: Street resurfacing and overlay projects
- **Slurry Seal**: Slurry seal maintenance projects
- **Drainage**: Drainage improvement projects
- **Utilities**: Utility coordination and installation
- **Other**: Custom infrastructure projects

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


## Support
For queries or issues:
- Darren Kraker, Sr Solutions Architect - dkraker@amazon.com
- Nick Riley, Jr SDE - njriley@calpoly.edu
