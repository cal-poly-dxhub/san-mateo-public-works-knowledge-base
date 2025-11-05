import aws_cdk as cdk
from aws_cdk import aws_iam as iam, aws_lambda as lambda_, aws_s3 as s3
from constructs import Construct


class KnowledgeBaseResources(Construct):
    def __init__(
        self, scope: Construct, construct_id: str, data_bucket: s3.IBucket, **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        # IAM Role for Knowledge Base
        self.kb_role = iam.Role(
            self,
            "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        data_bucket.grant_read(self.kb_role)

        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{cdk.Stack.of(self).region}::foundation-model/*"],
            )
        )

        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3vectors:*"],
                resources=["*"],
            )
        )

        # Lambda for KB creation
        kb_lambda = lambda_.Function(
            self,
            "KBCreatorLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="create_kb_s3vectors.on_event",
            code=lambda_.Code.from_asset("src/infrastructure"),
            timeout=cdk.Duration.minutes(5),
        )

        kb_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:CreateKnowledgeBase",
                    "bedrock:DeleteKnowledgeBase",
                    "bedrock:CreateDataSource",
                    "bedrock:DeleteDataSource",
                    "s3vectors:*",
                    "iam:PassRole",
                ],
                resources=["*"],
            )
        )

        # Custom Resource
        kb = cdk.CustomResource(
            self,
            "KnowledgeBase",
            service_token=kb_lambda.function_arn,
            properties={
                "KnowledgeBaseName": "dpw-project-management-kb",
                "RoleArn": self.kb_role.role_arn,
                "DataBucketArn": data_bucket.bucket_arn,
            },
        )

        self.kb_id = kb.get_att_string("KnowledgeBaseId")
