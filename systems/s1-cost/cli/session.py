"""Session state: message history, cost tracking, model selection."""

from dataclasses import dataclass, field

from utils.config import MODELS

SYSTEM_PROMPT = (
    "You are a helpful coding assistant running in a terminal. "
    "Keep responses concise and use markdown formatting. "
    "When showing code changes, use diff format or clearly indicate what to modify. "
    "Respond in the same language the user uses."
)


@dataclass
class SessionStats:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    per_model: dict = field(default_factory=lambda: {
        "sonnet": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0},
        "haiku": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0},
    })


class Session:
    def __init__(self, model: str = "sonnet"):
        self.model = model
        self.messages: list[dict] = []
        self.stats = SessionStats()

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

    def clear(self) -> None:
        self.messages.clear()

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = MODELS[self.model]
        return (
            (input_tokens / 1000) * pricing["input_cost_per_1k"]
            + (output_tokens / 1000) * pricing["output_cost_per_1k"]
        )
