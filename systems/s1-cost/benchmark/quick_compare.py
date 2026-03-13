"""
Benchmark: Baseline + 5 compression strategies on a single prompt.
Measures token reduction and net cost saving.

Usage:
    cd systems/s1-cost
    python -m benchmark.quick_compare
"""

import sys
import io
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import boto3

from strategies.compression.manual_refiner import ManualRefiner
from strategies.compression.semantic_summarizer import SemanticSummarizer
from strategies.compression.relevance_filter import RelevanceFilter
from strategies.compression.structure_optimizer import StructureOptimizer
from strategies.compression.llmlingua_compressor import LLMLinguaCompressor
from benchmark.llmlingua2_wrapper import OriginalLLMLingua2
from utils.config import MODELS, PRICING, AWS_REGION

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SONNET_MODEL_ID = MODELS["sonnet"]["id"]
MAX_TOKENS = 512
TEMPERATURE = 0

BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARK_DIR / "results"

client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def invoke_bedrock(system_prompt: str, user_message: str) -> dict:
    """Send a single request to Sonnet and return usage + text."""
    resp = client.invoke_model(
        modelId=SONNET_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": 1,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }),
    )
    body = json.loads(resp["body"].read())
    return {
        "input_tokens": body["usage"]["input_tokens"],
        "output_tokens": body["usage"]["output_tokens"],
        "output_text": body["content"][0]["text"],
    }


def calculate_cost(result: dict, model: str = "sonnet") -> float:
    p = PRICING[model]
    return (result["input_tokens"] / 1000) * p["input"] + \
           (result["output_tokens"] / 1000) * p["output"]


def track_haiku_cost(compressor, text, *args):
    """Wrap compress_prompt() to capture Haiku API token usage.

    LLMLinguaCompressor does not return Haiku token counts natively,
    so we monkey-patch invoke_model to intercept every Haiku call.
    """
    original = compressor.client.invoke_model
    usage = {"input_tokens": 0, "output_tokens": 0}

    def tracked(**kwargs):
        r = original(**kwargs)
        raw = r["body"].read()
        r["body"] = io.BytesIO(raw)  # re-wrap so compressor can still read
        parsed = json.loads(raw)
        usage["input_tokens"] += parsed["usage"]["input_tokens"]
        usage["output_tokens"] += parsed["usage"]["output_tokens"]
        return r

    compressor.client.invoke_model = tracked
    try:
        compressed, metrics = compressor.compress_prompt(text, *args)
    finally:
        compressor.client.invoke_model = original

    metrics["haiku_input_tokens"] = usage["input_tokens"]
    metrics["haiku_output_tokens"] = usage["output_tokens"]
    metrics["haiku_cost"] = (
        usage["input_tokens"] * PRICING["haiku"]["input"] / 1000
        + usage["output_tokens"] * PRICING["haiku"]["output"] / 1000
    )
    return compressed, metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_benchmark():
    system_prompt = (BENCHMARK_DIR / "system_prompt.txt").read_text().strip()
    prompt_data = json.loads((BENCHMARK_DIR / "test_prompt.json").read_text())
    user_message = (
        f"Given this architecture:\n{prompt_data['context']}"
        f"\n\nQuestion: {prompt_data['query']}"
    )

    # ---- Calibrate: measure system prompt tokens ----
    print("Calibrating system prompt tokens...")
    cal = invoke_bedrock(system_prompt, "x")
    sys_tokens = cal["input_tokens"] - 1  # "x" ≈ 1 token (approximate)
    print(f"  system_prompt ≈ {sys_tokens} tokens")

    # ---- Baseline ----
    print("Running baseline (no compression)...")
    baseline = invoke_bedrock(system_prompt, user_message)
    baseline["cost"] = calculate_cost(baseline)
    baseline_user_tokens = baseline["input_tokens"] - sys_tokens
    print(f"  {baseline['input_tokens']} input tokens "
          f"(system {sys_tokens} + user {baseline_user_tokens}), "
          f"${baseline['cost']:.4f}")

    # ---- 6 compression strategies ----
    compressors = {
        "manual_refiner":      ManualRefiner(),
        "semantic_summarizer": SemanticSummarizer(),
        "relevance_filter":    RelevanceFilter(),
        "structure_optimizer": StructureOptimizer(),
        "llmlingua":           LLMLinguaCompressor(),
        "llmlingua2":          OriginalLLMLingua2(rate=0.5),
    }

    results = {}
    for name, comp in compressors.items():
        print(f"Running {name}...")

        # Compress user_message (not system_prompt)
        if name == "relevance_filter":
            compressed, m = comp.compress_prompt(user_message, prompt_data["query"])
        elif name in ("semantic_summarizer", "llmlingua"):
            compressed, m = track_haiku_cost(comp, user_message)
        else:
            compressed, m = comp.compress_prompt(user_message)

        # Inference with compressed prompt
        r = invoke_bedrock(system_prompt, compressed)
        sonnet_cost = calculate_cost(r)
        haiku_cost = m.get("haiku_cost", 0)
        total_cost = sonnet_cost + haiku_cost

        compressed_user_tokens = r["input_tokens"] - sys_tokens
        user_msg_compress = (1 - compressed_user_tokens / baseline_user_tokens) * 100

        results[name] = {
            "input_tokens":          r["input_tokens"],
            "output_tokens":         r["output_tokens"],
            "compression_pct":       (1 - r["input_tokens"] / baseline["input_tokens"]) * 100,
            "user_msg_compress_pct": user_msg_compress,
            "sonnet_cost":           sonnet_cost,
            "haiku_cost":            haiku_cost,
            "total_cost":            total_cost,
            "net_saving_pct":        (baseline["cost"] - total_cost) / baseline["cost"] * 100,
            "output_text":           r["output_text"],
        }
        print(f"  {r['input_tokens']} tokens, "
              f"user_msg compression {user_msg_compress:.1f}%, "
              f"${total_cost:.4f}")

    # ---- Comparison table ----
    W = 105
    print(f"\n{'=' * W}")
    print(f"Strategy Comparison  (system_prompt={sys_tokens} tok, "
          f"user_msg={baseline_user_tokens} tok, total={baseline['input_tokens']} tok)")
    print(f"{'=' * W}")
    print(f"{'Strategy':<25} | {'Input Tok':>9} | {'Total %':>7} | "
          f"{'Msg %':>7} | {'Haiku $':>8} | {'Net Cost':>8} | {'Save%':>6}")
    print(f"{'-' * W}")
    print(f"{'Baseline':<25} | {baseline['input_tokens']:>9,} | {'--':>7} | "
          f"{'--':>7} | {'--':>8} | ${baseline['cost']:>7.4f} | {'--':>6}")

    for name, r in results.items():
        h = f"${r['haiku_cost']:.4f}" if r["haiku_cost"] > 0 else "--"
        print(f"{name:<25} | {r['input_tokens']:>9,} | "
              f"{r['compression_pct']:>6.1f}% | "
              f"{r['user_msg_compress_pct']:>6.1f}% | {h:>8} | "
              f"${r['total_cost']:>7.4f} | {r['net_saving_pct']:>5.1f}%")

    print(f"{'-' * W}")
    print("\n  Total %  = token saving / total input (includes uncompressed system_prompt)")
    print("  Msg %    = token saving / user_message only  <-- compare with literature")
    print("  * semantic_summarizer and llmlingua net cost includes Haiku compression cost")

    # Literature reference values
    print("\nLiterature reference values:")
    print("  Manual refinement:  30-50% (freeCodeCamp)")
    print("  Semantic summary:   40-60% (ML Mastery)")
    print("  Relevance filter:   50-70% (TDS)")
    print("  Structure format:   20-40%")
    print("  LLMLingua:          up to 20x (original paper)")

    # ---- Save JSON ----
    RESULTS_DIR.mkdir(exist_ok=True)
    output = {
        "system_prompt_tokens": sys_tokens,
        "baseline_user_msg_tokens": baseline_user_tokens,
        "baseline": {k: v for k, v in baseline.items() if k != "output_text"},
        "baseline_output_text": baseline["output_text"],
        "strategies": {},
    }
    for name, r in results.items():
        entry = {k: v for k, v in r.items() if k != "output_text"}
        entry["output_text"] = r["output_text"]
        output["strategies"][name] = entry

    path = RESULTS_DIR / "compression_results.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {path}")


if __name__ == "__main__":
    run_benchmark()
