import json
import os
from typing import Any, Dict, List

import boto3


def handler(event, context):
    """
    Handle search requests for the knowledge base
    """
    try:
        # Handle OPTIONS for CORS preflight
        method = event.get("httpMethod", "POST")
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization",
                },
                "body": "",
            }

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "")
        limit = body.get("limit", 10)
        model_id = body.get("model_id")

        print(
            f"Search request - Query: {query}, Limit: {limit}, Model: {model_id}"
        )

        # Check if this is a RAG search request
        path = event.get("path", "")

        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                    "Access-Control-Allow-Credentials": "true",
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
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                    "Access-Control-Allow-Credentials": "true",
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
                    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                    "Access-Control-Allow-Credentials": "true",
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
                "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
                "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps({"error": "Internal server error"}),
        }


def search_with_rag(
    query: str, limit: int = 10, selected_model: str = None
) -> dict:
    """
    Perform RAG search using Knowledge Base retrieve_and_generate
    """
    try:
        bedrock_agent_client = boto3.client("bedrock-agent-runtime")
        s3_client = boto3.client("s3")

        kb_id = os.environ.get("KB_ID")
        bucket_name = os.environ.get("BUCKET_NAME")
        model_id = selected_model or os.environ.get("BEDROCK_MODEL_ID")
        rag_prompt = os.environ.get("RAG_PROMPT")

        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        # Build retrieve_and_generate config
        rag_config = {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": model_id,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {"numberOfResults": limit}
                },
            },
        }

        # Add custom prompt if provided
        if rag_prompt:
            rag_config["knowledgeBaseConfiguration"]["generationConfiguration"] = {
                "promptTemplate": {"textPromptTemplate": f"{rag_prompt}\n\n$search_results$"}
            }

        # Use retrieve_and_generate for RAG
        response = bedrock_agent_client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration=rag_config,
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
                location = reference.get("location", {})

                # Extract S3 info and generate presigned URL
                s3_uri = location.get("s3Location", {}).get("uri", "")
                presigned_url = None
                project_name = "unknown"
                chunk_info = None
                source_doc_key = None

                if s3_uri and bucket_name:
                    s3_key = s3_uri.replace(f"s3://{bucket_name}/", "")

                    # Get metadata from S3 object
                    try:
                        obj_metadata = s3_client.head_object(
                            Bucket=bucket_name, Key=s3_key
                        )
                        obj_meta = obj_metadata.get("Metadata", {})

                        # Use project name from metadata
                        project_name = obj_meta.get("project-name", "unknown")

                        # Extract lesson ID for chunk info
                        lesson_id = obj_meta.get("lesson-id", "")
                        if lesson_id:
                            chunk_info = f"Lesson {lesson_id[:8]}"

                        # Get source document key
                        source_doc_key = obj_meta.get("source-document")

                    except Exception as e:
                        print(f"Error getting object metadata: {e}")

                    # Generate presigned URL for markdown
                    try:
                        presigned_url = s3_client.generate_presigned_url(
                            "get_object",
                            Params={"Bucket": bucket_name, "Key": s3_key},
                            ExpiresIn=3600,
                        )
                    except Exception as e:
                        print(f"Error generating presigned URL: {e}")

                sources.append(
                    {
                        "content": content,
                        "source": source_doc_key
                        or metadata.get(
                            "file_name",
                            s3_uri.split("/")[-1] if s3_uri else "unknown",
                        ),
                        "project": project_name,
                        "presigned_url": presigned_url,
                        "chunk": chunk_info,
                    }
                )

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
        s3_client = boto3.client("s3")

        kb_id = os.environ.get("KB_ID")
        bucket_name = os.environ.get("BUCKET_NAME")
        if not kb_id:
            raise ValueError("KB_ID environment variable not set")

        # Perform Knowledge Base retrieve
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": limit}
            },
        )

        # Format results
        results = []
        for item in response.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            metadata = item.get("metadata", {})
            location = item.get("location", {})

            # Extract S3 info and generate presigned URL
            s3_uri = location.get("s3Location", {}).get("uri", "")
            presigned_url = None
            project_name = "unknown"
            chunk_info = None
            source_doc_key = None

            if s3_uri and bucket_name:
                # Parse s3://bucket/key format
                s3_key = s3_uri.replace(f"s3://{bucket_name}/", "")

                # Get metadata from S3 object
                try:
                    obj_metadata = s3_client.head_object(
                        Bucket=bucket_name, Key=s3_key
                    )
                    obj_meta = obj_metadata.get("Metadata", {})

                    # Use project name from metadata
                    project_name = obj_meta.get("project-name", "unknown")

                    # Extract lesson ID for chunk info
                    lesson_id = obj_meta.get("lesson-id", "")
                    if lesson_id:
                        chunk_info = f"Lesson {lesson_id[:8]}"

                    # Get source document key
                    source_doc_key = obj_meta.get("source-document")

                except Exception as e:
                    print(f"Error getting object metadata: {e}")

                # Generate presigned URL for markdown file
                try:
                    presigned_url = s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket_name, "Key": s3_key},
                        ExpiresIn=3600,
                    )
                    print(f"Generated markdown presigned URL for {s3_key}")
                except Exception as e:
                    print(
                        f"Error generating presigned URL for {s3_key}: {str(e)}"
                    )

            results.append(
                {
                    "content": content,
                    "source": source_doc_key
                    or metadata.get(
                        "file_name",
                        s3_uri.split("/")[-1] if s3_uri else "unknown",
                    ),
                    "project": project_name,
                    "presigned_url": presigned_url,
                    "chunk": chunk_info,
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
