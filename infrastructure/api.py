from aws_cdk import aws_apigateway as apigateway
from constructs import Construct


class APIGateway(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        compute,
        auth,
        frontend_url: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api_config = config.get("api_gateway", {})
        throttle_config = api_config.get("throttle", {})

        # API Gateway
        cors_origins = []
        if frontend_url:
            cors_origins.append(frontend_url)

        self.api = apigateway.RestApi(
            self,
            "api",
            rest_api_name="project-management-data",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=cors_origins,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                ],
                allow_credentials=True,
            ),
        )

        # Cognito Authorizer
        self.authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[auth.user_pool],
        )

        # Usage Plan (throttling only, no API key)
        usage_plan = self.api.add_usage_plan(
            "usage-plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=throttle_config.get("rate_limit", 100),
                burst_limit=throttle_config.get("burst_limit", 200),
            ),
        )

        usage_plan.add_api_stage(stage=self.api.deployment_stage)

        # Projects endpoints
        projects = self.api.root.add_resource("projects")
        projects.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.projects_lambda, proxy=True),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        project_detail = projects.add_resource("{project_name}")
        project_detail.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.projects_lambda, proxy=True),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        project_detail.add_method(
            "DELETE",
            apigateway.LambdaIntegration(compute.projects_lambda, proxy=True),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Config endpoints
        config = self.api.root.add_resource("config")
        project_types = config.add_resource("project-types")
        project_types.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.projects_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Setup wizard
        wizard = self.api.root.add_resource("setup-wizard")
        wizard.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.wizard_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Legacy create project
        create_project = self.api.root.add_resource("create-project")
        create_project.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.wizard_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Update progress
        update_progress = self.api.root.add_resource("update-progress")
        update_progress.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.projects_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Tasks
        tasks = project_detail.add_resource("tasks")
        tasks.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.task_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        tasks.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.task_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        task_detail = tasks.add_resource("{task_id}")
        task_detail.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.task_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Lessons learned
        lessons = project_detail.add_resource("lessons-learned")
        lessons.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        conflicts = project_detail.add_resource("conflicts")
        conflicts.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        conflicts_resolve = conflicts.add_resource("resolve")
        conflicts_resolve.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.lessons_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Master lessons
        lessons_master = self.api.root.add_resource("lessons")

        project_types_lessons = lessons_master.add_resource("project-types")
        project_types_lessons.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        by_type = lessons_master.add_resource("by-type")
        by_type_detail = by_type.add_resource("{project_type}")
        by_type_detail.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        lesson_detail = lessons_master.add_resource("{lesson_id}")
        lesson_detail.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        conflicts_master = lessons_master.add_resource("conflicts")
        conflicts_by_type = conflicts_master.add_resource("by-type")
        conflicts_type = conflicts_by_type.add_resource("{project_type}")
        conflicts_type.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        conflict_resolve_base = conflicts_master.add_resource("resolve")
        conflict_resolve = conflict_resolve_base.add_resource("{conflict_id}")
        conflict_resolve.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Checklist
        checklist = project_detail.add_resource("checklist")
        checklist.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        checklist.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        checklist_task = checklist.add_resource("task")
        checklist_task.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        checklist_task.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        checklist_task.add_method(
            "DELETE",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        metadata = project_detail.add_resource("metadata")
        metadata.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Global checklist
        global_checklist = self.api.root.add_resource("global-checklist")
        global_checklist.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        global_checklist.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        global_sync = global_checklist.add_resource("sync")
        global_sync.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        global_init = global_checklist.add_resource("initialize")
        global_init.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Files
        file = self.api.root.add_resource("file")
        file_proxy = file.add_proxy(
            default_integration=apigateway.LambdaIntegration(
                compute.files_lambda
            ),
            any_method=False,
        )
        file_proxy.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.files_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Upload URL generation
        upload_url = self.api.root.add_resource("upload-url")
        upload_url.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.files_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Models
        models = self.api.root.add_resource("models")
        models.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.dashboard_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Search
        search = self.api.root.add_resource("search")
        search.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.search_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        project_search = self.api.root.add_resource("project-search")
        project_search.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.search_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        rag_search = self.api.root.add_resource("search-rag")
        rag_search.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.search_lambda, proxy=True),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Manual KB sync
        sync = self.api.root.add_resource("sync")
        sync_kb = sync.add_resource("knowledge-base")
        sync_kb.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.manual_sync_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        sync_kb_status = sync_kb.add_resource("status")
        sync_kb_status.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.manual_sync_lambda),
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
