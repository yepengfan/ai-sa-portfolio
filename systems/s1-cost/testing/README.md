# Compression Strategy Testing Framework

A comprehensive benchmark suite for evaluating and comparing 5 different prompt compression techniques.

## 🎯 Compression Strategies Tested

1. **SemanticSummarizer** - AI-powered summarization using Claude Haiku
2. **RelevanceFilter** - Content filtering based on query relevance
3. **StructureOptimizer** - Format optimization (JSON, bullets, etc.)
4. **LLMLinguaCompressor** - Token-level optimization inspired by LLMLingua
5. **ManualRefiner** - Rule-based text refinement and redundancy removal

## 🚀 Quick Start

### Prerequisites

1. **AWS Credentials**: Configure AWS credentials for Bedrock access
```bash
aws configure
```

2. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

### Run the Benchmark

```bash
# Simple execution
python run_benchmark.py

# Or run the benchmark directly
python compression_benchmark.py
```

### Analyze Results

```bash
# Generate visualizations and detailed report
python analyze_results.py

# Skip visualizations (faster)
python analyze_results.py --no-viz

# Specify custom results directory
python analyze_results.py --results-dir my_results/
```

## 📊 Test Datasets

The benchmark uses diverse test cases:

- **Short Queries** (3 tests): Simple questions and requests
- **Medium Prompts** (3 tests): Detailed instructions and explanations
- **Long Contexts** (2 tests): Comprehensive guides and analysis requests
- **Conversation Contexts** (1 test): Follow-up discussions with history

## 📈 Metrics Evaluated

### Performance Metrics
- **Compression Ratio**: `compressed_length / original_length`
- **Compression Savings**: `(1 - compression_ratio) × 100%`
- **Processing Time**: Time to compress each prompt
- **Success Rate**: Percentage of successful compressions
- **Effectiveness Score**: Combined metric (lower = better)

### Output Analysis
- Strategy rankings by multiple criteria
- Use case recommendations
- Detailed performance comparisons
- Visual charts and heatmaps

## 📁 Output Files

After running the benchmark, you'll find:

```
benchmark_results/
├── comprehensive_benchmark_results.json    # Complete results
├── strategy_comparison.csv                 # Summary table
├── {strategy_name}_results.json           # Individual strategy details
├── benchmark_report.md                    # Detailed analysis report
├── compression_benchmark_analysis.png     # Performance charts
└── strategy_heatmap.png                  # Comparison heatmap
```

## 🎯 Strategy Recommendations by Use Case

Based on typical benchmark results:

| Use Case | Recommended Strategy | Reasoning |
|----------|---------------------|-----------|
| **Real-time Applications** | Manual Refiner | Fastest processing, reliable |
| **Maximum Compression** | Semantic Summarizer | Highest compression ratios |
| **Production Systems** | Structure Optimizer | Best reliability and consistency |
| **Batch Processing** | LLMLingua Compressor | Good compression with acceptable speed |
| **Cost Optimization** | Semantic Summarizer | Maximum token savings |

## 🔧 Customization

### Adding New Test Cases

Edit the `_create_test_datasets()` method in `CompressionBenchmark`:

```python
"custom_category": [
    {
        "name": "my_test",
        "text": "Your test prompt here...",
        "query": "relevant query",
        "category": "custom"
    }
]
```

### Adding New Strategies

1. Implement your strategy with a `compress_prompt()` method
2. Add to the `strategies` dict in `CompressionBenchmark.__init__()`
3. Update the method dispatch logic in `_run_single_test()`

### Custom Metrics

Extend the `_calculate_performance_metrics()` method to add your own evaluation criteria.

## 🏆 Interpreting Results

### Effectiveness Score
- **Lower is better** (combines compression ratio and processing time)
- Weights: 70% compression ratio, 30% processing speed
- Best overall balance of performance factors

### Compression Savings
- **Higher is better** (percentage of original text removed)
- Directly correlates to token cost savings
- Target: >30% for meaningful impact

### Processing Time
- **Lower is better** (seconds per prompt)
- Critical for real-time applications
- Target: <1s for interactive use

### Success Rate
- **Higher is better** (percentage of successful compressions)
- Indicates strategy reliability and robustness
- Target: >95% for production use

## 🐛 Troubleshooting

### Common Issues

1. **AWS Bedrock Access**: Ensure proper IAM permissions for Bedrock
2. **Import Errors**: Check that all compression modules are in the path
3. **Memory Issues**: Reduce test dataset size for large prompts
4. **Timeout Errors**: Increase timeout values in strategy implementations

### Debug Mode

Add debug logging to individual strategies:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Contributing

To add new compression strategies or improve the testing framework:

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## 📜 License

This testing framework is part of the AI SA Portfolio project.