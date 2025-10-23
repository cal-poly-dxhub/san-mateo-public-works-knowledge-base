import json
import boto3
import os
from datetime import datetime
import base64

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')

def handler(event, context):
    """Handle lessons learned document upload and extraction"""
    
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    
    if method == 'POST' and '/documents' in path:
        return upload_and_extract(event)
    elif method == 'GET' and '/lessons-learned' in path:
        return get_lessons(event)
    
    return {
        'statusCode': 404,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': 'Not found'})
    }

def upload_and_extract(event):
    """Upload document and extract lessons learned"""
    try:
        body = json.loads(event.get('body', '{}'))
        project_name = event['pathParameters']['project_name']
        
        file_content = body.get('content')
        filename = body.get('filename')
        extract_lessons = body.get('extract_lessons', False)
        
        if not file_content or not filename:
            return error_response('Missing file content or filename')
        
        # Decode base64 content if needed
        try:
            content_text = base64.b64decode(file_content).decode('utf-8')
        except:
            content_text = file_content
        
        bucket_name = os.environ['BUCKET_NAME']
        project_type = body.get('project_type', 'other')
        
        # Upload document to S3
        doc_key = f"projects/{project_name}/documents/{filename}"
        s3.put_object(
            Bucket=bucket_name,
            Key=doc_key,
            Body=content_text.encode('utf-8')
        )
        
        if extract_lessons:
            # Extract lessons learned using LLM
            lessons = extract_lessons_from_document(
                content_text, 
                project_name, 
                datetime.now().strftime('%Y-%m-%d')
            )
            
            # Append to project lessons learned
            append_to_project_lessons(bucket_name, project_name, lessons)
            
            # Update master lessons learned
            update_master_lessons(bucket_name, project_type, project_name, lessons)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'message': 'Document uploaded and lessons extracted',
                    'lessons': lessons
                })
            }
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': 'Document uploaded successfully'})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e))

def extract_lessons_from_document(content, project_name, date):
    """Extract lessons learned from document using LLM"""
    
    prompt = f"""Extract lessons learned from this document for project "{project_name}".
Date: {date}

Format each lesson as:
## [Category] - {project_name} - {date}
**Lesson:** [Brief title]
**Details:** [Full description]
**Impact:** [What this affected]
**Recommendation:** [What to do differently]

---

Categories: Technical, Process, Communication, Safety, Budget, Timeline, Stakeholder Management

Focus on insights that would help future similar projects. Extract 3-5 key lessons.

Document Content:
{content[:4000]}

Return only the formatted lessons in markdown."""
    
    try:
        response = bedrock.invoke_model(
            modelId=os.environ.get('LESSONS_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        lessons = response_body['content'][0]['text']
        return lessons
        
    except Exception as e:
        print(f"Error extracting lessons: {str(e)}")
        return f"## General - {project_name} - {date}\n**Lesson:** Document uploaded\n**Details:** Automatic extraction failed\n\n---\n"

def append_to_project_lessons(bucket_name, project_name, new_lessons):
    """Append lessons to project's lessons-learned.md file"""
    
    lessons_key = f"projects/{project_name}/lessons-learned.md"
    
    try:
        # Get existing lessons
        response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
        existing_content = response['Body'].read().decode('utf-8')
    except:
        existing_content = f"# Lessons Learned - {project_name}\n\n"
    
    # Append new lessons
    updated_content = existing_content + "\n" + new_lessons + "\n"
    
    s3.put_object(
        Bucket=bucket_name,
        Key=lessons_key,
        Body=updated_content.encode('utf-8'),
        ContentType='text/markdown'
    )

def update_master_lessons(bucket_name, project_type, project_name, new_lessons):
    """Update master lessons learned file with LLM merge"""
    
    # Get current master file
    master_folder = f"lessons-learned/{project_type}"
    
    try:
        # List existing master files
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=master_folder
        )
        
        if 'Contents' in response and response['Contents']:
            # Get most recent master file
            latest_file = sorted(response['Contents'], key=lambda x: x['Key'])[-1]
            master_response = s3.get_object(Bucket=bucket_name, Key=latest_file['Key'])
            existing_master = master_response['Body'].read().decode('utf-8')
        else:
            existing_master = f"# Master Lessons Learned - {project_type.title()}\n\n"
    except:
        existing_master = f"# Master Lessons Learned - {project_type.title()}\n\n"
    
    # Merge using LLM
    merged_lessons = merge_lessons_with_llm(existing_master, new_lessons, project_name)
    
    # Save new versioned master file
    today = datetime.now().strftime('%Y-%m-%d')
    new_master_key = f"{master_folder}/master-{today}.md"
    
    s3.put_object(
        Bucket=bucket_name,
        Key=new_master_key,
        Body=merged_lessons.encode('utf-8'),
        ContentType='text/markdown'
    )

def merge_lessons_with_llm(existing_master, new_lessons, project_name):
    """Merge new lessons with existing master using LLM"""
    
    prompt = f"""Merge these new lessons learned with the existing master file.

Rules:
1. Deduplicate similar lessons (keep most comprehensive version)
2. If lessons contradict, keep the most recent one (from {project_name})
3. Organize by category (Technical, Process, Communication, Safety, Budget, Timeline, Stakeholder Management)
4. Maintain chronological order within categories (newest first)
5. Preserve all metadata (project name, date)

New Lessons from {project_name}:
{new_lessons}

Existing Master:
{existing_master}

Return the complete merged master file in markdown format."""
    
    try:
        response = bedrock.invoke_model(
            modelId=os.environ.get('LESSONS_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        merged = response_body['content'][0]['text']
        return merged
        
    except Exception as e:
        print(f"Error merging lessons: {str(e)}")
        # Fallback: just append
        return existing_master + "\n\n" + new_lessons

def get_lessons(event):
    """Get project lessons learned"""
    try:
        project_name = event['pathParameters']['project_name']
        bucket_name = os.environ['BUCKET_NAME']
        lessons_key = f"projects/{project_name}/lessons-learned.md"
        
        try:
            response = s3.get_object(Bucket=bucket_name, Key=lessons_key)
            content = response['Body'].read().decode('utf-8')
        except:
            content = f"# Lessons Learned - {project_name}\n\nNo lessons learned yet."
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'content': content})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e))

def error_response(message):
    return {
        'statusCode': 500,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': message})
    }
