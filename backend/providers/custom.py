import json
from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef


class CustomProvider(LLMProvider):
    id = "custom"
    name = "Custom OpenAI-Compatible"
    requires_api_key = False

    def __init__(self, api_key: str = "", base_url: str = "http://localhost:8000/v1"):
        self.api_key = api_key
        self.base_url = base_url

    def get_models(self) -> list[ModelInfo]:
        client = OpenAI(api_key=self.api_key or "sk-placeholder", base_url=self.base_url)
        try:
            models = client.models.list()
            return [
                ModelInfo(id=m.id, provider_id=self.id, name=m.id, context_window=128000)
                for m in models
            ]
        except Exception:
            return [ModelInfo(id="custom-model", provider_id=self.id, name="Custom Model")]

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        client = OpenAI(api_key=self.api_key or "sk-placeholder", base_url=self.base_url)
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
