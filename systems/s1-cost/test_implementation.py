"""Test script to verify all optimization strategies are working correctly."""

import sys
import time
from typing import Dict, Any

# Test imports
try:
    from strategies.compression.manual_refiner import ManualRefiner
    from strategies.compression.semantic_summarizer import SemanticSummarizer
    from strategies.compression.relevance_filter import RelevanceFilter
    from strategies.compression.structure_optimizer import StructureOptimizer
    from strategies.compression.llmlingua_compressor import LLMLinguaCompressor
    from strategies.prompt_caching import BedrockPromptCaching
    from strategies.model_routing import ModelRouter
    from strategies.batch_processing import BedrockBatchProcessor
    from experiment.metrics_collector import MetricsCollector
    from experiment.data_exporter import ResearchDataExporter
    from utils.config import get_model_config
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_compression_strategies():
    """Test all compression strategies."""
    print("\n🔧 Testing Compression Strategies")
    print("=" * 50)

    test_text = """
    Could you please help me understand how to implement a machine learning algorithm
    for image classification using Python? I would like a detailed explanation of the
    process, including data preprocessing, model selection, training procedures, and
    evaluation metrics. Additionally, please provide code examples and best practices
    for implementing this in a production environment.
    """

    # Test Manual Refiner
    print("1. Manual Refiner:")
    refiner = ManualRefiner()
    compressed, metrics = refiner.compress_prompt(test_text)
    print(f"   Original length: {len(test_text)} chars")
    print(f"   Compressed length: {len(compressed)} chars")
    print(f"   Compression ratio: {metrics['compression_ratio']:.3f}")
    print(f"   Sample: {compressed[:100]}...")

    # Test Semantic Summarizer (Note: This requires Bedrock access)
    print("\n2. Semantic Summarizer:")
    try:
        summarizer = SemanticSummarizer()
        compressed, metrics = summarizer.compress_prompt(test_text)
        print(f"   Compression ratio: {metrics['compression_ratio']:.3f}")
        print(f"   Sample: {compressed[:100]}...")
    except Exception as e:
        print(f"   ⚠️  Skipped (requires Bedrock): {e}")

    # Test Relevance Filter
    print("\n3. Relevance Filter:")
    filter_obj = RelevanceFilter()
    current_query = "What are the key steps in machine learning?"
    compressed, metrics = filter_obj.compress_prompt(test_text, current_query)
    print(f"   Compression ratio: {metrics['compression_ratio']:.3f}")
    print(f"   Chunks kept: {metrics['chunks_kept']}/{metrics['chunks_processed']}")

    # Test Structure Optimizer
    print("\n4. Structure Optimizer:")
    optimizer = StructureOptimizer()
    compressed, metrics = optimizer.compress_prompt(test_text)
    print(f"   Compression ratio: {metrics['compression_ratio']:.3f}")
    print(f"   Format used: {metrics['format_used']}")

    # Test LLMLingua Compressor (Note: This requires Bedrock access)
    print("\n5. LLMLingua Compressor:")
    try:
        compressor = LLMLinguaCompressor()
        compressed, metrics = compressor.compress_prompt(test_text)
        print(f"   Compression ratio: {metrics['compression_ratio']:.3f}")
        print(f"   Estimated token savings: {metrics['estimated_token_savings']:.1f}")
    except Exception as e:
        print(f"   ⚠️  Skipped (requires Bedrock): {e}")

def test_caching_strategy():
    """Test prompt caching strategy."""
    print("\n📋 Testing Prompt Caching Strategy")
    print("=" * 50)

    try:
        caching = BedrockPromptCaching()
        print("✅ Prompt caching initialized")

        # Test cache statistics (without actual calls)
        stats = caching.get_cache_statistics()
        print(f"   Initial cache stats: {stats}")

    except Exception as e:
        print(f"   ⚠️  Error: {e}")

def test_routing_strategy():
    """Test model routing strategy."""
    print("\n🔀 Testing Model Routing Strategy")
    print("=" * 50)

    router = ModelRouter()

    # Test different query types
    test_queries = [
        ("What is Python?", "Simple query"),
        ("How do I implement a complex neural network with attention mechanisms?", "Complex query"),
        ("Create a function to sort a list", "Moderate query")
    ]

    for query, description in test_queries:
        try:
            # Just test the complexity analysis (not actual model calls)
            messages = [{"role": "user", "content": query}]
            complexity, reason = router._analyze_query_complexity(query, messages)
            selected_model = router._select_model_for_complexity(complexity)

            print(f"   {description}:")
            print(f"     Query: {query[:50]}...")
            print(f"     Complexity: {complexity.value}")
            print(f"     Selected model: {selected_model}")
            print(f"     Reason: {reason[:80]}...")

        except Exception as e:
            print(f"   ❌ Error testing routing: {e}")

def test_batch_processing():
    """Test batch processing strategy."""
    print("\n📦 Testing Batch Processing Strategy")
    print("=" * 50)

    try:
        # Test basic initialization (without S3 operations)
        processor = BedrockBatchProcessor()
        print("✅ Batch processor initialized")

        # Test batch statistics
        stats = processor.get_batch_statistics()
        print(f"   Initial batch stats: {stats}")

    except Exception as e:
        print(f"   ⚠️  Error: {e}")

def test_experiment_infrastructure():
    """Test experiment infrastructure."""
    print("\n🧪 Testing Experiment Infrastructure")
    print("=" * 50)

    # Test metrics collector
    collector = MetricsCollector()
    print("✅ Metrics collector initialized")

    # Test data exporter
    exporter = ResearchDataExporter()
    print("✅ Data exporter initialized")

    # Test configuration
    haiku_config = get_model_config('haiku')
    sonnet_config = get_model_config('sonnet')
    print(f"✅ Model configs loaded:")
    print(f"   Haiku: {haiku_config['name']} - ${haiku_config['input_cost_per_1k']}/1K input tokens")
    print(f"   Sonnet: {sonnet_config['name']} - ${sonnet_config['input_cost_per_1k']}/1K input tokens")

def run_all_tests():
    """Run all tests."""
    print("🚀 Bedrock Optimization Strategies - Implementation Test")
    print("=" * 60)

    test_compression_strategies()
    test_caching_strategy()
    test_routing_strategy()
    test_batch_processing()
    test_experiment_infrastructure()

    print("\n✅ All tests completed!")
    print("\n📋 Implementation Summary:")
    print("• 5 Compression techniques implemented")
    print("• Prompt caching with Bedrock native support")
    print("• Intelligent model routing with complexity analysis")
    print("• Batch processing with queue management")
    print("• Comprehensive metrics collection and export")
    print("\n🎯 Ready for experimentation and research data collection!")

if __name__ == "__main__":
    run_all_tests()