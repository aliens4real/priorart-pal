"""CDK app entry point.

Composes all stacks. The order here matters only for cross-stack references —
CDK figures out the actual deployment order from those dependencies.
"""
from __future__ import annotations

import os

import aws_cdk as cdk

from stacks.api_gateway_stack import ApiGatewayStack
from stacks.app_runner_stack import AppRunnerStack
from stacks.auth_stack import AuthStack
from stacks.database_stack import DatabaseStack
from stacks.frontend_stack import FrontendStack
from stacks.monitoring_stack import MonitoringStack
from stacks.networking_stack import NetworkingStack
from stacks.secrets_stack import SecretsStack

PROJECT = "priorart-pal"
ENV_NAME = os.environ.get("ENV_NAME", "dev")

app = cdk.App()

# Bind env only when we have a real account. With a placeholder account,
# CDK tries to do context lookups (AZ list, AMI IDs, etc.) and fails
# without credentials. Synth without env still validates stack structure.
_account = os.environ.get("CDK_DEFAULT_ACCOUNT")
_region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
env: cdk.Environment | None = (
    cdk.Environment(account=_account, region=_region)
    if _account and _account != "000000000000"
    else None
)


def stack_id(name: str) -> str:
    return f"{PROJECT}-{ENV_NAME}-{name}"


networking = NetworkingStack(app, stack_id("networking"), env=env, project=PROJECT)
secrets = SecretsStack(app, stack_id("secrets"), env=env, project=PROJECT)
database = DatabaseStack(
    app,
    stack_id("database"),
    env=env,
    project=PROJECT,
    vpc=networking.vpc,
    db_security_group=networking.db_security_group,
)
auth = AuthStack(
    app,
    stack_id("auth"),
    env=env,
    project=PROJECT,
    hosted_ui_prefix=f"{PROJECT}-mk-auth",
)
app_runner = AppRunnerStack(
    app,
    stack_id("app-runner"),
    env=env,
    project=PROJECT,
    vpc=networking.vpc,
    app_security_group=networking.app_security_group,
    secrets=secrets,
    database=database,
)
api_gateway = ApiGatewayStack(
    app,
    stack_id("api-gateway"),
    env=env,
    project=PROJECT,
    user_pool=auth.user_pool,
    user_pool_client=auth.user_pool_client,
    app_runner_url=app_runner.service_url,
)
frontend = FrontendStack(app, stack_id("frontend"), env=env, project=PROJECT)
monitoring = MonitoringStack(
    app,
    stack_id("monitoring"),
    env=env,
    project=PROJECT,
    api_id=api_gateway.api_id,
    app_runner_service_arn=app_runner.service_arn,
)

cdk.Tags.of(app).add("project", PROJECT)
cdk.Tags.of(app).add("env", ENV_NAME)
cdk.Tags.of(app).add("owner", "mkerrigan")

app.synth()
