import os
import boto3
import traceback

def on_event(event, context):
    """CDK Custom Resource handler - returns data directly"""
    print(f"Event: {event}")
    request_type = event["RequestType"]
    props = event["ResourceProperties"]
    
    kb_name = props["KnowledgeBaseName"]
    role_arn = props["RoleArn"]
    data_bucket_arn = props["DataBucketArn"]
    
    region = os.environ.get('AWS_REGION')
    print(f"Region: {region}")
    
    try:
        bedrock = boto3.client("bedrock-agent", region_name=region)
        s3v = boto3.client("s3vectors", region_name=region)
        print("✓ Clients created")
        
        if request_type == "Create":
            # Create S3 Vectors bucket and index first
            vector_bucket_name = f"{kb_name}-vectors"
            index_name = f"{kb_name}-index"
            print(f"Creating vector bucket: {vector_bucket_name}")
            
            try:
                s3v.create_vector_bucket(vectorBucketName=vector_bucket_name)
                print("✓ Vector bucket created")
            except s3v.exceptions.ConflictException:
                print("✓ Vector bucket exists")
            
            try:
                s3v.create_index(
                    vectorBucketName=vector_bucket_name,
                    indexName=index_name,
                    dataType="float32",
                    dimension=1024,
                    distanceMetric="cosine"
                )
                print("✓ Index created")
            except s3v.exceptions.ConflictException:
                print("✓ Index exists")
            
            # Get account ID from context
            account_id = context.invoked_function_arn.split(":")[4]
            index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}/index/{index_name}"
            print(f"Index ARN: {index_arn}")
            
            # Create KB
            print("Creating Knowledge Base...")
            kb_response = bedrock.create_knowledge_base(
                name=kb_name,
                roleArn=role_arn,
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
                    }
                },
                storageConfiguration={
                    "type": "S3_VECTORS",
                    "s3VectorsConfiguration": {
                        "indexArn": index_arn
                    }
                }
            )
            
            kb_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
            print(f"✓ KB created: {kb_id}")
            
            # Create data source
            print("Creating data source...")
            ds_response = bedrock.create_data_source(
                knowledgeBaseId=kb_id,
                name="project-documents",
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": {
                        "bucketArn": data_bucket_arn,
                        "inclusionPrefixes": ["documents/"]
                    }
                },
                vectorIngestionConfiguration={
                    "chunkingConfiguration": {
                        "chunkingStrategy": "FIXED_SIZE",
                        "fixedSizeChunkingConfiguration": {
                            "maxTokens": 300,
                            "overlapPercentage": 10
                        }
                    },
                    "parsingConfiguration": {
                        "parsingStrategy": "BEDROCK_FOUNDATION_MODEL",
                        "bedrockFoundationModelConfiguration": {
                            "modelArn": f"arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
                        }
                    }
                }
            )
            
            ds_id = ds_response["dataSource"]["dataSourceId"]
            print(f"✓ Data source created: {ds_id}")
            
            # Return data for CDK Custom Resource
            return {
                "PhysicalResourceId": kb_id,
                "Data": {
                    "KnowledgeBaseId": kb_id,
                    "DataSourceId": ds_id,
                    "VectorBucketName": vector_bucket_name,
                    "IndexName": index_name
                }
            }
            
        elif request_type == "Delete":
            kb_id = event.get("PhysicalResourceId")
            print(f"Deleting KB: {kb_id}")
            if kb_id and kb_id != context.log_stream_name:
                try:
                    bedrock.delete_knowledge_base(knowledgeBaseId=kb_id)
                    print("✓ KB deleted")
                except Exception as e:
                    print(f"Delete error (ignored): {e}")
            return {"PhysicalResourceId": kb_id}
        else:
            # Update - no changes needed
            return {"PhysicalResourceId": event.get("PhysicalResourceId")}
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        traceback.print_exc()
        raise
