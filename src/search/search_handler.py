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

    return response.get("retrievalResults", [])


def search_global(query: str) -> List[Dict]:
    """Global search without filters"""
    knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")

    response = bedrock_agent.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 10}},
    )

    return response.get("retrievalResults", [])


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
