import json
import logging
import os
from typing import Dict, List

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_agent = boto3.client("bedrock-agent-runtime")
bedrock_runtime = boto3.client("bedrock-runtime")


def handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "")
        selected_model = body.get("model", None)

        if not query:
            return {
                "statusCode": 400,
                "headers": get_cors_headers(),
                "body": json.dumps({"error": "Query is required"}),
            }

        # Perform global search without filtering
        results = search_global(query)

        # Generate RAG response with selected model
        response = generate_rag_response(query, results, selected_model)

        return {
            "statusCode": 200,
            "headers": get_cors_headers(),
            "body": json.dumps({"response": response, "source_count": len(results)}),
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": get_cors_headers(),
            "body": json.dumps({"error": str(e)}),
        }


def search_with_project_filter(query: str, project: str) -> List[Dict]:
    """Search with project filter"""
    knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")
    bucket_name = os.getenv("BUCKET_NAME")

    response = bedrock_agent.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 10,
                "filter": {"equals": {"key": "project_name", "value": project}},
            }
        },
    )

    results = response.get("retrievalResults", [])
    
    # Enhance results with presigned URLs
    s3_client = boto3.client("s3")
    for result in results:
        location = result.get("location", {})
        s3_uri = location.get("s3Location", {}).get("uri", "")
        
        if s3_uri and bucket_name:
            s3_key = s3_uri.replace(f"s3://{bucket_name}/", "")
            
            # Get metadata from S3 object
            try:
                obj_metadata = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                obj_meta = obj_metadata.get('Metadata', {})
                
                # Extract lesson ID for chunk info
                lesson_id = obj_meta.get('lesson-id', '')
                if lesson_id:
                    result["chunk_info"] = f"Lesson {lesson_id[:8]}"
                
                # Get source document key
                source_doc_key = obj_meta.get('source-document')
                if source_doc_key:
                    result["source_document"] = source_doc_key
                    
            except Exception as e:
                logger.error(f"Error getting object metadata: {e}")
            
            # Generate presigned URL for markdown
            try:
                result["presigned_url"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': s3_key},
                    ExpiresIn=3600
                )
            except Exception as e:
                logger.error(f"Error generating presigned URL: {e}")
    
    return results


def search_global(query: str) -> List[Dict]:
    """Global search without filters"""
    knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")
    bucket_name = os.getenv("BUCKET_NAME")

    response = bedrock_agent.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 10}},
    )

    results = response.get("retrievalResults", [])
    
    # Enhance results with presigned URLs
    s3_client = boto3.client("s3")
    for result in results:
        location = result.get("location", {})
        s3_uri = location.get("s3Location", {}).get("uri", "")
        
        if s3_uri and bucket_name:
            s3_key = s3_uri.replace(f"s3://{bucket_name}/", "")
            
            # Get metadata from S3 object
            try:
                obj_metadata = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                obj_meta = obj_metadata.get('Metadata', {})
                
                # Use project name from metadata
                result["project_name"] = obj_meta.get('project-name', 'unknown')
                
                # Extract lesson ID for chunk info
                lesson_id = obj_meta.get('lesson-id', '')
                if lesson_id:
                    result["chunk_info"] = f"Lesson {lesson_id[:8]}"
                
                # Get source document key
                source_doc_key = obj_meta.get('source-document')
                if source_doc_key:
                    result["source_document"] = source_doc_key
                    
            except Exception as e:
                logger.error(f"Error getting object metadata: {e}")
            
            # Generate presigned URL for markdown
            try:
                result["presigned_url"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': s3_key},
                    ExpiresIn=3600
                )
            except Exception as e:
                logger.error(f"Error generating presigned URL: {e}")
    
    return results


def generate_rag_response(query: str, search_results: List[Dict], selected_model: str = None) -> str:
    """Generate RAG response using Claude"""
    model_id = selected_model or os.getenv("BEDROCK_MODEL_ID")

    # Prepare context from search results
    context_parts = []
    for result in search_results:
        content = result.get("content", {}).get("text", "")
        metadata = result.get("metadata", {})
        source = metadata.get("source", "Unknown")

        context_parts.append(f"Source: {source}\nContent: {content}\n")

    context = "\n---\n".join(context_parts)

    if not context:
        return "I couldn't find any relevant information to answer your question."

    prompt = f"""Based on the following context from meeting documents, please answer the user's question.
If the context doesn't contain enough information to answer the question, say so clearly.

Context:
{context}

Question: {query}

Answer:"""

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    response = bedrock_runtime.invoke_model(modelId=model_id, body=body)

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]


def get_cors_headers():
    """Return CORS headers"""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
