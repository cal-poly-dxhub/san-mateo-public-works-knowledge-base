import json
import os
from typing import Any, Dict, List

import boto3


def handler(event, context):
    """
    Handle search requests for the knowledge base
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "")
        limit = body.get("limit", 10)
        model_id = body.get("model_id")

        print(f"Search request - Query: {query}, Limit: {limit}, Model: {model_id}")

        # Check if this is a RAG search request
        path = event.get("path", "")

        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Query parameter is required"}),
            }

        if path.endswith("/search-rag"):
            # Perform RAG search
            result = search_with_rag(query, limit, model_id)
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "query": query,
                        "answer": result["answer"],
                        "sources": result["sources"],
                        "type": "rag",
                    }
                ),
            }
        else:
            # Perform regular vector search
            results = search_vector_index(query, limit)
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "query": query,
                        "results": results,
                        "message": f"Found {len(results)} results",
                    }
                ),
            }

    except Exception as e:
        print(f"Error in search handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error"}),
        }


def search_with_rag(query: str, limit: int = 10, selected_model: str = None) -> dict:
    """
    Perform RAG search using Knowledge Base retrieve_and_generate
    """
    try:
        bedrock_agent_client = boto3.client("bedrock-agent-runtime")
        
        kb_id = os.environ.get("KB_ID")
        model_id = selected_model or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        
        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        # Determine if model is an inference profile or foundation model
        region = os.environ.get('AWS_REGION', 'us-west-2')
        if model_id.startswith("us.") or model_id.startswith("eu."):
            model_arn = f"arn:aws:bedrock:{region}::inference-profile/{model_id}"
        else:
            model_arn = f"arn:aws:bedrock:{region}::foundation-model/{model_id}"

        # Use retrieve_and_generate for RAG
        response = bedrock_agent_client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": model_arn,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": limit
                        }
                    }
                }
            }
        )

        # Extract answer and sources
        answer = response.get("output", {}).get("text", "No answer generated")
        citations = response.get("citations", [])
        
        # Format sources from citations
        sources = []
        for citation in citations:
            for reference in citation.get("retrievedReferences", []):
                content = reference.get("content", {}).get("text", "")
                metadata = reference.get("metadata", {})
                sources.append({
                    "content": content,
                    "source": metadata.get("file_name", "unknown"),
                    "project": metadata.get("project_name", "unknown"),
                })

        return {"answer": answer, "sources": sources}

    except Exception as e:
        print(f"Error in RAG search: {str(e)}")
        return {
            "answer": f"I encountered an error while processing your question: {str(e)}",
            "sources": [],
        }




def search_vector_index(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search the Knowledge Base using retrieve API
    """
    try:
        # Initialize Bedrock Agent Runtime client
        bedrock_agent_client = boto3.client("bedrock-agent-runtime")
        
        kb_id = os.environ.get("KB_ID")
        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        # Perform Knowledge Base retrieve
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": limit
                }
            }
        )

        # Format results
        results = []
        for item in response.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            metadata = item.get("metadata", {})
            score = item.get("score", 0.0)
            
            results.append(
                {
                    "content": content,
                    "source": metadata.get("file_name", "unknown"),
                    "project": metadata.get("project_name", "unknown"),
                    "relevance_score": round(score * 100),
                    "metadata": metadata,
                }
            )

        return results

    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        return []


def chunk_text(
    text: str, chunk_size_tokens: int, overlap_tokens: int
) -> List[str]:
    """Chunk text with fixed size and overlap (same as ingestion script)"""
    chunk_size_chars = chunk_size_tokens * 4
    overlap_chars = overlap_tokens * 4

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size_chars
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap_chars
        if start >= len(text):
            break

    return chunks
