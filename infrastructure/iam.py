import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from constructs import Construct


class IAMPermissions(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        compute,
        storage,
        kb_id,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Bucket setup Lambda permissions
        storage.bucket.grant_read_write(compute.setup_lambda)

        # Wizard Lambda permissions
        storage.bucket.grant_read_write(compute.wizard_lambda)
        storage.project_data_table.grant_read_write_data(compute.wizard_lambda)
        compute.wizard_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"])
        )

        # Async lessons processor permissions
        storage.bucket.grant_read_write(compute.async_lessons_processor)
        compute.async_lessons_processor.add_to_role_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"])
        )
        compute.async_lessons_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
                resources=[
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:knowledge-base/{kb_id}"
                ],
            )
        )

        # Lessons Lambda permissions
        storage.bucket.grant_read_write(compute.lessons_lambda)
        storage.project_data_table.grant_read_data(compute.lessons_lambda)
        compute.lessons_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"])
        )
        compute.lessons_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:Retrieve"],
                resources=[
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:knowledge-base/{kb_id}"
                ],
            )
        )
        compute.lessons_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[compute.async_lessons_processor.function_arn],
            )
        )

        # Lessons master Lambda permissions
        storage.bucket.grant_read_write(compute.lessons_master_lambda)
        storage.project_data_table.grant_read_write_data(compute.lessons_master_lambda)

        # Checklist Lambda permissions
        storage.project_data_table.grant_read_write_data(compute.checklist_lambda)

        # Global checklist Lambda permissions
        storage.project_data_table.grant_read_write_data(
            compute.global_checklist_lambda
        )

        # Task Lambda permissions
        storage.project_data_table.grant_read_write_data(compute.task_lambda)

        # Dashboard Lambda permissions
        storage.bucket.grant_read(compute.dashboard_lambda)
        compute.dashboard_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=["*"],
            )
        )

        # Projects Lambda permissions
        storage.bucket.grant_read_write(compute.projects_lambda)
        storage.project_data_table.grant_read_write_data(compute.projects_lambda)
        compute.projects_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    compute.wizard_lambda.function_arn,
                    compute.async_lessons_processor.function_arn,
                ],
            )
        )

        # Files Lambda permissions
        storage.bucket.grant_read_write(compute.files_lambda)

        # Search Lambda permissions
        storage.bucket.grant_read_write(compute.search_lambda)
        compute.search_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"])
        )
        compute.search_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
                resources=[
                    "arn:aws:bedrock:*:*:knowledge-base/*"
                ],  # #TODO: Restrict to specific knowledge bases if needed
            )
        )
        compute.search_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:GetInferenceProfile"],
                resources=["*"],
            )
        )

        # Transformation Lambda permissions
        storage.bucket.grant_read_write(compute.transformation_lambda)

        # Allow Bedrock to invoke transformation lambda
        compute.transformation_lambda.add_permission(
            "BedrockInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        # Lessons sync Lambda permissions
        storage.bucket.grant_read_write(compute.lessons_sync_lambda)
        storage.project_data_table.grant_read_data(compute.lessons_sync_lambda)

        # Manual sync Lambda permissions
        compute.manual_sync_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:StartIngestionJob",
                    "bedrock:GetDataSource",
                    "bedrock:ListDataSources",
                    "bedrock:ListIngestionJobs",
                ],
                resources=[
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:knowledge-base/{kb_id}"
                ],
            )
        )
