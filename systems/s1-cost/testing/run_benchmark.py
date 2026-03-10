#!/usr/bin/env python3
"""Simple runner script for the compression benchmark."""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from compression_benchmark import CompressionBenchmark

def main():
    """Run the compression benchmark with basic error handling."""
    print("🚀 Starting Compression Strategy Benchmark")
    print("-" * 50)

    try:
        # Create benchmark instance
        benchmark = CompressionBenchmark(output_dir="benchmark_results")

        # Run comprehensive tests
        results = benchmark.run_comprehensive_benchmark()

        # Display results
        benchmark.print_results_summary(results)

        print(f"\n✅ Benchmark completed successfully!")
        print(f"📁 Results saved in: benchmark_results/")

    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure AWS credentials are configured for Bedrock")
        print("2. Verify that all compression modules are properly installed")
        print("3. Check that you have write permissions to the output directory")
        sys.exit(1)

if __name__ == "__main__":
    main()