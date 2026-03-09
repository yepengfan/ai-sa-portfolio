"""Manual prompt refinement for compression - removes redundancy and optimizes structure."""

import re
from typing import Dict, Tuple

class ManualRefiner:
    """Implements manual prompt compression through text refinement techniques."""

    def __init__(self):
        # Common redundant patterns to remove
        self.redundant_patterns = [
            (r'\b(please|kindly)\s+', ''),  # Remove politeness words
            (r'\b(could you|can you|would you)\s+', ''),  # Direct commands
            (r'\s+', ' '),  # Multiple spaces to single
            (r'\b(the|a|an)\s+(?=\w+\s+(is|are|was|were))', ''),  # Articles before "is/are"
            (r'\b(that|which|who)\s+(?=is|are|was|were)', ''),  # Relative pronouns
            (r'\b(very|really|quite|rather)\s+', ''),  # Intensity modifiers
            (r'\b(I would like|I want|I need)\s+', ''),  # First person requests
        ]

        # Word replacements for more concise alternatives
        self.word_replacements = {
            'information': 'info',
            'explanation': 'explanation',
            'understand': 'know',
            'demonstrate': 'show',
            'implement': 'build',
            'initialize': 'init',
            'configuration': 'config',
            'documentation': 'docs',
            'application': 'app',
            'development': 'dev',
            'environment': 'env',
            'repository': 'repo'
        }

    def compress_prompt(self, text: str) -> Tuple[str, Dict[str, float]]:
        """
        Compress prompt using manual refinement techniques.

        Args:
            text: Original prompt text

        Returns:
            Tuple of (compressed_text, metrics_dict)
        """
        original_text = text
        original_length = len(text)

        # Step 1: Apply redundant pattern removal
        for pattern, replacement in self.redundant_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Step 2: Apply word replacements for shorter synonyms
        for long_word, short_word in self.word_replacements.items():
            text = re.sub(r'\b' + long_word + r'\b', short_word, text, flags=re.IGNORECASE)

        # Step 3: Remove unnecessary punctuation and clean up
        text = re.sub(r'[,;]\s+', ' ', text)  # Remove commas/semicolons
        text = re.sub(r'\s+([.!?])', r'\1', text)  # Fix spacing around punctuation
        text = re.sub(r'\s+', ' ', text).strip()  # Clean up extra spaces

        # Step 4: Convert to keyword-first structure for common patterns
        text = self._optimize_question_structure(text)

        compressed_length = len(text)
        compression_ratio = compressed_length / original_length if original_length > 0 else 1.0

        metrics = {
            "original_length": original_length,
            "compressed_length": compressed_length,
            "compression_ratio": compression_ratio,
            "chars_saved": original_length - compressed_length,
            "compression_percent": round((1 - compression_ratio) * 100, 2)
        }

        return text, metrics

    def _optimize_question_structure(self, text: str) -> str:
        """Optimize question structure to be more keyword-first."""
        # Convert "What is X?" to "Define X" pattern
        text = re.sub(r'what is ([\w\s]+)\?', r'Define \1', text, flags=re.IGNORECASE)
        text = re.sub(r'how do I ([\w\s]+)\?', r'Show \1', text, flags=re.IGNORECASE)
        text = re.sub(r'can you explain ([\w\s]+)\?', r'Explain \1', text, flags=re.IGNORECASE)

        return text

    def estimate_token_savings(self, original_text: str, compressed_text: str) -> float:
        """
        Estimate token savings based on character reduction.
        Rough approximation: 1 token ≈ 4 characters for English text.
        """
        char_reduction = len(original_text) - len(compressed_text)
        estimated_token_savings = char_reduction / 4  # Rough estimate
        return estimated_token_savings

class AdvancedManualRefiner(ManualRefiner):
    """Extended manual refiner with more aggressive compression techniques."""

    def __init__(self):
        super().__init__()

        # More aggressive patterns for high compression scenarios
        self.aggressive_patterns = [
            (r'\b(in order to|so as to)\s+', 'to '),  # Simplify purpose phrases
            (r'\b(due to the fact that|because of the fact that)\s+', 'because '),  # Simplify causation
            (r'\b(at this point in time|at the present time)\s+', 'now '),  # Temporal simplification
            (r'\b(in the event that|in case)\s+', 'if '),  # Conditional simplification
            (r'\b(for the purpose of|with the intention of)\s+', 'to '),  # Purpose simplification
        ]

    def compress_prompt(self, text: str, aggressive: bool = False) -> Tuple[str, Dict[str, float]]:
        """
        Compress with optional aggressive mode.

        Args:
            text: Original prompt text
            aggressive: Use more aggressive compression techniques

        Returns:
            Tuple of (compressed_text, metrics_dict)
        """
        # First apply base compression
        text, metrics = super().compress_prompt(text)

        if aggressive:
            original_aggressive_length = len(text)

            # Apply aggressive patterns
            for pattern, replacement in self.aggressive_patterns:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

            # Update metrics for aggressive compression
            aggressive_length = len(text)
            total_original = metrics["original_length"]
            total_compression_ratio = aggressive_length / total_original if total_original > 0 else 1.0

            metrics.update({
                "aggressive_length": aggressive_length,
                "total_compression_ratio": total_compression_ratio,
                "total_compression_percent": round((1 - total_compression_ratio) * 100, 2),
                "aggressive_chars_saved": original_aggressive_length - aggressive_length
            })

        return text, metrics