import json

import aws_cdk as cdk
import yaml
from aws_cdk import Stack, aws_iam as iam, custom_resources as cr
from constructs import Construct

from infrastructure.api import APIGateway
from infrastructure.compute import ComputeResources
from infrastructure.iam import IAMPermissions
from infrastructure.knowledge_base import KnowledgeBaseResources
from infrastructure.parameters import SSMParameters
from infrastructure.storage import StorageResources


class ProjectManagementStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load configuration
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        print(f"Loaded config models: {config.get('models', {})}")

        # Create modular resources
        storage = StorageResources(self, "Storage")
        kb = KnowledgeBaseResources(self, "KnowledgeBase", storage.docs_bucket)
        compute = ComputeResources(self, "Compute", config, storage, kb.kb_id)
        IAMPermissions(self, "IAM", compute, storage, kb.kb_id)
        SSMParameters(self, "Parameters", config, kb.kb_id)
        APIGateway(self, "API", compute)

        # Output Knowledge Base ID
        cdk.CfnOutput(self, "KnowledgeBaseId", value=kb.kb_id)

        # Custom resource for bucket setup
        cr.AwsCustomResource(
            self,
            "BucketSetupCustomResource",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": compute.setup_lambda.function_name,
                    "Payload": json.dumps(
                        {
                            "RequestType": "Create",
                            "ResourceProperties": {"BucketName": storage.bucket.bucket_name},
                        }
                    ),
                },
                physical_resource_id=cr.PhysicalResourceId.of("bucket-setup"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"],
                        resources=[compute.setup_lambda.function_arn],
                    )
                ]
            ),
        )
