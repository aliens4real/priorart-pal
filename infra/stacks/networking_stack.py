"""VPC, subnets, security groups.

Pattern note: We split networking into its own stack because it changes
rarely. RDS, App Runner, etc. all reference VPC/SG outputs from here. If we
co-located networking with compute, every compute change would risk a VPC
churn — and VPC changes are slow and risky.
"""
from __future__ import annotations

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class NetworkingStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 2 AZs is the minimum RDS requires for failover. We pick small
        # subnets — this account doesn't need /16 per AZ.
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=f"{project}-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.20.0.0/20"),
            max_azs=2,
            nat_gateways=1,  # 1 NAT keeps cost down vs. 1-per-AZ
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="private-egress",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # App Runner sits in private-egress subnets via its VPC connector,
        # so it can reach Postgres and the public internet (for AI APIs).
        self.app_security_group = ec2.SecurityGroup(
            self,
            "AppSg",
            vpc=self.vpc,
            description="App Runner egress traffic",
            allow_all_outbound=True,
        )

        # RDS sits in isolated subnets — no egress, only the app SG can reach it.
        self.db_security_group = ec2.SecurityGroup(
            self,
            "DbSg",
            vpc=self.vpc,
            description="Postgres ingress from app only",
            allow_all_outbound=False,
        )
        self.db_security_group.add_ingress_rule(
            peer=self.app_security_group,
            connection=ec2.Port.tcp(5432),
            description="Postgres from App Runner",
        )
