import json
from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef, _stream_openai_compatible

REASONING_MAP = {
    "off": {},
    "high": {"thinking": {"type": "enabled"}},
    "xhigh": {"thinking": {"type": "enabled"}, "reasoning_effort": "max"},
    "max": {"thinking": {"type": "enabled"}, "reasoning_effort": "max"},
}


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
        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            models = client.models.list()
            result = []
            for m in models:
                mid = m.id
                result.append(ModelInfo(
                    id=mid,
                    provider_id=self.id,
                    name=mid,
                    context_window=128000,
                    capabilities=ModelCapabilities(
                        tool_calling=True,
                        reasoning="reasoner" in mid.lower() or "pro" in mid.lower(),
                    ),
                ))
            return result if result else self._default_models()
        except Exception:
            return self._default_models()

    def _default_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="deepseek-chat-v3.1", provider_id=self.id, name="DeepSeek Chat V3.1", context_window=128000, capabilities=ModelCapabilities(tool_calling=True)),
            ModelInfo(id="deepseek-reasoner-v4", provider_id=self.id, name="DeepSeek Reasoner V4", context_window=128000, capabilities=ModelCapabilities(reasoning=True, tool_calling=True)),
            ModelInfo(id="deepseek-v4-flash", provider_id=self.id, name="DeepSeek V4 Flash", context_window=128000, capabilities=ModelCapabilities(tool_calling=True)),
            ModelInfo(id="deepseek-v4-pro", provider_id=self.id, name="DeepSeek V4 Pro", context_window=128000, capabilities=ModelCapabilities(reasoning=True, tool_calling=True)),
        ]

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        extra = REASONING_MAP.get(reasoning_effort, REASONING_MAP.get("off", {})) if reasoning_effort else {}
        yield from _stream_openai_compatible(
            client=client,
            model=model,
            messages=[m.to_dict() for m in messages],
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            extra_body=extra if extra else None,
        )
