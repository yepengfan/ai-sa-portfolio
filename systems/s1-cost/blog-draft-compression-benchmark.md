# Benchmarking 5 Prompt Compression Techniques on Amazon Bedrock: What Actually Saves Money?

Prompt compression is one of the most direct ways to reduce LLM inference costs — shorter inputs mean fewer tokens billed. The literature promises impressive numbers: 30-50% compression from LLMLingua, 50-70% from selective context filtering, 60-80% from summarization. But how do these techniques perform in practice when measured against a real model on a real API?

I built and tested 5 prompt compression strategies on Amazon Bedrock (Claude Sonnet 4), ran them against the LongBench academic benchmark, and discovered that the simplest approaches often outperform the sophisticated ones.

## The 5 Compression Strategies

All five strategies share the same interface: take a text input, return a compressed version plus metrics. They differ fundamentally in *how* they decide what to keep and what to discard.

### 1. Manual Refiner — Regex-Based Text Cleanup

The simplest approach. Uses regular expressions to strip filler words, collapse whitespace, remove redundant phrases, and shorten common patterns. No ML, no API calls, purely mechanical.

```
Input:  "In order to effectively optimize the overall system performance..."
Output: "To optimize system performance..."
```

**Cost**: Zero. Runs locally with regex.

### 2. Semantic Summarizer — LLM-Powered Summarization

Sends the text to a cheaper model (Claude Haiku 4.5) with instructions to summarize while preserving key information. A `max_length_ratio` parameter controls the target compression level.

```
Input:  [800-word architecture description]
→ Haiku prompt: "Summarize to ~50% of original length, preserve technical details"
Output: [~200-word summary]
```

**Cost**: ~$0.003 per compression call (Haiku input + output tokens).

### 3. Relevance Filter — TF-IDF + Jaccard Chunk Selection

Splits the context into fixed-size chunks (~200 characters), scores each chunk's relevance to the user's query using TF-IDF cosine similarity and Jaccard overlap, then keeps only the top-scoring chunks. Two parameters control the behavior: `similarity_threshold` (minimum quality gate) and `max_chunks` (maximum quantity cap).

```
Input:  [10,000-word document] + query: "Where does the witch live?"
→ Score each chunk against query
→ Keep top 30 chunks above threshold 0.3
Output: [~2,000 words of most relevant passages]
```

**Cost**: Zero. TF-IDF and Jaccard are computed locally.

### 4. Structure Optimizer — Format Conversion

Converts prose into structured formats (JSON, bullet points, or markdown tables). The idea is that structured formats convey the same information in fewer tokens.

```
Input:  "The system uses three EC2 instances of type m5.xlarge running in us-east-1..."
Output: {"instances": {"type": "m5.xlarge", "count": 3, "region": "us-east-1"}}
```

**Cost**: Zero. Rule-based transformation.

### 5. LLMLingua Compressor — LLM Token Pruning

Inspired by the LLMLingua paper (Microsoft, 2023), this strategy uses a language model to score token importance and prune low-information tokens. Our initial implementation used Claude Haiku as the scoring model (approximating the approach). We later added real LLMLingua-2, which uses a fine-tuned BERT model (`microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank`) running locally on CPU.

```
Input:  "The normalized least mean square algorithm is engaged in the PLMS-PPIC method"
→ BERT scores each token's importance
→ Prune tokens below threshold (rate=0.5)
Output: "normalized least mean square algorithm engaged PLMS-PPIC method"
```

**Cost**: Haiku version ~$0.002/call. BERT version: zero (local inference).

## First Round: Why We Dropped Two Strategies

We ran all 5 strategies (plus real LLMLingua-2) on a custom prompt — an AWS Solutions Architect scenario with a ~1,800-token system prompt and ~800-token architecture context, evaluated against Claude Sonnet 4.

The results immediately revealed two strategies with limited practical value:

**Manual Refiner achieved only 4% compression** on technical text. Regex patterns designed for conversational filler ("in order to", "it is important to note that") barely match in architecture descriptions full of proper nouns and precise specifications. The approach works in theory but breaks down on domain-specific content.

**Structure Optimizer produced either quality collapse or minimal compression.** Converting technical prose to JSON sometimes discarded critical context, and for already-structured text (bullet points, numbered lists), there was nothing to optimize.

**LLMLingua (Haiku version) had negative ROI.** The Haiku API cost for scoring and pruning exceeded the Sonnet savings from the compression. Using an LLM to compress prompts sent to another LLM only makes economic sense if the compression model is dramatically cheaper — which Haiku is, but not by enough at low compression rates.

This left three strategies worth deeper investigation:

| Strategy | Why it survived |
|---|---|
| **LLMLingua-2 (BERT)** | Real token-level pruning, zero cost, literature backing |
| **RelevanceFilter** | High compression on long contexts, zero cost, query-aware |
| **SemanticSummarizer** | Highest compression potential, established technique |

## Experiment Design

### Dataset: LongBench

We used [LongBench](https://github.com/THUDM/LongBench), a standard academic benchmark for long-context understanding. We selected 5 samples across two task types:

- **multifieldqa_en** (3 samples, 2K-8K words): Factual question answering over academic papers
- **narrativeqa** (2 samples, 5K-10K words): Comprehension questions about literary texts

Each sample includes a long context, a question, and ground truth answers — enabling quality evaluation beyond just compression ratios.

### Parameter Sweep

We tested 10 strategy variants to find optimal configurations:

- **LLMLingua-2**: rate=0.5 (single config, BERT-based)
- **SemanticSummarizer**: 4 ratios (0.5, 0.6, 0.7, 0.8)
- **RelevanceFilter**: 5 threshold/chunk combinations (t0.7/c10, t0.5/c20, t0.3/c30, t0.3/c50, t0.3/c80)

### Evaluation

Three complementary metrics:

1. **LLM-as-judge** (primary): Haiku reads the question, ground truth answer, and model output, then returns YES/NO on correctness. Most interpretable — directly answers "did compression break the answer?"
2. **Token F1** (secondary): Standard SQuAD-style token overlap between model output and ground truth. Measures whether key answer tokens appear in the output.
3. **ROUGE-L** (reference): Longest common subsequence between compressed and baseline outputs. Measures output consistency rather than correctness.

### Baseline

All compressed outputs are compared against uncompressed Sonnet 4 output (temperature=0). The baseline itself scores 4/5 on judge pass rate — one question (about the Kondo effect in superconductivity) was too nuanced for even the full-context model to answer correctly per the ground truth.

## Results

### The Numbers

| Strategy | Compression | Cost Saving | Judge Pass | API Cost |
|---|---|---|---|---|
| **Baseline (no compression)** | — | — | **4/5** | $0.038/call |
| LLMLingua-2 (BERT) | 38.0% | 34.4% | 3/5 | **$0** |
| RelevanceFilter t0.3_c30 | 84.2% | 76.3% | **4/5** | **$0** |
| RelevanceFilter t0.3_c50 | 72.2% | 63.5% | **4/5** | **$0** |
| RelevanceFilter t0.3_c80 | 54.3% | 48.2% | **4/5** | **$0** |
| SemanticSummarizer 0.5 | 79.5% | 59.6% | 3/5 | ~$0.003 |
| SemanticSummarizer 0.6 | 83.6% | 66.1% | 1/5 | ~$0.003 |
| SemanticSummarizer 0.7 | 78.3% | 59.4% | 2/5 | ~$0.003 |
| SemanticSummarizer 0.8 | 81.4% | 64.4% | 3/5 | ~$0.003 |

### Compression Rates vs Literature

| Strategy | Our Data | Literature Reference | Verdict |
|---|---|---|---|
| LLMLingua-2 | 38% | 30-50% | Consistent |
| RelevanceFilter | 54-84% | 50-70% (Selective Context) | Consistent to slightly above |
| SemanticSummarizer | 76-81% | 60-80% | Consistent |

## Key Insights

### 1. RelevanceFilter is the surprise winner

RelevanceFilter t0.3_c30 compressed 84% of the context while maintaining the same answer quality as the uncompressed baseline (4/5 judge pass). The technique is conceptually simple — TF-IDF + Jaccard scoring on text chunks — but it works because most long documents contain large amounts of information irrelevant to the specific question being asked.

The key insight: **query-aware compression fundamentally outperforms query-agnostic compression** for QA tasks. If you know what the user is asking, you can aggressively discard everything else.

### 2. Compression can improve output quality

Both LLMLingua-2 and RelevanceFilter showed *higher* Token F1 scores than the uncompressed baseline. This "less is more" effect has been documented in the literature — removing noise helps the model focus on relevant information rather than getting distracted by irrelevant context.

### 3. LLM-based compression has a cost problem

SemanticSummarizer achieves high compression rates (76-81%) but each compression call costs ~$0.003 in Haiku API fees. For a Sonnet call averaging $0.038, that's an 8% overhead eating into savings. More critically, the Haiku model doesn't reliably follow length instructions — setting `max_length_ratio` to 0.5 vs 0.8 produces outputs differing by only ~5 percentage points in compression, because the model generates what it considers a "good summary" regardless of the target length.

### 4. Zero-cost methods have the best ROI

LLMLingua-2 (local BERT) and RelevanceFilter (local TF-IDF) both achieve meaningful compression with zero API cost. Every token they remove translates directly to savings on the inference call. This makes them strictly dominant over API-based compression for most use cases.

### 5. One metric isn't enough

ROUGE-L against baseline output (our initial evaluation method) produced universally low scores (0.25-0.40) that were hard to interpret. Adding Token F1 against ground truth and LLM-as-judge revealed that many "low ROUGE-L" outputs were actually correct answers, just worded differently. The judge metric proved most actionable: "Did the compressed prompt still produce a correct answer? Yes or No."

## Practical Recommendations

**If you have a query and long context** (RAG, document QA): Use RelevanceFilter with a low similarity threshold (0.3) and tune `max_chunks` based on your quality tolerance. Start with 30-50 chunks.

**If you need general-purpose compression** (no query available): Use LLMLingua-2 with rate=0.5. It's stable, free, and works on any text type.

**If you need maximum compression and can tolerate quality variance**: SemanticSummarizer achieves 80%+ compression, but verify outputs — it drops critical information in ~40-80% of cases depending on configuration.

## Limitations

This experiment used 5 LongBench samples — enough to identify trends and validate against literature, but not enough for statistical significance. The RelevanceFilter's strong performance may partly reflect the QA-oriented nature of our test data, where query relevance is a strong signal. Results on open-ended generation tasks may differ.

---

*Experiment code and full results are available in the [ai-sa-portfolio](https://github.com/yepengfan/ai-sa-portfolio) repository under `systems/s1-cost/benchmark/`.*
