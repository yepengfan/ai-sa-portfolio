# System S1: Cost Optimization

**AI SA Portfolio Monorepo > Systems > S1-Cost**

Comprehensive implementation of 4 Bedrock optimization strategies for cost reduction and performance improvement.

> **Note**: This system is part of the AI SA Portfolio monorepo. Navigate to `../../README.md` for overall architecture documentation.

## 🎯 System Overview

This project implements and evaluates all major Bedrock optimization strategies:

1. **Prompt Compression** (5 techniques)
2. **Prompt Caching** (Bedrock native)
3. **Model Routing** (Intelligence-based)
4. **Batch Processing** (Non-realtime optimization)

The implementation prioritizes research needs, providing comprehensive metrics collection and data export for academic comparison tables.

## 📁 Project Structure

```
├── chat.py                          # Original baseline implementation
├── enhanced_chat.py                 # Main enhanced chat with all strategies
├── test_implementation.py           # Test script to verify functionality
├── strategies/
│   ├── compression/
│   │   ├── manual_refiner.py            # Manual text refinement
│   │   ├── semantic_summarizer.py       # AI-powered summarization
│   │   ├── relevance_filter.py          # Context relevance filtering
│   │   ├── structure_optimizer.py       # Structure optimization
│   │   └── llmlingua_compressor.py      # Token-level compression
│   ├── prompt_caching.py           # Bedrock native prompt caching
│   ├── model_routing.py             # Intelligent model selection
│   └── batch_processing.py         # Batch inference management
├── experiment/
│   ├── metrics_collector.py        # Comprehensive metrics system
│   └── data_exporter.py            # Research data export tools
├── utils/
│   └── config.py                   # Configuration and constants
└── results/                        # Generated experiment results
    ├── *_results.csv               # Strategy-specific results
    ├── strategy_comparison.csv     # Cross-strategy comparison
    └── research_summary.json       # Executive summary
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# From ai-platform root directory
cd systems/s1-cost

# Install dependencies
uv sync

# Ensure AWS credentials are configured
aws configure
```

### 2. Run Tests

```bash
uv run python test_implementation.py
```

### 3. Run Enhanced Chat

```bash
uv run python enhanced_chat.py
```

### 4. Run Baseline (Original)

```bash
uv run python chat.py
```

## 📊 Strategy Details

### Strategy 1: Prompt Compression

Five distinct compression techniques:

#### 1.1 Manual Refiner (`manual`)
- **Method**: Rule-based text processing, redundancy removal
- **Expected Savings**: 30-50%
- **Best For**: Simple text compression, repeated queries
- **Implementation**: `strategies/compression/manual_refiner.py`

#### 1.2 Semantic Summarizer (`semantic`)
- **Method**: AI-powered summarization preserving meaning
- **Expected Savings**: 40-60%
- **Best For**: Long context windows, verbose inputs
- **Implementation**: `strategies/compression/semantic_summarizer.py`

#### 1.3 Relevance Filter (`relevance`)
- **Method**: Keep only context relevant to current query
- **Expected Savings**: 50-70%
- **Best For**: Large context with specific queries
- **Implementation**: `strategies/compression/relevance_filter.py`

#### 1.4 Structure Optimizer (`structure`)
- **Method**: Convert to JSON/bullet points for efficiency
- **Expected Savings**: 20-40%
- **Best For**: Structured data, lists, key-value pairs
- **Implementation**: `strategies/compression/structure_optimizer.py`

#### 1.5 LLMLingua Compressor (`llmlingua`)
- **Method**: Token-level compression using small model analysis
- **Expected Savings**: Up to 20x compression
- **Best For**: High compression needs, token-sensitive apps
- **Implementation**: `strategies/compression/llmlingua_compressor.py`

### Strategy 2: Prompt Caching (`prompt_caching`)

- **Method**: Bedrock native prompt caching
- **Expected Savings**: 90% discount on cache reads
- **Best For**: Repeated system prompts, multi-turn conversations
- **Features**: Configurable TTL (5min/1hr), automatic cache management
- **Implementation**: `strategies/prompt_caching.py`

### Strategy 3: Model Routing (`model_routing`)

- **Method**: Route simple→Haiku, complex→Sonnet based on analysis
- **Expected Savings**: 30-50% on simple queries
- **Best For**: Mixed workloads, cost-sensitive applications
- **Analysis Methods**: Keywords, structure, context, technical content
- **Implementation**: `strategies/model_routing.py`

### Strategy 4: Batch Processing (`batch_processing`)

- **Method**: Bedrock Batch Inference for non-realtime processing
- **Expected Savings**: 10-20% throughput improvement + batch discounts
- **Best For**: Offline processing, bulk operations, non-realtime scenarios
- **Features**: S3 integration, job monitoring, queue management
- **Implementation**: `strategies/batch_processing.py`

## 🔬 Research Features

### Comprehensive Metrics Collection

Every query captures:
- **Cost Metrics**: Input/output token costs, total session costs
- **Performance Metrics**: Latency, processing overhead
- **Quality Metrics**: Response accuracy, context preservation
- **Strategy-Specific**: Compression ratios, cache hit rates, routing decisions

### Data Export for Research

- **CSV Export**: Structured data for statistical analysis
- **JSON Export**: Programmatic data access
- **Comparison Tables**: Strategy-vs-strategy analysis
- **Research Summary**: Executive findings with recommendations

### Statistical Analysis

- Mean, median, standard deviation for all metrics
- Percentage improvements vs baseline
- Strategy suitability assessments
- Implementation complexity ratings

## 💬 Usage Examples

### Interactive Strategy Selection

```bash
python enhanced_chat.py
```

```
Available Optimization Strategies:
1. Prompt Compression:
   • manual - Manual text refinement
   • semantic - AI-powered summarization
   • relevance - Context relevance filtering
   • structure - Structure optimization
   • llmlingua - Token-level compression

2. prompt_caching - Bedrock native prompt caching
3. model_routing - Intelligent model selection
4. batch_processing - Queue for batch inference

Strategies: manual prompt_caching model_routing
✅ Active strategies: compression, prompt_caching, model_routing
   Compression method: manual
```

### Strategy Combinations

```python
# Example combinations for different use cases:

# Cost-focused setup
strategies = ['manual', 'prompt_caching', 'model_routing']

# Quality-focused setup
strategies = ['semantic', 'prompt_caching']

# High-compression setup
strategies = ['llmlingua', 'relevance']

# Batch processing setup
strategies = ['structure', 'batch_processing']
```

### Baseline Comparison

```python
# Run baseline first
python chat.py  # Original implementation

# Then run optimized version
python enhanced_chat.py  # With strategies enabled

# Export comparison data
# In enhanced chat: type 'export' to generate CSV/JSON
```

## 📈 Expected Research Outcomes

### Comparison Table Data Points

For each strategy combination:
- **Implementation Complexity**: Development effort, lines of code
- **Cost Savings**: Percentage reduction in token costs
- **Latency Impact**: Response time changes (+/-)
- **Suitable Scenarios**: Query types that benefit most
- **Quality Impact**: Response quality preservation

### Success Metrics Targets

- **Prompt Compression**: 20-40% token reduction
- **Prompt Caching**: 90% cost reduction on cache hits
- **Model Routing**: 30-50% cost savings on simple queries
- **Batch Processing**: 10-20% throughput improvement

## 🛠️ Implementation Notes

### AWS Setup Required

```bash
# Ensure proper AWS credentials and region
export AWS_REGION=us-east-1
aws configure list
```

### S3 Bucket for Batch Processing

The batch processing strategy automatically creates S3 buckets as needed, but you can specify custom buckets:

```python
batch_processor = BedrockBatchProcessor(s3_bucket="my-bedrock-batch-bucket")
```

### Model Access

Ensure you have access to required Bedrock models:
- Claude Haiku 4.5: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- Claude Sonnet 3.5: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`

### Inference Profiles

The baseline `chat.py` uses inference profiles. The enhanced version supports both inference profiles and on-demand model access.

## 📊 Data Analysis

### Export Research Data

```python
# In enhanced_chat.py interactive session:
# Type 'export' to generate:
# - strategy_name_results.csv
# - strategy_name_results.json
# - strategy_comparison.csv (if multiple strategies tested)
```

### Statistical Analysis

```python
from experiment.data_exporter import ResearchDataExporter

exporter = ResearchDataExporter()
exporter.export_strategy_comparison(baseline_metrics, strategy_results)
exporter.export_detailed_analysis(strategy_results)
exporter.generate_research_summary(baseline_metrics, strategy_results)
```

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all files are in correct directories
2. **Bedrock Access**: Check AWS credentials and model access
3. **S3 Permissions**: Ensure S3 read/write permissions for batch processing
4. **Token Limits**: Some compression strategies may hit token limits

### Debug Mode

```python
# Enable verbose logging in enhanced_chat.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Research Applications

This implementation is designed for:
- **Academic Research**: Comprehensive metrics for optimization analysis
- **Cost Analysis**: Real-world cost savings measurement
- **Performance Benchmarking**: Latency and throughput comparisons
- **Strategy Evaluation**: Determining optimal strategies for different use cases

## 🤝 Contributing

To extend this implementation:

1. **Add New Compression Techniques**: Extend `strategies/compression/`
2. **Enhance Routing Logic**: Modify `strategies/model_routing.py`
3. **Add Metrics**: Update `experiment/metrics_collector.py`
4. **Improve Analysis**: Extend `experiment/data_exporter.py`

## 📄 License

This is an educational implementation for AISA Week 11 research. Use responsibly and in accordance with AWS service terms.
