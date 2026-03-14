"""Bedrock streaming client using the Converse API."""

import boto3
from typing import Generator

from utils.config import MODELS, AWS_REGION


def get_model_id(model_name: str) -> str:
    """Resolve short name ('sonnet', 'haiku') to full Bedrock model ID."""
    return MODELS[model_name]["id"]


def stream_converse(
    model_name: str,
    messages: list[dict],
    system_prompt: str,
    max_tokens: int = 1024,
) -> Generator[str, None, dict]:
    """Stream a Bedrock Converse call, yielding text chunks.

    Yields each text delta as it arrives.
    Returns (via StopIteration.value) a dict:
        {"input_tokens": int, "output_tokens": int}
    """
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    response = client.converse_stream(
        modelId=get_model_id(model_name),
        messages=messages,
        system=[{"text": system_prompt}],
        inferenceConfig={"maxTokens": max_tokens},
    )

    usage = {"input_tokens": 0, "output_tokens": 0}

    for event in response["stream"]:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"]["delta"]
            if "text" in delta:
                yield delta["text"]
        elif "metadata" in event:
            u = event["metadata"].get("usage", {})
            usage["input_tokens"] = u.get("inputTokens", 0)
            usage["output_tokens"] = u.get("outputTokens", 0)

    return usage
