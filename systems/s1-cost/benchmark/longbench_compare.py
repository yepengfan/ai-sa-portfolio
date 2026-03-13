"""
Benchmark: compression strategies on LongBench public dataset.
Evaluates with Token F1 (vs ground truth) + LLM-as-judge + ROUGE-L (vs baseline).

Usage:
    cd systems/s1-cost
    uv run python -m benchmark.longbench_compare
"""

import re
import string
import sys
import io
import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import boto3
from rouge_score import rouge_scorer

from utils.config import MODELS, PRICING, AWS_REGION
from strategies.compression.semantic_summarizer import SemanticSummarizer
from strategies.compression.relevance_filter import RelevanceFilter
from benchmark.llmlingua2_wrapper import OriginalLLMLingua2

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SONNET_MODEL_ID = MODELS["sonnet"]["id"]
HAIKU_MODEL_ID = MODELS["haiku"]["id"]
MAX_TOKENS = 1024
TEMPERATURE = 0

BENCHMARK_DIR = Path(__file__).resolve().parent
DATA_DIR = BENCHMARK_DIR / "data"
RESULTS_DIR = BENCHMARK_DIR / "results"

# Selected samples: (dataset, index) — short / medium / long contexts
SAMPLES = [
    ("multifieldqa_en", 38),   # ~2,000 words
    ("multifieldqa_en", 5),    # ~5,000 words
    ("multifieldqa_en", 133),  # ~8,200 words
    ("narrativeqa", 2),        # ~5,400 words
    ("narrativeqa", 5),        # ~10,000 words
]

# ---------------------------------------------------------------------------
# Bedrock
# ---------------------------------------------------------------------------

client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def invoke_bedrock(user_message: str) -> dict:
    """Send request to Sonnet — no system prompt for LongBench."""
    response = client.invoke_model(
        modelId=SONNET_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": 1,
            "messages": [{"role": "user", "content": user_message}],
        }),
    )
    result = json.loads(response["body"].read())
    return {
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
        "output_text": result["content"][0]["text"],
    }


def calculate_cost(result: dict, model: str = "sonnet") -> float:
    p = PRICING[model]
    return (result["input_tokens"] / 1000) * p["input"] + \
           (result["output_tokens"] / 1000) * p["output"]


# ---------------------------------------------------------------------------
# Haiku cost tracker
# ---------------------------------------------------------------------------

def track_haiku_cost(compressor, text, *args, **call_kwargs):
    original_invoke = compressor.client.invoke_model
    haiku_usage = {"input_tokens": 0, "output_tokens": 0}

    def tracked_invoke(**kwargs):
        resp = original_invoke(**kwargs)
        body_bytes = resp["body"].read()
        resp["body"] = io.BytesIO(body_bytes)
        parsed = json.loads(body_bytes)
        haiku_usage["input_tokens"] += parsed["usage"]["input_tokens"]
        haiku_usage["output_tokens"] += parsed["usage"]["output_tokens"]
        return resp

    compressor.client.invoke_model = tracked_invoke
    try:
        compressed, metrics = compressor.compress_prompt(text, *args, **call_kwargs)
    finally:
        compressor.client.invoke_model = original_invoke

    metrics["haiku_input_tokens"] = haiku_usage["input_tokens"]
    metrics["haiku_output_tokens"] = haiku_usage["output_tokens"]
    metrics["haiku_cost"] = (
        haiku_usage["input_tokens"] * PRICING["haiku"]["input"] / 1000
        + haiku_usage["output_tokens"] * PRICING["haiku"]["output"] / 1000
    )
    return compressed, metrics


# ---------------------------------------------------------------------------
# ROUGE-L
# ---------------------------------------------------------------------------

_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)


def rouge_l(reference: str, hypothesis: str) -> float:
    return _scorer.score(reference, hypothesis)["rougeL"].fmeasure


# ---------------------------------------------------------------------------
# Token F1 (SQuAD-style, LongBench official metric for QA tasks)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, remove punctuation/articles, collapse whitespace."""
    text = text.lower()
    text = "".join(ch for ch in text if ch not in string.punctuation)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def token_f1(prediction: str, ground_truths: list[str]) -> float:
    """Max token-level F1 across all reference answers."""
    pred_tokens = _normalize(prediction).split()
    best = 0.0
    for gt in ground_truths:
        gt_tokens = _normalize(gt).split()
        common = Counter(pred_tokens) & Counter(gt_tokens)
        num_common = sum(common.values())
        if num_common == 0:
            continue
        precision = num_common / len(pred_tokens) if pred_tokens else 0
        recall = num_common / len(gt_tokens) if gt_tokens else 0
        f1 = 2 * precision * recall / (precision + recall)
        best = max(best, f1)
    return best


# ---------------------------------------------------------------------------
# LLM-as-judge (Haiku binary)
# ---------------------------------------------------------------------------

def llm_judge(question: str, ground_truths: list[str], model_output: str) -> dict:
    """Ask Haiku whether the model output correctly answers the question.

    Returns {"verdict": "YES"|"NO", "judge_cost": float}.
    """
    gt_str = " | ".join(ground_truths)
    prompt = (
        f"Question: {question}\n"
        f"Ground truth answer: {gt_str}\n"
        f"Model output: {model_output[:2000]}\n\n"
        "Does the model output correctly answer the question based on the ground truth? "
        "Reply with only YES or NO."
    )
    resp = client.invoke_model(
        modelId=HAIKU_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    result = json.loads(resp["body"].read())
    text = result["content"][0]["text"].strip().upper()
    cost = (
        result["usage"]["input_tokens"] * PRICING["haiku"]["input"] / 1000
        + result["usage"]["output_tokens"] * PRICING["haiku"]["output"] / 1000
    )
    return {"verdict": "YES" if "YES" in text else "NO", "judge_cost": cost}


# ---------------------------------------------------------------------------
# Strategy config
# ---------------------------------------------------------------------------

@dataclass
class StrategyConfig:
    """One strategy variant with its compressor instance and call-time kwargs."""
    compressor: Any
    call_kwargs: dict = field(default_factory=dict)
    needs_query: bool = False          # RelevanceFilter: compress_prompt(ctx, query, ...)
    needs_haiku_tracking: bool = False # SemanticSummarizer / LLMLinguaCompressor call Haiku


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_longbench_samples():
    """Load selected LongBench samples."""
    cache = {}
    samples = []
    for dataset_name, idx in SAMPLES:
        if dataset_name not in cache:
            path = DATA_DIR / f"{dataset_name}.jsonl"
            with open(path) as f:
                cache[dataset_name] = [json.loads(line) for line in f]
        raw = cache[dataset_name][idx]
        samples.append({
            "dataset": dataset_name,
            "index": idx,
            "context": raw["context"],
            "query": raw["input"],
            "answers": raw["answers"],
            "context_words": len(raw["context"].split()),
        })
    return samples


# ---------------------------------------------------------------------------
# Run one sample
# ---------------------------------------------------------------------------

def run_single_sample(sample, strategies: dict[str, StrategyConfig]):
    """Run baseline + all strategy variants on one LongBench sample."""
    context = sample["context"]
    query = sample["query"]
    answers = sample["answers"]
    user_message = f"{context}\n\nQuestion: {query}"

    # Baseline
    print(f"  Baseline...", end="", flush=True)
    baseline = invoke_bedrock(user_message)
    baseline["cost"] = calculate_cost(baseline)
    baseline["f1"] = round(token_f1(baseline["output_text"], answers), 4)
    judge = llm_judge(query, answers, baseline["output_text"])
    baseline["judge"] = judge["verdict"]
    baseline["judge_cost"] = judge["judge_cost"]
    print(f" {baseline['input_tokens']:,} tokens, ${baseline['cost']:.4f}, "
          f"F1={baseline['f1']:.3f}, judge={baseline['judge']}")

    # Strategy variants
    results = {}
    for name, cfg in strategies.items():
        print(f"  {name}...", end="", flush=True)

        try:
            # Generic dispatch based on StrategyConfig flags
            if cfg.needs_query and cfg.needs_haiku_tracking:
                compressed_ctx, comp_metrics = track_haiku_cost(
                    cfg.compressor, context, query, **cfg.call_kwargs)
            elif cfg.needs_query:
                compressed_ctx, comp_metrics = cfg.compressor.compress_prompt(
                    context, query, **cfg.call_kwargs)
            elif cfg.needs_haiku_tracking:
                compressed_ctx, comp_metrics = track_haiku_cost(
                    cfg.compressor, context, **cfg.call_kwargs)
            else:
                compressed_ctx, comp_metrics = cfg.compressor.compress_prompt(
                    context, **cfg.call_kwargs)

            compressed_msg = f"{compressed_ctx}\n\nQuestion: {query}"
            result = invoke_bedrock(compressed_msg)

            sonnet_cost = calculate_cost(result)
            haiku_cost = comp_metrics.get("haiku_cost", 0)
            total_cost = sonnet_cost + haiku_cost

            # Evaluation: all three metrics
            f1 = round(token_f1(result["output_text"], answers), 4)
            rl = round(rouge_l(baseline["output_text"], result["output_text"]), 4)
            judge = llm_judge(query, answers, result["output_text"])

            results[name] = {
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "compression_pct": (1 - result["input_tokens"] / baseline["input_tokens"]) * 100,
                "sonnet_cost": sonnet_cost,
                "haiku_cost": haiku_cost,
                "total_cost": total_cost,
                "net_saving_pct": (baseline["cost"] - total_cost) / baseline["cost"] * 100,
                "output_text": result["output_text"],
                "rouge_l": rl,
                "f1": f1,
                "judge": judge["verdict"],
                "judge_cost": judge["judge_cost"],
            }
            print(f" {results[name]['compression_pct']:.1f}%, F1={f1:.3f}, "
                  f"judge={judge['verdict']}, ROUGE-L={rl:.3f}")

        except Exception as e:
            print(f" ERROR: {e}")
            results[name] = {"error": str(e)}

    return baseline, results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_sample_table(sample, baseline, results):
    dataset = sample["dataset"]
    idx = sample["index"]
    words = sample["context_words"]

    print(f"\n{'=' * 120}")
    print(f"LongBench {dataset} #{idx} (context: {words:,} words, {baseline['input_tokens']:,} tokens)")
    print(f"Q: {sample['query'][:90]}...")
    print(f"GT: {' | '.join(sample['answers'])[:90]}")
    print(f"{'=' * 120}")

    header = (
        f"{'Strategy':<25} | {'Input Tok':>9} | {'Compress%':>9} | "
        f"{'Net Cost':>8} | {'Net Save%':>9} | {'F1':>6} | {'Judge':>5} | {'ROUGE-L':>7}"
    )
    print(header)
    print("-" * 120)

    print(
        f"{'Baseline':<25} | {baseline['input_tokens']:>9,} | {'—':>9} | "
        f"${baseline['cost']:>7.4f} | {'—':>9} | "
        f"{baseline['f1']:>6.4f} | {baseline['judge']:>5} | {'1.0000':>7}"
    )

    for name, r in results.items():
        if "error" in r:
            print(f"{name:<25} | {'ERROR':>9} | {r['error'][:50]}")
            continue

        print(
            f"{name:<25} | {r['input_tokens']:>9,} | "
            f"{r['compression_pct']:>8.1f}% | "
            f"${r['total_cost']:>7.4f} | "
            f"{r['net_saving_pct']:>8.1f}% | "
            f"{r['f1']:>6.4f} | {r['judge']:>5} | "
            f"{r['rouge_l']:>7.4f}"
        )
    print("-" * 120)


def print_summary(all_results, all_baselines):
    """Print aggregated summary across all samples."""
    print(f"\n{'=' * 120}")
    print("AGGREGATE SUMMARY (averaged across all samples)")
    print(f"{'=' * 120}")

    # Baseline F1 and judge pass rate
    bl_f1s = [b["f1"] for b in all_baselines]
    bl_pass = sum(1 for b in all_baselines if b["judge"] == "YES")
    avg_bl_f1 = sum(bl_f1s) / len(bl_f1s)
    print(f"Baseline: Avg F1={avg_bl_f1:.4f}, Judge pass={bl_pass}/{len(all_baselines)}\n")

    strategy_names = []
    for _, results in all_results:
        for name in results:
            if name not in strategy_names and "error" not in results[name]:
                strategy_names.append(name)

    header = (
        f"{'Strategy':<25} | {'Avg Compress%':>13} | {'Avg Save%':>10} | "
        f"{'Avg F1':>7} | {'F1 Drop':>8} | {'Judge Pass':>10} | {'Avg ROUGE-L':>11}"
    )
    print(header)
    print("-" * 120)

    for name in strategy_names:
        comp_pcts, save_pcts, f1s, rouge_ls = [], [], [], []
        judge_yes = 0
        count = 0
        for _, results in all_results:
            if name in results and "error" not in results[name]:
                r = results[name]
                comp_pcts.append(r["compression_pct"])
                save_pcts.append(r["net_saving_pct"])
                f1s.append(r["f1"])
                rouge_ls.append(r["rouge_l"])
                if r["judge"] == "YES":
                    judge_yes += 1
                count += 1

        if not comp_pcts:
            continue

        avg_comp = sum(comp_pcts) / len(comp_pcts)
        avg_save = sum(save_pcts) / len(save_pcts)
        avg_f1 = sum(f1s) / len(f1s)
        avg_rl = sum(rouge_ls) / len(rouge_ls)
        f1_drop = avg_bl_f1 - avg_f1

        print(
            f"{name:<25} | {avg_comp:>12.1f}% | {avg_save:>9.1f}% | "
            f"{avg_f1:>7.4f} | {f1_drop:>+7.4f} | "
            f"{judge_yes}/{count:>9} | {avg_rl:>10.4f}"
        )

    print("-" * 120)
    print("\nF1 = token-level F1 vs ground truth (higher=better)")
    print("F1 Drop = baseline F1 - strategy F1 (positive=quality loss)")
    print("Judge Pass = Haiku binary YES/NO (correct answer?)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_strategies() -> dict[str, StrategyConfig]:
    """Build strategy registry: 3 strategies with parameter variants."""
    strategies: dict[str, StrategyConfig] = {}

    # --- LLMLingua-2 (BERT, local, zero cost) ---
    strategies["llmlingua2"] = StrategyConfig(
        compressor=OriginalLLMLingua2(rate=0.5))

    # --- SemanticSummarizer: vary max_length_ratio (cap removed) ---
    for ratio in [0.5, 0.6, 0.7, 0.8]:
        strategies[f"semantic_{ratio}"] = StrategyConfig(
            compressor=SemanticSummarizer(),
            call_kwargs={"max_length_ratio": ratio},
            needs_haiku_tracking=True)

    # --- RelevanceFilter: vary threshold + max_chunks ---
    for thresh, chunks in [(0.7, 10), (0.5, 20), (0.3, 30), (0.3, 50), (0.3, 80)]:
        rf = RelevanceFilter(similarity_threshold=thresh)
        strategies[f"relevance_t{thresh}_c{chunks}"] = StrategyConfig(
            compressor=rf,
            call_kwargs={"max_chunks": chunks},
            needs_query=True)

    return strategies


def run_benchmark():
    samples = load_longbench_samples()
    print(f"Loaded {len(samples)} LongBench samples:")
    for s in samples:
        print(f"  {s['dataset']}[{s['index']}]: {s['context_words']:,} words")
    print()

    strategies = build_strategies()
    print(f"{len(strategies)} strategy variants registered.\n")

    all_results = []
    all_baselines = []
    total_cost = 0

    for i, sample in enumerate(samples):
        print(f"\n--- Sample {i+1}/{len(samples)}: {sample['dataset']}[{sample['index']}] "
              f"({sample['context_words']:,} words) ---")

        baseline, results = run_single_sample(sample, strategies)
        all_results.append((baseline, results))
        all_baselines.append(baseline)

        # Track costs (including judge costs)
        total_cost += baseline["cost"] + baseline.get("judge_cost", 0)
        for r in results.values():
            if "error" not in r:
                total_cost += r["total_cost"] + r.get("judge_cost", 0)

        print_sample_table(sample, baseline, results)

    # Aggregate summary
    print_summary(all_results, all_baselines)

    # Total cost
    print(f"\nTotal Bedrock API cost: ${total_cost:.4f}")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    strategy_configs = {
        name: {
            "class": type(cfg.compressor).__name__,
            "call_kwargs": cfg.call_kwargs,
        }
        for name, cfg in strategies.items()
    }
    output = {
        "metadata": {
            "model": SONNET_MODEL_ID,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "num_samples": len(samples),
            "num_strategies": len(strategies),
            "dataset": "LongBench (multifieldqa_en + narrativeqa)",
            "total_cost": total_cost,
            "strategy_configs": strategy_configs,
        },
        "samples": [],
    }
    for (baseline, results), sample in zip(all_results, samples):
        sample_out = {
            "dataset": sample["dataset"],
            "index": sample["index"],
            "context_words": sample["context_words"],
            "query": sample["query"],
            "answers": sample["answers"],
            "baseline": {
                k: v for k, v in baseline.items() if k != "output_text"
            },
            "baseline_output": baseline["output_text"],
            "strategies": {},
        }
        for name, r in results.items():
            if "error" in r:
                sample_out["strategies"][name] = {"error": r["error"]}
            else:
                sample_out["strategies"][name] = {
                    k: v for k, v in r.items() if k != "output_text"
                }
                sample_out["strategies"][name]["output"] = r["output_text"]
        output["samples"].append(sample_out)

    results_path = RESULTS_DIR / "longbench_results.json"
    results_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Results saved to {results_path}")


if __name__ == "__main__":
    run_benchmark()
