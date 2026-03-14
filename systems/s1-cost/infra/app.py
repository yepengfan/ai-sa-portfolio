#!/usr/bin/env python3
"""CDK app entry point for BedrockCost monitoring infrastructure."""

import aws_cdk as cdk

from stacks.monitoring_stack import MonitoringStack

app = cdk.App()

alert_email = app.node.try_get_context("alert_email") or "fanyepeng97@gmail.com"

MonitoringStack(
    app,
    "BedrockCostMonitoring",
    alert_email=alert_email,
    env=cdk.Environment(region="us-east-1"),
)

app.synth()
