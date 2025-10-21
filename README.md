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

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Deploy AWS infrastructure:
   ```bash
   cdk deploy
   ```

3. Configure settings in `config.yaml`

## Usage

Create a new project through the Smart Setup Wizard, then manage tasks and progress through the interactive roadmap. Use the AI Assistant for questions, template generation, and guidance.

## Project Types Supported

- Reconstruction
- Resurface
- Slurry Seal
- Drainage
- Utilities
- Other infrastructure projects

## Files

- `project_management_stack.py` - AWS CDK infrastructure
- `config.yaml` - AI prompts and configuration
- `frontend/` - Next.js web application
