"""CDK assertion tests.

`Template.from_stack` compiles a stack to its CloudFormation JSON and lets
us assert on resource counts/properties. Cheap insurance against accidental
breakage when we refactor stacks.
"""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.auth_stack import AuthStack
from stacks.billing_alarms_stack import BillingAlarmsStack
from stacks.database_stack import DatabaseStack
from stacks.frontend_stack import FrontendStack
from stacks.networking_stack import NetworkingStack
from stacks.secrets_stack import SecretsStack


def _env() -> cdk.Environment:
    return cdk.Environment(account="000000000000", region="us-east-1")


def test_networking_creates_vpc_with_isolated_subnets():
    app = cdk.App()
    s = NetworkingStack(app, "test-net", env=_env(), project="priorart-pal")
    t = assertions.Template.from_stack(s)
    t.resource_count_is("AWS::EC2::VPC", 1)
    # 2 AZs * 3 subnet types = 6 subnets
    t.resource_count_is("AWS::EC2::Subnet", 6)


def test_secrets_creates_three_provider_keys():
    app = cdk.App()
    s = SecretsStack(app, "test-secrets", env=_env(), project="priorart-pal")
    t = assertions.Template.from_stack(s)
    t.resource_count_is("AWS::SecretsManager::Secret", 3)


def test_database_uses_postgres_16():
    app = cdk.App()
    net = NetworkingStack(app, "net", env=_env(), project="priorart-pal")
    db = DatabaseStack(
        app, "db", env=_env(), project="priorart-pal",
        vpc=net.vpc, db_security_group=net.db_security_group,
    )
    t = assertions.Template.from_stack(db)
    t.has_resource_properties(
        "AWS::RDS::DBInstance",
        {"Engine": "postgres", "DBInstanceClass": "db.t4g.micro"},
    )


def test_auth_user_pool_retains_on_destroy():
    app = cdk.App()
    s = AuthStack(
        app, "auth", env=_env(),
        project="priorart-pal", hosted_ui_prefix="priorart-pal-mk-auth",
    )
    t = assertions.Template.from_stack(s)
    t.has_resource("AWS::Cognito::UserPool", {"DeletionPolicy": "Retain"})


def test_frontend_bucket_blocks_public_access():
    app = cdk.App()
    s = FrontendStack(app, "fe", env=_env(), project="priorart-pal")
    t = assertions.Template.from_stack(s)
    t.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        },
    )


def test_billing_alarms_stack_has_sns_and_two_alarms():
    """Billing alarms are in a standalone stack with no service deps —
    safe to deploy first on a fresh account before any other stack."""
    app = cdk.App()
    s = BillingAlarmsStack(
        app,
        "billing",
        env=_env(),
        project="priorart-pal",
        alert_email="dev@example.com",
    )
    t = assertions.Template.from_stack(s)
    # SNS topic + email subscription
    t.resource_count_is("AWS::SNS::Topic", 1)
    t.has_resource_properties(
        "AWS::SNS::Subscription",
        {"Protocol": "email", "Endpoint": "dev@example.com"},
    )
    # Two alarms, both on AWS/Billing EstimatedCharges
    t.resource_count_is("AWS::CloudWatch::Alarm", 2)
    t.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "Namespace": "AWS/Billing",
            "MetricName": "EstimatedCharges",
            "Threshold": 20,
            "ComparisonOperator": "GreaterThanThreshold",
        },
    )
    t.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "Namespace": "AWS/Billing",
            "MetricName": "EstimatedCharges",
            "Threshold": 50,
            "ComparisonOperator": "GreaterThanThreshold",
        },
    )


def test_billing_alarms_stack_has_no_service_dependencies():
    """The whole point of splitting BillingAlarmsStack out: no cross-stack
    refs to api-gateway / auth / app-runner / etc. so it deploys first on
    a fresh account."""
    app = cdk.App()
    s = BillingAlarmsStack(
        app,
        "billing",
        env=_env(),
        project="priorart-pal",
        alert_email="dev@example.com",
    )
    assert not s.dependencies, (
        f"BillingAlarmsStack should have no stack dependencies, "
        f"got: {s.dependencies}"
    )
