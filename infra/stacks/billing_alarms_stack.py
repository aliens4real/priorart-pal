"""Account-wide billing alarms — independent of any service stack.

Why a separate stack from `MonitoringStack`:

- Billing alarms are **account-scoped**, not service-scoped. Spending too
  much is a fact about the AWS account, not about any one component.
- Splitting them out lets us deploy alarms first — the safest possible
  first deploy on a fresh account — without dragging in the API Gateway,
  Cognito, App Runner, etc. that the per-service dashboard requires.
- Future growth: alarm thresholds, notification routing (Slack, PagerDuty),
  and budgets all live here without polluting the dashboard stack.

AWS quirks for billing alarms:

- The `AWS/Billing` metric namespace lives **only in us-east-1**, regardless
  of where the rest of your stacks are. We deploy this stack in us-east-1
  anyway, so this is a non-issue here — flagging only because it bites if
  someone clones the pattern into a different region.
- The alarm requires "Receive Billing Alerts" to be enabled in the AWS
  account's billing preferences. That's a one-time per-account toggle in
  the console; **CDK cannot toggle it** — no API exists. If the alarm
  shows `INSUFFICIENT_DATA` after deploy, that's almost always why.
- Email subscriptions need to be confirmed via a click-through in the
  email SNS sends. Until confirmed, the topic doesn't deliver.
"""
from __future__ import annotations

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_subs
from constructs import Construct


class BillingAlarmsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project: str,
        alert_email: str,
        billing_thresholds_usd: tuple[int, ...] = (20, 50),
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.billing_topic = sns.Topic(
            self,
            "BillingAlerts",
            display_name=f"{project} billing alerts",
            topic_name=f"{project}-billing-alerts",
        )
        self.billing_topic.add_subscription(
            sns_subs.EmailSubscription(alert_email)
        )

        # AWS/Billing publishes once every ~6 hours. A single-period
        # evaluation is enough — these alarms are budget tripwires, not
        # latency-sensitive signals.
        billing_metric = cw.Metric(
            namespace="AWS/Billing",
            metric_name="EstimatedCharges",
            dimensions_map={"Currency": "USD"},
            statistic="Maximum",
            period=Duration.hours(6),
        )

        self.billing_alarms: list[cw.Alarm] = []
        for threshold in billing_thresholds_usd:
            alarm = cw.Alarm(
                self,
                f"Billing{threshold}",
                alarm_name=f"{project}-billing-{threshold}-usd",
                alarm_description=(
                    f"Alerts when estimated AWS charges exceed USD {threshold} "
                    f"for the month. Budget guardrail; not latency-sensitive."
                ),
                metric=billing_metric,
                threshold=threshold,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.IGNORE,
            )
            alarm.add_alarm_action(cw_actions.SnsAction(self.billing_topic))
            self.billing_alarms.append(alarm)

        CfnOutput(
            self,
            "BillingTopicArn",
            value=self.billing_topic.topic_arn,
            description="Subscribe additional emails / Slack here as needed.",
        )
