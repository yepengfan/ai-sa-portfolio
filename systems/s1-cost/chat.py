import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Using Claude Haiku 4.5 with cross-region inference profile
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Claude Haiku 4.5 on-demand pricing (per 1K tokens)
# Note: Even with inference profiles, you can track equivalent per-token costs for analysis
INPUT_COST_PER_1K = 0.000125  # $0.000125 per 1K input tokens
OUTPUT_COST_PER_1K = 0.000625  # $0.000625 per 1K output tokens

total_cost = 0.0
total_tokens = {"input": 0, "output": 0}
messages = []

print("Chat with Claude Haiku 4.5 via Inference Profile (type 'quit' to exit)\n")

while True:
    user_input = input("You: ").strip()
    if not user_input or user_input.lower() == "exit":
        print(f"\nSession totals: {total_tokens['input']} input tokens, {total_tokens['output']} output tokens")
        print(f"Equivalent on-demand cost: ${total_cost:.6f}")
        print("Note: Using inference profile - actual costs depend on provisioned capacity")
        break

    messages.append({"role": "user", "content": user_input})

    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": messages,
        }),
    )

    result = json.loads(response["body"].read())
    assistant_text = result["content"][0]["text"]
    input_tokens = result["usage"]["input_tokens"]
    output_tokens = result["usage"]["output_tokens"]

    messages.append({"role": "assistant", "content": assistant_text})

    # Track token usage and calculate equivalent on-demand cost for analysis
    total_tokens["input"] += input_tokens
    total_tokens["output"] += output_tokens

    query_cost = (input_tokens / 1000) * INPUT_COST_PER_1K + (output_tokens / 1000) * OUTPUT_COST_PER_1K
    total_cost += query_cost

    print(f"\nAssistant: {assistant_text}")
    print(f"\n[Tokens: {input_tokens} in / {output_tokens} out | Query equiv. cost: ${query_cost:.6f} | Session total: ${total_cost:.6f}]\n")
