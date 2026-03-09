"""Intelligent model routing - route simple queries to Haiku, complex to Sonnet for cost optimization."""

import boto3
import json
import re
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"

class ModelRouter:
    """
    Routes queries to appropriate models based on complexity analysis.
    Simple queries → Claude Haiku (lower cost)
    Complex queries → Claude Sonnet (higher capability)
    """

    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)

        # Model configurations
        self.models = {
            "haiku": {
                "id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                "cost_per_1k_input": 0.000125,
                "cost_per_1k_output": 0.000625,
                "name": "Claude Haiku 4.5",
                "suitable_for": ["simple", "moderate"]
            },
            "sonnet": {
                "id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
                "name": "Claude Sonnet 3.5",
                "suitable_for": ["moderate", "complex"]
            }
        }

        # Routing statistics
        self.routing_stats = {
            "total_queries": 0,
            "haiku_routed": 0,
            "sonnet_routed": 0,
            "routing_decisions": [],
            "cost_savings": 0.0
        }

    def route_and_invoke(self, user_input: str, messages: List[Dict[str, str]],
                        max_tokens: int = 1024,
                        force_model: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Route query to appropriate model and invoke.

        Args:
            user_input: Current user query
            messages: Conversation history
            max_tokens: Maximum output tokens
            force_model: Force specific model ("haiku" or "sonnet")

        Returns:
            Tuple of (response, routing_metrics)
        """
        self.routing_stats["total_queries"] += 1

        # Determine model to use
        if force_model:
            selected_model = force_model
            complexity = QueryComplexity.MODERATE  # Default for forced routing
            routing_reason = f"Force routed to {force_model}"
        else:
            complexity, routing_reason = self._analyze_query_complexity(user_input, messages)
            selected_model = self._select_model_for_complexity(complexity)

        # Record routing decision
        decision = {
            "query": user_input[:100],  # First 100 chars for analysis
            "complexity": complexity.value,
            "selected_model": selected_model,
            "reason": routing_reason
        }
        self.routing_stats["routing_decisions"].append(decision)

        # Update routing counters
        if selected_model == "haiku":
            self.routing_stats["haiku_routed"] += 1
        else:
            self.routing_stats["sonnet_routed"] += 1

        # Invoke selected model
        model_config = self.models[selected_model]
        try:
            response = self.client.invoke_model(
                modelId=model_config["id"],
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": messages,
                }),
            )

            result = json.loads(response["body"].read())

            # Calculate cost savings from routing
            cost_savings = self._calculate_routing_savings(result, selected_model)
            self.routing_stats["cost_savings"] += cost_savings

            # Create routing metrics
            routing_metrics = {
                "selected_model": selected_model,
                "model_name": model_config["name"],
                "complexity": complexity.value,
                "routing_reason": routing_reason,
                "cost_savings": cost_savings,
                "input_tokens": result["usage"]["input_tokens"],
                "output_tokens": result["usage"]["output_tokens"],
                "model_cost_per_1k_input": model_config["cost_per_1k_input"],
                "model_cost_per_1k_output": model_config["cost_per_1k_output"]
            }

            return result, routing_metrics

        except Exception as e:
            error_metrics = {
                "selected_model": selected_model,
                "complexity": complexity.value,
                "error": str(e),
                "cost_savings": 0.0
            }
            return None, error_metrics

    def _analyze_query_complexity(self, query: str, messages: List[Dict[str, str]]) -> Tuple[QueryComplexity, str]:
        """
        Analyze query complexity using multiple methods.

        Returns:
            Tuple of (complexity_level, reasoning)
        """
        # Method 1: Keyword-based analysis
        keyword_complexity, keyword_reason = self._keyword_based_complexity(query)

        # Method 2: Query structure analysis
        structure_complexity, structure_reason = self._structure_based_complexity(query)

        # Method 3: Context analysis
        context_complexity, context_reason = self._context_based_complexity(query, messages)

        # Method 4: Length and technical content analysis
        content_complexity, content_reason = self._content_based_complexity(query)

        # Combine analyses to make final decision
        complexities = [keyword_complexity, structure_complexity, context_complexity, content_complexity]
        reasons = [keyword_reason, structure_reason, context_reason, content_reason]

        # Count complexity votes
        simple_votes = complexities.count(QueryComplexity.SIMPLE)
        moderate_votes = complexities.count(QueryComplexity.MODERATE)
        complex_votes = complexities.count(QueryComplexity.COMPLEX)

        # Determine final complexity (bias toward higher complexity for safety)
        if complex_votes >= 1:  # Any complex vote → complex
            final_complexity = QueryComplexity.COMPLEX
            final_reason = f"Complex routing: {', '.join(reasons)}"
        elif moderate_votes >= 2:  # Multiple moderate votes → moderate
            final_complexity = QueryComplexity.MODERATE
            final_reason = f"Moderate routing: {', '.join(reasons)}"
        else:
            final_complexity = QueryComplexity.SIMPLE
            final_reason = f"Simple routing: {', '.join(reasons)}"

        return final_complexity, final_reason

    def _keyword_based_complexity(self, query: str) -> Tuple[QueryComplexity, str]:
        """Analyze complexity based on keywords in the query."""
        query_lower = query.lower()

        # Complex keywords indicating need for advanced reasoning
        complex_keywords = [
            'analyze', 'compare', 'evaluate', 'assess', 'critique', 'reasoning', 'logic',
            'algorithm', 'optimize', 'design', 'architecture', 'strategy', 'complex',
            'detailed', 'comprehensive', 'in-depth', 'thorough', 'advanced', 'sophisticated',
            'debug', 'troubleshoot', 'diagnose', 'solve', 'prove', 'demonstrate',
            'research', 'investigate', 'explore', 'discover'
        ]

        # Simple keywords indicating straightforward queries
        simple_keywords = [
            'what is', 'define', 'explain', 'describe', 'tell me', 'show me',
            'hello', 'hi', 'help', 'basic', 'simple', 'quick', 'short',
            'list', 'name', 'identify', 'find'
        ]

        # Moderate keywords
        moderate_keywords = [
            'how to', 'create', 'build', 'implement', 'generate', 'write',
            'modify', 'update', 'change', 'fix', 'improve', 'enhance'
        ]

        # Count keyword matches
        complex_matches = sum(1 for keyword in complex_keywords if keyword in query_lower)
        simple_matches = sum(1 for keyword in simple_keywords if keyword in query_lower)
        moderate_matches = sum(1 for keyword in moderate_keywords if keyword in query_lower)

        if complex_matches > 0:
            return QueryComplexity.COMPLEX, f"Complex keywords: {complex_matches}"
        elif moderate_matches > 0:
            return QueryComplexity.MODERATE, f"Moderate keywords: {moderate_matches}"
        elif simple_matches > 0:
            return QueryComplexity.SIMPLE, f"Simple keywords: {simple_matches}"
        else:
            return QueryComplexity.MODERATE, "No clear keyword indicators"

    def _structure_based_complexity(self, query: str) -> Tuple[QueryComplexity, str]:
        """Analyze complexity based on query structure."""
        # Multiple questions or complex sentence structure
        question_marks = query.count('?')
        sentences = len(re.findall(r'[.!?]+', query))
        words = len(query.split())

        if question_marks > 2 or sentences > 3:
            return QueryComplexity.COMPLEX, f"Multi-part query: {question_marks} questions, {sentences} sentences"
        elif words > 50:
            return QueryComplexity.MODERATE, f"Long query: {words} words"
        elif words < 10:
            return QueryComplexity.SIMPLE, f"Short query: {words} words"
        else:
            return QueryComplexity.MODERATE, f"Medium query: {words} words"

    def _context_based_complexity(self, query: str, messages: List[Dict[str, str]]) -> Tuple[QueryComplexity, str]:
        """Analyze complexity based on conversation context."""
        if len(messages) <= 2:
            return QueryComplexity.SIMPLE, "No significant context"

        # Analyze previous messages for technical complexity
        context_content = " ".join([msg["content"] for msg in messages[-4:]])  # Last 4 messages
        context_lower = context_content.lower()

        technical_terms = ['code', 'function', 'class', 'database', 'api', 'algorithm',
                          'variable', 'method', 'object', 'array', 'json', 'xml']

        technical_count = sum(1 for term in technical_terms if term in context_lower)

        if technical_count > 5:
            return QueryComplexity.COMPLEX, f"Technical context: {technical_count} technical terms"
        elif technical_count > 2:
            return QueryComplexity.MODERATE, f"Some technical context: {technical_count} technical terms"
        else:
            return QueryComplexity.SIMPLE, f"Simple context: {technical_count} technical terms"

    def _content_based_complexity(self, query: str) -> Tuple[QueryComplexity, str]:
        """Analyze complexity based on content patterns."""
        # Check for code patterns
        code_patterns = [
            r'```', r'`[^`]+`', r'\bdef\s+\w+', r'\bclass\s+\w+', r'\bfunction\s+\w+',
            r'import\s+\w+', r'#include', r'<\w+>', r'\{[^}]+\}', r'\[[^\]]+\]'
        ]

        code_matches = sum(1 for pattern in code_patterns if re.search(pattern, query))

        # Check for mathematical content
        math_patterns = [r'\d+\s*[+\-*/]\s*\d+', r'[∑∏∫∂]', r'\b(equation|formula|calculate)\b']
        math_matches = sum(1 for pattern in math_patterns if re.search(pattern, query, re.IGNORECASE))

        # Check for data analysis content
        data_patterns = [r'\b(dataset|dataframe|csv|json|sql)\b', r'\b(analysis|statistics|correlation)\b']
        data_matches = sum(1 for pattern in data_patterns if re.search(pattern, query, re.IGNORECASE))

        total_technical_matches = code_matches + math_matches + data_matches

        if total_technical_matches > 3:
            return QueryComplexity.COMPLEX, f"High technical content: {total_technical_matches} patterns"
        elif total_technical_matches > 1:
            return QueryComplexity.MODERATE, f"Some technical content: {total_technical_matches} patterns"
        else:
            return QueryComplexity.SIMPLE, f"Low technical content: {total_technical_matches} patterns"

    def _select_model_for_complexity(self, complexity: QueryComplexity) -> str:
        """Select appropriate model based on complexity."""
        if complexity == QueryComplexity.SIMPLE:
            return "haiku"  # Cost-effective for simple queries
        elif complexity == QueryComplexity.MODERATE:
            return "haiku"  # Haiku can handle most moderate tasks well
        else:  # COMPLEX
            return "sonnet"  # Use more capable model for complex reasoning

    def _calculate_routing_savings(self, result: Dict[str, Any], selected_model: str) -> float:
        """Calculate cost savings from routing decision."""
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]

        # Calculate actual cost with selected model
        selected_config = self.models[selected_model]
        actual_cost = ((input_tokens / 1000) * selected_config["cost_per_1k_input"] +
                      (output_tokens / 1000) * selected_config["cost_per_1k_output"])

        # Calculate cost if we always used Sonnet (more expensive model)
        sonnet_config = self.models["sonnet"]
        sonnet_cost = ((input_tokens / 1000) * sonnet_config["cost_per_1k_input"] +
                      (output_tokens / 1000) * sonnet_config["cost_per_1k_output"])

        # Savings = what we would have paid with Sonnet - what we actually paid
        savings = sonnet_cost - actual_cost if selected_model == "haiku" else 0.0

        return max(0.0, savings)  # Ensure non-negative

    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive routing statistics."""
        total = self.routing_stats["total_queries"]
        if total == 0:
            return {"error": "No queries routed yet"}

        haiku_rate = self.routing_stats["haiku_routed"] / total
        sonnet_rate = self.routing_stats["sonnet_routed"] / total

        # Analyze complexity distribution
        complexity_dist = {}
        for decision in self.routing_stats["routing_decisions"]:
            complexity = decision["complexity"]
            complexity_dist[complexity] = complexity_dist.get(complexity, 0) + 1

        # Calculate average savings per query
        avg_savings_per_query = self.routing_stats["cost_savings"] / total if total > 0 else 0

        return {
            "total_queries": total,
            "haiku_routed": self.routing_stats["haiku_routed"],
            "sonnet_routed": self.routing_stats["sonnet_routed"],
            "haiku_rate": round(haiku_rate, 3),
            "sonnet_rate": round(sonnet_rate, 3),
            "total_cost_savings": round(self.routing_stats["cost_savings"], 6),
            "avg_savings_per_query": round(avg_savings_per_query, 6),
            "complexity_distribution": complexity_dist,
            "recent_decisions": self.routing_stats["routing_decisions"][-5:]  # Last 5 decisions
        }

    def reset_routing_stats(self):
        """Reset routing statistics."""
        self.routing_stats = {
            "total_queries": 0,
            "haiku_routed": 0,
            "sonnet_routed": 0,
            "routing_decisions": [],
            "cost_savings": 0.0
        }