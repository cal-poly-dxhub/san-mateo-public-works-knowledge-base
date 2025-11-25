import json

import aws_cdk as cdk
import yaml
from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from constructs import Construct
from infrastructure.api import APIGateway
from infrastructure.auth import CognitoAuth
from infrastructure.compute import ComputeResources
from infrastructure.frontend import FrontendHosting
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
        kb = KnowledgeBaseResources(
            self, "KnowledgeBase", config, storage.bucket
        )
        compute = ComputeResources(self, "Compute", config, storage, kb.kb_id)
        IAMPermissions(self, "IAM", compute, storage, kb.kb_id)
        SSMParameters(self, "Parameters", config, kb.kb_id)
        auth = CognitoAuth(self, "Auth")
        frontend = FrontendHosting(
            self,
            "Frontend",
            api_url="",
            user_pool_id=auth.user_pool.user_pool_id,
            user_pool_client_id=auth.user_pool_client.user_pool_client_id,
            region=self.region,
        )
        api = APIGateway(
            self,
            "API",
            config,
            compute,
            auth,
            frontend_url=f"https://{frontend.url}",
        )

        # Update frontend with API URL
        frontend.service.task_definition.default_container.add_environment(
            "NEXT_PUBLIC_API_URL", api.api.url
        )

        # Add CORS origin to all Lambda functions
        frontend_origin = f"https://{frontend.url}"
        for lambda_func in [
            compute.projects_lambda,
            compute.wizard_lambda,
            compute.dashboard_lambda,
            compute.lessons_lambda,
            compute.lessons_master_lambda,
            compute.checklist_lambda,
            compute.global_checklist_lambda,
            compute.files_lambda,
            compute.search_lambda,
            compute.manual_sync_lambda,
        ]:
            lambda_func.add_environment("ALLOWED_ORIGIN", frontend_origin)

        # Configure S3 event trigger for lessons sync
        storage.add_lessons_sync_trigger(compute.lessons_sync_lambda)

        # Configure S3 event trigger for upload processing
        storage.add_upload_processor_trigger(compute.s3_upload_processor)

        # Output Knowledge Base ID
        cdk.CfnOutput(self, "KnowledgeBaseId", value=kb.kb_id)
        cdk.CfnOutput(self, "FrontendURL", value=f"https://{frontend.url}")
        cdk.CfnOutput(self, "ApiURL", value=api.api.url)
        cdk.CfnOutput(self, "UserPoolId", value=auth.user_pool.user_pool_id)
        cdk.CfnOutput(
            self,
            "UserPoolClientId",
            value=auth.user_pool_client.user_pool_client_id,
        )

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
                            "ResourceProperties": {
                                "BucketName": storage.bucket.bucket_name
                            },
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

        # Custom resource for global checklist initialization
        cr.AwsCustomResource(
            self,
            "GlobalChecklistInitCustomResource",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": compute.global_checklist_lambda.function_name,
                    "Payload": json.dumps(
                        {
                            "httpMethod": "POST",
                            "path": "/global-checklist/initialize",
                        }
                    ),
                },
                physical_resource_id=cr.PhysicalResourceId.of("global-checklist-init"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"],
                        resources=[compute.global_checklist_lambda.function_arn],
                    )
                ]
            ),
        )
