import json
import boto3
import os

bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

def handler(event, context):
    """Handle AI assistant queries"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        question = body.get('question')
        project_id = body.get('projectId')
        request_type = body.get('type', 'question')  # question, template, alert
        
        if request_type == 'template':
            return generate_template(body)
        elif request_type == 'alert':
            return check_proactive_alerts(project_id)
        else:
            return answer_question(question, project_id)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def answer_question(question, project_id):
    """Answer user question using AI with project context"""
    
    # Get project context
    project_context = get_project_context(project_id) if project_id else {}
    
    # Search knowledge base for relevant information
    knowledge_results = search_knowledge_base(question)
    
    prompt = f"""You are an experienced Public Works senior engineer assistant.

Project Context:
{json.dumps(project_context, indent=2) if project_context else 'No specific project context'}

User Question: {question}

Relevant Information:
{knowledge_results}

Provide a helpful, specific answer that:
1. Directly answers the question
2. References specific regulations or procedures when applicable
3. Suggests next steps
4. Warns about common pitfalls
5. Provides links to templates if relevant

Be concise but thorough."""
    
    try:
        response = bedrock.invoke_model(
            modelId=os.environ['AI_ASSISTANT_MODEL_ID'],
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        answer = response_body['content'][0]['text']
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'answer': answer,
                'context': project_context
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def generate_template(body):
    """Generate document template"""
    
    document_type = body.get('documentType')
    project_details = body.get('projectDetails', {})
    
    prompt = f"""Generate a {document_type} for this project:

Project Details:
{json.dumps(project_details, indent=2)}

The document should be professional, complete, and ready to use with all project-specific information filled in.

Format as markdown."""
    
    try:
        response = bedrock.invoke_model(
            modelId=os.environ['TEMPLATE_GENERATION_MODEL_ID'],
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        template = response_body['content'][0]['text']
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'template': template,
                'documentType': document_type
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def check_proactive_alerts(project_id):
    """Check for proactive alerts based on project status"""
    
    project_status = get_project_status(project_id)
    recent_activity = get_recent_activity(project_id)
    
    prompt = f"""Analyze this project and identify potential issues or recommendations.

Project Status:
{json.dumps(project_status, indent=2)}

Recent Activity:
{json.dumps(recent_activity, indent=2)}

Check for:
- Tasks that should have started but haven't
- Dependencies blocking progress
- Upcoming deadlines needing preparation
- Common issues from similar projects
- Coordination gaps

Return JSON:
{{"alerts": [{{"severity": "warning", "title": "Title", "message": "Details", "suggestedAction": "What to do", "relatedTasks": []}}]}}"""
    
    try:
        response = bedrock.invoke_model(
            modelId=os.environ['AI_ASSISTANT_MODEL_ID'],
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Extract JSON
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            alerts = json.loads(content[start:end])
        else:
            alerts = {"alerts": []}
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(alerts)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 200,
            'body': json.dumps({"alerts": []})
        }

def get_project_context(project_id):
    """Get project context from DynamoDB"""
    try:
        table = dynamodb.Table(os.environ['PROJECT_DATA_TABLE_NAME'])
        response = table.get_item(Key={'project_id': project_id, 'item_id': 'config'})
        return response.get('Item', {})
    except:
        return {}

def get_project_status(project_id):
    """Get current project status"""
    try:
        table = dynamodb.Table(os.environ['PROJECT_DATA_TABLE_NAME'])
        response = table.query(
            KeyConditionExpression='project_id = :pid',
            ExpressionAttributeValues={':pid': project_id}
        )
        return response.get('Items', [])
    except:
        return []

def get_recent_activity(project_id):
    """Get recent project activity"""
    return []

def search_knowledge_base(query):
    """Search knowledge base for relevant information"""
    # This would integrate with the vector search
    return "Relevant regulations and procedures..."
