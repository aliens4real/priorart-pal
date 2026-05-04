"""AWS App Runner service for the FastAPI backend.

Pattern note: App Runner is "Fargate without the ECS YAML". You give it a
container image (we'll use ECR) and it gives you a public HTTPS URL with
auto-scaling. Two important pieces:

1. **VPC connector** — App Runner runs in AWS-managed networking by default.
   To reach RDS (which is in our VPC's isolated subnets), we attach a VPC
   connector that gives App Runner ENIs in our private-egress subnets.

2. **IAM** — App Runner needs two roles: an "instance role" (what the app
   process can do at runtime — e.g., read Secrets Manager) and an "access
   role" (what App Runner itself can do — pull images from ECR).

This stack is wired but not fully built — we'll add the actual container
image + ECR repo in Phase 2 once we have something to run.
"""
from __future__ import annotations

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from constructs import Construct


class AppRunnerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        vpc: ec2.IVpc,
        app_security_group: ec2.ISecurityGroup,
        secrets,
        database,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.repository = ecr.Repository(
            self,
            "ApiRepo",
            repository_name=f"{project}/api",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(max_image_count=10, description="Keep last 10")
            ],
        )

        # Roles wired but service is not created yet — App Runner construct
        # is L1 in CDK and noisy. We'll instantiate it in Phase 2 with a
        # real image URI.
        self.instance_role = iam.Role(
            self,
            "InstanceRole",
            assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
            description="Runtime permissions for FastAPI process",
        )
        for secret in (secrets.voyage_key, secrets.cohere_key, secrets.anthropic_key):
            secret.grant_read(self.instance_role)
        if database.db_credentials_secret is not None:
            database.db_credentials_secret.grant_read(self.instance_role)

        self.access_role = iam.Role(
            self,
            "AccessRole",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            description="App Runner pulls images from our ECR repo",
        )
        self.repository.grant_pull(self.access_role)

        # Placeholder outputs — will be real once service is created in Phase 2
        self.service_url = "https://placeholder-app-runner-url.invalid"
        self.service_arn = "arn:aws:apprunner:us-east-1:placeholder"

        CfnOutput(
            self,
            "EcrRepoUri",
            value=self.repository.repository_uri,
            description="Push images here for App Runner to pull",
        )
