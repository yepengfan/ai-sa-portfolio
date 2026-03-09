"""Quick demo of enhanced chat functionality without interactive mode."""

from enhanced_chat import EnhancedBedrockChat

def demo_optimization_strategies():
    """Demonstrate the optimization strategies without full interactive mode."""
    print("🚀 Quick Demo: Bedrock Optimization Strategies")
    print("=" * 60)

    # Create enhanced chat instance
    chat = EnhancedBedrockChat()

    # Test text compression techniques
    print("\n1. Testing Compression Techniques:")
    test_text = "Could you please help me understand how to implement a basic web scraper using Python? I would like a comprehensive explanation."

    # Test manual refiner
    compressed, metrics = chat.manual_refiner.compress_prompt(test_text)
    print(f"   Manual Refiner:")
    print(f"   Original: {test_text[:50]}...")
    print(f"   Compressed: {compressed[:50]}...")
    print(f"   Savings: {metrics['compression_percent']:.1f}%")

    # Test structure optimizer
    compressed, metrics = chat.structure_optimizer.compress_prompt(test_text)
    print(f"\n   Structure Optimizer:")
    print(f"   Compressed: {compressed[:60]}...")
    print(f"   Savings: {metrics['compression_percent']:.1f}%")

    # Test model routing complexity analysis
    print("\n2. Testing Model Routing:")
    test_queries = [
        "What is Python?",
        "Implement a comprehensive machine learning pipeline with hyperparameter tuning"
    ]

    for query in test_queries:
        complexity, reason = chat.model_router._analyze_query_complexity(query, [])
        selected_model = chat.model_router._select_model_for_complexity(complexity)
        print(f"   Query: {query[:40]}...")
        print(f"   Complexity: {complexity.value} → {selected_model}")

    # Test metrics collection
    print("\n3. Testing Metrics Collection:")
    collector = chat.metrics_collector
    print(f"   ✅ Metrics collector ready")
    print(f"   Current metrics count: {len(collector.metrics)}")

    # Test data export capability
    print("\n4. Testing Data Export:")
    exporter = chat.data_exporter
    print(f"   ✅ Data exporter ready")
    print(f"   Results directory: {exporter.results_dir}")

    print("\n✅ Demo completed successfully!")
    print("\nTo run full interactive session:")
    print("   python enhanced_chat.py")
    print("\nTo run baseline comparison:")
    print("   python chat.py")

if __name__ == "__main__":
    demo_optimization_strategies()