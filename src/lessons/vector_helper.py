"""Reusable helper for vector operations across the codebase"""
import json
import os
import boto3
from typing import List, Dict, Any

lambda_client = boto3.client("lambda")

# S3 Vectors client - may not be available in all environments
try:
    s3vectors_client = boto3.client("s3vectors")
except Exception:
    s3vectors_client = None


def trigger_vector_ingestion(bucket_name: str, s3_key: str):
    """
    Trigger vector ingestion for an S3 object.
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key (e.g., "projects/my-project/lessons-learned.json")
    """
    try:
        lambda_client.invoke(
            FunctionName=os.environ.get("ASYNC_LESSONS_PROCESSOR_NAME"),
            InvocationType="Event",
            Payload=json.dumps({
                "Records": [{
                    "s3": {
                        "bucket": {"name": bucket_name},
                        "object": {"key": s3_key}
                    }
                }]
            })
        )
        print(f"Triggered vector ingestion for {s3_key}")
    except Exception as e:
        print(f"Error triggering vector ingestion for {s3_key}: {e}")


def trigger_project_lessons_ingestion(bucket_name: str, project_name: str):
    """Trigger vector sync for project lessons file"""
    from sync_lessons_vectors import sync_lessons_to_vectors
    import json
    
    # Read lessons from S3
    s3_key = f"projects/{project_name}/lessons-learned.json"
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        lessons_data = json.loads(response['Body'].read().decode('utf-8'))
        lessons = lessons_data.get('lessons', [])
        
        # Sync directly with correct parameter order
        sync_lessons_to_vectors(
            bucket_name=bucket_name,
            lessons_key=s3_key,
            lessons=lessons,
            project_name=project_name
        )
        print(f"Triggered vector sync for {s3_key}")
    except Exception as e:
        print(f"Error triggering vector sync for {s3_key}: {e}")


def trigger_type_lessons_ingestion(bucket_name: str, project_type: str):
    """Trigger vector ingestion for project type master lessons file"""
    s3_key = f"lessons-learned/{project_type}/master-lessons.json"
    trigger_vector_ingestion(bucket_name, s3_key)


def delete_vectors_by_project(vector_bucket_name: str, index_name: str, project_name: str):
    """
    Delete all vectors for a specific project.
    
    Args:
        vector_bucket_name: S3 Vectors bucket name
        index_name: Vector index name
        project_name: Project name to filter by
    """
    try:
        vector_ids = []
        next_token = None
        
        # Paginate through all vectors
        while True:
            params = {
                "vectorBucketName": vector_bucket_name,
                "indexName": index_name,
                "returnMetadata": True,
                "maxResults": 500
            }
            if next_token:
                params["nextToken"] = next_token
                
            response = s3vectors_client.list_vectors(**params)
            
            # Filter by project_name
            for v in response.get("vectors", []):
                if v.get("metadata", {}).get("project_name") == project_name:
                    vector_ids.append(v["key"])
            
            next_token = response.get("nextToken")
            if not next_token:
                break
        
        if vector_ids:
            # Delete in batches of 100
            for i in range(0, len(vector_ids), 100):
                batch = vector_ids[i:i+100]
                s3vectors_client.delete_vectors(
                    vectorBucketName=vector_bucket_name,
                    indexName=index_name,
                    keys=batch
                )
            print(f"Deleted {len(vector_ids)} vectors for project {project_name}")
        else:
            print(f"No vectors found for project {project_name}")
            
    except Exception as e:
        print(f"Error deleting vectors for project {project_name}: {e}")


def delete_vectors_by_file(vector_bucket_name: str, index_name: str, project_name: str, file_name: str):
    """
    Delete vectors for a specific file within a project.
    
    Args:
        vector_bucket_name: S3 Vectors bucket name
        index_name: Vector index name
        project_name: Project name
        file_name: File name to filter by
    """
    try:
        vector_ids = []
        next_token = None
        
        # Paginate through all vectors
        while True:
            params = {
                "vectorBucketName": vector_bucket_name,
                "indexName": index_name,
                "returnMetadata": True,
                "maxResults": 500
            }
            if next_token:
                params["nextToken"] = next_token
                
            response = s3vectors_client.list_vectors(**params)
            
            # Filter by project_name and file_name
            for v in response.get("vectors", []):
                metadata = v.get("metadata", {})
                if (metadata.get("project_name") == project_name and 
                    metadata.get("file_name") == file_name):
                    vector_ids.append(v["key"])
            
            next_token = response.get("nextToken")
            if not next_token:
                break
        
        if vector_ids:
            # Delete in batches of 100
            for i in range(0, len(vector_ids), 100):
                batch = vector_ids[i:i+100]
                s3vectors_client.delete_vectors(
                    vectorBucketName=vector_bucket_name,
                    indexName=index_name,
                    keys=batch
                )
            print(f"Deleted {len(vector_ids)} vectors for {project_name}/{file_name}")
            
    except Exception as e:
        print(f"Error deleting vectors for {project_name}/{file_name}: {e}")


def query_vectors_by_project(
    vector_bucket_name: str,
    index_name: str,
    query_embedding: List[float],
    project_name: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Query vectors filtered by project.
    
    Args:
        vector_bucket_name: S3 Vectors bucket name
        index_name: Vector index name
        query_embedding: Query vector embedding
        project_name: Project name to filter by
        max_results: Maximum number of results
        
    Returns:
        List of matching vectors with metadata
    """
    try:
        response = s3vectors_client.query_vectors(
            vectorBucketName=vector_bucket_name,
            indexName=index_name,
            queryVector={"float32": query_embedding},
            metadataFilters={
                "project_name": {"equals": project_name}
            },
            maxResults=max_results
        )
        
        return response.get("vectors", [])
        
    except Exception as e:
        print(f"Error querying vectors for project {project_name}: {e}")
        return []


def query_vectors_by_type(
    vector_bucket_name: str,
    index_name: str,
    query_embedding: List[float],
    project_type: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Query vectors filtered by project type.
    
    Args:
        vector_bucket_name: S3 Vectors bucket name
        index_name: Vector index name
        query_embedding: Query vector embedding
        project_type: Project type to filter by (e.g., "slurry-seal")
        max_results: Maximum number of results
        
    Returns:
        List of matching vectors with metadata
    """
    try:
        response = s3vectors_client.query_vectors(
            vectorBucketName=vector_bucket_name,
            indexName=index_name,
            queryVector={"float32": query_embedding},
            metadataFilters={
                "project_type": {"equals": project_type}
            },
            maxResults=max_results
        )
        
        return response.get("vectors", [])
        
    except Exception as e:
        print(f"Error querying vectors for type {project_type}: {e}")
        return []


def query_lessons_only(
    vector_bucket_name: str,
    index_name: str,
    query_embedding: List[float],
    project_name: str = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Query only lesson vectors, optionally filtered by project.
    
    Args:
        vector_bucket_name: S3 Vectors bucket name
        index_name: Vector index name
        query_embedding: Query vector embedding
        project_name: Optional project name to filter by
        max_results: Maximum number of results
        
    Returns:
        List of matching lesson vectors with metadata
    """
    try:
        filters = {"is_lesson": {"equals": "true"}}
        if project_name:
            filters["project_name"] = {"equals": project_name}
            
        response = s3vectors_client.query_vectors(
            vectorBucketName=vector_bucket_name,
            indexName=index_name,
            queryVector={"float32": query_embedding},
            metadataFilters=filters,
            maxResults=max_results
        )
        
        return response.get("vectors", [])
        
    except Exception as e:
        print(f"Error querying lesson vectors: {e}")
        return []
