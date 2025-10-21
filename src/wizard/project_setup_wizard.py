import json
import boto3
import os
from datetime import datetime
import uuid

bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """Handle project setup wizard requests"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        project_name = body.get('projectName')
        project_type = body.get('projectType')
        location = body.get('location')
        area_size = body.get('areaSize')
        special_conditions = body.get('specialConditions', [])
        
        # Generate project configuration using AI
        project_config = generate_project_config(
            project_type, location, area_size, special_conditions
        )
        
        # Store project in DynamoDB
        project_id = str(uuid.uuid4())
        table = dynamodb.Table(os.environ['PROJECT_DATA_TABLE_NAME'])
        
        table.put_item(Item={
            'project_id': project_id,
            'item_id': 'config',
            'projectName': project_name,
            'projectType': project_type,
            'location': location,
            'areaSize': area_size,
            'specialConditions': special_conditions,
            'config': project_config,
            'status': 'active',
            'createdDate': datetime.utcnow().isoformat(),
            'lastUpdated': datetime.utcnow().isoformat()
        })
        
        # Store tasks separately for easier querying
        for task in project_config.get('tasks', []):
            task_id = str(uuid.uuid4())
            table.put_item(Item={
                'project_id': project_id,
                'item_id': f"task#{task_id}",
                'taskData': task,
                'status': 'not_started',
                'createdDate': datetime.utcnow().isoformat()
            })
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'projectId': project_id,
                'config': project_config
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def generate_project_config(project_type, location, area_size, special_conditions):
    """Generate project configuration using AI"""
    
    prompt = f"""Based on the following project information, generate a complete project configuration.

Project Information:
- Project Type: {project_type}
- Location: {location}
- Work Area Size: {area_size} acres
- Special Conditions: {', '.join(special_conditions) if special_conditions else 'None'}

Generate a comprehensive project setup including tasks, stakeholders, permits, timeline, and budget estimate.

Return JSON in this format:
{{
  "projectConfig": {{
    "tasks": [{{"phase": "Survey", "task": "Initial site survey", "description": "Details", "estimatedDays": 5, "dependencies": [], "required": true}}],
    "stakeholders": [{{"name": "PG&E", "type": "utility", "contactReason": "Gas line coordination", "timing": "At 60% design"}}],
    "permits": [{{"name": "Encroachment Permit", "agency": "County", "estimatedTime": "2-3 weeks", "required": true}}],
    "timeline": {{"totalEstimatedDays": 365, "milestones": [{{"name": "Design Complete", "estimatedDay": 90}}]}},
    "budgetEstimate": {{"low": 100000, "high": 150000, "basis": "Similar projects"}}
  }}
}}"""
    
    try:
        response = bedrock.invoke_model(
            modelId=os.environ['PROJECT_SETUP_MODEL_ID'],
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Extract JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])['projectConfig']
        
        return generate_default_config(project_type)
        
    except Exception as e:
        print(f"Error generating config: {str(e)}")
        return generate_default_config(project_type)

def generate_default_config(project_type):
    """Generate a basic default configuration"""
    return {
        "tasks": [
            {"phase": "Survey", "task": "Initial site survey", "description": "Conduct field survey", "estimatedDays": 5, "dependencies": [], "required": True},
            {"phase": "Design", "task": "30% design", "description": "Preliminary design", "estimatedDays": 20, "dependencies": ["Initial site survey"], "required": True}
        ],
        "stakeholders": [
            {"name": "Local utilities", "type": "utility", "contactReason": "Coordination", "timing": "At 60% design"}
        ],
        "permits": [
            {"name": "Encroachment Permit", "agency": "County", "estimatedTime": "2-3 weeks", "required": True}
        ],
        "timeline": {
            "totalEstimatedDays": 365,
            "milestones": [{"name": "Design Complete", "estimatedDay": 90}]
        },
        "budgetEstimate": {
            "low": 100000,
            "high": 200000,
            "basis": "Typical range for project type"
        }
    }
