"""LLMLingua-inspired compression using Claude Haiku for token-level optimization."""

import boto3
import json
import re
from typing import Dict, List, Tuple, Optional

class LLMLinguaCompressor:
    """
    Simplified LLMLingua-inspired compression using Claude Haiku.
    Uses a small model to identify and remove low-information-value tokens.
    """

    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.compressor_model = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    def compress_prompt(self, text: str, compression_ratio: float = 0.5,
                       preserve_questions: bool = True) -> Tuple[str, Dict[str, float]]:
        """
        Compress text using LLMLingua-inspired token optimization.

        Args:
            text: Original text to compress
            compression_ratio: Target compression ratio (0.5 = 50% of original tokens)
            preserve_questions: Whether to preserve question structures

        Returns:
            Tuple of (compressed_text, metrics_dict)
        """
        original_length = len(text)
        original_words = len(text.split())

        if original_length < 50:  # Too short to compress meaningfully
            return text, self._create_metrics(original_length, original_length, 1.0, 0)

        try:
            # Step 1: Identify critical tokens that must be preserved
            critical_tokens = self._identify_critical_tokens(text, preserve_questions)

            # Step 2: Use Claude to identify tokens to remove
            tokens_to_remove = self._identify_removable_tokens(text, compression_ratio, critical_tokens)

            # Step 3: Apply token removal while preserving meaning
            compressed_text = self._apply_token_removal(text, tokens_to_remove, critical_tokens)

            # Step 4: Clean up and validate result
            compressed_text = self._post_process_compression(compressed_text)

            compressed_length = len(compressed_text)
            compression_ratio_actual = compressed_length / original_length if original_length > 0 else 1.0

            compressed_words = len(compressed_text.split())
            token_savings_estimate = original_words - compressed_words

            metrics = self._create_metrics(
                original_length, compressed_length, compression_ratio_actual, token_savings_estimate
            )

            return compressed_text, metrics

        except Exception as e:
            print(f"LLMLingua compression failed: {e}")
            return text, self._create_metrics(original_length, original_length, 1.0, 0, error=str(e))

    def _identify_critical_tokens(self, text: str, preserve_questions: bool) -> List[str]:
        """Identify tokens that are critical and should not be removed."""
        critical_tokens = []

        # Always preserve question words
        question_words = ['what', 'how', 'why', 'where', 'when', 'who', 'which', 'whose']
        critical_tokens.extend(question_words)

        # Preserve technical terms (capitalized words, numbers, special chars)
        technical_terms = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b|\b\d+\b|[{}()\[\]<>]', text)
        critical_tokens.extend(technical_terms)

        # Preserve key action words
        action_words = ['create', 'build', 'implement', 'analyze', 'explain', 'describe',
                       'generate', 'write', 'develop', 'design', 'optimize', 'debug']
        critical_tokens.extend(action_words)

        return list(set([token.lower() for token in critical_tokens]))

    def _identify_removable_tokens(self, text: str, target_ratio: float,
                                  critical_tokens: List[str]) -> List[str]:
        """Use Claude to identify tokens that can be removed with minimal information loss."""
        try:
            prompt = self._create_token_analysis_prompt(text, target_ratio)

            response = self.client.invoke_model(
                modelId=self.compressor_model,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 512,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                }),
            )

            result = json.loads(response["body"].read())
            analysis_response = result["content"][0]["text"].strip()

            # Parse the response to extract removable tokens
            removable_tokens = self._parse_token_analysis(analysis_response, critical_tokens)

            return removable_tokens

        except Exception as e:
            # Fallback to rule-based token removal
            return self._fallback_token_identification(text, critical_tokens)

    def _create_token_analysis_prompt(self, text: str, target_ratio: float) -> str:
        """Create prompt for Claude to analyze which tokens can be removed."""
        target_percent = int((1 - target_ratio) * 100)

        return f"""Analyze this text and identify words that can be removed to compress it by approximately {target_percent}% while preserving the core meaning:

Text: "{text}"

Instructions:
1. Identify filler words, redundant phrases, and low-information tokens
2. Preserve all question words, technical terms, numbers, and action verbs
3. Focus on articles, prepositions, adjectives, and redundant phrases
4. List the removable words separated by commas

Removable words:"""

    def _parse_token_analysis(self, analysis_response: str, critical_tokens: List[str]) -> List[str]:
        """Parse Claude's response to extract removable tokens."""
        # Look for comma-separated words in the response
        words_line = ""
        for line in analysis_response.split('\n'):
            if ',' in line and len(line.split(',')) > 2:  # Likely the word list
                words_line = line
                break

        if not words_line:
            # Try to find any list of words
            words_match = re.search(r'([a-z]+(?:,\s*[a-z]+)+)', analysis_response.lower())
            if words_match:
                words_line = words_match.group(1)

        # Extract and clean words
        removable_tokens = []
        if words_line:
            words = [word.strip().lower() for word in words_line.split(',')]
            removable_tokens = [word for word in words
                              if word.isalpha() and len(word) > 1 and word not in critical_tokens]

        return removable_tokens

    def _fallback_token_identification(self, text: str, critical_tokens: List[str]) -> List[str]:
        """Fallback rule-based token identification when Claude analysis fails."""
        # Common low-information words that can often be removed
        removable_candidates = [
            'the', 'a', 'an', 'and', 'or', 'but', 'so', 'for', 'in', 'on', 'at',
            'to', 'of', 'with', 'by', 'very', 'really', 'quite', 'rather',
            'somewhat', 'particularly', 'especially', 'actually', 'basically',
            'generally', 'specifically', 'simply', 'just', 'only', 'even',
            'also', 'too', 'well', 'now', 'then', 'here', 'there'
        ]

        # Filter out critical tokens
        return [token for token in removable_candidates if token not in critical_tokens]

    def _apply_token_removal(self, text: str, tokens_to_remove: List[str],
                           critical_tokens: List[str]) -> str:
        """Apply token removal while preserving meaning and readability."""
        if not tokens_to_remove:
            return text

        # Create pattern for removable tokens (word boundaries to avoid partial matches)
        pattern_parts = []
        for token in tokens_to_remove:
            escaped_token = re.escape(token)
            # Only remove if it's a complete word and not part of a critical phrase
            pattern_parts.append(f'\\b{escaped_token}\\b')

        if not pattern_parts:
            return text

        # Apply removal with careful pattern matching
        pattern = '|'.join(pattern_parts)
        compressed = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Clean up extra spaces and punctuation
        compressed = re.sub(r'\s+', ' ', compressed)
        compressed = re.sub(r'\s+([,.!?;:])', r'\1', compressed)  # Fix punctuation spacing
        compressed = re.sub(r'([,.!?;:])\s*([,.!?;:])', r'\1\2', compressed)  # Remove duplicate punct

        return compressed.strip()

    def _post_process_compression(self, text: str) -> str:
        """Clean up compressed text to ensure readability."""
        # Fix common issues from token removal
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'^\s*[,.;:]\s*', '', text)  # Remove leading punctuation
        text = re.sub(r'\s*[,.;:]\s*$', '', text)  # Remove trailing punctuation
        text = re.sub(r'([.!?])\s*([a-z])', r'\1 \2', text)  # Fix sentence spacing

        # Ensure proper capitalization after sentence endings
        sentences = re.split(r'([.!?]+\s*)', text)
        for i in range(len(sentences)):
            if sentences[i] and not re.match(r'[.!?]+\s*', sentences[i]):
                sentences[i] = sentences[i][0].upper() + sentences[i][1:] if len(sentences[i]) > 0 else sentences[i]

        return ''.join(sentences).strip()

    def _create_metrics(self, original_length: int, compressed_length: int,
                       compression_ratio: float, token_savings: int,
                       error: str = None) -> Dict[str, float]:
        """Create metrics dictionary for compression results."""
        metrics = {
            "original_length": original_length,
            "compressed_length": compressed_length,
            "compression_ratio": compression_ratio,
            "compression_percent": round((1 - compression_ratio) * 100, 2),
            "estimated_token_savings": token_savings,
            "compression_method": "llmlingua_inspired"
        }

        if error:
            metrics["error"] = error

        return metrics

class BatchLLMLinguaCompressor(LLMLinguaCompressor):
    """Batch version of LLMLingua compressor for processing multiple texts efficiently."""

    def compress_batch(self, texts: List[str], compression_ratio: float = 0.5) -> List[Tuple[str, Dict[str, float]]]:
        """
        Compress multiple texts in batch for efficiency.

        Args:
            texts: List of texts to compress
            compression_ratio: Target compression ratio

        Returns:
            List of (compressed_text, metrics) tuples
        """
        results = []

        for i, text in enumerate(texts):
            print(f"Compressing text {i+1}/{len(texts)}...")
            compressed, metrics = self.compress_prompt(text, compression_ratio)
            results.append((compressed, metrics))

        return results