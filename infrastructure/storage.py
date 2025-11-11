import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb, aws_s3 as s3, aws_s3_notifications as s3n
from constructs import Construct


class StorageResources(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Main project management bucket (used for everything including Knowledge Base)
        self.bucket = s3.Bucket(
            self,
            "ProjectManagementBucket",
            bucket_name="dpw-project-management",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
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

    def add_lessons_sync_trigger(self, lessons_sync_lambda):
        """Add S3 event notification to trigger lessons sync Lambda"""
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(lessons_sync_lambda),
            s3.NotificationKeyFilter(prefix="projects/", suffix="/lessons.json")
        )
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_REMOVED,
            s3n.LambdaDestination(lessons_sync_lambda),
            s3.NotificationKeyFilter(prefix="projects/", suffix="/lessons.json")
        )
