import json

from aws_cdk import aws_ssm as ssm
from constructs import Construct


class SSMParameters(Construct):
    def __init__(
        self, scope: Construct, construct_id: str, config: dict, kb_id: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Knowledge Base ID
        ssm.StringParameter(
            self,
            "KnowledgeBaseId",
            parameter_name="/project-management/knowledge-base-id",
            string_value=kb_id,
            description="Knowledge Base ID for vector search",
        )

        # RAG search prompt
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

        # RAG search model ID
        ssm.StringParameter(
            self,
            "RagSearchModelId",
            parameter_name="/project-management/rag-search/model-id",
            string_value="anthropic.claude-3-sonnet-20240229-v1:0",
            description="Model ID for RAG search",
        )

        # Available search models
        available_models = config.get("models", {}).get("available_search_models", [])
        ssm.StringParameter(
            self,
            "AvailableSearchModels",
            parameter_name="/project-management/available-search-models",
            string_value=json.dumps(available_models),
            description="Available search models for frontend dropdown",
        )

        ssm.StringParameter(
            self,
            "AvailableModels",
            parameter_name="/project-management/available-models",
            string_value=json.dumps({"available_search_models": available_models}),
            description="Available AI models for search",
        )
