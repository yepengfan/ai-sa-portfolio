---
date: 2026-03-12
plan: AISA
tags: [learning/AI-SA, benchmark, plan]
---

# Benchmark Plan: Bedrock Inference Optimization Strategies

## Goal

Run baseline + 5 compression techniques on a single prompt. Compare token savings and cost reduction. Validate experimental data against literature values.

Extend to caching, routing, and batch using the same prompt and methodology.

Final deliverable: a comparison table of **strategy / use case / measured savings / implementation complexity**.

---

## 1. Methodology

All strategies share the same methodology for comparability:

```
Same prompt → Apply optimization (or not) → Send to Sonnet (temp=0) → Record metrics → Compare to baseline
```

### Fixed Parameters

```python
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"  # from utils/config.py
PARAMS = {"temperature": 0, "max_tokens": 1024, "top_p": 1}
```

### Recorded Metrics

Each Bedrock invocation records (all from API response `usage` field):

| Metric | Source | Notes |
|--------|--------|-------|
| `input_tokens` | `response.usage.input_tokens` | Actual tokens sent after compression |
| `output_tokens` | `response.usage.output_tokens` | Model output tokens |
| `cost` | `input_tokens × input_price + output_tokens × output_price` | Calculated, deterministic |
| `output_text` | `response.content[0].text` | Stored for quality evaluation |

### Comparison Formulas

```
compression_ratio = 1 - (compressed_input_tokens / baseline_input_tokens)
cost_saving_pct   = (baseline_cost - compressed_cost) / baseline_cost × 100
```

For SemanticSummarizer and LLMLinguaCompressor (compression step calls Haiku):

```
net_cost    = compressed_inference_cost + compression_api_cost
net_saving  = baseline_cost - net_cost
```

---

## 2. Prompt Design

A single prompt with three parts. Designed to support subsequent caching tests (system prompt >= 1024 tokens).

### Structure

```
┌──────────────────────────────────┐
│  system_prompt (>=1024 tokens)   │  ← Cached prefix for future caching experiments
│  AWS SA role + 5 pillars +       │
│  service catalog + response fmt  │
├──────────────────────────────────┤
│  context (~800 tokens)           │  ← Realistic architecture description
│  VPC topology / service config / │
│  traffic patterns / current cost │
├──────────────────────────────────┤
│  query (~50 tokens)              │  ← Specific question
│  "Based on the architecture      │
│   above, suggest 3 cost          │
│   optimization strategies"       │
└──────────────────────────────────┘
```

### Design Rationale

| Part | Length | Reason |
|------|--------|--------|
| system_prompt | >= 1024 tokens | Bedrock prompt caching minimum threshold; reusable for later experiments |
| context | ~800 tokens | Long enough for compression to be meaningful; simulates real RAG scenarios |
| query | ~50 tokens | Short question so context is the primary compression target |

### Assembly

```python
# system_prompt goes into Bedrock API's system field
# context + query are concatenated as the user message
user_message = f"Given this architecture:\n{context}\n\nQuestion: {query}"
```

### Files

- `benchmark/system_prompt.txt` — system prompt text
- `benchmark/test_prompt.json` — context + query

---

## 3. Compression Experiment

### 5 Strategies Under Test

From code review (`strategies/compression/`):

| # | Strategy | Class | Interface | Requires Bedrock? |
|---|----------|-------|-----------|:-:|
| 1 | Manual Refiner | `ManualRefiner` | `compress_prompt(text) → (compressed, metrics)` | No |
| 2 | Semantic Summarizer | `SemanticSummarizer` | `compress_prompt(text) → (compressed, metrics)` | Yes (Haiku) |
| 3 | Relevance Filter | `RelevanceFilter` | `compress_prompt(text, query) → (compressed, metrics)` | No |
| 4 | Structure Optimizer | `StructureOptimizer` | `compress_prompt(text) → (compressed, metrics)` | No |
| 5 | LLMLingua Compressor | `LLMLinguaCompressor` | `compress_prompt(text) → (compressed, metrics)` | Yes (Haiku) |

Additionally, real LLMLingua-2 (local BERT model, zero API cost) was added as a 6th strategy.

> Note: RelevanceFilter requires an additional `query` parameter (to determine which context chunks are relevant). All others take only text.

**Tracking Haiku compression cost**: SemanticSummarizer and LLMLinguaCompressor call Haiku internally. A `track_haiku_cost()` wrapper monkey-patches `compressor.client.invoke_model` to intercept Haiku calls and capture token usage.

### Two Benchmark Modes

1. **quick_compare.py** — Single custom prompt (system_prompt + context + query), measures compression with system prompt denominator correction
2. **longbench_compare.py** — 5 LongBench samples (multifieldqa_en + narrativeqa), parameter sweep across strategy variants, evaluates with Token F1 + LLM-as-judge + ROUGE-L

### Evaluation (LongBench)

| Metric | Compares Against | Measures | Reliability |
|--------|-----------------|----------|-------------|
| **LLM-as-judge** (Haiku YES/NO) | Ground truth | Semantic correctness | High |
| **Token F1** (SQuAD-style) | Ground truth | Answer token overlap | Medium |
| **ROUGE-L** | Baseline output | Output consistency | Low (surface similarity only) |

### Run Commands

```bash
cd systems/s1-cost
python -m benchmark.quick_compare          # single-prompt benchmark
uv run python -m benchmark.longbench_compare   # LongBench benchmark
```

### File Structure

```
systems/s1-cost/
├── benchmark/
│   ├── __init__.py
│   ├── system_prompt.txt
│   ├── test_prompt.json
│   ├── quick_compare.py
│   ├── longbench_compare.py
│   ├── llmlingua2_wrapper.py
│   ├── data/                        # LongBench datasets (gitignored)
│   │   ├── multifieldqa_en.jsonl
│   │   └── narrativeqa.jsonl
│   └── results/
│       ├── compression_results.json
│       └── longbench_results.json
├── strategies/compression/
│   ├── manual_refiner.py
│   ├── semantic_summarizer.py
│   ├── relevance_filter.py
│   ├── structure_optimizer.py
│   └── llmlingua_compressor.py
└── utils/config.py
```

### Literature Reference Values

| Strategy | Literature Range | Source |
|----------|-----------------|--------|
| Manual refinement | 30-50% | freeCodeCamp |
| Semantic summarization | 40-60% | ML Mastery |
| Relevance filtering | 50-70% | Towards Data Science |
| Structure optimization | 20-40% | General |
| LLMLingua | up to 20x | Original paper (Microsoft, 2023) |

---

## 4. Future Extensions

Extend to 3 additional strategies using the same prompt. Same methodology: same prompt → apply optimization → send to Bedrock → compare to baseline.

| Strategy | What to Do | New Code Needed? |
|----------|-----------|:-:|
| Caching | Send the same request twice (cold → warm), check `cacheReadInputTokens` in API response | Add `cache_control` parameter to invoke_bedrock |
| Routing | Use ModelRouter to assess complexity, route to Haiku or Sonnet | Call existing `model_routing.py` |
| Batch | No API call needed — calculate using baseline token counts × batch pricing | Pure math |

Extensions only require adding functions to the benchmark scripts; no changes to the experiment framework.

---

## 5. Acceptance Criteria

### Compression Experiment

| Criterion | Pass Condition |
|-----------|---------------|
| Script runs | `python -m benchmark.quick_compare` completes without errors |
| All strategies covered | Each has input_tokens, compression_ratio, cost |
| Data source is correct | Token counts come from Bedrock API response, not local estimates |
| Net saving is correct | SemanticSummarizer and LLMLingua savings account for Haiku compression cost |
| Comparable to literature | Output includes literature reference values for comparison |
| Reproducible | Re-running produces identical token counts and costs (temp=0) |
