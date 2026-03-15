"""Tests for the BedrockCost monitoring CDK stack."""

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

from stacks.monitoring_stack import MonitoringStack

NAMESPACE = "BedrockCost"


def _make_template(alert_email: str = "", cost_threshold: float = 10.0) -> Template:
    app = cdk.App()
    stack = MonitoringStack(
        app,
        "TestStack",
        alert_email=alert_email,
        cost_threshold=cost_threshold,
    )
    return Template.from_stack(stack)


class TestSNSTopic:
    def test_topic_created(self):
        template = _make_template()
        template.resource_count_is("AWS::SNS::Topic", 1)

    def test_topic_display_name(self):
        template = _make_template()
        template.has_resource_properties(
            "AWS::SNS::Topic",
            {"DisplayName": "Bedrock Cost Alert"},
        )

    def test_no_subscription_without_email(self):
        template = _make_template(alert_email="")
        template.resource_count_is("AWS::SNS::Subscription", 0)

    def test_email_subscription_when_provided(self):
        template = _make_template(alert_email="test@example.com")
        template.has_resource_properties(
            "AWS::SNS::Subscription",
            {
                "Protocol": "email",
                "Endpoint": "test@example.com",
            },
        )


class TestAlarm:
    def test_alarm_created(self):
        template = _make_template()
        template.resource_count_is("AWS::CloudWatch::Alarm", 1)

    def test_alarm_properties(self):
        template = _make_template(cost_threshold=1.0)
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            Match.object_like({
                "AlarmName": "bedrock-daily-cost-high",
                "Namespace": NAMESPACE,
                "MetricName": "InferredCost",
                "Statistic": "Sum",
                "Threshold": 1.0,
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 1,
                "TreatMissingData": "notBreaching",
            }),
        )

    def test_alarm_custom_threshold(self):
        template = _make_template(cost_threshold=5.0)
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            Match.object_like({"Threshold": 5.0}),
        )

    def test_alarm_has_sns_action(self):
        template = _make_template()
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            Match.object_like({
                "AlarmActions": Match.any_value(),
            }),
        )


class TestDashboard:
    def test_dashboard_created(self):
        template = _make_template()
        template.resource_count_is("AWS::CloudWatch::Dashboard", 1)

    def test_dashboard_name(self):
        template = _make_template()
        template.has_resource_properties(
            "AWS::CloudWatch::Dashboard",
            Match.object_like({"DashboardName": "BedrockCost"}),
        )
