"""Semantic summarization for prompt compression using AI-powered text condensation."""

import boto3
import json
from typing import Dict, Tuple, Optional

class SemanticSummarizer:
    """Uses Claude Haiku to create semantic summaries of long prompts while preserving meaning."""

    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.summarizer_model = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    def compress_prompt(self, text: str, max_length_ratio: float = 0.5) -> Tuple[str, Dict[str, float]]:
        """
        Compress text using semantic summarization.

        Args:
            text: Original text to compress
            max_length_ratio: Maximum length as ratio of original (0.5 = 50% of original)

        Returns:
            Tuple of (compressed_text, metrics_dict)
        """
        original_length = len(text)
        target_length = int(original_length * max_length_ratio)

        # If text is already short, return as-is
        if original_length < 100:
            return text, {
                "original_length": original_length,
                "compressed_length": original_length,
                "compression_ratio": 1.0,
                "compression_percent": 0.0,
                "semantic_preservation": 1.0
            }

        try:
            # Create summarization prompt
            summarization_prompt = self._create_summarization_prompt(text, target_length)

            # Call Claude to create summary
            response = self.client.invoke_model(
                modelId=self.summarizer_model,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": min(4096, target_length // 3),  # Cap at Haiku max
                    "messages": [
                        {"role": "user", "content": summarization_prompt}
                    ],
                }),
            )

            result = json.loads(response["body"].read())
            compressed_text = result["content"][0]["text"].strip()

            # Validate summary quality
            if len(compressed_text) < 10:  # Too short, likely failed
                return text, self._create_error_metrics(original_length, "Summary too short")

            compressed_length = len(compressed_text)
            compression_ratio = compressed_length / original_length if original_length > 0 else 1.0

            metrics = {
                "original_length": original_length,
                "compressed_length": compressed_length,
                "compression_ratio": compression_ratio,
                "compression_percent": round((1 - compression_ratio) * 100, 2),
                "target_length": target_length,
                "target_achieved": compressed_length <= target_length * 1.2,  # 20% tolerance
                "semantic_preservation": self._estimate_semantic_preservation(compression_ratio),
                "summarization_tokens_used": result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
            }

            return compressed_text, metrics

        except Exception as e:
            print(f"Semantic summarization failed: {e}")
            return text, self._create_error_metrics(original_length, str(e))

    def _create_summarization_prompt(self, text: str, target_length: int) -> str:
        """Create an effective summarization prompt."""
        return f"""Compress the following text to approximately {target_length} characters while preserving all key information and meaning.

Rules:
- Maintain all important facts and context
- Preserve technical terms and specific details
- Use concise language without losing clarity
- Keep the same overall structure and intent
- If it's a question, preserve the question format

Original text:
{text}

Compressed version:"""

    def _estimate_semantic_preservation(self, compression_ratio: float) -> float:
        """
        Estimate semantic preservation based on compression ratio.
        This is a heuristic - in practice, you'd want to use semantic similarity metrics.
        """
        if compression_ratio >= 0.8:  # Light compression
            return 0.95
        elif compression_ratio >= 0.6:  # Moderate compression
            return 0.90
        elif compression_ratio >= 0.4:  # Heavy compression
            return 0.85
        else:  # Very heavy compression
            return 0.80

    def _create_error_metrics(self, original_length: int, error: str) -> Dict[str, float]:
        """Create error metrics when summarization fails."""
        return {
            "original_length": original_length,
            "compressed_length": original_length,
            "compression_ratio": 1.0,
            "compression_percent": 0.0,
            "error": error,
            "semantic_preservation": 1.0
        }

class ContextAwareSummarizer(SemanticSummarizer):
    """Enhanced summarizer that considers conversation context."""

    def compress_with_context(self, text: str, conversation_history: list,
                            max_length_ratio: float = 0.5) -> Tuple[str, Dict[str, float]]:
        """
        Compress text while considering conversation context.

        Args:
            text: Current text to compress
            conversation_history: Previous messages for context
            max_length_ratio: Target compression ratio

        Returns:
            Tuple of (compressed_text, metrics_dict)
        """
        # Extract context keywords from conversation history
        context_keywords = self._extract_context_keywords(conversation_history)

        original_length = len(text)
        target_length = int(original_length * max_length_ratio)

        try:
            # Create context-aware summarization prompt
            prompt = self._create_context_aware_prompt(text, context_keywords, target_length)

            response = self.client.invoke_model(
                modelId=self.summarizer_model,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": min(4096, target_length // 3),
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                }),
            )

            result = json.loads(response["body"].read())
            compressed_text = result["content"][0]["text"].strip()

            compressed_length = len(compressed_text)
            compression_ratio = compressed_length / original_length if original_length > 0 else 1.0

            metrics = {
                "original_length": original_length,
                "compressed_length": compressed_length,
                "compression_ratio": compression_ratio,
                "compression_percent": round((1 - compression_ratio) * 100, 2),
                "context_keywords_used": len(context_keywords),
                "semantic_preservation": self._estimate_semantic_preservation(compression_ratio),
                "context_aware": True
            }

            return compressed_text, metrics

        except Exception as e:
            return text, self._create_error_metrics(original_length, str(e))

    def _extract_context_keywords(self, conversation_history: list) -> list:
        """Extract important keywords from conversation history."""
        keywords = []
        for message in conversation_history[-3:]:  # Last 3 messages for context
            content = message.get("content", "")
            # Simple keyword extraction - could be enhanced with NLP
            words = content.split()
            keywords.extend([w for w in words if len(w) > 4 and w.isalpha()])

        # Return unique keywords
        return list(set(keywords))

    def _create_context_aware_prompt(self, text: str, context_keywords: list, target_length: int) -> str:
        """Create context-aware summarization prompt."""
        context_info = f"Context keywords from conversation: {', '.join(context_keywords[:10])}" if context_keywords else ""

        return f"""Compress the following text to approximately {target_length} characters while preserving meaning and considering the conversation context.

{context_info}

Rules:
- Preserve information relevant to the ongoing conversation
- Maintain technical accuracy and specific details
- Use concise language without losing essential meaning
- Keep context-relevant terms and concepts

Text to compress:
{text}

Compressed version:"""