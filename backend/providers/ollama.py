import json
from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef


class OllamaProvider(LLMProvider):
    id = "ollama"
    name = "Ollama (Local)"
    requires_api_key = False
    base_url = "http://localhost:11434/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def get_models(self) -> list[ModelInfo]:
        try:
            import requests
            resp = requests.get(f"{self.base_url.rstrip('/v1')}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m["name"]
                models.append(ModelInfo(
                    id=name,
                    provider_id=self.id,
                    name=name,
                    context_window=32768,
                    capabilities=ModelCapabilities(tool_calling=True),
                ))
            return models
        except Exception as e:
            print(f"[ollama] could not fetch models: {e}")
            return []

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        client = OpenAI(api_key=self.api_key or "ollama", base_url=self.base_url)
        body = {"model": model, "messages": [m.to_dict() for m in messages], "stream": True}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if tools:
            body["tools"] = [t.to_schema() for t in tools]
            body["tool_choice"] = tool_choice

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
                        continue
                    yield StreamEvent(type=StreamEventType.TOOL_CALL, tool_call_id=tc.id or "", tool_name=tc.function.name or "", tool_args=args)
            if chunk.choices[0].finish_reason:
                yield StreamEvent(type=StreamEventType.FINISH, finish_reason=chunk.choices[0].finish_reason)
