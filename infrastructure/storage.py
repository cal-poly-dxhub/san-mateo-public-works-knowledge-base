import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb, aws_s3 as s3
from constructs import Construct


class StorageResources(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Main project management bucket
        self.bucket = s3.Bucket(
            self,
            "ProjectManagementBucket",
            bucket_name="dpw-project-management",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.DELETE,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["*"],
                    exposed_headers=["ETag"],
                    max_age=3000,
                )
            ],
        )

        # Docs bucket for knowledge base
        self.docs_bucket = s3.Bucket(
            self,
            "DocsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # DynamoDB table for project data
        self.project_data_table = dynamodb.Table(
            self,
            "ProjectManagementTable",
            table_name="project-management-data",
            partition_key=dynamodb.Attribute(
                name="project_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="item_id", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
