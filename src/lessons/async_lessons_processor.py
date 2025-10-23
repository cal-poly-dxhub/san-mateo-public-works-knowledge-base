import json
import boto3
import os
from datetime import datetime
from lessons_api import extract_lessons_from_document, append_to_project_lessons, update_master_lessons

def handler(event, context):
    """Process lessons extraction asynchronously"""
    try:
        project_name = event['project_name']
        project_type = event['project_type']
        content_text = event['content']
        filename = event['filename']
        bucket_name = os.environ['BUCKET_NAME']
        
        print(f"Starting async lessons processing for {project_name}")
        
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
        
        print(f"Successfully processed {len(lessons)} lessons for {project_name}")
        return {'statusCode': 200, 'message': 'Lessons processed successfully'}
        
    except Exception as e:
        print(f"Error processing lessons async: {str(e)}")
        return {'statusCode': 500, 'error': str(e)}
