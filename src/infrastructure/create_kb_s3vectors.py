import os

import boto3
import cfnresponse
import yaml


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def on_event(event, context):
    print(f"Event: {event}")
    request_type = event["RequestType"]
    props = event["ResourceProperties"]

    kb_name = props["KnowledgeBaseName"]
    role_arn = props["RoleArn"]
    data_bucket_arn = props["DataBucketArn"]
    region = os.environ.get("AWS_REGION")

    config = load_config()
    chunk_size = config["vector_search"]["chunk_size_tokens"]
    overlap = config["vector_search"]["overlap_tokens"]

    try:
        bedrock = boto3.client("bedrock-agent", region_name=region)
        s3v = boto3.client("s3vectors", region_name=region)

        if request_type == "Create":
            vector_bucket_name = f"{kb_name}-vectors"
            index_name = f"{kb_name}-index"

            try:
                s3v.create_vector_bucket(vectorBucketName=vector_bucket_name)
            except s3v.exceptions.ConflictException:
                pass

            try:
                s3v.create_index(
                    vectorBucketName=vector_bucket_name,
                    indexName=index_name,
                    dataType="float32",
                    dimension=1024,
                    distanceMetric="cosine",
                    MetadataConfiguration={
                        "nonFilterableMetadataKeys": [
                            "AMAZON_BEDROCK_TEXT",
                            "AMAZON_BEDROCK_METADATA",
                        ]
                    },
                )
            except s3v.exceptions.ConflictException:
                pass

            account_id = context.invoked_function_arn.split(":")[4]
            index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}/index/{index_name}"

            kb_response = bedrock.create_knowledge_base(
                name=kb_name,
                roleArn=role_arn,
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
                    },
                },
                storageConfiguration={
                    "type": "S3_VECTORS",
                    "s3VectorsConfiguration": {"indexArn": index_arn},
                },
            )

            kb_id = kb_response["knowledgeBase"]["knowledgeBaseId"]

            bedrock.create_data_source(
                knowledgeBaseId=kb_id,
                name="project-documents",
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": {
                        "bucketArn": data_bucket_arn,
                        "inclusionPrefixes": ["documents/"],
                    },
                },
                vectorIngestionConfiguration={
                    "chunkingConfiguration": {
                        "chunkingStrategy": "FIXED_SIZE",
                        "fixedSizeChunkingConfiguration": {
                            "maxTokens": chunk_size,
                            "overlapPercentage": int(
                                (overlap / chunk_size) * 100
                            ),
                        },
                    }
                },
            )

            cfnresponse.send(
                event,
                context,
                cfnresponse.SUCCESS,
                {"KnowledgeBaseId": kb_id},
                kb_id,
            )

        elif request_type == "Delete":
            kb_id = event.get("PhysicalResourceId")
            if kb_id and kb_id != context.log_stream_name:
                try:
                    bedrock.delete_knowledge_base(knowledgeBaseId=kb_id)
                except Exception:
                    pass
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, kb_id)
        else:
            cfnresponse.send(
                event,
                context,
                cfnresponse.SUCCESS,
                {},
                event.get("PhysicalResourceId"),
            )

    except Exception as e:
        print(f"ERROR: {str(e)}")
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {},
            event.get("PhysicalResourceId", context.log_stream_name),
        )
