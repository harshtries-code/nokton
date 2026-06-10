from openai import OpenAI
from .base import LLMProvider, ModelInfo, _stream_openai_compatible


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
        yield from _stream_openai_compatible(
            client=client,
            model=model,
            messages=[m.to_dict() for m in messages],
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
