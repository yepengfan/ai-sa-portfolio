"""
Benchmark: Caching, Routing, and Batch strategies on the same prompt.

Usage:
    cd systems/s1-cost
    uv run python -m benchmark.strategy_compare
"""

import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import boto3

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
AWS_REGION = "us-east-1"
MAX_TOKENS = 1024
TEMPERATURE = 0

PRICING = {
    "sonnet": {"input": 0.003, "output": 0.015},
    "haiku":  {"input": 0.000125, "output": 0.000625},
    # Caching: write = 1.25x input, read = 0.1x input
    "sonnet_cache_write": 0.00375,
    "sonnet_cache_read":  0.0003,
    # Batch: 50% of on-demand
    "sonnet_batch": {"input": 0.0015, "output": 0.0075},
    "haiku_batch":  {"input": 0.0000625, "output": 0.0003125},
}

BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARK_DIR / "results"

client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calculate_cost(input_tokens, output_tokens, model="sonnet"):
    p = PRICING[model]
    return (input_tokens / 1000) * p["input"] + (output_tokens / 1000) * p["output"]


def load_prompt():
    """Load the custom SA prompt (system + context + query)."""
    system_prompt = (BENCHMARK_DIR / "system_prompt.txt").read_text()
    prompt_data = json.loads((BENCHMARK_DIR / "test_prompt.json").read_text())
    user_message = f"Given this architecture:\n{prompt_data['context']}\n\nQuestion: {prompt_data['query']}"
    return system_prompt, user_message, prompt_data["query"]


# ---------------------------------------------------------------------------
# 1. CACHING BENCHMARK
# ---------------------------------------------------------------------------

def run_caching_benchmark(system_prompt, user_message):
    """Send same request twice with cache_control. Compare cold vs warm."""
    print("\n" + "=" * 80)
    print("STRATEGY 1: PROMPT CACHING")
    print("=" * 80)

    results = {}

    for label in ["cold (cache write)", "warm (cache read)"]:
        print(f"\n  {label}...", end="", flush=True)
        start = time.time()

        response = client.invoke_model(
            modelId=SONNET_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "system": [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [{"role": "user", "content": user_message}],
            }),
        )

        latency = time.time() - start
        result = json.loads(response["body"].read())
        usage = result["usage"]

        entry = {
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
            "latency_s": round(latency, 2),
            "output_preview": result["content"][0]["text"][:200],
        }

        # Cost calculation with cache pricing
        # Bedrock reports input_tokens (non-cached) separately from
        # cache_creation_input_tokens and cache_read_input_tokens.
        cache_write_tokens = entry["cache_creation_input_tokens"]
        cache_read_tokens = entry["cache_read_input_tokens"]

        entry["cost"] = (
            (entry["input_tokens"] / 1000) * PRICING["sonnet"]["input"]
            + (cache_write_tokens / 1000) * PRICING["sonnet_cache_write"]
            + (cache_read_tokens / 1000) * PRICING["sonnet_cache_read"]
            + (entry["output_tokens"] / 1000) * PRICING["sonnet"]["output"]
        )

        key = "cold" if "cold" in label else "warm"
        results[key] = entry
        print(f" {entry['input_tokens']} tokens, "
              f"cache_write={cache_write_tokens}, cache_read={cache_read_tokens}, "
              f"${entry['cost']:.4f}, {latency:.1f}s")

    # Summary — no-cache baseline uses total input tokens (regular + cached)
    total_input = (results["cold"]["input_tokens"]
                   + results["cold"]["cache_creation_input_tokens"]
                   + results["cold"]["cache_read_input_tokens"])
    no_cache_cost = calculate_cost(total_input, results["cold"]["output_tokens"])
    warm_cost = results["warm"]["cost"]
    saving = no_cache_cost - warm_cost

    print(f"\n  --- Caching Summary ---")
    print(f"  Without caching:  ${no_cache_cost:.4f}")
    print(f"  Cold (first call): ${results['cold']['cost']:.4f} "
          f"(cache write costs 1.25x on {results['cold']['cache_creation_input_tokens']} tokens)")
    print(f"  Warm (cache hit):  ${warm_cost:.4f}")
    print(f"  Saving per warm call: ${saving:.4f} ({saving/no_cache_cost*100:.1f}%)")
    cold_premium = results["cold"]["cost"] - no_cache_cost
    print(f"  Break-even: {cold_premium / saving:.1f} warm calls to recoup cold write premium" if saving > 0 else "  No savings detected")

    results["summary"] = {
        "no_cache_cost": no_cache_cost,
        "cold_cost": results["cold"]["cost"],
        "warm_cost": warm_cost,
        "saving_per_warm_call": saving,
        "saving_pct": saving / no_cache_cost * 100 if no_cache_cost > 0 else 0,
    }
    return results


# ---------------------------------------------------------------------------
# 2. ROUTING BENCHMARK
# ---------------------------------------------------------------------------

# Test queries at different complexity levels
ROUTING_QUERIES = [
    {
        "query": "What is Amazon S3?",
        "expected": "simple",
    },
    {
        "query": "List the five pillars of the AWS Well-Architected Framework.",
        "expected": "simple",
    },
    {
        "query": "How do I set up a VPC with public and private subnets?",
        "expected": "moderate",
    },
    {
        "query": "Based on the architecture above, suggest 3 cost optimization strategies with estimated monthly savings.",
        "expected": "complex",
    },
    {
        "query": "Compare the trade-offs between using Aurora Serverless v2 versus provisioned Aurora for a workload with variable traffic patterns peaking at 10x baseline, and recommend an approach that optimizes for both cost and latency.",
        "expected": "complex",
    },
]


def run_routing_benchmark(system_prompt, user_message):
    """Route queries to Haiku or Sonnet, compare quality and cost."""
    print("\n" + "=" * 80)
    print("STRATEGY 2: MODEL ROUTING")
    print("=" * 80)

    from strategies.model_routing import ModelRouter
    router = ModelRouter()

    results = []

    for i, rq in enumerate(ROUTING_QUERIES):
        query = rq["query"]
        print(f"\n  Query {i+1}: \"{query[:70]}...\"" if len(query) > 70
              else f"\n  Query {i+1}: \"{query}\"")

        # Use the full context for the complex query, just the query for others
        if rq["expected"] == "complex" and "architecture above" in query:
            messages = [{"role": "user", "content": user_message}]
        else:
            messages = [{"role": "user", "content": query}]

        # Get routing decision
        complexity, reason = router._analyze_query_complexity(query, messages)
        selected = router._select_model_for_complexity(complexity)
        print(f"    Router: {complexity.value} → {selected}")

        # Call both Haiku and Sonnet for comparison
        entry = {"query": query, "expected": rq["expected"],
                 "routed_complexity": complexity.value, "routed_model": selected}

        for model_name, model_id in [("haiku", HAIKU_MODEL_ID), ("sonnet", SONNET_MODEL_ID)]:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "messages": messages,
            }
            # Add system prompt for the complex architecture query
            if rq["expected"] == "complex" and "architecture above" in query:
                body["system"] = system_prompt

            resp = client.invoke_model(modelId=model_id, body=json.dumps(body))
            result = json.loads(resp["body"].read())
            usage = result["usage"]
            cost = calculate_cost(usage["input_tokens"], usage["output_tokens"], model_name)

            entry[model_name] = {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cost": cost,
                "output_preview": result["content"][0]["text"][:300],
            }
            print(f"    {model_name}: {usage['input_tokens']} in / {usage['output_tokens']} out, ${cost:.5f}")

        # Savings from routing to Haiku
        if selected == "haiku":
            entry["routing_saving"] = entry["sonnet"]["cost"] - entry["haiku"]["cost"]
            entry["routing_saving_pct"] = entry["routing_saving"] / entry["sonnet"]["cost"] * 100
        else:
            entry["routing_saving"] = 0
            entry["routing_saving_pct"] = 0

        results.append(entry)

    # Summary table
    print(f"\n  --- Routing Summary ---")
    print(f"  {'Query':<55} | {'Router':>10} | {'Haiku $':>9} | {'Sonnet $':>9} | {'Saving':>8}")
    print(f"  {'-'*55}-+-{'-'*10}-+-{'-'*9}-+-{'-'*9}-+-{'-'*8}")

    total_routed_cost = 0
    total_sonnet_cost = 0
    for r in results:
        q_short = r["query"][:55]
        routed = r["routed_model"]
        h_cost = r["haiku"]["cost"]
        s_cost = r["sonnet"]["cost"]
        routed_cost = h_cost if routed == "haiku" else s_cost
        total_routed_cost += routed_cost
        total_sonnet_cost += s_cost
        saving_str = f"${r['routing_saving']:.4f}" if r["routing_saving"] > 0 else "—"
        print(f"  {q_short:<55} | {routed:>10} | ${h_cost:>8.5f} | ${s_cost:>8.5f} | {saving_str:>8}")

    total_saving = total_sonnet_cost - total_routed_cost
    print(f"\n  Total (all-Sonnet): ${total_sonnet_cost:.5f}")
    print(f"  Total (routed):     ${total_routed_cost:.5f}")
    print(f"  Routing saves:      ${total_saving:.5f} ({total_saving/total_sonnet_cost*100:.1f}%)")

    return {
        "queries": results,
        "total_sonnet_cost": total_sonnet_cost,
        "total_routed_cost": total_routed_cost,
        "total_saving": total_saving,
        "total_saving_pct": total_saving / total_sonnet_cost * 100 if total_sonnet_cost > 0 else 0,
    }


# ---------------------------------------------------------------------------
# 3. BATCH BENCHMARK (pure math)
# ---------------------------------------------------------------------------

def run_batch_benchmark(baseline_input_tokens, baseline_output_tokens):
    """Calculate batch pricing savings — no API call needed."""
    print("\n" + "=" * 80)
    print("STRATEGY 3: BATCH PROCESSING")
    print("=" * 80)

    results = {}
    for model in ["sonnet", "haiku"]:
        realtime = calculate_cost(baseline_input_tokens, baseline_output_tokens, model)
        batch_key = f"{model}_batch"
        batch = (
            (baseline_input_tokens / 1000) * PRICING[batch_key]["input"]
            + (baseline_output_tokens / 1000) * PRICING[batch_key]["output"]
        )
        saving = realtime - batch
        results[model] = {
            "input_tokens": baseline_input_tokens,
            "output_tokens": baseline_output_tokens,
            "realtime_cost": realtime,
            "batch_cost": batch,
            "saving": saving,
            "saving_pct": saving / realtime * 100,
        }

    print(f"\n  Based on baseline tokens: {baseline_input_tokens} input, {baseline_output_tokens} output")
    print(f"\n  {'Model':<10} | {'Realtime':>10} | {'Batch (50%)':>12} | {'Saving':>10} | {'Saving %':>8}")
    print(f"  {'-'*10}-+-{'-'*10}-+-{'-'*12}-+-{'-'*10}-+-{'-'*8}")

    for model, r in results.items():
        print(f"  {model:<10} | ${r['realtime_cost']:>9.5f} | ${r['batch_cost']:>11.5f} | "
              f"${r['saving']:>9.5f} | {r['saving_pct']:>7.1f}%")

    print(f"\n  Trade-off: 50% cost reduction, but up to 24-hour turnaround.")
    print(f"  Best for: bulk evaluation, non-interactive workloads, daily batch reports.")

    # Scale projection
    print(f"\n  --- Scale Projection (1000 calls/day) ---")
    for model, r in results.items():
        daily_save = r["saving"] * 1000
        monthly_save = daily_save * 30
        print(f"  {model}: ${daily_save:.2f}/day, ${monthly_save:.2f}/month saved")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark():
    system_prompt, user_message, query = load_prompt()
    print(f"Loaded prompt: system={len(system_prompt)} chars, user={len(user_message)} chars\n")

    # First get baseline for reference
    print("Running baseline (no optimization)...", end="", flush=True)
    resp = client.invoke_model(
        modelId=SONNET_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }),
    )
    baseline = json.loads(resp["body"].read())
    bl_usage = baseline["usage"]
    bl_cost = calculate_cost(bl_usage["input_tokens"], bl_usage["output_tokens"])
    print(f" {bl_usage['input_tokens']} in / {bl_usage['output_tokens']} out, ${bl_cost:.4f}")

    # Run all three strategies
    total_cost = bl_cost
    caching_results = run_caching_benchmark(system_prompt, user_message)
    total_cost += caching_results["cold"]["cost"] + caching_results["warm"]["cost"]

    routing_results = run_routing_benchmark(system_prompt, user_message)
    total_cost += routing_results["total_routed_cost"] + routing_results["total_sonnet_cost"]

    batch_results = run_batch_benchmark(bl_usage["input_tokens"], bl_usage["output_tokens"])

    # Final comparison table
    print("\n" + "=" * 80)
    print("FINAL COMPARISON: ALL STRATEGIES")
    print("=" * 80)

    print(f"\n  Baseline Sonnet cost: ${bl_cost:.4f} "
          f"({bl_usage['input_tokens']} in / {bl_usage['output_tokens']} out)")

    strategies = [
        ("Prompt Caching (warm)", caching_results["summary"]["saving_pct"],
         "Same model, 90% off cached input tokens", "Repeated prompts"),
        ("Model Routing (Haiku)", routing_results["total_saving_pct"],
         "Cheaper model for simple queries", "Mixed-complexity workloads"),
        ("Batch Processing", batch_results["sonnet"]["saving_pct"],
         "50% off, 24h turnaround", "Non-interactive workloads"),
    ]

    print(f"\n  {'Strategy':<30} | {'Saving %':>9} | {'Mechanism':<40} | {'Best For'}")
    print(f"  {'-'*30}-+-{'-'*9}-+-{'-'*40}-+-{'-'*30}")
    for name, pct, mechanism, best_for in strategies:
        print(f"  {name:<30} | {pct:>8.1f}% | {mechanism:<40} | {best_for}")

    print(f"\n  Total benchmark API cost: ${total_cost:.4f}")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    output = {
        "baseline": {
            "model": SONNET_MODEL_ID,
            "input_tokens": bl_usage["input_tokens"],
            "output_tokens": bl_usage["output_tokens"],
            "cost": bl_cost,
        },
        "caching": {
            k: v for k, v in caching_results.items()
            if k != "cold" or True  # keep all
        },
        "routing": routing_results,
        "batch": batch_results,
    }

    # Clean output_preview from routing for JSON
    for q in output["routing"]["queries"]:
        for m in ["haiku", "sonnet"]:
            if m in q:
                q[m].pop("output_preview", None)
    for k in ["cold", "warm"]:
        if k in output["caching"]:
            output["caching"][k].pop("output_preview", None)

    results_path = RESULTS_DIR / "strategy_results.json"
    results_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n  Results saved to {results_path}")


if __name__ == "__main__":
    run_benchmark()
