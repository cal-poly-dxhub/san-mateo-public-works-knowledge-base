import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigateway
from constructs import Construct


class APIGateway(Construct):
    def __init__(self, scope: Construct, construct_id: str, config: dict, compute, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api_config = config.get("api_gateway", {})
        throttle_config = api_config.get("throttle", {})
        quota_config = api_config.get("quota", {})

        # API Gateway
        self.api = apigateway.RestApi(
            self,
            "api",
            rest_api_name="project-management-data",
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

        # API Key
        api_key = self.api.add_api_key(
            "api-key"
        )

        # Usage Plan
        usage_plan = self.api.add_usage_plan(
            "usage-plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=throttle_config.get("rate_limit", 100),
                burst_limit=throttle_config.get("burst_limit", 200)
            ),
            quota=apigateway.QuotaSettings(
                limit=quota_config.get("limit", 10000),
                period=getattr(apigateway.Period, quota_config.get("period", "DAY"))
            ),
        )

        usage_plan.add_api_stage(stage=self.api.deployment_stage)
        usage_plan.add_api_key(api_key)

        cdk.CfnOutput(
            scope,
            "ApiKeyId",
            value=api_key.key_id,
            description="API Key ID for Project Knowledge System",
        )

        # Projects endpoints
        projects = self.api.root.add_resource("projects")
        projects.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.projects_lambda),
            api_key_required=True,
        )

        project_detail = projects.add_resource("{project_name}")
        project_detail.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.projects_lambda),
            api_key_required=True,
        )
        project_detail.add_method(
            "DELETE",
            apigateway.LambdaIntegration(compute.projects_lambda),
            api_key_required=True,
        )

        # Config endpoints
        config = self.api.root.add_resource("config")
        project_types = config.add_resource("project-types")
        project_types.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.projects_lambda),
            api_key_required=True,
        )

        # Setup wizard
        wizard = self.api.root.add_resource("setup-wizard")
        wizard.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.wizard_lambda),
            api_key_required=True,
        )

        # Legacy create project
        create_project = self.api.root.add_resource("create-project")
        create_project.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.wizard_lambda),
            api_key_required=True,
        )

        # Update progress
        update_progress = self.api.root.add_resource("update-progress")
        update_progress.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.projects_lambda),
            api_key_required=True,
        )

        # Tasks
        tasks = project_detail.add_resource("tasks")
        tasks.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.task_lambda),
            api_key_required=True,
        )
        tasks.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.task_lambda),
            api_key_required=True,
        )

        task_detail = tasks.add_resource("{task_id}")
        task_detail.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.task_lambda),
            api_key_required=True,
        )

        # Lessons learned
        lessons = project_detail.add_resource("lessons-learned")
        lessons.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_lambda),
            api_key_required=True,
        )

        documents = project_detail.add_resource("documents")
        documents.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.projects_lambda),
            api_key_required=True,
        )

        conflicts = project_detail.add_resource("conflicts")
        conflicts.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_lambda),
            api_key_required=True,
        )

        conflicts_resolve = conflicts.add_resource("resolve")
        conflicts_resolve.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.lessons_lambda),
            api_key_required=True,
        )

        # Master lessons
        lessons_master = self.api.root.add_resource("lessons")

        project_types_lessons = lessons_master.add_resource("project-types")
        project_types_lessons.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            api_key_required=True,
        )

        by_type = lessons_master.add_resource("by-type")
        by_type_detail = by_type.add_resource("{project_type}")
        by_type_detail.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            api_key_required=True,
        )

        lesson_detail = lessons_master.add_resource("{lesson_id}")
        lesson_detail.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            api_key_required=True,
        )

        conflicts_master = lessons_master.add_resource("conflicts")
        conflicts_by_type = conflicts_master.add_resource("by-type")
        conflicts_type = conflicts_by_type.add_resource("{project_type}")
        conflicts_type.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            api_key_required=True,
        )

        conflict_resolve_base = conflicts_master.add_resource("resolve")
        conflict_resolve = conflict_resolve_base.add_resource("{conflict_id}")
        conflict_resolve.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.lessons_master_lambda),
            api_key_required=True,
        )

        # Checklist
        checklist = project_detail.add_resource("checklist")
        checklist.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            api_key_required=True,
        )
        checklist.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            api_key_required=True,
        )

        checklist_task = checklist.add_resource("task")
        checklist_task.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            api_key_required=True,
        )
        checklist_task.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            api_key_required=True,
        )
        checklist_task.add_method(
            "DELETE",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            api_key_required=True,
        )

        metadata = project_detail.add_resource("metadata")
        metadata.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.checklist_lambda),
            api_key_required=True,
        )

        # Global checklist
        global_checklist = self.api.root.add_resource("global-checklist")
        global_checklist.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            api_key_required=True,
        )
        global_checklist.add_method(
            "PUT",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            api_key_required=True,
        )

        global_sync = global_checklist.add_resource("sync")
        global_sync.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            api_key_required=True,
        )

        global_init = global_checklist.add_resource("initialize")
        global_init.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.global_checklist_lambda),
            api_key_required=True,
        )

        # Files
        file = self.api.root.add_resource("file")
        file_proxy = file.add_proxy(
            default_integration=apigateway.LambdaIntegration(compute.files_lambda),
            any_method=False,
        )
        file_proxy.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.files_lambda),
            api_key_required=True,
        )

        # Models
        models = self.api.root.add_resource("models")
        models.add_method(
            "GET",
            apigateway.LambdaIntegration(compute.dashboard_lambda),
            api_key_required=True,
        )

        # Search
        search = self.api.root.add_resource("search")
        search.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.search_lambda),
            api_key_required=True,
        )

        project_search = self.api.root.add_resource("project-search")
        project_search.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.search_lambda),
            api_key_required=True,
        )

        rag_search = self.api.root.add_resource("search-rag")
        rag_search.add_method(
            "POST",
            apigateway.LambdaIntegration(compute.search_lambda, proxy=True),
            api_key_required=True,
        )
