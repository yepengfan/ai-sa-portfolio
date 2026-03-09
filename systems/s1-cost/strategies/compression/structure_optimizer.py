"""Structure optimizer for prompt compression - converts text to efficient formats."""

import json
import re
from typing import Dict, List, Tuple, Any

class StructureOptimizer:
    """Optimizes text structure for token efficiency using JSON and bullet points."""

    def __init__(self, preferred_format: str = "json"):
        self.preferred_format = preferred_format  # "json", "bullets", or "auto"

    def compress_prompt(self, text: str, format_type: str = None) -> Tuple[str, Dict[str, float]]:
        """
        Optimize text structure for token efficiency.

        Args:
            text: Original text
            format_type: Format to use ("json", "bullets", "auto", or None for default)

        Returns:
            Tuple of (optimized_text, metrics_dict)
        """
        original_length = len(text)
        format_to_use = format_type or self.preferred_format

        # Analyze text to determine best optimization approach
        analysis = self._analyze_text_structure(text)

        if format_to_use == "auto":
            format_to_use = self._auto_select_format(analysis)

        # Apply appropriate optimization
        if format_to_use == "json":
            optimized_text = self._convert_to_json_structure(text, analysis)
        elif format_to_use == "bullets":
            optimized_text = self._convert_to_bullet_points(text, analysis)
        else:
            optimized_text = self._apply_general_optimization(text)

        optimized_length = len(optimized_text)
        compression_ratio = optimized_length / original_length if original_length > 0 else 1.0

        metrics = {
            "original_length": original_length,
            "optimized_length": optimized_length,
            "compression_ratio": compression_ratio,
            "compression_percent": round((1 - compression_ratio) * 100, 2),
            "format_used": format_to_use,
            "structure_complexity": analysis["complexity_score"],
            "list_items_found": analysis["list_items"],
            "key_value_pairs_found": analysis["key_value_pairs"]
        }

        return optimized_text, metrics

    def _analyze_text_structure(self, text: str) -> Dict[str, Any]:
        """Analyze text structure to determine optimization strategy."""
        # Count list-like patterns
        list_patterns = [
            r'^\s*[-*•]\s+',  # Bullet points
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[a-zA-Z]\.\s+',  # Lettered lists
        ]

        list_items = 0
        for pattern in list_patterns:
            list_items += len(re.findall(pattern, text, re.MULTILINE))

        # Count key-value like patterns
        key_value_patterns = [
            r'\w+:\s*\w+',  # "key: value"
            r'\w+\s*=\s*\w+',  # "key = value"
            r'\w+\s+is\s+\w+',  # "key is value"
        ]

        key_value_pairs = 0
        for pattern in key_value_patterns:
            key_value_pairs += len(re.findall(pattern, text))

        # Calculate complexity score
        sentences = len(re.findall(r'[.!?]+', text))
        words = len(text.split())
        complexity_score = (sentences * 2 + words) / max(len(text), 1) * 100

        return {
            "list_items": list_items,
            "key_value_pairs": key_value_pairs,
            "sentences": sentences,
            "words": words,
            "complexity_score": complexity_score,
            "has_structured_content": list_items > 2 or key_value_pairs > 2
        }

    def _auto_select_format(self, analysis: Dict[str, Any]) -> str:
        """Auto-select the best format based on text analysis."""
        if analysis["key_value_pairs"] >= analysis["list_items"] and analysis["key_value_pairs"] > 2:
            return "json"
        elif analysis["list_items"] > 2:
            return "bullets"
        else:
            return "general"

    def _convert_to_json_structure(self, text: str, analysis: Dict[str, Any]) -> str:
        """Convert text to JSON-like structure for efficiency."""
        # Extract key information and structure it as JSON
        try:
            # Simple approach: extract main topics and subtopics
            structure = self._extract_json_structure(text)
            if structure:
                return json.dumps(structure, separators=(',', ':'))  # Compact JSON
            else:
                return self._apply_general_optimization(text)
        except:
            return self._apply_general_optimization(text)

    def _extract_json_structure(self, text: str) -> Dict[str, Any]:
        """Extract structured information from text."""
        structure = {}

        # Look for question-answer patterns
        qa_matches = re.findall(r'(.*?)[?:]\s*(.*?)(?=[.!?]|$)', text, re.DOTALL)
        if qa_matches:
            structure["queries"] = []
            for question, answer in qa_matches[:5]:  # Limit to 5 for brevity
                if len(question.strip()) > 5 and len(answer.strip()) > 5:
                    structure["queries"].append({
                        "q": question.strip()[:50],  # Limit length
                        "context": answer.strip()[:100]
                    })

        # Look for task/instruction patterns
        task_patterns = [
            r'(create|build|implement|develop|write|generate)\s+(.+?)(?=[.!?]|$)',
            r'(explain|describe|analyze|compare)\s+(.+?)(?=[.!?]|$)',
        ]

        tasks = []
        for pattern in task_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for action, target in matches:
                tasks.append({"action": action, "target": target.strip()[:50]})

        if tasks:
            structure["tasks"] = tasks[:3]  # Limit to 3 tasks

        # Extract key terms
        key_terms = re.findall(r'\b[A-Z][a-zA-Z]{3,15}\b', text)  # Capitalized words
        if key_terms:
            structure["terms"] = list(set(key_terms[:10]))  # Unique terms, max 10

        return structure if len(structure) > 0 else None

    def _convert_to_bullet_points(self, text: str, analysis: Dict[str, Any]) -> str:
        """Convert text to efficient bullet point format."""
        # Split into sentences and convert to bullet points
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        # Group related sentences
        bullet_points = []
        for sentence in sentences[:8]:  # Limit to 8 points for brevity
            # Shorten sentence while preserving meaning
            shortened = self._shorten_sentence(sentence)
            if shortened:
                bullet_points.append(f"• {shortened}")

        return "\n".join(bullet_points) if bullet_points else text

    def _shorten_sentence(self, sentence: str) -> str:
        """Shorten a sentence while preserving key information."""
        # Remove filler words
        filler_words = ['very', 'really', 'quite', 'rather', 'somewhat', 'particularly',
                       'especially', 'specifically', 'generally', 'basically']

        for word in filler_words:
            sentence = re.sub(r'\b' + word + r'\b', '', sentence, flags=re.IGNORECASE)

        # Clean up extra spaces
        sentence = re.sub(r'\s+', ' ', sentence).strip()

        # Limit length
        if len(sentence) > 80:
            words = sentence.split()
            sentence = ' '.join(words[:12]) + '...' if len(words) > 12 else sentence

        return sentence

    def _apply_general_optimization(self, text: str) -> str:
        """Apply general structure optimizations."""
        # Remove redundant phrases
        optimized = text

        # Remove common redundant phrases
        redundant_phrases = [
            r'as you can see,?\s*',
            r'it is important to note that\s*',
            r'please note that\s*',
            r'it should be mentioned that\s*',
            r'keep in mind that\s*',
            r'bear in mind that\s*',
        ]

        for phrase in redundant_phrases:
            optimized = re.sub(phrase, '', optimized, flags=re.IGNORECASE)

        # Optimize punctuation
        optimized = re.sub(r'\s*,\s*', ',', optimized)  # Remove spaces around commas
        optimized = re.sub(r'\s*;\s*', ';', optimized)  # Remove spaces around semicolons
        optimized = re.sub(r'\s+', ' ', optimized)  # Multiple spaces to single

        return optimized.strip()

class AdvancedStructureOptimizer(StructureOptimizer):
    """Advanced structure optimizer with domain-specific optimizations."""

    def __init__(self):
        super().__init__()
        self.domain_patterns = {
            "code": {
                "keywords": ["function", "class", "method", "variable", "algorithm"],
                "optimizer": self._optimize_code_structure
            },
            "data": {
                "keywords": ["data", "table", "query", "analysis", "dataset"],
                "optimizer": self._optimize_data_structure
            },
            "instructions": {
                "keywords": ["create", "build", "implement", "generate", "write"],
                "optimizer": self._optimize_instruction_structure
            }
        }

    def compress_prompt(self, text: str, format_type: str = None) -> Tuple[str, Dict[str, float]]:
        """Enhanced compression with domain-specific optimizations."""
        # Identify domain
        domain = self._identify_domain(text)

        if domain and domain in self.domain_patterns:
            # Apply domain-specific optimization
            optimizer = self.domain_patterns[domain]["optimizer"]
            optimized_text = optimizer(text)
            original_length = len(text)
            optimized_length = len(optimized_text)

            metrics = {
                "original_length": original_length,
                "optimized_length": optimized_length,
                "compression_ratio": optimized_length / original_length if original_length > 0 else 1.0,
                "format_used": f"domain_{domain}",
                "domain_detected": domain
            }
            metrics["compression_percent"] = round((1 - metrics["compression_ratio"]) * 100, 2)

            return optimized_text, metrics
        else:
            # Fall back to base optimization
            return super().compress_prompt(text, format_type)

    def _identify_domain(self, text: str) -> str:
        """Identify the domain of the text."""
        text_lower = text.lower()
        domain_scores = {}

        for domain, config in self.domain_patterns.items():
            score = sum(1 for keyword in config["keywords"] if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score

        return max(domain_scores, key=domain_scores.get) if domain_scores else None

    def _optimize_code_structure(self, text: str) -> str:
        """Optimize code-related prompts."""
        # Convert to structured format for code tasks
        structure = {
            "task": self._extract_main_task(text),
            "requirements": self._extract_requirements(text),
            "constraints": self._extract_constraints(text)
        }

        # Filter out empty sections
        structure = {k: v for k, v in structure.items() if v}

        if len(structure) > 1:
            return json.dumps(structure, separators=(',', ':'))
        else:
            return self._apply_general_optimization(text)

    def _optimize_data_structure(self, text: str) -> str:
        """Optimize data-related prompts."""
        # Focus on data operations and requirements
        key_info = []

        # Extract data operations
        operations = re.findall(r'(analyze|process|transform|query|filter)\s+([^.!?]+)', text, re.IGNORECASE)
        for op, target in operations:
            key_info.append(f"{op}: {target.strip()}")

        return "\n".join(key_info) if key_info else self._apply_general_optimization(text)

    def _optimize_instruction_structure(self, text: str) -> str:
        """Optimize instruction-based prompts."""
        # Extract imperative sentences and key requirements
        imperatives = re.findall(r'(create|build|implement|generate|write|develop)\s+([^.!?]+)', text, re.IGNORECASE)

        if imperatives:
            structured = {"actions": []}
            for action, target in imperatives:
                structured["actions"].append(f"{action} {target.strip()}")

            return json.dumps(structured, separators=(',', ':'))
        else:
            return self._apply_general_optimization(text)

    def _extract_main_task(self, text: str) -> str:
        """Extract the main task from text."""
        # Look for imperative sentences
        imperatives = re.findall(r'(create|build|implement|write|generate|develop|make)\s+([^.!?]+)', text, re.IGNORECASE)
        if imperatives:
            return f"{imperatives[0][0]} {imperatives[0][1].strip()}"
        return ""

    def _extract_requirements(self, text: str) -> List[str]:
        """Extract requirements from text."""
        requirements = []

        # Look for requirement patterns
        req_patterns = [
            r'must\s+([^.!?]+)',
            r'should\s+([^.!?]+)',
            r'need\s+to\s+([^.!?]+)',
            r'require[sd]?\s+([^.!?]+)'
        ]

        for pattern in req_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements.extend([match.strip() for match in matches])

        return requirements[:5]  # Limit to 5 requirements

    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints from text."""
        constraints = []

        # Look for constraint patterns
        constraint_patterns = [
            r'cannot\s+([^.!?]+)',
            r'do not\s+([^.!?]+)',
            r'avoid\s+([^.!?]+)',
            r'without\s+([^.!?]+)'
        ]

        for pattern in constraint_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            constraints.extend([match.strip() for match in matches])

        return constraints[:3]  # Limit to 3 constraints