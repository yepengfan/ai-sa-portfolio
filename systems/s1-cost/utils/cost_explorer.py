"""Query AWS Cost Explorer for Bedrock spending trends."""

import boto3
from datetime import date, timedelta

from utils.config import AWS_REGION


def get_bedrock_cost_trend(days: int = 7) -> list[dict]:
    """Fetch daily Bedrock cost for the past N days."""
    ce = boto3.client("ce", region_name=AWS_REGION)
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=days)).isoformat()

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="DAILY",
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": ["Amazon Bedrock"],
            }
        },
        Metrics=["UnblendedCost"],
    )

    results = []
    for item in response["ResultsByTime"]:
        results.append({
            "date": item["TimePeriod"]["Start"],
            "cost": float(item["Total"]["UnblendedCost"]["Amount"]),
        })
    return results


if __name__ == "__main__":
    for day in get_bedrock_cost_trend():
        print(f"  {day['date']}  ${day['cost']:.4f}")
