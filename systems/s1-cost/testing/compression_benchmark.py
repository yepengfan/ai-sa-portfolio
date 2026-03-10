"""Comprehensive testing framework for comparing all 5 compression strategies."""

import time
import json
import csv
from typing import Dict, List, Tuple, Any
from pathlib import Path
import statistics

# Import all compression strategies
import sys
sys.path.append('../strategies/compression')

from semantic_summarizer import SemanticSummarizer, ContextAwareSummarizer
from relevance_filter import RelevanceFilter, AdvancedRelevanceFilter
from structure_optimizer import StructureOptimizer, AdvancedStructureOptimizer
from llmlingua_compressor import LLMLinguaCompressor, BatchLLMLinguaCompressor
from manual_refiner import ManualRefiner, AdvancedManualRefiner


class CompressionBenchmark:
    """Comprehensive benchmark suite for testing compression strategies."""

    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize all compression strategies
        self.strategies = {
            "semantic_summarizer": SemanticSummarizer(),
            "context_aware_summarizer": ContextAwareSummarizer(),
            "relevance_filter": RelevanceFilter(),
            "advanced_relevance_filter": AdvancedRelevanceFilter(),
            "structure_optimizer": StructureOptimizer(),
            "advanced_structure_optimizer": AdvancedStructureOptimizer(),
            "llmlingua_compressor": LLMLinguaCompressor(),
            "manual_refiner": ManualRefiner(),
            "advanced_manual_refiner": AdvancedManualRefiner()
        }

        # Test datasets
        self.test_datasets = self._create_test_datasets()

    def _create_test_datasets(self) -> Dict[str, List[Dict[str, str]]]:
        """Create diverse test datasets for comprehensive evaluation."""
        return {
            "short_queries": [
                {
                    "name": "simple_question",
                    "text": "What is machine learning and how does it work?",
                    "query": "machine learning basics",
                    "category": "educational"
                },
                {
                    "name": "code_request",
                    "text": "Please write a Python function that calculates the factorial of a number using recursion.",
                    "query": "python factorial function",
                    "category": "coding"
                },
                {
                    "name": "explanation_request",
                    "text": "Can you explain the difference between supervised and unsupervised learning in simple terms?",
                    "query": "supervised vs unsupervised learning",
                    "category": "educational"
                }
            ],

            "medium_prompts": [
                {
                    "name": "detailed_instruction",
                    "text": """I need to create a web application that allows users to upload CSV files, process the data, and generate visualizations. The application should have the following features: file upload functionality, data validation and cleaning, multiple chart types (bar, line, pie), interactive dashboards, and the ability to export results as PDF reports. Please provide a detailed implementation plan with technology recommendations.""",
                    "query": "web app csv data visualization",
                    "category": "project_planning"
                },
                {
                    "name": "technical_explanation",
                    "text": """Explain how database indexing works in PostgreSQL. Cover the different types of indexes available, when to use each type, how they impact query performance, and best practices for index maintenance. Also discuss the trade-offs between query speed and write performance when using indexes extensively.""",
                    "query": "PostgreSQL indexing performance",
                    "category": "technical_deep_dive"
                },
                {
                    "name": "troubleshooting_scenario",
                    "text": """I'm experiencing performance issues with my React application. The app becomes slow when rendering large lists of data, and the UI freezes during data fetching operations. The app uses Redux for state management, makes frequent API calls, and renders complex component trees. Help me identify potential performance bottlenecks and provide optimization strategies.""",
                    "query": "React performance optimization",
                    "category": "debugging"
                }
            ],

            "long_contexts": [
                {
                    "name": "comprehensive_guide",
                    "text": """I'm building a comprehensive e-commerce platform and need guidance on the entire architecture. The system should handle user authentication and authorization, product catalog management with categories and search functionality, shopping cart and wishlist features, multiple payment gateway integrations, order management and tracking, inventory management, customer reviews and ratings, email notifications, admin dashboard for managing all aspects of the platform, analytics and reporting, mobile API endpoints, and scalability for handling thousands of concurrent users. I want to use modern technologies and follow best practices for security, performance, and maintainability. Please provide a detailed technical architecture including database design, API structure, security considerations, deployment strategies, monitoring and logging, testing approaches, and potential challenges I might face during development. Also suggest the best technology stack for both frontend and backend development.""",
                    "query": "e-commerce platform architecture",
                    "category": "system_design"
                },
                {
                    "name": "research_analysis",
                    "text": """Analyze the current state of artificial intelligence in healthcare, focusing on diagnostic imaging, drug discovery, personalized medicine, and clinical decision support systems. Discuss the key technologies being used, major players in the industry, recent breakthroughs and their clinical implications, regulatory challenges and approval processes, ethical considerations including bias and privacy, economic impact on healthcare costs, integration challenges with existing hospital systems, training requirements for healthcare professionals, patient acceptance and trust issues, data quality and standardization problems, and future trends and predictions for the next 5-10 years. Include specific examples of successful AI implementations in major hospitals or healthcare systems.""",
                    "query": "AI healthcare applications analysis",
                    "category": "research_analysis"
                }
            ],

            "conversation_contexts": [
                {
                    "name": "ongoing_discussion",
                    "text": "Following up on our previous discussion about microservices architecture, I'd like to dive deeper into service communication patterns and data consistency challenges.",
                    "query": "microservices communication patterns",
                    "category": "follow_up",
                    "conversation_history": [
                        {"content": "We discussed microservices vs monolith architecture"},
                        {"content": "You mentioned service mesh and API gateways"},
                        {"content": "We talked about database per service pattern"}
                    ]
                }
            ]
        }

    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark across all strategies and datasets."""
        print("Starting comprehensive compression benchmark...")

        results = {
            "timestamp": time.time(),
            "strategies": {},
            "summary": {},
            "recommendations": {}
        }

        all_strategy_results = []

        for strategy_name, strategy in self.strategies.items():
            print(f"\n--- Testing {strategy_name} ---")
            strategy_results = self._test_strategy(strategy_name, strategy)
            results["strategies"][strategy_name] = strategy_results
            all_strategy_results.append((strategy_name, strategy_results))

            # Save individual results
            self._save_strategy_results(strategy_name, strategy_results)

        # Generate summary and recommendations
        results["summary"] = self._generate_summary(all_strategy_results)
        results["recommendations"] = self._generate_recommendations(all_strategy_results)

        # Save comprehensive results
        self._save_comprehensive_results(results)

        return results

    def _test_strategy(self, strategy_name: str, strategy) -> Dict[str, Any]:
        """Test a single compression strategy across all datasets."""
        strategy_results = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "average_compression_ratio": 0.0,
            "average_processing_time": 0.0,
            "dataset_results": {},
            "performance_metrics": {}
        }

        all_compression_ratios = []
        all_processing_times = []

        for dataset_name, dataset in self.test_datasets.items():
            print(f"  Testing on {dataset_name}...")
            dataset_results = []

            for test_case in dataset:
                result = self._run_single_test(strategy_name, strategy, test_case)
                dataset_results.append(result)

                strategy_results["total_tests"] += 1
                if result["success"]:
                    strategy_results["successful_tests"] += 1
                    all_compression_ratios.append(result["metrics"]["compression_ratio"])
                    all_processing_times.append(result["processing_time"])
                else:
                    strategy_results["failed_tests"] += 1

            strategy_results["dataset_results"][dataset_name] = dataset_results

        # Calculate aggregate metrics
        if all_compression_ratios:
            strategy_results["average_compression_ratio"] = statistics.mean(all_compression_ratios)
            strategy_results["compression_ratio_std"] = statistics.stdev(all_compression_ratios) if len(all_compression_ratios) > 1 else 0

        if all_processing_times:
            strategy_results["average_processing_time"] = statistics.mean(all_processing_times)
            strategy_results["processing_time_std"] = statistics.stdev(all_processing_times) if len(all_processing_times) > 1 else 0

        strategy_results["performance_metrics"] = self._calculate_performance_metrics(
            all_compression_ratios, all_processing_times, strategy_results["successful_tests"], strategy_results["total_tests"]
        )

        return strategy_results

    def _run_single_test(self, strategy_name: str, strategy, test_case: Dict[str, str]) -> Dict[str, Any]:
        """Run a single test case for a strategy."""
        result = {
            "test_name": test_case["name"],
            "category": test_case["category"],
            "original_length": len(test_case["text"]),
            "success": False,
            "processing_time": 0.0,
            "compressed_text": "",
            "metrics": {},
            "error": None
        }

        try:
            start_time = time.time()

            # Call appropriate compression method based on strategy
            if "semantic" in strategy_name:
                compressed_text, metrics = strategy.compress_prompt(test_case["text"])
            elif "relevance" in strategy_name:
                query = test_case.get("query", "")
                compressed_text, metrics = strategy.compress_prompt(test_case["text"], query)
            elif "context_aware" in strategy_name and "conversation_history" in test_case:
                compressed_text, metrics = strategy.compress_with_context(
                    test_case["text"],
                    test_case["conversation_history"]
                )
            elif "structure" in strategy_name:
                compressed_text, metrics = strategy.compress_prompt(test_case["text"])
            elif "llmlingua" in strategy_name:
                compressed_text, metrics = strategy.compress_prompt(test_case["text"])
            elif "manual" in strategy_name:
                if "advanced" in strategy_name:
                    compressed_text, metrics = strategy.compress_prompt(test_case["text"], aggressive=True)
                else:
                    compressed_text, metrics = strategy.compress_prompt(test_case["text"])
            else:
                compressed_text, metrics = strategy.compress_prompt(test_case["text"])

            processing_time = time.time() - start_time

            result.update({
                "success": True,
                "processing_time": processing_time,
                "compressed_text": compressed_text,
                "compressed_length": len(compressed_text),
                "metrics": metrics
            })

        except Exception as e:
            result["error"] = str(e)
            print(f"    Error in {test_case['name']}: {e}")

        return result

    def _calculate_performance_metrics(self, compression_ratios: List[float],
                                     processing_times: List[float],
                                     successful_tests: int, total_tests: int) -> Dict[str, float]:
        """Calculate comprehensive performance metrics."""
        if not compression_ratios or not processing_times:
            return {}

        # Compression efficiency metrics
        avg_compression = statistics.mean(compression_ratios)
        compression_savings = (1 - avg_compression) * 100

        # Speed metrics
        avg_speed = statistics.mean(processing_times)

        # Reliability metrics
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0

        # Combined effectiveness score (lower compression ratio = better, lower time = better)
        # Normalized score where lower is better
        effectiveness_score = (avg_compression * 0.7) + (avg_speed / 10 * 0.3)

        return {
            "average_compression_ratio": avg_compression,
            "compression_savings_percent": compression_savings,
            "average_processing_time": avg_speed,
            "success_rate_percent": success_rate,
            "effectiveness_score": effectiveness_score,
            "best_compression_ratio": min(compression_ratios),
            "worst_compression_ratio": max(compression_ratios),
            "fastest_processing_time": min(processing_times),
            "slowest_processing_time": max(processing_times)
        }

    def _generate_summary(self, all_results: List[Tuple[str, Dict]]) -> Dict[str, Any]:
        """Generate summary analysis across all strategies."""
        summary = {
            "best_compression": {"strategy": "", "ratio": 1.0, "savings_percent": 0.0},
            "fastest_processing": {"strategy": "", "time": float('inf')},
            "most_reliable": {"strategy": "", "success_rate": 0.0},
            "best_overall": {"strategy": "", "score": float('inf')},
            "strategy_rankings": []
        }

        rankings = []

        for strategy_name, results in all_results:
            metrics = results.get("performance_metrics", {})
            if not metrics:
                continue

            # Track best performers
            if metrics["average_compression_ratio"] < summary["best_compression"]["ratio"]:
                summary["best_compression"] = {
                    "strategy": strategy_name,
                    "ratio": metrics["average_compression_ratio"],
                    "savings_percent": metrics["compression_savings_percent"]
                }

            if metrics["average_processing_time"] < summary["fastest_processing"]["time"]:
                summary["fastest_processing"] = {
                    "strategy": strategy_name,
                    "time": metrics["average_processing_time"]
                }

            if metrics["success_rate_percent"] > summary["most_reliable"]["success_rate"]:
                summary["most_reliable"] = {
                    "strategy": strategy_name,
                    "success_rate": metrics["success_rate_percent"]
                }

            if metrics["effectiveness_score"] < summary["best_overall"]["score"]:
                summary["best_overall"] = {
                    "strategy": strategy_name,
                    "score": metrics["effectiveness_score"]
                }

            # Add to rankings
            rankings.append({
                "strategy": strategy_name,
                "compression_ratio": metrics["average_compression_ratio"],
                "compression_savings": metrics["compression_savings_percent"],
                "processing_time": metrics["average_processing_time"],
                "success_rate": metrics["success_rate_percent"],
                "effectiveness_score": metrics["effectiveness_score"]
            })

        # Sort rankings by effectiveness score (lower is better)
        rankings.sort(key=lambda x: x["effectiveness_score"])
        summary["strategy_rankings"] = rankings

        return summary

    def _generate_recommendations(self, all_results: List[Tuple[str, Dict]]) -> Dict[str, str]:
        """Generate strategy recommendations based on results."""
        recommendations = {}

        # Analyze results to provide contextual recommendations
        summary_data = []
        for strategy_name, results in all_results:
            metrics = results.get("performance_metrics", {})
            if metrics:
                summary_data.append((strategy_name, metrics))

        if not summary_data:
            return {"general": "Insufficient data for recommendations"}

        # Sort by different criteria
        by_compression = sorted(summary_data, key=lambda x: x[1]["average_compression_ratio"])
        by_speed = sorted(summary_data, key=lambda x: x[1]["average_processing_time"])
        by_reliability = sorted(summary_data, key=lambda x: x[1]["success_rate_percent"], reverse=True)

        recommendations.update({
            "best_compression": f"For maximum compression, use {by_compression[0][0]} (saves {by_compression[0][1]['compression_savings_percent']:.1f}% on average)",
            "fastest_processing": f"For speed-critical applications, use {by_speed[0][0]} ({by_speed[0][1]['average_processing_time']:.3f}s average)",
            "most_reliable": f"For reliability, use {by_reliability[0][0]} ({by_reliability[0][1]['success_rate_percent']:.1f}% success rate)",
            "general_purpose": f"For balanced performance, use {by_compression[0][0] if by_compression[0][1]['success_rate_percent'] > 80 else by_reliability[0][0]}",
            "use_cases": {
                "real_time_applications": by_speed[0][0],
                "batch_processing": by_compression[0][0],
                "production_systems": by_reliability[0][0],
                "cost_optimization": by_compression[0][0]
            }
        })

        return recommendations

    def _save_strategy_results(self, strategy_name: str, results: Dict[str, Any]):
        """Save individual strategy results."""
        filepath = self.output_dir / f"{strategy_name}_results.json"
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

    def _save_comprehensive_results(self, results: Dict[str, Any]):
        """Save comprehensive benchmark results."""
        # JSON results
        json_filepath = self.output_dir / "comprehensive_benchmark_results.json"
        with open(json_filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # CSV summary for easy analysis
        csv_filepath = self.output_dir / "strategy_comparison.csv"
        self._create_csv_summary(results, csv_filepath)

        print(f"\nResults saved to {self.output_dir}/")
        print(f"- Comprehensive results: {json_filepath}")
        print(f"- CSV summary: {csv_filepath}")

    def _create_csv_summary(self, results: Dict[str, Any], filepath: Path):
        """Create CSV summary of strategy comparison."""
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'strategy', 'avg_compression_ratio', 'compression_savings_percent',
                'avg_processing_time', 'success_rate_percent', 'effectiveness_score',
                'total_tests', 'successful_tests', 'failed_tests'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for strategy_name, strategy_results in results["strategies"].items():
                metrics = strategy_results.get("performance_metrics", {})
                if metrics:
                    writer.writerow({
                        'strategy': strategy_name,
                        'avg_compression_ratio': metrics.get("average_compression_ratio", 0),
                        'compression_savings_percent': metrics.get("compression_savings_percent", 0),
                        'avg_processing_time': metrics.get("average_processing_time", 0),
                        'success_rate_percent': metrics.get("success_rate_percent", 0),
                        'effectiveness_score': metrics.get("effectiveness_score", 0),
                        'total_tests': strategy_results.get("total_tests", 0),
                        'successful_tests': strategy_results.get("successful_tests", 0),
                        'failed_tests': strategy_results.get("failed_tests", 0)
                    })

    def print_results_summary(self, results: Dict[str, Any]):
        """Print a formatted summary of benchmark results."""
        print("\n" + "="*80)
        print("COMPRESSION STRATEGY BENCHMARK RESULTS")
        print("="*80)

        summary = results.get("summary", {})

        print(f"\n🏆 BEST PERFORMERS:")
        print(f"  • Best Compression: {summary['best_compression']['strategy']} ({summary['best_compression']['savings_percent']:.1f}% savings)")
        print(f"  • Fastest Processing: {summary['fastest_processing']['strategy']} ({summary['fastest_processing']['time']:.3f}s)")
        print(f"  • Most Reliable: {summary['most_reliable']['strategy']} ({summary['most_reliable']['success_rate']:.1f}% success)")
        print(f"  • Best Overall: {summary['best_overall']['strategy']} (effectiveness score: {summary['best_overall']['score']:.3f})")

        print(f"\n📊 STRATEGY RANKINGS (by overall effectiveness):")
        for i, ranking in enumerate(summary.get("strategy_rankings", []), 1):
            print(f"  {i:2d}. {ranking['strategy']:25s} | "
                  f"Compression: {ranking['compression_savings']:5.1f}% | "
                  f"Speed: {ranking['processing_time']:6.3f}s | "
                  f"Success: {ranking['success_rate']:5.1f}%")

        print(f"\n💡 RECOMMENDATIONS:")
        recommendations = results.get("recommendations", {})
        for key, recommendation in recommendations.items():
            if key != "use_cases":
                print(f"  • {key.replace('_', ' ').title()}: {recommendation}")

        print(f"\n🎯 USE CASE RECOMMENDATIONS:")
        use_cases = recommendations.get("use_cases", {})
        for use_case, strategy in use_cases.items():
            print(f"  • {use_case.replace('_', ' ').title()}: {strategy}")


if __name__ == "__main__":
    # Run comprehensive benchmark
    benchmark = CompressionBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    benchmark.print_results_summary(results)