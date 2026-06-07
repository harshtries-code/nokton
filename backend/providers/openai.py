import json
from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef

REASONING_MAP = {
    "off": {"reasoning_effort": "none"},
    "high": {"reasoning_effort": "high"},
    "xhigh": {"reasoning_effort": "xhigh"},
}


class OpenAIProvider(LLMProvider):
    id = "openai"
    name = "OpenAI"
    requires_api_key = True
    base_url = "https://api.openai.com/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="gpt-4o", provider_id=self.id, name="GPT-4o", context_window=128000, capabilities=ModelCapabilities(vision=True, reasoning=False)),
            ModelInfo(id="gpt-4o-mini", provider_id=self.id, name="GPT-4o Mini", context_window=128000, capabilities=ModelCapabilities(vision=True, reasoning=False)),
            ModelInfo(id="o3-mini", provider_id=self.id, name="o3 Mini", context_window=200000, capabilities=ModelCapabilities(reasoning=True)),
            ModelInfo(id="gpt-4.1", provider_id=self.id, name="GPT-4.1", context_window=1000000, capabilities=ModelCapabilities(vision=True)),
        ]

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
    ):
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
                        yield StreamEvent(type=StreamEventType.TOOL_CALL_PARTIAL, tool_call_id=tc.id or "", tool_name=tc.function.name or "", tool_args={"__partial": tc.function.arguments or ""})
                        continue
                    yield StreamEvent(type=StreamEventType.TOOL_CALL, tool_call_id=tc.id or "", tool_name=tc.function.name or "", tool_args=args)
            if chunk.choices[0].finish_reason:
                usage = None
                if chunk.usage:
                    usage = {"input": chunk.usage.prompt_tokens, "output": chunk.usage.completion_tokens, "total": chunk.usage.total_tokens}
                yield StreamEvent(type=StreamEventType.FINISH, finish_reason=chunk.choices[0].finish_reason, usage=usage)

    def validate_api_key(self, key: str) -> bool:
        try:
            import requests
            resp = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=5,
            )
            if resp.status_code == 200:
                return True
            if resp.status_code in (401, 403):
                return False
            return bool(key)
        except Exception:
            return bool(key)
