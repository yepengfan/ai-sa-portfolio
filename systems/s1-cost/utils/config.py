"""Configuration and constants for Bedrock optimization strategies."""

import os
from typing import Dict, Any

# Model configurations
MODELS = {
    "haiku": {
        "id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "input_cost_per_1k": 0.000125,
        "output_cost_per_1k": 0.000625,
        "name": "Claude Haiku 4.5"
    },
    "sonnet": {
        "id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015,
        "name": "Claude Sonnet 4"
    }
}

# Pricing lookup (per 1K tokens) — used by benchmark scripts
PRICING = {
    "sonnet": {"input": 0.003, "output": 0.015},
    "haiku":  {"input": 0.000125, "output": 0.000625},
    # Caching: write = 1.25x input, read = 0.1x input
    "sonnet_cache_write": 0.00375,
    "sonnet_cache_read":  0.0003,
    # Batch: 50% of on-demand
    "sonnet_batch": {"input": 0.0015, "output": 0.0075},
    "haiku_batch":  {"input": 0.0000625, "output": 0.0003125},
}

# AWS configuration
AWS_REGION = "us-east-1"

# Experiment configuration
EXPERIMENT_CONFIG = {
    "baseline_queries_count": 50,
    "test_queries_count": 50,
    "max_tokens": 1024,
    "results_dir": "./results"
}

# Strategy-specific configurations
COMPRESSION_CONFIG = {
    "manual_refiner": {
        "target_reduction": 0.3,  # 30% reduction target
        "preserve_meaning": True
    },
    "semantic_summarizer": {
        "max_length_ratio": 0.5,  # Max 50% of original length
        "model_for_summary": "haiku"
    },
    "relevance_filter": {
        "similarity_threshold": 0.7,
        "max_context_chunks": 10
    },
    "structure_optimizer": {
        "preferred_format": "json",
        "bullet_point_threshold": 3
    },
    "llmlingua": {
        "compression_ratio": 0.5,  # Target 50% compression
        "preserve_questions": True
    }
}

CACHING_CONFIG = {
    "ttl_minutes": 60,  # 1 hour TTL
    "cache_system_prompts": True,
    "cache_context": True
}

ROUTING_CONFIG = {
    "simple_keywords": [
        "what is", "define", "explain", "hello", "hi", "simple",
        "basic", "quick", "short"
    ],
    "complex_keywords": [
        "analyze", "compare", "detailed", "comprehensive", "complex",
        "reasoning", "logic", "prove", "algorithm", "code"
    ],
    "default_model": "haiku"
}

BATCH_CONFIG = {
    "batch_size": 10,
    "max_wait_time": 300,  # 5 minutes max wait
    "job_prefix": "aisa-experiment"
}

def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get model configuration by name."""
    return MODELS.get(model_name, MODELS["haiku"])

def ensure_results_dir():
    """Ensure results directory exists."""
    os.makedirs(EXPERIMENT_CONFIG["results_dir"], exist_ok=True)