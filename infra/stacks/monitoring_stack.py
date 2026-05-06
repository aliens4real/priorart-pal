"""Per-service CloudWatch dashboard.

Surfaces request count / latency / error metrics for the API Gateway
and (later) App Runner / RDS. Account-wide billing alarms live in
[`billing_alarms_stack.py`](billing_alarms_stack.py) — separate stack
so they can deploy on a fresh account without depending on any service
yet existing.
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
