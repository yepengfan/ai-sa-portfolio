"""Session state: message history, cost tracking, model selection."""

from dataclasses import dataclass, field

from utils.config import MODELS

SYSTEM_PROMPT = (
    "You are a helpful coding assistant running in a terminal. "
    "Keep responses concise and use markdown formatting. "
    "When showing code changes, use diff format or clearly indicate what to modify. "
    "Respond in the same language the user uses."
)


def _empty_model_stats() -> dict:
    return {k: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0} for k in MODELS}


@dataclass
class SessionStats:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    per_model: dict = field(default_factory=_empty_model_stats)


class Session:
    def __init__(self, model: str = "sonnet"):
        self.model = model
        self.messages: list[dict] = []
        self.stats = SessionStats()
        self._pending_file_context: str | None = None

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": [{"text": text}]})

    def add_assistant_message(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": [{"text": text}]})

    def record_usage(self, input_tokens: int, output_tokens: int, cost: float) -> None:
        self.stats.calls += 1
        self.stats.input_tokens += input_tokens
        self.stats.output_tokens += output_tokens
        self.stats.cost_usd += cost

        m = self.stats.per_model[self.model]
        m["calls"] += 1
        m["input_tokens"] += input_tokens
        m["output_tokens"] += output_tokens
        m["cost"] += cost

    def set_file_context(self, context: str) -> None:
        self._pending_file_context = context

    def consume_file_context(self) -> str | None:
        ctx = self._pending_file_context
        self._pending_file_context = None
        return ctx

    def clear(self) -> None:
        self.messages.clear()
        self._pending_file_context = None

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = MODELS[self.model]
        return (
            (input_tokens / 1000) * pricing["input_cost_per_1k"]
            + (output_tokens / 1000) * pricing["output_cost_per_1k"]
        )
