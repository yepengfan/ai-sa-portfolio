"""Relevance filtering for prompt compression - keeps only relevant context fragments."""

import re
import math
from typing import Dict, List, Tuple
from collections import Counter

class RelevanceFilter:
    """Filters text to keep only fragments relevant to the current query."""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def compress_prompt(self, full_context: str, current_query: str,
                       max_chunks: int = 10) -> Tuple[str, Dict[str, float]]:
        """
        Filter context to keep only relevant chunks for the current query.

        Args:
            full_context: Complete context text
            current_query: Current user query
            max_chunks: Maximum number of chunks to keep

        Returns:
            Tuple of (filtered_context, metrics_dict)
        """
        original_length = len(full_context)

        # Split context into meaningful chunks
        chunks = self._split_into_chunks(full_context)

        if len(chunks) <= max_chunks:
            # If we have fewer chunks than the limit, return original
            return full_context, {
                "original_length": original_length,
                "compressed_length": original_length,
                "compression_ratio": 1.0,
                "compression_percent": 0.0,
                "chunks_processed": len(chunks),
                "chunks_kept": len(chunks),
                "relevance_threshold": self.similarity_threshold
            }

        # Calculate relevance scores for each chunk
        chunk_scores = self._calculate_relevance_scores(chunks, current_query)

        # Select top relevant chunks
        top_chunks = self._select_top_chunks(chunks, chunk_scores, max_chunks)

        # Reconstruct text from selected chunks
        filtered_text = self._reconstruct_text(top_chunks)

        compressed_length = len(filtered_text)
        compression_ratio = compressed_length / original_length if original_length > 0 else 1.0

        metrics = {
            "original_length": original_length,
            "compressed_length": compressed_length,
            "compression_ratio": compression_ratio,
            "compression_percent": round((1 - compression_ratio) * 100, 2),
            "chunks_processed": len(chunks),
            "chunks_kept": len(top_chunks),
            "relevance_threshold": self.similarity_threshold,
            "avg_relevance_score": sum(chunk_scores[:len(top_chunks)]) / len(top_chunks) if top_chunks else 0.0
        }

        return filtered_text, metrics

    def _split_into_chunks(self, text: str, chunk_size: int = 200) -> List[str]:
        """Split text into meaningful chunks."""
        # First try to split by sentences
        sentences = re.split(r'[.!?]+\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If chunks are too large, split by words
        if max(len(chunk) for chunk in chunks) > chunk_size * 2:
            word_chunks = []
            for chunk in chunks:
                if len(chunk) > chunk_size * 2:
                    words = chunk.split()
                    for i in range(0, len(words), chunk_size // 10):  # Approx 10 chars per word
                        word_chunk = " ".join(words[i:i + chunk_size // 10])
                        if word_chunk.strip():
                            word_chunks.append(word_chunk.strip())
                else:
                    word_chunks.append(chunk)
            chunks = word_chunks

        return [chunk for chunk in chunks if len(chunk.strip()) > 10]  # Filter very short chunks

    def _calculate_relevance_scores(self, chunks: List[str], query: str) -> List[float]:
        """Calculate relevance scores using TF-IDF-like approach."""
        # Tokenize query
        query_tokens = set(self._tokenize(query.lower()))

        scores = []
        for chunk in chunks:
            chunk_tokens = self._tokenize(chunk.lower())
            score = self._calculate_similarity(query_tokens, chunk_tokens)
            scores.append(score)

        return scores

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - splits on whitespace and removes punctuation."""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()

        # Filter out very short words and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these',
                     'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
                     'us', 'them'}

        return [token for token in tokens if len(token) > 2 and token not in stop_words]

    def _calculate_similarity(self, query_tokens: set, chunk_tokens: List[str]) -> float:
        """Calculate similarity between query and chunk tokens."""
        if not query_tokens or not chunk_tokens:
            return 0.0

        chunk_counter = Counter(chunk_tokens)
        chunk_token_set = set(chunk_tokens)

        # Jaccard similarity (intersection over union)
        intersection = len(query_tokens & chunk_token_set)
        union = len(query_tokens | chunk_token_set)

        jaccard_score = intersection / union if union > 0 else 0.0

        # TF-IDF-like scoring for query terms in chunk
        tfidf_score = 0.0
        for token in query_tokens:
            if token in chunk_counter:
                tf = chunk_counter[token] / len(chunk_tokens)  # Term frequency
                tfidf_score += tf

        # Combine scores
        combined_score = (jaccard_score * 0.4) + (tfidf_score * 0.6)

        return combined_score

    def _select_top_chunks(self, chunks: List[str], scores: List[float], max_chunks: int) -> List[str]:
        """Select top-scoring chunks."""
        # Sort chunks by score in descending order
        scored_chunks = list(zip(chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Filter by threshold and take top max_chunks
        filtered_chunks = [chunk for chunk, score in scored_chunks
                          if score >= self.similarity_threshold][:max_chunks]

        # If we don't have enough high-scoring chunks, take top max_chunks regardless
        if len(filtered_chunks) < max_chunks // 2:
            filtered_chunks = [chunk for chunk, score in scored_chunks[:max_chunks]]

        return filtered_chunks

    def _reconstruct_text(self, chunks: List[str]) -> str:
        """Reconstruct text from selected chunks."""
        if not chunks:
            return ""

        # Join chunks with appropriate spacing
        return " ".join(chunks)

class AdvancedRelevanceFilter(RelevanceFilter):
    """Enhanced relevance filter with semantic understanding."""

    def __init__(self, similarity_threshold: float = 0.7):
        super().__init__(similarity_threshold)
        self.semantic_keywords = {
            'code': ['function', 'class', 'method', 'variable', 'algorithm', 'programming'],
            'data': ['database', 'table', 'query', 'analysis', 'statistics', 'dataset'],
            'web': ['website', 'html', 'css', 'javascript', 'frontend', 'backend'],
            'ml': ['machine learning', 'model', 'training', 'prediction', 'neural network'],
            'system': ['server', 'deployment', 'infrastructure', 'architecture', 'scaling']
        }

    def _calculate_similarity(self, query_tokens: set, chunk_tokens: List[str]) -> float:
        """Enhanced similarity calculation with semantic categories."""
        base_score = super()._calculate_similarity(query_tokens, chunk_tokens)

        # Add semantic category bonus
        semantic_bonus = self._calculate_semantic_bonus(query_tokens, chunk_tokens)

        return min(1.0, base_score + semantic_bonus * 0.2)  # Cap at 1.0

    def _calculate_semantic_bonus(self, query_tokens: set, chunk_tokens: List[str]) -> float:
        """Calculate bonus score based on semantic category matching."""
        query_categories = self._identify_categories(query_tokens)
        chunk_categories = self._identify_categories(set(chunk_tokens))

        if not query_categories or not chunk_categories:
            return 0.0

        # Calculate category overlap
        overlap = len(query_categories & chunk_categories)
        total = len(query_categories | chunk_categories)

        return overlap / total if total > 0 else 0.0

    def _identify_categories(self, tokens: set) -> set:
        """Identify semantic categories from tokens."""
        categories = set()
        for category, keywords in self.semantic_keywords.items():
            for keyword in keywords:
                keyword_tokens = set(keyword.split())
                if keyword_tokens & tokens:  # If any keyword tokens match
                    categories.add(category)
        return categories