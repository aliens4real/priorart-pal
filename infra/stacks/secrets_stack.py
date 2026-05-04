"""Secrets Manager entries for the AI provider API keys.

Pattern note: We create the secret resources empty here. The actual key
values get filled in via the AWS console or CLI AFTER deploy — never in
code, never in git. App Runner reads them at runtime via IAM permissions
granted in the AppRunnerStack.
"""
from __future__ import annotations

from aws_cdk import Stack
from aws_cdk import aws_secretsmanager as sm
from constructs import Construct


class SecretsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.voyage_key = sm.Secret(
            self,
            "VoyageKey",
            secret_name=f"{project}/voyage-api-key",
            description="Voyage AI API key for embeddings",
        )
        self.cohere_key = sm.Secret(
            self,
            "CohereKey",
            secret_name=f"{project}/cohere-api-key",
            description="Cohere API key for reranking",
        )
        self.anthropic_key = sm.Secret(
            self,
            "AnthropicKey",
            secret_name=f"{project}/anthropic-api-key",
            description="Anthropic API key for generation",
        )
