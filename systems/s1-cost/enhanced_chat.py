"""Enhanced chat application with all Bedrock optimization strategies integrated."""

import sys
import time
from typing import Dict, List, Optional, Any
import uuid

# Import all optimization strategies
from strategies.compression.manual_refiner import ManualRefiner, AdvancedManualRefiner
from strategies.compression.semantic_summarizer import SemanticSummarizer, ContextAwareSummarizer
from strategies.compression.relevance_filter import RelevanceFilter, AdvancedRelevanceFilter
from strategies.compression.structure_optimizer import StructureOptimizer, AdvancedStructureOptimizer
from strategies.compression.llmlingua_compressor import LLMLinguaCompressor, BatchLLMLinguaCompressor
from strategies.prompt_caching import BedrockPromptCaching, SmartPromptCaching
from strategies.model_routing import ModelRouter
from strategies.batch_processing import BedrockBatchProcessor, BatchQueryManager

# Import experiment infrastructure
from experiment.metrics_collector import MetricsCollector
from experiment.data_exporter import ResearchDataExporter
from utils.config import get_model_config, ensure_results_dir

class EnhancedBedrockChat:
    """
    Enhanced Bedrock chat with integrated optimization strategies.
    Supports all 4 optimization approaches: compression, caching, routing, batch processing.
    """

    def __init__(self):
        # Initialize all optimization strategies
        self.manual_refiner = ManualRefiner()
        self.semantic_summarizer = SemanticSummarizer()
        self.relevance_filter = RelevanceFilter()
        self.structure_optimizer = StructureOptimizer()
        self.llmlingua_compressor = LLMLinguaCompressor()

        self.prompt_caching = SmartPromptCaching()
        self.model_router = ModelRouter()
        self.batch_manager = BatchQueryManager()

        # Experiment infrastructure
        self.metrics_collector = MetricsCollector()
        self.data_exporter = ResearchDataExporter()

        # Chat state
        self.messages = []
        self.session_id = str(uuid.uuid4())[:8]

        # Strategy settings
        self.active_strategies = set()
        self.compression_strategy = None

        ensure_results_dir()

    def run_interactive_session(self):
        """Run interactive chat session with strategy selection."""
        print("🚀 Enhanced Bedrock Chat with Optimization Strategies")
        print("=" * 60)

        self._show_available_strategies()
        self._configure_strategies()

        print(f"\n💬 Chat Session Started (ID: {self.session_id})")
        print("Type 'quit' to exit, 'stats' for statistics, 'strategies' to reconfigure\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit']:
                    self._session_cleanup()
                    break

                elif user_input.lower() == 'stats':
                    self._show_session_stats()
                    continue

                elif user_input.lower() == 'strategies':
                    self._configure_strategies()
                    continue

                elif user_input.lower() == 'export':
                    self._export_session_data()
                    continue

                # Process query with active optimizations
                response = self._process_optimized_query(user_input)

                if response:
                    print(f"\nAssistant: {response['text']}")
                    self._show_query_metrics(response['metrics'])
                else:
                    print("\n❌ Query processing failed")

            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted by user")
                self._session_cleanup()
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    def _show_available_strategies(self):
        """Show available optimization strategies."""
        print("\n📋 Available Optimization Strategies:")
        print("1. Prompt Compression:")
        print("   • manual - Manual text refinement")
        print("   • semantic - AI-powered summarization")
        print("   • relevance - Context relevance filtering")
        print("   • structure - Structure optimization")
        print("   • llmlingua - Token-level compression")
        print("\n2. prompt_caching - Bedrock native prompt caching")
        print("3. model_routing - Intelligent model selection")
        print("4. batch_processing - Queue for batch inference")

    def _configure_strategies(self):
        """Configure active optimization strategies."""
        print("\n⚙️ Strategy Configuration")
        print("Enter strategies to activate (space-separated):")
        print("Example: manual prompt_caching model_routing")

        strategy_input = input("Strategies: ").strip()

        if not strategy_input:
            print("No strategies selected - using baseline mode")
            self.active_strategies.clear()
            return

        strategies = strategy_input.split()
        self.active_strategies.clear()
        compression_strategies = ['manual', 'semantic', 'relevance', 'structure', 'llmlingua']

        for strategy in strategies:
            if strategy in compression_strategies:
                self.active_strategies.add('compression')
                self.compression_strategy = strategy
            elif strategy in ['prompt_caching', 'model_routing', 'batch_processing']:
                self.active_strategies.add(strategy)

        print(f"✅ Active strategies: {', '.join(self.active_strategies)}")
        if 'compression' in self.active_strategies:
            print(f"   Compression method: {self.compression_strategy}")

    def _process_optimized_query(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Process query with active optimization strategies."""
        start_time = time.time()
        query_id = f"q_{len(self.messages)//2 + 1:03d}"

        # Add user message to conversation
        self.messages.append({"role": "user", "content": user_input})
        original_user_input = user_input

        # Apply optimizations based on active strategies
        optimization_metrics = {}

        # 1. Apply compression if active
        if 'compression' in self.active_strategies and self.compression_strategy:
            user_input, compression_metrics = self._apply_compression(user_input)
            optimization_metrics['compression'] = compression_metrics

        # 2. Handle batch processing
        if 'batch_processing' in self.active_strategies:
            return self._handle_batch_query(user_input, query_id, start_time)

        # 3. Determine model via routing
        if 'model_routing' in self.active_strategies:
            model_config, routing_metrics = self._apply_model_routing(user_input)
            optimization_metrics['routing'] = routing_metrics
        else:
            model_config = get_model_config('haiku')  # Default

        # Update messages with optimized input
        self.messages[-1]["content"] = user_input

        # 4. Apply caching and invoke model
        try:
            if 'prompt_caching' in self.active_strategies:
                result, cache_metrics = self.prompt_caching.smart_invoke(
                    model_id=model_config['id'],
                    messages=self.messages
                )
                optimization_metrics['caching'] = cache_metrics
            else:
                # Standard invoke via model router or direct
                if 'model_routing' in self.active_strategies:
                    result, routing_metrics = self.model_router.route_and_invoke(
                        user_input=user_input,
                        messages=self.messages
                    )
                    optimization_metrics['routing'].update(routing_metrics)
                else:
                    # Fallback to original chat.py method
                    import boto3
                    import json
                    client = boto3.client("bedrock-runtime", region_name="us-east-1")

                    response = client.invoke_model(
                        modelId=model_config['id'],
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 1024,
                            "messages": self.messages,
                        }),
                    )
                    result = json.loads(response["body"].read())

        except Exception as e:
            print(f"Model invocation error: {e}")
            return None

        if not result:
            return None

        assistant_text = result["content"][0]["text"]
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]

        # Add assistant response to conversation
        self.messages.append({"role": "assistant", "content": assistant_text})

        # Record metrics
        strategy_name = self._get_strategy_name()
        query_metrics = self.metrics_collector.record_query(
            strategy_name=strategy_name,
            query_id=query_id,
            user_input=original_user_input,
            response=assistant_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_per_1k=model_config['input_cost_per_1k'],
            output_cost_per_1k=model_config['output_cost_per_1k'],
            start_time=start_time,
            **self._flatten_optimization_metrics(optimization_metrics)
        )

        return {
            'text': assistant_text,
            'metrics': query_metrics,
            'optimization_details': optimization_metrics
        }

    def _apply_compression(self, text: str) -> tuple[str, Dict[str, Any]]:
        """Apply selected compression strategy."""
        if self.compression_strategy == 'manual':
            return self.manual_refiner.compress_prompt(text)
        elif self.compression_strategy == 'semantic':
            return self.semantic_summarizer.compress_prompt(text)
        elif self.compression_strategy == 'relevance':
            # Use conversation context for relevance filtering
            context = " ".join([msg["content"] for msg in self.messages[-4:]])
            return self.relevance_filter.compress_prompt(context, text)
        elif self.compression_strategy == 'structure':
            return self.structure_optimizer.compress_prompt(text)
        elif self.compression_strategy == 'llmlingua':
            return self.llmlingua_compressor.compress_prompt(text)
        else:
            return text, {}

    def _apply_model_routing(self, user_input: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Apply model routing and return selected model config."""
        # The model router handles the actual routing and invocation
        # Here we just need to prepare for it
        haiku_config = get_model_config('haiku')
        sonnet_config = get_model_config('sonnet')

        # Return haiku as default - routing happens in route_and_invoke
        return haiku_config, {"routing_prepared": True}

    def _handle_batch_query(self, user_input: str, query_id: str, start_time: float) -> Dict[str, Any]:
        """Handle batch processing workflow."""
        # Queue the query
        self.batch_manager.queue_query(user_input, self.messages.copy())

        # Try to submit batch if enough queries
        job_arn = self.batch_manager.submit_batch_when_ready(batch_size=5)  # Smaller batch for demo

        if job_arn:
            print(f"🔄 Batch job submitted: {job_arn}")

        # Check for completed batches
        completed_jobs = self.batch_manager.check_completed_jobs()
        if completed_jobs:
            print(f"✅ {len(completed_jobs)} batch job(s) completed")

        # For now, return a placeholder response for queued items
        return {
            'text': f"Query queued for batch processing. Queue status: {self.batch_manager.get_queue_status()}",
            'metrics': None,
            'batch_info': {
                'queued': True,
                'job_submitted': job_arn is not None,
                'queue_status': self.batch_manager.get_queue_status()
            }
        }

    def _flatten_optimization_metrics(self, optimization_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten optimization metrics for storage."""
        flat_metrics = {}

        for strategy, metrics in optimization_metrics.items():
            if strategy == 'compression':
                flat_metrics['compression_ratio'] = metrics.get('compression_ratio', 1.0)
            elif strategy == 'caching':
                flat_metrics['cache_hit'] = metrics.get('cache_hit', False)
            elif strategy == 'routing':
                flat_metrics['routing_decision'] = metrics.get('selected_model', '')
            elif strategy == 'batch':
                flat_metrics['batch_position'] = metrics.get('batch_position', -1)

        return flat_metrics

    def _get_strategy_name(self) -> str:
        """Get current strategy combination name."""
        if not self.active_strategies:
            return "baseline"

        strategy_parts = []
        if 'compression' in self.active_strategies:
            strategy_parts.append(self.compression_strategy)
        if 'prompt_caching' in self.active_strategies:
            strategy_parts.append('caching')
        if 'model_routing' in self.active_strategies:
            strategy_parts.append('routing')
        if 'batch_processing' in self.active_strategies:
            strategy_parts.append('batch')

        return '_'.join(strategy_parts)

    def _show_query_metrics(self, metrics):
        """Show query metrics in a concise format."""
        if not metrics:
            return

        print(f"📊 [Tokens: {metrics.input_tokens}→{metrics.output_tokens} | "
              f"Cost: ${metrics.total_cost:.6f} | "
              f"Latency: {metrics.latency_ms}ms]")

        # Show compression ratio if applicable
        if hasattr(metrics, 'compression_ratio') and metrics.compression_ratio < 1.0:
            compression_percent = (1 - metrics.compression_ratio) * 100
            print(f"📉 Compression: {compression_percent:.1f}% reduction")

    def _show_session_stats(self):
        """Show current session statistics."""
        print("\n📈 Session Statistics")
        print("=" * 40)

        strategy_name = self._get_strategy_name()
        stats = self.metrics_collector.get_strategy_summary(strategy_name)

        if 'error' in stats:
            print("No queries processed yet")
            return

        print(f"Strategy: {strategy_name}")
        print(f"Total queries: {stats['total_queries']}")
        print(f"Avg tokens: {stats['avg_input_tokens']:.1f} input / {stats['avg_output_tokens']:.1f} output")
        print(f"Avg cost per query: ${stats['avg_total_cost']:.6f}")
        print(f"Total session cost: ${stats['total_cost']:.6f}")
        print(f"Avg latency: {stats['avg_latency_ms']:.1f}ms")

        if stats['avg_compression_ratio'] < 1.0:
            print(f"Avg compression: {(1-stats['avg_compression_ratio'])*100:.1f}%")

        if stats['cache_hit_rate'] > 0:
            print(f"Cache hit rate: {stats['cache_hit_rate']*100:.1f}%")

    def _export_session_data(self):
        """Export current session data for analysis."""
        print("\n📤 Exporting session data...")

        # Export current metrics
        strategy_name = self._get_strategy_name()
        csv_path = self.metrics_collector.export_csv(strategy_name)
        json_path = self.metrics_collector.export_json(strategy_name)

        print(f"✅ Data exported:")
        print(f"   CSV: {csv_path}")
        print(f"   JSON: {json_path}")

    def _session_cleanup(self):
        """Cleanup when session ends."""
        print(f"\n📊 Final Session Summary:")
        print(f"Session ID: {self.session_id}")
        print(f"Total messages: {len(self.messages)}")

        if self.messages:
            self._show_session_stats()
            print("\nExporting session data...")
            self._export_session_data()

        print("\n👋 Session ended. Data saved for analysis.")

def main():
    """Main function to run enhanced chat."""
    try:
        chat = EnhancedBedrockChat()
        chat.run_interactive_session()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()