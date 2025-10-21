import os

import boto3
import cfnresponse


def on_event(event, context):
    request_type = event["RequestType"]
    props = event["ResourceProperties"]

    bucket_name = props["VectorBucketName"]
    index_name = props["IndexName"]
    distance_metric = props["DistanceMetric"]
    data_type = props["DataType"]
    dimension = int(props["Dimension"])

    s3v = boto3.client("s3vectors")
    try:
        if request_type == "Create":
            try:
                s3v.create_vector_bucket(vectorBucketName=bucket_name)
            except s3v.exceptions.ConflictException:
                pass

            try:
                s3v.create_index(
                    vectorBucketName=bucket_name,
                    indexName=index_name,
                    dataType=data_type,
                    dimension=dimension,
                    distanceMetric=distance_metric,
                )
            except s3v.exceptions.ConflictException:
                pass

            bucket_arn = f"arn:aws:s3vectors:{os.environ.get('AWS_REGION')}:{_account_id(context)}:bucket/{bucket_name}"
            idx = s3v.get_index(indexName=index_name, vectorBucketName=bucket_name)
            index_arn = idx.get("indexArn") or f"{bucket_arn}/index/{index_name}"

            data = {"VectorBucketArn": bucket_arn, "IndexArn": index_arn}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, data)
        elif request_type == "Delete":
            try:
                s3v.delete_index(indexName=index_name, vectorBucketName=bucket_name)
            except Exception:
                pass
            try:
                s3v.delete_vector_bucket(vectorBucketName=bucket_name)
            except Exception:
                pass
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        else:
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": str(e)})


def _account_id(context):
    arn = context.invoked_function_arn
    return arn.split(":")[4]
