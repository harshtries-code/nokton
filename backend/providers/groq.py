from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, _stream_openai_compatible

REASONING_MAP = {
    "off": {},
    "high": {"reasoning_effort": "high"},
    "xhigh": {"reasoning_effort": "high"},
}


class GroqProvider(LLMProvider):
    id = "groq"
    name = "Groq"
    requires_api_key = True
    base_url = "https://api.groq.com/openai/v1"

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
                        reasoning="deepseek-r1" in mid.lower() or "reasoning" in mid.lower(),
                    ),
                ))
            return result if result else self._default_models()
        except Exception:
            return self._default_models()

    def _default_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="llama-3.3-70b-versatile", provider_id=self.id, name="Llama 3.3 70B", context_window=128000, capabilities=ModelCapabilities(tool_calling=True)),
            ModelInfo(id="llama-3.1-8b-instant", provider_id=self.id, name="Llama 3.1 8B Instant", context_window=128000, capabilities=ModelCapabilities(tool_calling=True)),
            ModelInfo(id="mixtral-8x7b-32768", provider_id=self.id, name="Mixtral 8x7B", context_window=32768),
            ModelInfo(id="deepseek-r1-distill-llama-70b", provider_id=self.id, name="DeepSeek R1 Distill 70B", context_window=128000, capabilities=ModelCapabilities(reasoning=True)),
        ]

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        extra = REASONING_MAP.get(reasoning_effort, {}) if reasoning_effort else {}
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
