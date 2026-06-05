from datetime import datetime
from dataclasses import dataclass, field
from ..providers.model_catalog import ModelCatalog


@dataclass
class UsageRecord:
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = ""


class CostTracker:
    def __init__(self, catalog: ModelCatalog | None = None):
        self._catalog = catalog or ModelCatalog()
        self.session_input = 0
        self.session_output = 0
        self.session_reasoning = 0
        self.total_input = 0
        self.total_output = 0
        self.total_cost = 0.0
        self._history: list[UsageRecord] = []

    def add_usage(self, provider: str, model: str, input_tokens: int, output_tokens: int, reasoning_tokens: int = 0):
        pricing = None
        if self._catalog:
            info = self._catalog.find_model(model)
            if info and info.pricing:
                pricing = info.pricing

        cost = 0.0
        if pricing and not pricing.is_free:
            cost = (
                input_tokens * pricing.input_per_1m / 1_000_000
                + output_tokens * pricing.output_per_1m / 1_000_000
            )

        self.session_input += input_tokens
        self.session_output += output_tokens
        self.session_reasoning += reasoning_tokens
        self.total_input += input_tokens
        self.total_output += output_tokens
        self.total_cost += cost

        record = UsageRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            cost_usd=cost,
            timestamp=datetime.now().isoformat(),
        )
        self._history.append(record)

    def get_session_summary(self) -> dict:
        return {
            "input_tokens": self.session_input,
            "output_tokens": self.session_output,
            "reasoning_tokens": self.session_reasoning,
            "total_tokens": self.session_input + self.session_output + self.session_reasoning,
            "cost_usd": round(self.session_cost, 6),
        }

    def get_total_summary(self) -> dict:
        return {
            "input_tokens": self.total_input,
            "output_tokens": self.total_output,
            "cost_usd": round(self.total_cost, 6),
        }

    @property
    def session_cost(self) -> float:
        return sum(r.cost_usd for r in self._history)

    def reset_session(self):
        self.session_input = 0
        self.session_output = 0
        self.session_reasoning = 0
        self._history.clear()
