import json
import os
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

def decimal_to_number(obj):
    """Convert Decimal to int or float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def handler(event, context):
    """Handle checklist requests"""
    try:
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, PUT, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-Api-Key'
                },
                'body': ''
            }
        
        if '/checklist' in path and method == 'GET':
            project_name = event['pathParameters']['project_name']
            return get_checklist(project_name)
        
        elif '/checklist' in path and method == 'PUT':
            project_name = event['pathParameters']['project_name']
            body = json.loads(event.get('body', '{}'))
            task_id = body.get('task_id')
            completed_date = body.get('completed_date')
            return update_task(project_name, task_id, completed_date)
        
        return {
            'statusCode': 404,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Not found'})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def get_checklist(project_name):
    """Get all tasks for a project from DynamoDB"""
    try:
        table = dynamodb.Table(os.environ['PROJECT_DATA_TABLE_NAME'])
        
        # Get project config to find project_id
        response = table.scan(
            FilterExpression='projectName = :pname',
            ExpressionAttributeValues={':pname': project_name}
        )
        
        if not response['Items']:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'tasks': [],
                    'progress': {'total': 0, 'completed': 0, 'percentage': 0}
                })
            }
        
        project_id = response['Items'][0]['project_id']
        
        # Get all tasks for this project
        response = table.query(
            KeyConditionExpression='project_id = :pid AND begins_with(item_id, :task)',
            ExpressionAttributeValues={
                ':pid': project_id,
                ':task': 'task#'
            }
        )
        
        tasks = []
        completed_count = 0
        
        for item in response['Items']:
            task_data = item.get('taskData', {})
            completed_date = item.get('completed_date')
            
            task = {
                'task_id': item['item_id'],
                'phase': task_data.get('phase', ''),
                'task': task_data.get('task', ''),
                'description': task_data.get('description', ''),
                'estimatedDays': decimal_to_number(task_data.get('estimatedDays', 0)),
                'dependencies': task_data.get('dependencies', []),
                'required': task_data.get('required', True),
                'completed_date': completed_date,
                'status': 'completed' if completed_date else item.get('status', 'not_started')
            }
            
            if completed_date:
                completed_count += 1
            
            tasks.append(task)
        
        # Calculate progress
        total = len(tasks)
        percentage = int((completed_count / total * 100)) if total > 0 else 0
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'tasks': tasks,
                'progress': {
                    'total': total,
                    'completed': completed_count,
                    'percentage': percentage
                }
            })
        }
        
    except Exception as e:
        print(f"Error getting checklist: {str(e)}")
        raise

def update_task(project_name, task_id, completed_date):
    """Update task completion status"""
    try:
        table = dynamodb.Table(os.environ['PROJECT_DATA_TABLE_NAME'])
        
        # Get project_id
        response = table.scan(
            FilterExpression='projectName = :pname',
            ExpressionAttributeValues={':pname': project_name}
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Project not found'})
            }
        
        project_id = response['Items'][0]['project_id']
        
        # Update task
        update_expr = 'SET #status = :status'
        expr_values = {':status': 'completed' if completed_date else 'not_started'}
        expr_names = {'#status': 'status'}
        
        if completed_date:
            update_expr += ', completed_date = :date'
            expr_values[':date'] = completed_date
        else:
            update_expr += ' REMOVE completed_date'
        
        table.update_item(
            Key={'project_id': project_id, 'item_id': task_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names
        )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': 'Task updated'})
        }
        
    except Exception as e:
        print(f"Error updating task: {str(e)}")
        raise
