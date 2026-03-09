"""Bedrock native prompt caching implementation for cost optimization."""

import boto3
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

class BedrockPromptCaching:
    """
    Implements Bedrock native prompt caching for Claude models.
    Provides 90% discount on cache reads with configurable TTL.
    """

    def __init__(self, region_name: str = "us-east-1", ttl_minutes: int = 60):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.ttl_minutes = ttl_minutes
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "total_queries": 0,
            "cache_savings": 0.0
        }

    def invoke_with_cache(self, model_id: str, messages: List[Dict[str, str]],
                         system_prompt: Optional[str] = None,
                         max_tokens: int = 1024,
                         cache_system: bool = True,
                         cache_context: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Invoke model with prompt caching enabled.

        Args:
            model_id: Bedrock model ID
            messages: Conversation messages
            system_prompt: Optional system prompt to cache
            max_tokens: Maximum output tokens
            cache_system: Whether to cache system prompt
            cache_context: Whether to cache conversation context

        Returns:
            Tuple of (response, cache_metrics)
        """
        self.cache_stats["total_queries"] += 1

        # Prepare request body with caching
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }

        # Add system prompt with caching if provided
        if system_prompt and cache_system:
            body["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        elif system_prompt:
            body["system"] = system_prompt

        # Apply context caching to conversation history
        if cache_context and len(messages) > 2:
            # Cache the conversation context (all messages except the last user message)
            cached_messages = self._apply_context_caching(messages)
            body["messages"] = cached_messages

        try:
            start_time = time.time()

            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )

            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds

            result = json.loads(response["body"].read())

            # Analyze cache usage from response
            cache_metrics = self._analyze_cache_usage(result, latency)

            return result, cache_metrics

        except Exception as e:
            error_metrics = {
                "cache_hit": False,
                "cache_write": False,
                "latency_ms": 0,
                "error": str(e)
            }
            return None, error_metrics

    def _apply_context_caching(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Apply caching to conversation context.
        Caches all messages except the latest user message.
        """
        cached_messages = messages.copy()

        # Find the last assistant message to apply cache control
        last_assistant_idx = -1
        for i in range(len(cached_messages) - 1, -1, -1):
            if cached_messages[i]["role"] == "assistant":
                last_assistant_idx = i
                break

        # Apply cache control to the last assistant message
        if last_assistant_idx >= 0:
            cached_messages[last_assistant_idx]["cache_control"] = {"type": "ephemeral"}

        return cached_messages

    def _analyze_cache_usage(self, response: Dict[str, Any], latency: float) -> Dict[str, Any]:
        """
        Analyze response to determine cache hit/miss status.
        Note: This is simplified - actual cache analysis would require Bedrock API response fields.
        """
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Heuristic: Lower latency often indicates cache hit
        cache_hit = latency < 500  # Less than 500ms suggests cache hit

        if cache_hit:
            self.cache_stats["hits"] += 1
        else:
            self.cache_stats["misses"] += 1
            self.cache_stats["writes"] += 1

        # Calculate savings (90% discount on cached tokens)
        cache_savings = 0.0
        if cache_hit:
            # Assume 70% of input tokens were from cache (conservative estimate)
            cached_tokens = int(input_tokens * 0.7)
            cache_savings = cached_tokens * 0.9  # 90% savings on cached tokens

        self.cache_stats["cache_savings"] += cache_savings

        cache_metrics = {
            "cache_hit": cache_hit,
            "cache_write": not cache_hit,
            "latency_ms": round(latency, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cached_tokens": int(input_tokens * 0.7) if cache_hit else 0,
            "estimated_cache_savings": cache_savings,
            "cache_hit_rate": self.cache_stats["hits"] / self.cache_stats["total_queries"],
            "total_cache_savings": self.cache_stats["cache_savings"]
        }

        return cache_metrics

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_queries = self.cache_stats["total_queries"]
        if total_queries == 0:
            return {"error": "No queries processed yet"}

        hit_rate = self.cache_stats["hits"] / total_queries
        miss_rate = self.cache_stats["misses"] / total_queries

        return {
            "total_queries": total_queries,
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "cache_writes": self.cache_stats["writes"],
            "hit_rate": round(hit_rate, 3),
            "miss_rate": round(miss_rate, 3),
            "total_cache_savings": round(self.cache_stats["cache_savings"], 6),
            "ttl_minutes": self.ttl_minutes,
            "cache_efficiency": round(hit_rate * 0.9, 3)  # Hit rate * 90% savings
        }

    def reset_cache_stats(self):
        """Reset cache statistics."""
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "total_queries": 0,
            "cache_savings": 0.0
        }

class SmartPromptCaching(BedrockPromptCaching):
    """
    Enhanced prompt caching with intelligent cache management.
    Automatically determines what to cache based on content patterns.
    """

    def __init__(self, region_name: str = "us-east-1", ttl_minutes: int = 60):
        super().__init__(region_name, ttl_minutes)
        self.cache_patterns = {
            "system_prompts": [],
            "common_contexts": [],
            "few_shot_examples": []
        }

    def smart_invoke(self, model_id: str, messages: List[Dict[str, str]],
                    system_prompt: Optional[str] = None,
                    max_tokens: int = 1024) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Intelligently apply caching based on content analysis.

        Args:
            model_id: Bedrock model ID
            messages: Conversation messages
            system_prompt: Optional system prompt
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (response, cache_metrics)
        """
        # Analyze content to determine optimal caching strategy
        cache_strategy = self._analyze_cache_strategy(messages, system_prompt)

        # Apply intelligent caching
        return self.invoke_with_cache(
            model_id=model_id,
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            cache_system=cache_strategy["cache_system"],
            cache_context=cache_strategy["cache_context"]
        )

    def _analyze_cache_strategy(self, messages: List[Dict[str, str]],
                              system_prompt: Optional[str] = None) -> Dict[str, bool]:
        """
        Analyze content to determine optimal caching strategy.

        Returns:
            Dictionary with caching recommendations
        """
        strategy = {
            "cache_system": True,  # Default to cache system prompts
            "cache_context": False
        }

        # Cache system prompt if it's substantial
        if system_prompt and len(system_prompt) > 100:
            strategy["cache_system"] = True

        # Cache context if conversation is long and has repeated patterns
        if len(messages) > 4:
            # Check for repeated patterns that benefit from caching
            context_length = sum(len(msg["content"]) for msg in messages[:-1])
            if context_length > 500:  # Substantial context
                strategy["cache_context"] = True

            # Check for few-shot examples or structured content
            if self._has_few_shot_examples(messages):
                strategy["cache_context"] = True

        return strategy

    def _has_few_shot_examples(self, messages: List[Dict[str, str]]) -> bool:
        """
        Detect if messages contain few-shot examples that should be cached.
        """
        # Look for patterns indicating few-shot examples
        example_indicators = [
            "example:", "for example", "e.g.", "instance:",
            "input:", "output:", "question:", "answer:"
        ]

        for message in messages[:-1]:  # Exclude current user message
            content_lower = message["content"].lower()
            if any(indicator in content_lower for indicator in example_indicators):
                return True

        return False

    def learn_cache_pattern(self, content_type: str, content: str):
        """
        Learn common patterns for more efficient caching.

        Args:
            content_type: Type of content ("system_prompts", "common_contexts", "few_shot_examples")
            content: Content to learn from
        """
        if content_type in self.cache_patterns:
            # Simple pattern learning - store content hashes or key phrases
            if len(content) > 50:  # Only learn from substantial content
                self.cache_patterns[content_type].append({
                    "length": len(content),
                    "hash": hash(content),
                    "timestamp": datetime.now().isoformat(),
                    "sample": content[:100]  # Store sample for analysis
                })

                # Keep only recent patterns (last 100)
                if len(self.cache_patterns[content_type]) > 100:
                    self.cache_patterns[content_type] = self.cache_patterns[content_type][-100:]

    def get_learned_patterns(self) -> Dict[str, Any]:
        """Get statistics about learned cache patterns."""
        stats = {}
        for pattern_type, patterns in self.cache_patterns.items():
            if patterns:
                avg_length = sum(p["length"] for p in patterns) / len(patterns)
                stats[pattern_type] = {
                    "count": len(patterns),
                    "avg_length": round(avg_length, 2),
                    "recent_samples": [p["sample"] for p in patterns[-3:]]
                }
            else:
                stats[pattern_type] = {"count": 0, "avg_length": 0, "recent_samples": []}

        return stats