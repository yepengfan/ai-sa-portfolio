"""Cost estimation for running the compression benchmark."""

import json
from typing import Dict, List
from pathlib import Path

# Current AWS Bedrock pricing for Claude Haiku (as of March 2024)
# Prices are per 1,000 tokens
BEDROCK_HAIKU_PRICING = {
    "input_tokens": 0.00025,    # $0.00025 per 1K input tokens
    "output_tokens": 0.00125,   # $0.00125 per 1K output tokens
}

class BenchmarkCostEstimator:
    """Estimate the cost of running the compression benchmark."""

    def __init__(self):
        # Test datasets from the benchmark
        self.test_datasets = {
            "short_queries": [
                "What is machine learning and how does it work?",
                "Please write a Python function that calculates the factorial of a number using recursion.",
                "Can you explain the difference between supervised and unsupervised learning in simple terms?"
            ],
            "medium_prompts": [
                """I need to create a web application that allows users to upload CSV files, process the data, and generate visualizations. The application should have the following features: file upload functionality, data validation and cleaning, multiple chart types (bar, line, pie), interactive dashboards, and the ability to export results as PDF reports. Please provide a detailed implementation plan with technology recommendations.""",

                """Explain how database indexing works in PostgreSQL. Cover the different types of indexes available, when to use each type, how they impact query performance, and best practices for index maintenance. Also discuss the trade-offs between query speed and write performance when using indexes extensively.""",

                """I'm experiencing performance issues with my React application. The app becomes slow when rendering large lists of data, and the UI freezes during data fetching operations. The app uses Redux for state management, makes frequent API calls, and renders complex component trees. Help me identify potential performance bottlenecks and provide optimization strategies."""
            ],
            "long_contexts": [
                """I'm building a comprehensive e-commerce platform and need guidance on the entire architecture. The system should handle user authentication and authorization, product catalog management with categories and search functionality, shopping cart and wishlist features, multiple payment gateway integrations, order management and tracking, inventory management, customer reviews and ratings, email notifications, admin dashboard for managing all aspects of the platform, analytics and reporting, mobile API endpoints, and scalability for handling thousands of concurrent users. I want to use modern technologies and follow best practices for security, performance, and maintainability. Please provide a detailed technical architecture including database design, API structure, security considerations, deployment strategies, monitoring and logging, testing approaches, and potential challenges I might face during development. Also suggest the best technology stack for both frontend and backend development.""",

                """Analyze the current state of artificial intelligence in healthcare, focusing on diagnostic imaging, drug discovery, personalized medicine, and clinical decision support systems. Discuss the key technologies being used, major players in the industry, recent breakthroughs and their clinical implications, regulatory challenges and approval processes, ethical considerations including bias and privacy, economic impact on healthcare costs, integration challenges with existing hospital systems, training requirements for healthcare professionals, patient acceptance and trust issues, data quality and standardization problems, and future trends and predictions for the next 5-10 years. Include specific examples of successful AI implementations in major hospitals or healthcare systems."""
            ],
            "conversation_contexts": [
                "Following up on our previous discussion about microservices architecture, I'd like to dive deeper into service communication patterns and data consistency challenges."
            ]
        }

        # Strategies that make Bedrock API calls
        self.ai_strategies = {
            "semantic_summarizer": {"calls_per_test": 1, "avg_output_ratio": 0.5},
            "context_aware_summarizer": {"calls_per_test": 1, "avg_output_ratio": 0.5},  # Only for conversation context
            "llmlingua_compressor": {"calls_per_test": 1, "avg_output_ratio": 0.2}  # Token analysis call
        }

        # Non-AI strategies (no cost)
        self.non_ai_strategies = [
            "relevance_filter", "advanced_relevance_filter",
            "structure_optimizer", "advanced_structure_optimizer",
            "manual_refiner", "advanced_manual_refiner"
        ]

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 characters per token for English text."""
        return len(text) // 4

    def calculate_benchmark_cost(self) -> Dict[str, float]:
        """Calculate the total cost to run the benchmark."""

        total_input_tokens = 0
        total_output_tokens = 0
        total_api_calls = 0
        cost_breakdown = {}

        # Calculate costs for each AI strategy
        for strategy_name, config in self.ai_strategies.items():
            strategy_input_tokens = 0
            strategy_output_tokens = 0
            strategy_calls = 0

            # Process each dataset
            for dataset_name, texts in self.test_datasets.items():
                for text in texts:
                    # Special handling for context_aware_summarizer (only runs on conversation contexts)
                    if strategy_name == "context_aware_summarizer" and dataset_name != "conversation_contexts":
                        continue

                    base_tokens = self.estimate_tokens(text)

                    # Add system prompt tokens (compression instructions)
                    system_prompt_tokens = 150  # Estimated tokens for compression instructions

                    input_tokens = base_tokens + system_prompt_tokens
                    output_tokens = int(base_tokens * config["avg_output_ratio"])

                    strategy_input_tokens += input_tokens * config["calls_per_test"]
                    strategy_output_tokens += output_tokens * config["calls_per_test"]
                    strategy_calls += config["calls_per_test"]

            # Calculate costs for this strategy
            input_cost = (strategy_input_tokens / 1000) * BEDROCK_HAIKU_PRICING["input_tokens"]
            output_cost = (strategy_output_tokens / 1000) * BEDROCK_HAIKU_PRICING["output_tokens"]
            strategy_total_cost = input_cost + output_cost

            cost_breakdown[strategy_name] = {
                "input_tokens": strategy_input_tokens,
                "output_tokens": strategy_output_tokens,
                "api_calls": strategy_calls,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": strategy_total_cost
            }

            total_input_tokens += strategy_input_tokens
            total_output_tokens += strategy_output_tokens
            total_api_calls += strategy_calls

        # Calculate total benchmark cost
        total_input_cost = (total_input_tokens / 1000) * BEDROCK_HAIKU_PRICING["input_tokens"]
        total_output_cost = (total_output_tokens / 1000) * BEDROCK_HAIKU_PRICING["output_tokens"]
        total_cost = total_input_cost + total_output_cost

        return {
            "total_cost": total_cost,
            "total_input_cost": total_input_cost,
            "total_output_cost": total_output_cost,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_api_calls": total_api_calls,
            "cost_breakdown": cost_breakdown,
            "pricing_info": BEDROCK_HAIKU_PRICING,
            "non_ai_strategies": len(self.non_ai_strategies)
        }

    def print_cost_estimate(self):
        """Print formatted cost estimate."""
        costs = self.calculate_benchmark_cost()

        print("="*70)
        print("🧮 COMPRESSION BENCHMARK COST ESTIMATE")
        print("="*70)

        print(f"\n💰 TOTAL ESTIMATED COST: ${costs['total_cost']:.4f}")
        print(f"   • Input tokens cost:   ${costs['total_input_cost']:.4f}")
        print(f"   • Output tokens cost:  ${costs['total_output_cost']:.4f}")

        print(f"\n📊 USAGE BREAKDOWN:")
        print(f"   • Total API calls:     {costs['total_api_calls']:,}")
        print(f"   • Total input tokens:  {costs['total_input_tokens']:,}")
        print(f"   • Total output tokens: {costs['total_output_tokens']:,}")

        print(f"\n🤖 AI STRATEGY COSTS:")
        for strategy, details in costs['cost_breakdown'].items():
            print(f"   • {strategy:25s} ${details['total_cost']:.4f} "
                  f"({details['api_calls']:2d} calls)")

        print(f"\n🚀 NON-AI STRATEGIES: {costs['non_ai_strategies']} strategies (FREE)")
        print(f"   • No API calls required for rule-based strategies")

        print(f"\n💡 PRICING DETAILS (Claude Haiku via Bedrock):")
        print(f"   • Input tokens:  ${costs['pricing_info']['input_tokens']:.5f} per 1,000")
        print(f"   • Output tokens: ${costs['pricing_info']['output_tokens']:.5f} per 1,000")

        print(f"\n📈 COST PER TEST CASE:")
        total_tests = sum(len(texts) for texts in self.test_datasets.values())
        ai_tests = len(self.test_datasets["short_queries"]) + len(self.test_datasets["medium_prompts"]) + \
                  len(self.test_datasets["long_contexts"]) + len(self.test_datasets["conversation_contexts"])

        if ai_tests > 0:
            cost_per_ai_test = costs['total_cost'] / (len(costs['cost_breakdown']) * ai_tests) * 3  # 3 AI strategies
            print(f"   • Average per AI test: ${cost_per_ai_test:.5f}")

        print(f"\n⚠️  COST VARIABLES:")
        print(f"   • Actual token usage may vary ±20%")
        print(f"   • Compression ratios affect output token costs")
        print(f"   • API latency doesn't affect costs")
        print(f"   • Failed requests may still incur input token costs")

        # Cost comparison
        print(f"\n💸 COST COMPARISON:")
        print(f"   • ☕ Cup of coffee:     ~$3.00 (150x more expensive)")
        print(f"   • 🍫 Candy bar:        ~$1.50 (75x more expensive)")
        print(f"   • 📧 Email (1¢):       ~$0.01 (5x more expensive)")
        print(f"   • 🎯 This benchmark:   ${costs['total_cost']:.4f}")

    def estimate_production_costs(self, prompts_per_day: int = 1000,
                                avg_prompt_length: int = 500) -> Dict[str, float]:
        """Estimate costs for production usage."""

        # Estimate tokens per prompt
        tokens_per_prompt = avg_prompt_length // 4

        # Assume 50% compression ratio on average
        output_tokens_per_prompt = int(tokens_per_prompt * 0.5)

        daily_costs = {}

        for strategy in self.ai_strategies:
            daily_input_tokens = prompts_per_day * tokens_per_prompt
            daily_output_tokens = prompts_per_day * output_tokens_per_prompt

            daily_input_cost = (daily_input_tokens / 1000) * BEDROCK_HAIKU_PRICING["input_tokens"]
            daily_output_cost = (daily_output_tokens / 1000) * BEDROCK_HAIKU_PRICING["output_tokens"]
            daily_total = daily_input_cost + daily_output_cost

            daily_costs[strategy] = {
                "daily_cost": daily_total,
                "monthly_cost": daily_total * 30,
                "yearly_cost": daily_total * 365,
                "tokens_per_day": daily_input_tokens + daily_output_tokens
            }

        return daily_costs

    def print_production_estimate(self, prompts_per_day: int = 1000):
        """Print production cost estimates."""
        costs = self.estimate_production_costs(prompts_per_day)

        print(f"\n" + "="*70)
        print(f"🏭 PRODUCTION COST ESTIMATES ({prompts_per_day:,} prompts/day)")
        print("="*70)

        for strategy, details in costs.items():
            print(f"\n📈 {strategy.upper()}:")
            print(f"   • Daily:   ${details['daily_cost']:8.2f}")
            print(f"   • Monthly: ${details['monthly_cost']:8.2f}")
            print(f"   • Yearly:  ${details['yearly_cost']:8.2f}")
            print(f"   • Tokens/day: {details['tokens_per_day']:,}")

def main():
    """Run cost estimation."""
    estimator = BenchmarkCostEstimator()

    # Print benchmark costs
    estimator.print_cost_estimate()

    # Print production estimates
    estimator.print_production_estimate(prompts_per_day=1000)
    estimator.print_production_estimate(prompts_per_day=10000)

if __name__ == "__main__":
    main()