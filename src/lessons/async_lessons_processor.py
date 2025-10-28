import json
import boto3
import os
from vector_helper import trigger_project_lessons_ingestion, trigger_type_lessons_ingestion
from lessons_processor import extract_and_merge_lessons

def handler(event, context):
    """Process lessons extraction asynchronously with superseding logic"""
    try:
        project_name = event['project_name']
        project_type = event['project_type']
        content_text = event['content']
        filename = event['filename']
        bucket_name = os.environ['BUCKET_NAME']
        
        print(f"Starting async lessons processing for {project_name}")
        
        # Extract and merge lessons with superseding logic
        stats = extract_and_merge_lessons(
            content=content_text,
            filename=filename,
            project_name=project_name,
            project_type=project_type,
            bucket_name=bucket_name
        )
        
        print(f"Lessons processing complete for {project_name}:")
        print(f"  Project level: +{stats['project_added']} lessons, {stats.get('project_conflicts', 0)} conflicts")
        print(f"  Type level: +{stats['type_added']} lessons, {stats.get('type_conflicts', 0)} conflicts")
        
        # Trigger vector ingestion for updated lessons files
        trigger_vector_ingestion(bucket_name, project_name, project_type)
        
        return {
            'statusCode': 200,
            'message': 'Lessons processed successfully',
            'stats': stats
        }
        
    except Exception as e:
        print(f"Error processing lessons async: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'error': str(e)}


def trigger_vector_ingestion(bucket_name, project_name, project_type):
    """Trigger vector ingestion for lessons learned files"""
    trigger_project_lessons_ingestion(bucket_name, project_name)
    trigger_type_lessons_ingestion(bucket_name, project_type)

