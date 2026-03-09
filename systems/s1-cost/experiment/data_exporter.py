"""Data export and analysis tools for Bedrock optimization research."""

import csv
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

class ResearchDataExporter:
    """Exports experiment data for research analysis and comparison tables."""

    def __init__(self, results_dir: str = "./results"):
        self.results_dir = results_dir
        self.ensure_results_dir()

    def ensure_results_dir(self):
        """Ensure results directory exists."""
        os.makedirs(self.results_dir, exist_ok=True)

    def export_strategy_comparison(self, baseline_metrics: List[Dict[str, Any]],
                                 strategy_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Export comprehensive strategy comparison for research table.

        Args:
            baseline_metrics: Baseline performance metrics
            strategy_results: Dictionary of {strategy_name: [metrics_list]}

        Returns:
            Path to exported comparison file
        """
        comparison_data = []

        # Process baseline
        if baseline_metrics:
            baseline_summary = self._summarize_metrics(baseline_metrics)
            baseline_row = {
                "Strategy": "Baseline (No Optimization)",
                "Queries_Processed": len(baseline_metrics),
                "Avg_Input_Tokens": baseline_summary["avg_input_tokens"],
                "Avg_Output_Tokens": baseline_summary["avg_output_tokens"],
                "Avg_Total_Cost": baseline_summary["avg_total_cost"],
                "Avg_Latency_ms": baseline_summary["avg_latency_ms"],
                "Total_Cost": baseline_summary["total_cost"],
                "Cost_Savings_Percent": 0.0,
                "Token_Savings_Percent": 0.0,
                "Implementation_Complexity": "None",
                "Suitable_Scenarios": "All queries",
                "Quality_Impact": "None"
            }
            comparison_data.append(baseline_row)

        # Process each strategy
        for strategy_name, metrics_list in strategy_results.items():
            if not metrics_list:
                continue

            strategy_summary = self._summarize_metrics(metrics_list)

            # Calculate improvements vs baseline
            cost_savings = 0.0
            token_savings = 0.0
            if baseline_metrics:
                baseline_summary = self._summarize_metrics(baseline_metrics)
                cost_savings = self._calculate_percentage_change(
                    baseline_summary["avg_total_cost"],
                    strategy_summary["avg_total_cost"]
                )
                token_savings = self._calculate_percentage_change(
                    baseline_summary["avg_input_tokens"],
                    strategy_summary["avg_input_tokens"]
                )

            strategy_row = {
                "Strategy": strategy_name,
                "Queries_Processed": len(metrics_list),
                "Avg_Input_Tokens": strategy_summary["avg_input_tokens"],
                "Avg_Output_Tokens": strategy_summary["avg_output_tokens"],
                "Avg_Total_Cost": strategy_summary["avg_total_cost"],
                "Avg_Latency_ms": strategy_summary["avg_latency_ms"],
                "Total_Cost": strategy_summary["total_cost"],
                "Cost_Savings_Percent": cost_savings,
                "Token_Savings_Percent": token_savings,
                "Implementation_Complexity": self._assess_implementation_complexity(strategy_name),
                "Suitable_Scenarios": self._identify_suitable_scenarios(strategy_name, strategy_summary),
                "Quality_Impact": self._assess_quality_impact(strategy_name, strategy_summary)
            }
            comparison_data.append(strategy_row)

        # Export to CSV
        filepath = os.path.join(self.results_dir, "strategy_comparison.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                "Strategy", "Queries_Processed", "Avg_Input_Tokens", "Avg_Output_Tokens",
                "Avg_Total_Cost", "Avg_Latency_ms", "Total_Cost", "Cost_Savings_Percent",
                "Token_Savings_Percent", "Implementation_Complexity", "Suitable_Scenarios",
                "Quality_Impact"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comparison_data)

        print(f"Strategy comparison exported to {filepath}")
        return filepath

    def export_detailed_analysis(self, strategy_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Export detailed statistical analysis for each strategy."""
        analysis_data = {}

        for strategy_name, metrics_list in strategy_results.items():
            if not metrics_list:
                continue

            # Extract key metrics
            costs = [m.get("total_cost", 0) for m in metrics_list]
            latencies = [m.get("latency_ms", 0) for m in metrics_list]
            input_tokens = [m.get("input_tokens", 0) for m in metrics_list]
            output_tokens = [m.get("output_tokens", 0) for m in metrics_list]

            strategy_analysis = {
                "strategy_name": strategy_name,
                "sample_size": len(metrics_list),
                "cost_analysis": self._statistical_analysis(costs, "Cost ($)"),
                "latency_analysis": self._statistical_analysis(latencies, "Latency (ms)"),
                "input_token_analysis": self._statistical_analysis(input_tokens, "Input Tokens"),
                "output_token_analysis": self._statistical_analysis(output_tokens, "Output Tokens"),
                "strategy_specific_metrics": self._extract_strategy_specific_metrics(strategy_name, metrics_list)
            }

            analysis_data[strategy_name] = strategy_analysis

        # Export to JSON
        filepath = os.path.join(self.results_dir, "detailed_analysis.json")
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(analysis_data, jsonfile, indent=2)

        print(f"Detailed analysis exported to {filepath}")
        return filepath

    def generate_research_summary(self, baseline_metrics: List[Dict[str, Any]],
                                strategy_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate executive summary for research report."""
        summary = {
            "experiment_overview": {
                "total_strategies_tested": len(strategy_results),
                "baseline_queries": len(baseline_metrics) if baseline_metrics else 0,
                "total_experimental_queries": sum(len(metrics) for metrics in strategy_results.values()),
                "experiment_date": datetime.now().isoformat()
            },
            "key_findings": {},
            "recommendations": {}
        }

        if baseline_metrics:
            baseline_summary = self._summarize_metrics(baseline_metrics)
            baseline_cost = baseline_summary["avg_total_cost"]

            # Find best performing strategies
            best_cost_savings = {"strategy": None, "savings": 0}
            best_token_reduction = {"strategy": None, "reduction": 0}
            fastest_response = {"strategy": None, "latency": float('inf')}

            for strategy_name, metrics_list in strategy_results.items():
                if not metrics_list:
                    continue

                strategy_summary = self._summarize_metrics(metrics_list)

                # Cost savings
                cost_savings = self._calculate_percentage_change(baseline_cost, strategy_summary["avg_total_cost"])
                if cost_savings > best_cost_savings["savings"]:
                    best_cost_savings = {"strategy": strategy_name, "savings": cost_savings}

                # Token reduction
                token_reduction = self._calculate_percentage_change(
                    baseline_summary["avg_input_tokens"],
                    strategy_summary["avg_input_tokens"]
                )
                if token_reduction > best_token_reduction["reduction"]:
                    best_token_reduction = {"strategy": strategy_name, "reduction": token_reduction}

                # Latency
                if strategy_summary["avg_latency_ms"] < fastest_response["latency"]:
                    fastest_response = {"strategy": strategy_name, "latency": strategy_summary["avg_latency_ms"]}

            summary["key_findings"] = {
                "best_cost_savings": best_cost_savings,
                "best_token_reduction": best_token_reduction,
                "fastest_response": fastest_response
            }

            # Generate recommendations
            summary["recommendations"] = self._generate_recommendations(strategy_results, baseline_summary)

        # Export summary
        filepath = os.path.join(self.results_dir, "research_summary.json")
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(summary, jsonfile, indent=2)

        print(f"Research summary exported to {filepath}")
        return filepath

    def _summarize_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate summary statistics from metrics list."""
        if not metrics_list:
            return {}

        # Extract values
        costs = [m.get("total_cost", 0) for m in metrics_list]
        latencies = [m.get("latency_ms", 0) for m in metrics_list]
        input_tokens = [m.get("input_tokens", 0) for m in metrics_list]
        output_tokens = [m.get("output_tokens", 0) for m in metrics_list]

        return {
            "avg_total_cost": round(statistics.mean(costs), 6),
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "avg_input_tokens": round(statistics.mean(input_tokens), 2),
            "avg_output_tokens": round(statistics.mean(output_tokens), 2),
            "total_cost": round(sum(costs), 6),
            "total_queries": len(metrics_list)
        }

    def _calculate_percentage_change(self, baseline: float, new_value: float) -> float:
        """Calculate percentage change (positive = savings/reduction)."""
        if baseline == 0:
            return 0.0
        return round(((baseline - new_value) / baseline) * 100, 2)

    def _statistical_analysis(self, values: List[float], metric_name: str) -> Dict[str, float]:
        """Perform statistical analysis on a list of values."""
        if not values:
            return {"error": f"No data for {metric_name}"}

        return {
            "metric": metric_name,
            "count": len(values),
            "mean": round(statistics.mean(values), 4),
            "median": round(statistics.median(values), 4),
            "std_dev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "range": round(max(values) - min(values), 4)
        }

    def _extract_strategy_specific_metrics(self, strategy_name: str, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract strategy-specific metrics."""
        specific_metrics = {}

        # Compression strategies
        if "compression" in strategy_name.lower():
            compression_ratios = [m.get("compression_ratio", 1.0) for m in metrics_list]
            specific_metrics["avg_compression_ratio"] = round(statistics.mean(compression_ratios), 3)
            specific_metrics["avg_compression_percent"] = round((1 - statistics.mean(compression_ratios)) * 100, 2)

        # Caching strategies
        if "caching" in strategy_name.lower():
            cache_hits = [m.get("cache_hit", False) for m in metrics_list]
            specific_metrics["cache_hit_rate"] = round(sum(cache_hits) / len(cache_hits), 3)

        # Routing strategies
        if "routing" in strategy_name.lower():
            routing_decisions = [m.get("routing_decision", "") for m in metrics_list]
            decision_counts = {}
            for decision in routing_decisions:
                decision_counts[decision] = decision_counts.get(decision, 0) + 1
            specific_metrics["routing_distribution"] = decision_counts

        # Batch processing
        if "batch" in strategy_name.lower():
            batch_positions = [m.get("batch_position", -1) for m in metrics_list if m.get("batch_position", -1) >= 0]
            if batch_positions:
                specific_metrics["avg_batch_position"] = round(statistics.mean(batch_positions), 2)

        return specific_metrics

    def _assess_implementation_complexity(self, strategy_name: str) -> str:
        """Assess implementation complexity of each strategy."""
        complexity_map = {
            "manual_refiner": "Low - Rule-based text processing",
            "semantic_summarizer": "Medium - Requires AI model calls",
            "relevance_filter": "Medium - Text analysis and similarity scoring",
            "structure_optimizer": "Low - Pattern matching and formatting",
            "llmlingua_compressor": "High - Advanced token analysis",
            "prompt_caching": "Low - Bedrock native feature",
            "model_routing": "Medium - Multi-criteria decision logic",
            "batch_processing": "High - Queue management and S3 integration"
        }

        for key, complexity in complexity_map.items():
            if key in strategy_name.lower():
                return complexity

        return "Medium - Standard implementation"

    def _identify_suitable_scenarios(self, strategy_name: str, summary: Dict[str, float]) -> str:
        """Identify suitable scenarios for each strategy."""
        scenario_map = {
            "manual_refiner": "Simple text compression, repeated queries",
            "semantic_summarizer": "Long context windows, verbose inputs",
            "relevance_filter": "Large context with specific queries",
            "structure_optimizer": "Structured data, lists, key-value pairs",
            "llmlingua_compressor": "High compression needs, token-sensitive apps",
            "prompt_caching": "Repeated system prompts, multi-turn conversations",
            "model_routing": "Mixed workloads, cost-sensitive applications",
            "batch_processing": "Non-realtime processing, bulk operations"
        }

        for key, scenarios in scenario_map.items():
            if key in strategy_name.lower():
                return scenarios

        return "General purpose optimization"

    def _assess_quality_impact(self, strategy_name: str, summary: Dict[str, float]) -> str:
        """Assess quality impact of each strategy."""
        # This would ideally be based on actual quality measurements
        # For now, provide theoretical assessments
        quality_map = {
            "manual_refiner": "Minimal - Preserves meaning",
            "semantic_summarizer": "Low - May lose minor details",
            "relevance_filter": "Medium - May remove relevant context",
            "structure_optimizer": "Minimal - Format change only",
            "llmlingua_compressor": "Medium - Aggressive compression may affect quality",
            "prompt_caching": "None - No content modification",
            "model_routing": "Variable - Depends on routing accuracy",
            "batch_processing": "None - Same model capabilities"
        }

        for key, quality in quality_map.items():
            if key in strategy_name.lower():
                return quality

        return "Unknown - Requires evaluation"

    def _generate_recommendations(self, strategy_results: Dict[str, List[Dict[str, Any]]],
                                baseline_summary: Dict[str, float]) -> Dict[str, str]:
        """Generate implementation recommendations based on results."""
        recommendations = {}

        # Cost optimization recommendation
        best_cost_strategy = None
        best_cost_savings = 0
        for strategy_name, metrics_list in strategy_results.items():
            if not metrics_list:
                continue
            strategy_summary = self._summarize_metrics(metrics_list)
            cost_savings = self._calculate_percentage_change(
                baseline_summary["avg_total_cost"],
                strategy_summary["avg_total_cost"]
            )
            if cost_savings > best_cost_savings:
                best_cost_savings = cost_savings
                best_cost_strategy = strategy_name

        if best_cost_strategy:
            recommendations["cost_optimization"] = (f"Use {best_cost_strategy} for {best_cost_savings}% cost savings")

        # General recommendations
        recommendations["implementation_priority"] = "Start with low-complexity strategies: prompt_caching, manual_refiner"
        recommendations["production_readiness"] = "Test quality impact thoroughly before production deployment"
        recommendations["monitoring"] = "Implement metrics collection to track optimization effectiveness"

        return recommendations