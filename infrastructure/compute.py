import aws_cdk as cdk
from aws_cdk import Duration, aws_lambda as _lambda
from constructs import Construct


class ComputeResources(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        storage,
        kb_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda layers
        self.meeting_data_layer = _lambda.LayerVersion(
            self,
            "MeetingDataLayer",
            code=_lambda.Code.from_asset("layers/meeting_data"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Shared meeting_data module",
        )

        self.common_layer = _lambda.LayerVersion(
            self,
            "CommonUtilitiesLayer",
            code=_lambda.Code.from_asset("./src/common"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Common utilities including vector_helper",
        )

        # Bucket setup Lambda
        self.setup_lambda = _lambda.Function(
            self,
            "BucketSetupLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="bucket_setup.handler",
            code=_lambda.Code.from_asset("./src/setup"),
            timeout=Duration.seconds(30),
            environment={"BUCKET_NAME": storage.bucket.bucket_name},
        )

        # Project setup wizard Lambda
        self.wizard_lambda = _lambda.Function(
            self,
            "ProjectSetupWizardLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="project_setup_wizard.handler",
            code=_lambda.Code.from_asset("./src/wizard"),
            timeout=Duration.minutes(5),
            layers=[self.meeting_data_layer],
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
                "PROJECT_SETUP_MODEL_ID": config["models"]["primary_llm"],
                "TASK_GENERATION_MODEL_ID": config["models"]["primary_llm"],
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
            },
        )

        # Async lessons processor Lambda
        self.async_lessons_processor = _lambda.Function(
            self,
            "AsyncLessonsProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="async_lessons_processor.handler",
            code=_lambda.Code.from_asset("./src/lessons"),
            timeout=Duration.minutes(5),
            layers=[self.common_layer],
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
                "LESSONS_EXTRACTOR_MODEL_ID": config["models"]["lessons_extractor"],
                "CONFLICT_DETECTOR_MODEL_ID": config["models"]["conflict_detector"],
                "KB_ID": kb_id,
            },
        )

        # Lessons learned Lambda
        self.lessons_lambda = _lambda.Function(
            self,
            "LessonsLearnedLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lessons_api.handler",
            code=_lambda.Code.from_asset("./src/lessons"),
            timeout=Duration.seconds(300),
            layers=[self.common_layer],
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
                "LESSONS_EXTRACTOR_MODEL_ID": config["models"]["lessons_extractor"],
                "CONFLICT_DETECTOR_MODEL_ID": config["models"]["conflict_detector"],
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
                "ASYNC_LESSONS_PROCESSOR_NAME": self.async_lessons_processor.function_name,
                "KB_ID": kb_id,
            },
        )

        # Lessons master Lambda
        self.lessons_master_lambda = _lambda.Function(
            self,
            "LessonsMasterLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lessons_master_api.handler",
            code=_lambda.Code.from_asset("src/lessons"),
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
            },
            timeout=Duration.seconds(30),
        )

        # Checklist Lambda
        self.checklist_lambda = _lambda.Function(
            self,
            "ChecklistLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="checklist_api.handler",
            code=_lambda.Code.from_asset("./src/checklist"),
            timeout=Duration.seconds(30),
            environment={
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
            },
        )

        # Global checklist Lambda
        self.global_checklist_lambda = _lambda.Function(
            self,
            "GlobalChecklistLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="global_checklist_manager.handler",
            code=_lambda.Code.from_asset("./src/checklist"),
            timeout=Duration.seconds(60),
            environment={
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
            },
        )

        # Task manager Lambda
        self.task_lambda = _lambda.Function(
            self,
            "TaskManagerLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="task_manager.handler",
            code=_lambda.Code.from_asset("./src/tasks"),
            timeout=Duration.seconds(30),
            layers=[self.meeting_data_layer],
            environment={
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
            },
        )

        # Dashboard Lambda
        self.dashboard_lambda = _lambda.Function(
            self,
            "DashboardLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="dashboard_api.handler",
            code=_lambda.Code.from_asset("./src/dashboard"),
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
            },
        )

        # Projects Lambda
        self.projects_lambda = _lambda.Function(
            self,
            "ProjectsLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="projects_api.handler",
            code=_lambda.Code.from_asset("./src/projects"),
            layers=[self.meeting_data_layer],
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
                "PROJECT_WIZARD_LAMBDA_NAME": self.wizard_lambda.function_name,
                "PROJECT_DATA_TABLE_NAME": storage.project_data_table.table_name,
            },
        )

        # Files Lambda
        self.files_lambda = _lambda.Function(
            self,
            "FilesLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="files_api.handler",
            code=_lambda.Code.from_asset("./src/files"),
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
            },
        )

        # Search Lambda
        self.search_lambda = _lambda.Function(
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
            timeout=Duration.minutes(1),
            environment={
                "BUCKET_NAME": storage.bucket.bucket_name,
                "KB_ID": kb_id,
                "BEDROCK_MODEL_ID": config["models"]["primary_llm"],
            },
        )
