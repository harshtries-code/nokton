import json
import requests
from openai import OpenAI
from typing import Generator
from .base import LLMProvider, ModelInfo, ModelCapabilities, ModelPricing, StreamEvent, StreamEventType, Message, ToolDef

REASONING_MAP = {
    "off": {},
    "high": {"reasoning": {"effort": "high"}},
    "xhigh": {"reasoning": {"effort": "xhigh"}},
}


class OpenRouterProvider(LLMProvider):
    id = "openrouter"
    name = "OpenRouter"
    requires_api_key = True
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_models(self) -> list[ModelInfo]:
        try:
            resp = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        models = []
        for m in data.get("data", []):
            model_id = m["id"]
            is_free = model_id.endswith(":free")
            pricing_data = m.get("pricing", {})
            models.append(ModelInfo(
                id=model_id,
                provider_id=self.id,
                name=m.get("name", model_id),
                context_window=m.get("context_length", 128000),
                max_output=m.get("top_provider", {}).get("max_completion_tokens", 8192),
                capabilities=ModelCapabilities(
                    vision="image" in m.get("input_modalities", []),
                    tool_calling="tools" in m.get("capabilities", []),
                    streaming=True,
                    reasoning="reasoning" in m.get("capabilities", []),
                ),
                pricing=ModelPricing(
                    input_per_1m=float(pricing_data.get("prompt", 0)),
                    output_per_1m=float(pricing_data.get("completion", 0)),
                    is_free=is_free,
                ),
            ))
        return models

    def stream_chat(
        self,
        model: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        tool_choice: str = "auto",
        reasoning_effort: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> Generator[StreamEvent, None, None]:
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        body = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if stop:
            body["stop"] = stop
        if tools:
            body["tools"] = [t.to_schema() for t in tools]
            body["tool_choice"] = tool_choice
        if reasoning_effort:
            body.update(REASONING_MAP.get(reasoning_effort, {}))

        try:
            stream = client.chat.completions.create(**body)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=str(e))
            return

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    args = {}
                    try:
                        if tc.function.arguments:
                            args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_PARTIAL,
                            tool_call_id=tc.id or "",
                            tool_name=tc.function.name or "",
                            tool_args={"__partial": tc.function.arguments or ""},
                        )
                        continue
                    yield StreamEvent(
                        type=StreamEventType.TOOL_CALL,
                        tool_call_id=tc.id or "",
                        tool_name=tc.function.name or "",
                        tool_args=args,
                    )

            if chunk.choices[0].finish_reason:
                usage = None
                if chunk.usage:
                    usage = {
                        "input": chunk.usage.prompt_tokens,
                        "output": chunk.usage.completion_tokens,
                        "total": chunk.usage.total_tokens,
                    }
                yield StreamEvent(
                    type=StreamEventType.FINISH,
                    finish_reason=chunk.choices[0].finish_reason,
                    usage=usage,
                )

    def validate_api_key(self, key: str) -> bool:
        try:
            resp = requests.get(
                f"{self.base_url}/auth/key",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
