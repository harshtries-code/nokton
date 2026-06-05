import json
from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef


class DeepSeekProvider(LLMProvider):
    id = "deepseek"
    name = "DeepSeek"
    requires_api_key = True
    base_url = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="deepseek-chat", provider_id=self.id, name="DeepSeek V4", context_window=1000000, capabilities=ModelCapabilities(tool_calling=True, reasoning=True)),
            ModelInfo(id="deepseek-reasoner", provider_id=self.id, name="DeepSeek Reasoner", context_window=1000000, capabilities=ModelCapabilities(reasoning=True)),
        ]

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        body = {"model": model, "messages": [m.to_dict() for m in messages], "stream": True}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if tools:
            body["tools"] = [t.to_schema() for t in tools]
            body["tool_choice"] = tool_choice
        if reasoning_effort:
            body["thinking"] = {"type": "enabled"}
            if reasoning_effort == "max":
                body["reasoning_effort"] = "max"

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
                usage = None
                if chunk.usage:
                    usage = {"input": chunk.usage.prompt_tokens, "output": chunk.usage.completion_tokens, "total": chunk.usage.total_tokens}
                yield StreamEvent(type=StreamEventType.FINISH, finish_reason=chunk.choices[0].finish_reason, usage=usage)
