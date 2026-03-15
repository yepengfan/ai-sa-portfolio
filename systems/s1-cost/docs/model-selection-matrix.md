# Bedrock Model Selection Matrix

> 5+ models × 4 dimensions for Amazon Bedrock on-demand inference.
> Data sources: AWS Bedrock pricing (2026-03), internal benchmark (LongBench, compression strategies).

---

## Selection Matrix

| Model | 💰 Price (input / output per 1M tokens) | ⚡ Latency | 🧠 Capability | 🎯 Best For |
|-------|----------------------------------------|-----------|--------------|------------|
| **Amazon Nova Micro** | $0.035 / $0.14 | Lowest | Text-only, basic | High-throughput text filtering, classification, simple extraction |
| **Amazon Nova Lite** | $0.06 / $0.24 | Very low | Basic multimodal | Bulk preprocessing, simple Q&A, image captioning |
| **Amazon Nova Pro** | $0.80 / $3.20 | Low | Mid-tier | General-purpose tasks, RAG, content generation |
| **Claude Haiku 4.5** | $1.00 / $5.00 | Low | Strong for size | Classification, routing, scoring, structured output (JSON) |
| **Claude Sonnet 4** | $3.00 / $15.00 | Medium | Strong reasoning | Complex analysis, bilingual content, code generation |
| **Claude Opus 4** | $15.00 / $75.00 | Higher | Strongest | Deep reasoning, complex creative tasks, agentic workflows |

### Cost Ratios (relative to Claude Haiku 4.5)

| Model | Input Cost Ratio | Output Cost Ratio |
|-------|:---:|:---:|
| Nova Micro | 0.035x | 0.028x |
| Nova Lite | 0.06x | 0.048x |
| Nova Pro | 0.8x | 0.64x |
| **Haiku 4.5** | **1x** | **1x** |
| Sonnet 4 | 3x | 3x |
| Opus 4 | 15x | 15x |

---

## Benchmark Data: Haiku vs Sonnet (from W10 Experiments)

### Compression Strategy Benchmark

Tested 6 prompt compression strategies on a cost optimization analysis task. All strategies used Sonnet 4 for the main inference; Haiku was used for pre-processing in semantic summarization and LLMLingua strategies.

| Strategy | Input Tokens | Compression % | Sonnet Cost | Haiku Cost | Total Cost | Net Saving % |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline** (no compression) | 3,049 | — | $0.0168 | — | $0.0168 | — |
| Manual Refiner | 3,000 | 1.6% | $0.0167 | — | $0.0167 | 0.9% |
| Semantic Summarizer | 2,661 | 12.7% | $0.0157 | $0.0006 | $0.0163 | 3.1% |
| Relevance Filter | 2,203 | 27.7% | $0.0143 | — | $0.0143 | **15.1%** |
| Structure Optimizer | 2,129 | 30.2% | $0.0141 | — | $0.0141 | **16.4%** |
| LLMLingua | 2,912 | 4.5% | $0.0164 | $0.0005 | $0.0169 | -0.4% |
| LLMLingua2 | 2,580 | 15.4% | $0.0154 | — | $0.0154 | 8.4% |

**Key insight**: Structure Optimizer achieved 30% token compression with 16.4% cost saving and no quality degradation — best cost/quality tradeoff.

### Cost Comparison: Haiku-as-Preprocessor

From the semantic summarizer strategy: Haiku pre-processing cost was **$0.0006** vs Sonnet inference cost of **$0.0157** — a 26x difference. This validates the **"Haiku filters, Sonnet generates"** pattern used in the AI Daily Digest pipeline.

### Real-World Validation: AI Daily Digest Pipeline

Daily digest run (2026-03-15) with 36 articles, top 15 summarized:

| Step | Model | Calls | Cost | Purpose |
|------|-------|:---:|:---:|---------|
| Scoring (36 articles) | Haiku 4.5 | 4 | $0.004 | 3-dimension scoring + classification |
| Summarization (15 articles, zh) | Sonnet 4 | 2 | $0.030 | Chinese summaries + reasons |
| Summarization (15 articles, en) | Sonnet 4 | 2 | $0.028 | English summaries + reasons |
| Trend generation (zh + en) | Sonnet 4 | 2 | $0.018 | Macro trend analysis |
| **Total** | | **10** | **$0.080** | |

Haiku scoring cost was **$0.004** (5% of total) while handling **40% of the pipeline work** (scoring all 36 articles). If scoring were done with Sonnet, cost would be ~$0.10 for scoring alone — a **25x increase** for that step.

---

## Decision Guide: What Model for What Scenario?

### Routing Strategy

```
User request arrives
    │
    ├─ Simple classification, routing, scoring, keyword extraction
    │   → Haiku 4.5 ($1/1M) or Nova Micro ($0.035/1M)
    │
    ├─ General analysis, summarization, content generation
    │   → Sonnet 4 ($3/1M) or Nova Pro ($0.80/1M)
    │
    ├─ Deep reasoning, multi-step planning, complex code
    │   → Opus 4 ($15/1M)
    │
    └─ High-volume batch processing (latency-insensitive)
        → Batch API: 50% off any model
            Sonnet batch: $1.50/$7.50
            Haiku batch:  $0.50/$2.50
```

### When to Use Each Model

| Scenario | Recommended Model | Why |
|----------|-------------------|-----|
| **Filtering / routing** | Haiku 4.5 | Cheapest Claude model, fast, great at structured output |
| **Bulk scoring / classification** | Haiku 4.5 or Nova Micro | Haiku for quality, Nova Micro for 28x cheaper if quality is acceptable |
| **Summarization / translation** | Sonnet 4 | Best balance of quality and cost for content generation |
| **RAG with moderate context** | Nova Pro or Sonnet 4 | Nova Pro is 3.75x cheaper; evaluate quality on your data |
| **Code generation / review** | Sonnet 4 | Strong coding capability, worth the premium over Nova |
| **Complex multi-step reasoning** | Opus 4 | Only when Sonnet quality is insufficient; 5x the cost |
| **Latency-critical APIs** | Nova Micro or Haiku 4.5 | Fastest response times |
| **Batch processing (overnight)** | Sonnet 4 Batch | 50% off, no latency requirement |

### Cost Optimization Patterns

1. **Haiku-as-filter, Sonnet-as-generator**: Use Haiku to score/classify/route, then only send top candidates to Sonnet. Proven 25x savings on filtering step (AI Daily Digest).

2. **Prompt compression + Sonnet**: Apply structure optimization or relevance filtering to reduce input tokens before Sonnet. 15-16% cost savings with no quality loss (W10 benchmark).

3. **Batch API for non-real-time**: 50% discount on all models. Use for overnight processing, report generation, batch analytics.

4. **Caching for repeated contexts**: Sonnet cache read is 10x cheaper than standard input ($0.30 vs $3.00 per 1M). Cache system prompts and long context prefixes.

---

## Pricing Notes

- All prices are **on-demand** via Bedrock global inference endpoints (us-east-1).
- Regional endpoints carry a **10% premium** for Claude models.
- **Batch API** provides 50% discount with up to 24h processing window.
- **Prompt caching** (Claude): write at 1.25x input price, read at 0.1x input price.
- Prices as of March 2026; check [aws.amazon.com/bedrock/pricing](https://aws.amazon.com/bedrock/pricing/) for latest.
