import json

import aws_cdk as cdk
import yaml
from aws_cdk import (
    CustomResource,
    Duration,
    Stack,
)
from aws_cdk import (
    aws_apigateway as apigateway,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_ssm as ssm,
)
from aws_cdk import (
    custom_resources as cr,
)
from constructs import Construct


class ProjectManagementStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load configuration
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        print(f"Loaded config models: {config.get('models', {})}")

        # Create SSM parameters for prompts and templates
        self.create_ssm_parameters(config)

        # S3 Bucket for project management data
        bucket = s3.Bucket(
            self,
            "ProjectManagementBucket",
            bucket_name="dpw-project-management",
            removal_policy=cdk.RemovalPolicy.DESTROY,  # TODO Change to RETAIN
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

        # DynamoDB table for vector ingestion cache
        ingestion_cache_table = dynamodb.Table(
            self,
            "VectorIngestionCache",
            table_name="vector-ingestion-cache",
            partition_key=dynamodb.Attribute(
                name="file_key", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # S3 Vectors Knowledge Base Components
        vector_bucket_name = "dpw-project-mgmt-vectors"
        index_name = "project-mgmt-index"

        # Docs bucket for knowledge base data source
        docs_bucket = s3.Bucket(
            self,
            "DocsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # Lambda to create S3 Vector bucket + index
        s3vectors_fn = _lambda.Function(
            self,
            "S3VectorsCreator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="create_bucket.on_event",
            code=_lambda.Code.from_asset(
                "./src/search",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install boto3==1.39.10 urllib3 -t /asset-output && cp -au . /asset-output",
                    ],
                ),
            ),
            timeout=Duration.minutes(5),
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # IAM for S3 Vectors API (mock implementation)
        s3vectors_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3vectors:CreateVectorBucket",
                    "s3vectors:GetVectorBucket",
                    "s3vectors:DeleteVectorBucket",
                    "s3vectors:CreateIndex",
                    "s3vectors:GetIndex",
                    "s3vectors:DeleteIndex",
                    "s3vectors:ListIndexes",
                ],
                resources=["*"],
            )
        )

        # Custom resource to return bucket/index ARNs
        s3vectors_provider = cr.Provider(
            self, "S3VectorsProvider", on_event_handler=s3vectors_fn
        )
        s3vectors_cr = CustomResource(
            self,
            "S3VectorsResource",
            service_token=s3vectors_provider.service_token,
            properties={
                "VectorBucketName": vector_bucket_name,
                "IndexName": index_name,
                "DistanceMetric": "cosine",
                "DataType": "float32",
                "Dimension": 1024,
            },
        )

        vector_bucket_arn = s3vectors_cr.get_att_string("VectorBucketArn")
        index_arn = s3vectors_cr.get_att_string("IndexArn")

        # Bucket Setup Lambda
        setup_lambda = _lambda.Function(
            self,
            "BucketSetupLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="bucket_setup.handler",
            code=_lambda.Code.from_asset("./src/setup"),
            environment={"BUCKET_NAME": bucket.bucket_name},
        )
        bucket.grant_read_write(setup_lambda)

        # Project Setup Lambda
        # Batch Processing Infrastructure
        from aws_cdk import aws_sqs as sqs

        # DynamoDB table for project management data
        project_data_table = dynamodb.Table(
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

        # SQS queue for sequential file processing
        batch_queue = sqs.Queue(
            self,
            "BatchProcessingQueue",
            queue_name="batch-file-processing",
            visibility_timeout=Duration.minutes(15),
        )

        # Create Lambda layer for shared meeting_data dependency
        meeting_data_layer = _lambda.LayerVersion(
            self,
            "MeetingDataLayer",
            code=_lambda.Code.from_asset("layers/meeting_data"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Shared meeting_data module",
        )

        # Project Setup Wizard Lambda
        wizard_lambda = _lambda.Function(
            self,
            "ProjectSetupWizardLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="project_setup_wizard.handler",
            code=_lambda.Code.from_asset("./src/wizard"),
            timeout=cdk.Duration.minutes(5),
            layers=[meeting_data_layer],
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "PROJECT_SETUP_MODEL_ID": config["models"]["primary_llm"],
                "TASK_GENERATION_MODEL_ID": config["models"]["primary_llm"],
                "PROJECT_DATA_TABLE_NAME": project_data_table.table_name,
            },
        )
        bucket.grant_read_write(wizard_lambda)
        project_data_table.grant_read_write_data(wizard_lambda)
        wizard_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"], resources=["*"]
            )
        )

        # AI Assistant Lambda
        # Create Lambda Layer for common utilities
        common_layer = _lambda.LayerVersion(
            self,
            "CommonUtilitiesLayer",
            code=_lambda.Code.from_asset("./src/common"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Common utilities including vector_helper",
        )

        # Lessons Learned Lambda
        lessons_lambda = _lambda.Function(
            self,
            "LessonsLearnedLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lessons_api.handler",
            code=_lambda.Code.from_asset("./src/lessons"),
            timeout=cdk.Duration.seconds(300),  # 5 min for sync processing
            layers=[common_layer],
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "LESSONS_EXTRACTOR_MODEL_ID": config["models"][
                    "lessons_extractor"
                ],
                "CONFLICT_DETECTOR_MODEL_ID": config["models"][
                    "conflict_detector"
                ],
                "PROJECT_DATA_TABLE_NAME": project_data_table.table_name,
            },
        )
        bucket.grant_read_write(lessons_lambda)
        project_data_table.grant_read_data(lessons_lambda)
        lessons_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"], resources=["*"]
            )
        )

        # Async Lessons Processor Lambda
        async_lessons_processor = _lambda.Function(
            self,
            "AsyncLessonsProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="async_lessons_processor.handler",
            code=_lambda.Code.from_asset("./src/lessons"),
            timeout=cdk.Duration.minutes(5),  # Longer timeout for processing
            layers=[common_layer],
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "LESSONS_EXTRACTOR_MODEL_ID": config["models"][
                    "lessons_extractor"
                ],
                "CONFLICT_DETECTOR_MODEL_ID": config["models"][
                    "conflict_detector"
                ],
                "VECTOR_BUCKET_NAME": vector_bucket_name,
                "INDEX_NAME": index_name,
                "EMBEDDING_MODEL_ID": config["models"]["embeddings"],
            },
        )
        bucket.grant_read_write(async_lessons_processor)
        async_lessons_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"], resources=["*"]
            )
        )
        async_lessons_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3vectors:PutVectors",
                    "s3vectors:DeleteVectors",
                    "s3vectors:QueryVectors",
                    "s3vectors:ListVectors",
                    "s3vectors:GetVectors",
                    "s3vectors:GetIndex",
                    "s3vectors:GetVectorBucket",
                ],
                resources=["*"],
            )
        )

        # Add async processor name to lessons lambda environment
        lessons_lambda.add_environment(
            "ASYNC_LESSONS_PROCESSOR_NAME",
            async_lessons_processor.function_name,
        )
        lessons_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[async_lessons_processor.function_arn],
            )
        )

        # Checklist Lambda
        checklist_lambda = _lambda.Function(
            self,
            "ChecklistLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="checklist_api.handler",
            code=_lambda.Code.from_asset("./src/checklist"),
            timeout=cdk.Duration.seconds(30),
            environment={
                "PROJECT_DATA_TABLE_NAME": project_data_table.table_name,
            },
        )
        project_data_table.grant_read_write_data(checklist_lambda)

        # Task Manager Lambda
        task_lambda = _lambda.Function(
            self,
            "TaskManagerLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="task_manager.handler",
            code=_lambda.Code.from_asset("./src/tasks"),
            timeout=cdk.Duration.seconds(30),
            layers=[meeting_data_layer],
            environment={
                "PROJECT_DATA_TABLE_NAME": project_data_table.table_name,
            },
        )
        project_data_table.grant_read_write_data(task_lambda)

        # Vector Ingestion Lambda
        vector_ingestion_lambda = _lambda.Function(
            self,
            "VectorIngestionLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="vector_ingestion.handler",
            code=_lambda.Code.from_asset("./src/ingestion"),
            timeout=cdk.Duration.minutes(5),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "EMBEDDING_MODEL_ID": config["models"]["embeddings"],
            },
        )
        bucket.grant_read_write(vector_ingestion_lambda)
        ingestion_cache_table.grant_read_write_data(vector_ingestion_lambda)
        vector_ingestion_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"], resources=["*"]
            )
        )
        vector_ingestion_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3vectors:PutVectors",
                    "s3vectors:GetIndex",
                    "s3vectors:GetVectorBucket",
                ],
                resources=["*"],
            )
        )
        vector_ingestion_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/project-management/vector-ingestion/*"
                ],
            )
        )

        # Add vector ingestion lambda to wizard lambda environment
        wizard_lambda.add_environment(
            "VECTOR_INGESTION_LAMBDA_NAME",
            vector_ingestion_lambda.function_name,
        )
        wizard_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[vector_ingestion_lambda.function_arn],
            )
        )

        # Add vector ingestion lambda to async lessons processor
        async_lessons_processor.add_environment(
            "VECTOR_INGESTION_LAMBDA_NAME",
            vector_ingestion_lambda.function_name,
        )
        async_lessons_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[vector_ingestion_lambda.function_arn],
            )
        )

        # Create SSM parameter for available search models
        available_models = config["models"]["available_search_models"]
        ssm.StringParameter(
            self,
            "AvailableSearchModels",
            parameter_name="/project-management/available-search-models",
            string_value=json.dumps(available_models),
            description="Available search models for frontend dropdown",
        )

        # Dashboard Lambda (simplified)
        dashboard_lambda = _lambda.Function(
            self,
            "DashboardLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="dashboard_api.handler",
            code=_lambda.Code.from_asset("./src/dashboard"),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
            },
        )
        bucket.grant_read(dashboard_lambda)
        dashboard_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=["*"],
            )
        )

        # Projects API Lambda
        projects_lambda = _lambda.Function(
            self,
            "ProjectsLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="projects_api.handler",
            code=_lambda.Code.from_asset("./src/projects"),
            layers=[meeting_data_layer],
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "PROJECT_WIZARD_LAMBDA_NAME": wizard_lambda.function_name,
                "VECTOR_BUCKET_NAME": vector_bucket_name,
                "INDEX_NAME": index_name,
                "PROJECT_DATA_TABLE_NAME": project_data_table.table_name,
            },
        )
        bucket.grant_read_write(projects_lambda)
        project_data_table.grant_read_write_data(projects_lambda)
        projects_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[wizard_lambda.function_arn],
            )
        )
        # Grant S3 Vectors permissions
        projects_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3vectors:ListVectors",
                    "s3vectors:DeleteVectors",
                    "s3vectors:GetIndex",
                    "s3vectors:GetVectorBucket",
                ],
                resources=["*"],
            )
        )

        # Files API Lambda
        files_lambda = _lambda.Function(
            self,
            "FilesLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="files_api.handler",
            code=_lambda.Code.from_asset("./src/files"),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
            },
        )
        bucket.grant_read_write(files_lambda)

        # Knowledge Base Search Lambda
        search_lambda = _lambda.Function(
            self,
            "SearchLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="search.handler",
            code=_lambda.Code.from_asset(
                "./src/search",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install boto3==1.39.10 urllib3 -t /asset-output && cp -au . /asset-output",
                    ],
                ),
            ),
            timeout=cdk.Duration.minutes(1),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "DOCS_BUCKET_NAME": docs_bucket.bucket_name,
                "VECTOR_BUCKET_NAME": vector_bucket_name,
                "INDEX_NAME": index_name,
                "VECTOR_BUCKET_ARN": f"arn:aws:s3vectors:{self.region}:{self.account}:bucket/{vector_bucket_name}",
                "INDEX_ARN": f"arn:aws:s3vectors:{self.region}:{self.account}:bucket/{vector_bucket_name}/index/{index_name}",
                "EMBEDDING_MODEL_ID": config["models"]["embeddings"],
                "BEDROCK_MODEL_ID": config["models"]["primary_llm"],
            },
        )
        bucket.grant_read_write(search_lambda)
        docs_bucket.grant_read_write(search_lambda)
        search_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"], resources=["*"]
            )
        )
        search_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3vectors:QueryVectors",
                    "s3vectors:GetVectors",
                    "s3vectors:GetIndex",
                    "s3vectors:GetVectorBucket",
                ],
                resources=["*"],
            )
        )
        search_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/project-management/rag-search/*"
                ],
            )
        )

        # API Gateway
        # API Gateway with API Key authentication
        api = apigateway.RestApi(
            self,
            "DashboardApi",
            rest_api_name="Project Management Dashboard API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "x-api-key",
                    "X-Amz-Security-Token",
                ],
                allow_credentials=False,
            ),
        )

        # Create API Key
        api_key = api.add_api_key(
            "ProjectKnowledgeApiKey", api_key_name="project-knowledge-key"
        )

        # Create Usage Plan
        usage_plan = api.add_usage_plan(
            "ProjectKnowledgeUsagePlan",
            name="project-knowledge-usage-plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100, burst_limit=200
            ),
            quota=apigateway.QuotaSettings(
                limit=10000, period=apigateway.Period.DAY
            ),
        )

        # Associate Usage Plan with API Stage
        usage_plan.add_api_stage(stage=api.deployment_stage)

        # Associate API Key with Usage Plan
        usage_plan.add_api_key(api_key)

        # Output API Key
        cdk.CfnOutput(
            self,
            "ApiKeyId",
            value=api_key.key_id,
            description="API Key ID for Project Knowledge System",
        )

        # Projects endpoints
        projects_resource = api.root.add_resource("projects")
        projects_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(projects_lambda),
            api_key_required=True,
        )

        # Config endpoints
        config_resource = api.root.add_resource("config")
        project_types_resource = config_resource.add_resource("project-types")
        project_types_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(projects_lambda),
            api_key_required=True,
        )

        # Project detail routes
        project_detail_resource = projects_resource.add_resource(
            "{project_name}"
        )
        project_detail_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(projects_lambda),
            api_key_required=True,
        )
        project_detail_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(projects_lambda),
            api_key_required=True,
        )

        # Project setup wizard endpoint
        wizard_resource = api.root.add_resource("setup-wizard")
        wizard_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(wizard_lambda),
            api_key_required=True,
        )

        # Task management endpoints
        tasks_resource = project_detail_resource.add_resource("tasks")
        tasks_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(task_lambda),
            api_key_required=True,
        )
        tasks_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(task_lambda),
            api_key_required=True,
        )

        task_detail_resource = tasks_resource.add_resource("{task_id}")
        task_detail_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(task_lambda),
            api_key_required=True,
        )

        # Create project endpoint (legacy, now uses wizard)
        create_project_resource = api.root.add_resource("create-project")
        create_project_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(wizard_lambda),
            api_key_required=True,
        )

        # Update progress endpoint
        update_progress_resource = api.root.add_resource("update-progress")
        update_progress_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(projects_lambda),
            api_key_required=True,
        )

        # Lessons learned endpoints
        lessons_resource = project_detail_resource.add_resource(
            "lessons-learned"
        )
        lessons_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(lessons_lambda),
            api_key_required=True,
        )

        # Master lessons learned endpoints
        lessons_master_lambda = _lambda.Function(
            self,
            "LessonsMasterLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lessons_master_api.handler",
            code=_lambda.Code.from_asset("src/lessons"),
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "PROJECT_DATA_TABLE_NAME": project_data_table.table_name,
            },
            timeout=Duration.seconds(30),
        )

        bucket.grant_read_write(lessons_master_lambda)
        project_data_table.grant_read_write_data(lessons_master_lambda)

        lessons_master_resource = api.root.add_resource("lessons")

        # GET /lessons/project-types
        project_types_resource = lessons_master_resource.add_resource(
            "project-types"
        )
        project_types_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(lessons_master_lambda),
            api_key_required=True,
        )

        # GET /lessons/by-type/{project_type}
        by_type_resource = lessons_master_resource.add_resource("by-type")
        by_type_detail_resource = by_type_resource.add_resource(
            "{project_type}"
        )
        by_type_detail_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(lessons_master_lambda),
            api_key_required=True,
        )

        # PUT /lessons/{lesson_id}
        lesson_detail_resource = lessons_master_resource.add_resource(
            "{lesson_id}"
        )
        lesson_detail_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(lessons_master_lambda),
            api_key_required=True,
        )

        # GET /lessons/conflicts/by-type/{project_type}
        conflicts_master_resource = lessons_master_resource.add_resource("conflicts")
        conflicts_by_type_resource = conflicts_master_resource.add_resource("by-type")
        conflicts_type_resource = conflicts_by_type_resource.add_resource("{project_type}")
        conflicts_type_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(lessons_master_lambda),
            api_key_required=True,
        )

        # POST /lessons/conflicts/resolve/{conflict_id}
        conflict_resolve_base = conflicts_master_resource.add_resource("resolve")
        conflict_resolve_resource = conflict_resolve_base.add_resource("{conflict_id}")
        conflict_resolve_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(lessons_master_lambda),
            api_key_required=True,
        )

        documents_resource = project_detail_resource.add_resource("documents")
        documents_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(lessons_lambda),
            api_key_required=True,
        )

        # Conflicts endpoints
        conflicts_resource = project_detail_resource.add_resource("conflicts")
        conflicts_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(lessons_lambda),
            api_key_required=True,
        )

        conflicts_resolve_resource = conflicts_resource.add_resource("resolve")
        conflicts_resolve_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(lessons_lambda),
            api_key_required=True,
        )

        # Checklist endpoints
        checklist_resource = project_detail_resource.add_resource("checklist")
        checklist_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(checklist_lambda),
            api_key_required=True,
        )
        checklist_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(checklist_lambda),
            api_key_required=True,
        )

        # Metadata endpoint
        metadata_resource = project_detail_resource.add_resource("metadata")
        metadata_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(checklist_lambda),
            api_key_required=True,
        )

        file_resource = api.root.add_resource("file")
        file_proxy = file_resource.add_proxy(
            default_integration=apigateway.LambdaIntegration(files_lambda),
            any_method=True,
        )

        # Available models endpoint (keep with dashboard)
        models_resource = api.root.add_resource("models")
        models_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(dashboard_lambda),
            api_key_required=True,
        )

        # Knowledge Base search endpoints
        search_resource = api.root.add_resource("search")
        search_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(search_lambda),
            api_key_required=True,
        )

        project_search_resource = api.root.add_resource("project-search")
        project_search_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(search_lambda),
            api_key_required=True,
        )

        # RAG search endpoint
        rag_search_resource = api.root.add_resource("search-rag")
        rag_search_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                search_lambda,
                proxy=True,
            ),
            api_key_required=True,
        )

        # Custom Resource for bucket setup
        cr.AwsCustomResource(
            self,
            "BucketSetupCustomResource",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": setup_lambda.function_name,
                    "Payload": json.dumps(
                        {
                            "RequestType": "Create",
                            "ResourceProperties": {
                                "BucketName": bucket.bucket_name
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
                        resources=[setup_lambda.function_arn],
                    )
                ]
            ),
        )

    def create_ssm_parameters(self, config):
        """Create SSM parameters for prompts and templates"""
        # Create parameters for RAG search configuration
        ssm.StringParameter(
            self,
            "RagSearchPrompt",
            parameter_name="/project-management/rag-search/prompt",
            string_value="""You are an AI assistant helping Public Works engineers with project management questions.

Use the following context to answer the user's question. Focus on providing actionable guidance.

Context:
{context}

Question: {question}

Answer:""",
            description="RAG search prompt template for project management",
        )

        ssm.StringParameter(
            self,
            "RagSearchModelId",
            parameter_name="/project-management/rag-search/model-id",
            string_value="anthropic.claude-3-sonnet-20240229-v1:0",
            description="Model ID for RAG search",
        )

        # Create parameters for vector ingestion configuration
        vector_config = config.get("vector_ingestion", {})
        ssm.StringParameter(
            self,
            "VectorChunkSizeTokens",
            parameter_name="/project-management/vector-ingestion/chunk-size-tokens",
            string_value=str(vector_config.get("chunk_size_tokens", 512)),
            description="Chunk size in tokens for vector ingestion",
        )

        ssm.StringParameter(
            self,
            "VectorOverlapTokens",
            parameter_name="/project-management/vector-ingestion/overlap-tokens",
            string_value=str(vector_config.get("overlap_tokens", 64)),
            description="Overlap tokens for vector ingestion",
        )

        ssm.StringParameter(
            self,
            "VectorBucketName",
            parameter_name="/project-management/vector-ingestion/vector-bucket-name",
            string_value=vector_config.get(
                "vector_bucket_name", "dpw-project-mgmt-vectors"
            ),
            description="S3 vectors bucket name",
        )

        ssm.StringParameter(
            self,
            "VectorIndexName",
            parameter_name="/project-management/vector-ingestion/index-name",
            string_value=vector_config.get("index_name", "project-mgmt-index"),
            description="S3 vectors index name",
        )

        # Available search models parameter
        available_models = config.get("models", {}).get(
            "available_search_models", []
        )
        ssm.StringParameter(
            self,
            "AvailableModels",
            parameter_name="/project-management/available-models",
            string_value=json.dumps(
                {"available_search_models": available_models}
            ),
            description="Available AI models for search",
        )
