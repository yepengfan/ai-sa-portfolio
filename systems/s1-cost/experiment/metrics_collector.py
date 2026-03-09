"""Comprehensive metrics collection system for Bedrock optimization research."""

import json
import time
import csv
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    timestamp: str
    strategy_name: str
    query_id: str
    user_input: str
    response: str

    # Token metrics
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Cost metrics
    input_cost: float
    output_cost: float
    total_cost: float

    # Performance metrics
    latency_ms: int
    processing_overhead_ms: int = 0

    # Strategy-specific metrics
    compression_ratio: float = 1.0
    cache_hit: bool = False
    routing_decision: str = ""
    batch_position: int = -1

    # Quality metrics (to be filled manually or via evaluation)
    quality_score: float = 0.0
    accuracy_preserved: bool = True
    context_preserved: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

class MetricsCollector:
    """Collects and manages experiment metrics."""

    def __init__(self, results_dir: str = "./results"):
        self.results_dir = results_dir
        self.metrics: List[QueryMetrics] = []
        self.ensure_results_dir()

    def ensure_results_dir(self):
        """Ensure results directory exists."""
        os.makedirs(self.results_dir, exist_ok=True)

    def start_query_timer(self) -> float:
        """Start timing a query."""
        return time.time()

    def calculate_cost(self, input_tokens: int, output_tokens: int,
                      input_cost_per_1k: float, output_cost_per_1k: float) -> Dict[str, float]:
        """Calculate costs from token usage."""
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

    def record_query(self,
                    strategy_name: str,
                    query_id: str,
                    user_input: str,
                    response: str,
                    input_tokens: int,
                    output_tokens: int,
                    input_cost_per_1k: float,
                    output_cost_per_1k: float,
                    start_time: float,
                    **kwargs) -> QueryMetrics:
        """Record metrics for a single query."""

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        costs = self.calculate_cost(input_tokens, output_tokens,
                                  input_cost_per_1k, output_cost_per_1k)

        metrics = QueryMetrics(
            timestamp=datetime.now().isoformat(),
            strategy_name=strategy_name,
            query_id=query_id,
            user_input=user_input,
            response=response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost=costs["input_cost"],
            output_cost=costs["output_cost"],
            total_cost=costs["total_cost"],
            latency_ms=latency_ms,
            **kwargs
        )

        self.metrics.append(metrics)
        return metrics

    def export_csv(self, strategy_name: str = None) -> str:
        """Export metrics to CSV file."""
        if strategy_name:
            filename = f"{strategy_name}_results.csv"
            filtered_metrics = [m for m in self.metrics if m.strategy_name == strategy_name]
        else:
            filename = "all_results.csv"
            filtered_metrics = self.metrics

        filepath = os.path.join(self.results_dir, filename)

        if not filtered_metrics:
            print(f"No metrics found for strategy: {strategy_name}")
            return filepath

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=filtered_metrics[0].to_dict().keys())
            writer.writeheader()
            for metric in filtered_metrics:
                writer.writerow(metric.to_dict())

        print(f"Exported {len(filtered_metrics)} records to {filepath}")
        return filepath

    def export_json(self, strategy_name: str = None) -> str:
        """Export metrics to JSON file."""
        if strategy_name:
            filename = f"{strategy_name}_results.json"
            filtered_metrics = [m for m in self.metrics if m.strategy_name == strategy_name]
        else:
            filename = "all_results.json"
            filtered_metrics = self.metrics

        filepath = os.path.join(self.results_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump([m.to_dict() for m in filtered_metrics], jsonfile, indent=2)

        print(f"Exported {len(filtered_metrics)} records to {filepath}")
        return filepath

    def get_strategy_summary(self, strategy_name: str) -> Dict[str, Any]:
        """Get summary statistics for a strategy."""
        strategy_metrics = [m for m in self.metrics if m.strategy_name == strategy_name]

        if not strategy_metrics:
            return {"error": f"No metrics found for strategy: {strategy_name}"}

        # Calculate averages
        avg_input_tokens = sum(m.input_tokens for m in strategy_metrics) / len(strategy_metrics)
        avg_output_tokens = sum(m.output_tokens for m in strategy_metrics) / len(strategy_metrics)
        avg_total_cost = sum(m.total_cost for m in strategy_metrics) / len(strategy_metrics)
        avg_latency = sum(m.latency_ms for m in strategy_metrics) / len(strategy_metrics)
        avg_compression = sum(m.compression_ratio for m in strategy_metrics) / len(strategy_metrics)

        # Calculate totals
        total_queries = len(strategy_metrics)
        total_cost = sum(m.total_cost for m in strategy_metrics)
        cache_hits = sum(1 for m in strategy_metrics if m.cache_hit)
        cache_hit_rate = cache_hits / total_queries if total_queries > 0 else 0

        return {
            "strategy_name": strategy_name,
            "total_queries": total_queries,
            "avg_input_tokens": round(avg_input_tokens, 2),
            "avg_output_tokens": round(avg_output_tokens, 2),
            "avg_total_cost": round(avg_total_cost, 6),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_compression_ratio": round(avg_compression, 3),
            "total_cost": round(total_cost, 6),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "cache_hits": cache_hits
        }

    def compare_strategies(self, baseline_strategy: str, comparison_strategies: List[str]) -> Dict[str, Any]:
        """Compare strategies against baseline."""
        baseline_summary = self.get_strategy_summary(baseline_strategy)

        if "error" in baseline_summary:
            return baseline_summary

        comparison = {
            "baseline": baseline_summary,
            "comparisons": {}
        }

        for strategy in comparison_strategies:
            strategy_summary = self.get_strategy_summary(strategy)
            if "error" not in strategy_summary:
                # Calculate improvements
                cost_saving = ((baseline_summary["avg_total_cost"] - strategy_summary["avg_total_cost"])
                             / baseline_summary["avg_total_cost"]) * 100
                token_saving = ((baseline_summary["avg_input_tokens"] - strategy_summary["avg_input_tokens"])
                               / baseline_summary["avg_input_tokens"]) * 100
                latency_change = ((strategy_summary["avg_latency_ms"] - baseline_summary["avg_latency_ms"])
                                / baseline_summary["avg_latency_ms"]) * 100

                strategy_summary["cost_saving_percent"] = round(cost_saving, 2)
                strategy_summary["token_saving_percent"] = round(token_saving, 2)
                strategy_summary["latency_change_percent"] = round(latency_change, 2)

                comparison["comparisons"][strategy] = strategy_summary

        return comparison

    def clear_metrics(self):
        """Clear all collected metrics."""
        self.metrics.clear()