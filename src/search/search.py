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

        print(f"Search request - Query: {query}, Limit: {limit}")

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
            result = search_with_rag(query, limit)
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


def search_with_rag(query: str, limit: int = 10) -> dict:
    """
    Perform RAG search: retrieve relevant documents and generate answer using LLM
    """
    try:
        # First, get relevant documents using vector search
        documents = search_vector_index(query, limit)

        if not documents:
            return {
                "answer": "I couldn't find any relevant information in the project documentation to answer your question.",
                "sources": [],
            }

        # Prepare context from retrieved documents with citation numbers
        context_parts = []
        for i, doc in enumerate(documents):
            context_parts.append(
                f"[{i + 1}] Source: {doc['source']}\nContent: {doc['content']}"
            )

        context = "\n\n".join(context_parts)

        # Load RAG configuration
        config = load_config()
        rag_config = config.get("rag_search", {})
        model_id = rag_config.get(
            "model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
        )

        prompt = f"""You are an AI assistant that answers questions based on project documentation.

Use the following context from the documentation to answer the user's question. When referencing information, include inline citations using [1], [2], [3] etc. to indicate which source you're using.

IMPORTANT: Format your response using markdown syntax:
- Start with a brief intro paragraph
- Use ## for section headings if organizing multiple topics
- Use **bold text** for key terms and important points
- Use bullet points (- ) or numbered lists (1. ) for multiple items
- Add a blank line between paragraphs and list items
- Keep each point concise

Context:
{context}

Question: {query}

Provide your answer in well-formatted markdown:"""

        # Call the LLM
        bedrock_client = boto3.client("bedrock-runtime")

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = bedrock_client.invoke_model(
            modelId=model_id, body=json.dumps(request_body)
        )

        result = json.loads(response["body"].read())
        answer = result["content"][0]["text"]

        return {"answer": answer, "sources": documents}

    except Exception as e:
        print(f"Error in RAG search: {str(e)}")
        return {
            "answer": f"I encountered an error while processing your question: {str(e)}",
            "sources": [],
        }


def load_config():
    """Load configuration from SSM parameters"""
    try:
        ssm_client = boto3.client("ssm")

        # Get RAG search configuration from SSM
        prompt_response = ssm_client.get_parameter(
            Name="/meeting-automation/rag-search/prompt"
        )
        model_response = ssm_client.get_parameter(
            Name="/meeting-automation/rag-search/model-id"
        )

        return {
            "rag_search": {
                "model_id": model_response["Parameter"]["Value"],
                "prompt": prompt_response["Parameter"]["Value"],
            }
        }
    except Exception as e:
        print(f"Error loading config from SSM: {e}")
        # Fallback to default config
        return {
            "rag_search": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "prompt": """You are an AI assistant that answers questions based on meeting transcripts and project documentation.

Use the following context from meeting transcripts to answer the user's question. If the information is not available in the context, say so clearly.

Context:
{context}

Question: {question}

Answer:""",
            }
        }


def search_vector_index(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search the S3 vector index using embeddings
    """
    try:
        # Initialize clients
        bedrock_client = boto3.client("bedrock-runtime")
        s3vectors_client = boto3.client("s3vectors")
        s3_client = boto3.client("s3")

        # Generate embedding for query
        embedding_response = bedrock_client.invoke_model(
            modelId=os.environ.get(
                "EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
            ),
            body=json.dumps({"inputText": query}),
        )

        embedding_result = json.loads(embedding_response["body"].read())
        query_embedding = embedding_result["embedding"]

        # Prepare search parameters
        search_params = {
            "vectorBucketName": os.environ.get(
                "VECTOR_BUCKET_NAME", "dpw-project-mgmt-vectors"
            ),
            "indexName": os.environ.get("INDEX_NAME", "project-mgmt-index"),
            "queryVector": {"float32": query_embedding},
            "topK": limit,
            "returnDistance": True,
            "returnMetadata": True,
        }

        print("Searching all documents in knowledge base")

        # Perform vector search
        search_response = s3vectors_client.query_vectors(**search_params)

        # Format results and get actual content
        results = []
        for vector in search_response.get("vectors", []):
            metadata = vector.get("metadata", {})

            # Get chunk content directly from vector metadata
            chunk_content = metadata.get("content", "Content not available")

            results.append(
                {
                    "content": chunk_content,
                    "source": metadata.get("file_name", "unknown"),
                    "project": metadata.get("project_name", "unknown"),
                    "relevance_score": round(
                        (1.0 - vector.get("distance", 0.0)) * 100
                    ),  # Convert to percentage
                    "chunk_index": metadata.get("chunk_index", "0"),
                    "total_chunks": metadata.get("total_chunks", "1"),
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
