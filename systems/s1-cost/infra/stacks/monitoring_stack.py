"""CloudWatch Dashboard + Alarm + SNS for Bedrock cost monitoring."""

from aws_cdk import (
    Duration,
    Stack,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
)
from constructs import Construct

NAMESPACE = "BedrockCost"
CALLERS = ["nano-cc", "benchmark"]
MODELS = ["sonnet", "haiku"]


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        alert_email: str = "",
        cost_threshold: float = 10.0,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- SNS Topic ---
        self.topic = sns.Topic(self, "CostAlertTopic", display_name="Bedrock Cost Alert")

        if alert_email:
            self.topic.add_subscription(subs.EmailSubscription(alert_email))

        # --- Alarm: daily inferred cost ---
        cost_metric = cw.Metric(
            namespace=NAMESPACE,
            metric_name="InferredCost",
            statistic="Sum",
            period=Duration.days(1),
        )

        self.alarm = cw.Alarm(
            self,
            "DailyCostAlarm",
            alarm_name="bedrock-daily-cost-high",
            alarm_description=f"Bedrock daily inferred cost exceeds ${cost_threshold:.2f}",
            metric=cost_metric,
            threshold=cost_threshold,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        self.alarm.add_alarm_action(cw_actions.SnsAction(self.topic))

        # --- Dashboard ---
        self.dashboard = cw.Dashboard(
            self, "Dashboard", dashboard_name="BedrockCost"
        )

        # Row 1: cost trend + daily total + call count
        self.dashboard.add_widgets(
            cw.GraphWidget(
                title="Inferred Cost by Model",
                width=12,
                height=6,
                left=[
                    cw.Metric(
                        namespace=NAMESPACE,
                        metric_name="InferredCost",
                        dimensions_map={"ModelId": model, "Caller": caller},
                        statistic="Sum",
                        period=Duration.minutes(5),
                        label=f"{model} ({caller})",
                    )
                    for model in MODELS
                    for caller in CALLERS
                ],
            ),
            cw.SingleValueWidget(
                title="Daily Cost (Today)",
                width=6,
                height=6,
                metrics=[cost_metric],
            ),
            cw.SingleValueWidget(
                title="Invocations (Today)",
                width=6,
                height=6,
                metrics=[
                    cw.Metric(
                        namespace=NAMESPACE,
                        metric_name="InputTokens",
                        statistic="SampleCount",
                        period=Duration.days(1),
                        label="Total Calls",
                    )
                ],
            ),
        )

        # Row 2: token usage + invocations by caller
        self.dashboard.add_widgets(
            cw.GraphWidget(
                title="Token Usage by Model",
                width=12,
                height=6,
                stacked=True,
                left=[
                    cw.Metric(
                        namespace=NAMESPACE,
                        metric_name=metric_name,
                        dimensions_map={"ModelId": model, "Caller": "nano-cc"},
                        statistic="Sum",
                        period=Duration.minutes(5),
                        label=f"{model} {direction}",
                    )
                    for model in MODELS
                    for metric_name, direction in [
                        ("InputTokens", "In"),
                        ("OutputTokens", "Out"),
                    ]
                ],
            ),
            cw.GraphWidget(
                title="Invocations by Caller",
                width=12,
                height=6,
                left=[
                    cw.Metric(
                        namespace=NAMESPACE,
                        metric_name="InputTokens",
                        dimensions_map={"Caller": caller},
                        statistic="SampleCount",
                        period=Duration.minutes(5),
                        label=caller,
                    )
                    for caller in CALLERS
                ],
            ),
        )
