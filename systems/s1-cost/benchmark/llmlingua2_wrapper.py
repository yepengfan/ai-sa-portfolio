"""Wrapper around the real LLMLingua-2 (BERT-based, local CPU, zero API cost)."""

from llmlingua import PromptCompressor


class OriginalLLMLingua2:
    """Wrapper around LLMLingua-2 BERT model for token-level compression."""

    def __init__(self, rate: float = 0.5):
        self.rate = rate
        print("Loading LLMLingua-2 model (one-time)...", end="", flush=True)
        self.compressor = PromptCompressor(
            model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
            use_llmlingua2=True,
            device_map="cpu",
        )
        print(" done.")

    def compress_prompt(self, text: str) -> tuple:
        result = self.compressor.compress_prompt(
            text,
            rate=self.rate,
            force_tokens=["\n", "?"],
        )
        metrics = {
            "original_length": len(text),
            "compressed_length": len(result["compressed_prompt"]),
            "compression_ratio": len(result["compressed_prompt"]) / len(text) if text else 1.0,
            "origin_tokens": result["origin_tokens"],
            "compressed_tokens": result["compressed_tokens"],
            "ratio_display": result["ratio"],
        }
        return result["compressed_prompt"], metrics
