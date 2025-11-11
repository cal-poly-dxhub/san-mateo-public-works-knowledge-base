import json
import boto3
from typing import Dict, List, Any

s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Transform lessons JSON into individual chunks for knowledge base ingestion"""
    
    output_files = []
    
    for input_file in event['inputFiles']:
        # Skip non-lesson files
        original_uri = input_file['originalFileLocation']['s3_location']['uri']
        if 'lessons-learned.json' not in original_uri:
            # Pass through non-lesson files unchanged
            output_files.append(input_file)
            continue
            
        # Process lesson files
        transformed_batches = []
        
        for batch in input_file['contentBatches']:
            # Download and parse the lesson file
            response = s3_client.get_object(
                Bucket=event['bucketName'], 
                Key=batch['key']
            )
            content = json.loads(response['Body'].read().decode('utf-8'))
            
            # Extract project type from file path or metadata
            project_type = input_file.get('fileMetadata', {}).get('project_type', 'unknown')
            
            # Transform each lesson into individual chunks
            lesson_chunks = []
            for lesson in content.get('lessons', []):
                chunk_text = f"""{project_type.title()} Lesson Learned: {lesson.get('title', 'Untitled')}

Lesson: {lesson.get('lesson', '')}
Impact: {lesson.get('impact', '')}
Recommendation: {lesson.get('recommendation', '')}
Severity: {lesson.get('severity', 'Unknown')}"""

                lesson_chunks.append({
                    "contentBody": chunk_text,
                    "contentType": "TEXT",
                    "contentMetadata": {
                        "source_document": lesson.get('source_document', ''),
                        "project_name": lesson.get('project_name', ''),
                        "severity": lesson.get('severity', ''),
                        "lesson_id": lesson.get('id', '')
                    }
                })
            
            # Upload transformed chunks back to S3
            chunks_content = {"fileContents": lesson_chunks}
            output_key = batch['key'].replace('.json', '_transformed.json')
            
            s3_client.put_object(
                Bucket=event['bucketName'],
                Key=output_key,
                Body=json.dumps(chunks_content),
                ContentType='application/json'
            )
            
            transformed_batches.append({"key": output_key})
        
        # Add transformed file to output
        output_files.append({
            "originalFileLocation": input_file['originalFileLocation'],
            "fileMetadata": input_file.get('fileMetadata', {}),
            "contentBatches": transformed_batches
        })
    
    return {"outputFiles": output_files}
