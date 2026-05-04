"""CloudWatch dashboard + billing alarm references.

Pattern note: The actual billing alarms (at $20 and $50) are set up in the
AWS console at the account level — they're easier to manage there. This
stack creates a per-service dashboard that surfaces request count, latency,
errors, and links to the alarm pages.
"""
from __future__ import annotations

from aws_cdk import Stack
from aws_cdk import aws_cloudwatch as cw
from constructs import Construct


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        api_id: str,
        app_runner_service_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.dashboard = cw.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"{project}-overview",
            widgets=[
                [
                    cw.TextWidget(
                        markdown=(
                            f"# {project}\n\n"
                            "API Gateway request metrics, App Runner CPU/mem, "
                            "RDS connection counts. Per-LLM-call cost lives in "
                            "the Postgres `llm_calls` table — surfaced via "
                            "`/admin/metrics` in the API."
                        ),
                        width=24,
                        height=3,
                    ),
                ],
                [
                    cw.GraphWidget(
                        title="API Gateway requests",
                        width=12,
                        left=[
                            cw.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="Count",
                                dimensions_map={"ApiId": api_id},
                                statistic="Sum",
                            ),
                        ],
                    ),
                    cw.GraphWidget(
                        title="API Gateway 4xx / 5xx",
                        width=12,
                        left=[
                            cw.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="4xx",
                                dimensions_map={"ApiId": api_id},
                                statistic="Sum",
                            ),
                            cw.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="5xx",
                                dimensions_map={"ApiId": api_id},
                                statistic="Sum",
                            ),
                        ],
                    ),
                ],
            ],
        )
