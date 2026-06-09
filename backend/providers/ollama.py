from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, _stream_openai_compatible


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
