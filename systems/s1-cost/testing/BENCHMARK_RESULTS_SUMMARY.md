# Compression Benchmark Results

## Experiment Setup

- **Baseline model**: Claude Sonnet 4 (Bedrock, temp=0)
- **Dataset**: LongBench (5 samples: 3 multifieldqa_en + 2 narrativeqa, 2K-10K words)
- **Evaluation**: Token F1 vs ground truth, LLM-as-judge (Haiku YES/NO), ROUGE-L vs baseline
- **Total cost**: $0.87 (two rounds)

Tested 6 strategies initially; narrowed to 3 with practical value after first round.

Dropped strategies:
- **ManualRefiner**: 4% compression on technical text (regex too simple)
- **StructureOptimizer**: quality collapse or minimal compression
- **LLMLingua (Haiku imitation)**: negative ROI (Haiku overhead > Sonnet savings)

## Results: 3 Strategies x 10 Parameter Variants

### Aggregate (5 LongBench samples)

| Strategy | Avg Compression | Avg Cost Saving | Judge Pass | Avg F1 | API Cost |
|---|---|---|---|---|---|
| **Baseline** | — | — | **4/5** | 0.055 | $0.038/call |
| **LLMLingua-2 (BERT)** | 38.0% | 34.4% | 3/5 | 0.073 | $0 |
| **RelevanceFilter t0.3_c30** | 84.2% | 76.3% | **4/5** | 0.091 | $0 |
| **RelevanceFilter t0.3_c50** | 72.2% | 63.5% | **4/5** | 0.081 | $0 |
| **RelevanceFilter t0.3_c80** | 54.3% | 48.2% | **4/5** | 0.059 | $0 |
| SemanticSummarizer 0.5 | 79.5% | 59.6% | 3/5 | 0.034 | ~$0.003 |
| SemanticSummarizer 0.6 | 83.6% | 66.1% | 1/5 | 0.040 | ~$0.003 |
| SemanticSummarizer 0.7 | 78.3% | 59.4% | 2/5 | 0.042 | ~$0.003 |
| SemanticSummarizer 0.8 | 81.4% | 64.4% | 3/5 | 0.041 | ~$0.003 |

### vs Literature

| Strategy | Our Data | Literature Reference | Verdict |
|---|---|---|---|
| LLMLingua-2 | 38% | 30-50% | Consistent |
| RelevanceFilter t0.3_c50 | 72% | 50-70% (Selective Context) | Slightly above, reasonable |
| SemanticSummarizer | 76-81% | 60-80% | Consistent |

## Key Findings

1. **RelevanceFilter t0.3_c30 is the clear winner**: 84% compression, matches baseline quality (4/5 judge pass), zero cost. TF-IDF + Jaccard chunk selection works surprisingly well.

2. **"Less is more" effect observed**: LLMLingua-2 and RelevanceFilter show *higher* F1 than baseline after compression (negative F1 drop). Removing noise helps the model focus.

3. **LLMLingua-2 is a reliable free baseline**: 38% compression, stable across samples (lowest variance), zero API cost. Uses local BERT model.

4. **SemanticSummarizer has inconsistent quality**: High compression but judge pass rate as low as 1/5. Haiku doesn't follow length instructions precisely — `max_length_ratio` parameter has limited effect.

5. **Compression cost matters**: For LLM-based compression (SemanticSummarizer), Haiku API cost eats into savings. Zero-cost local methods (LLMLingua-2, RelevanceFilter) have better ROI.

## Recommendations

| Scenario | Strategy | Why |
|---|---|---|
| Long context RAG with query | RelevanceFilter t0.3_c30-c50 | High compression, zero cost, query-aware |
| General compression (no query) | LLMLingua-2 (rate=0.5) | Stable, zero cost, works on any text |
| Maximum compression (quality trade-off acceptable) | SemanticSummarizer 0.5 | 80% compression, but verify output quality |

## Limitations

- Small sample size (n=5) — results are directional, not statistically significant
- Token F1 is low across the board due to Sonnet's verbose outputs vs short ground truth answers; relative comparisons are meaningful, absolute values are not
- RelevanceFilter requires a query; not applicable to query-free compression scenarios

## Files

- `benchmark/longbench_compare.py` — main benchmark script
- `benchmark/quick_compare.py` — single-prompt benchmark (system prompt + user message)
- `benchmark/llmlingua2_wrapper.py` — LLMLingua-2 BERT wrapper
- `benchmark/results/longbench_results.json` — full results with outputs
- `benchmark/results/compression_results.json` — quick_compare results
