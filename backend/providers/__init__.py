from .base import LLMProvider, ModelInfo, StreamEvent, StreamEventType, Message, ToolDef, ModelCapabilities
from .openrouter import OpenRouterProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .deepseek import DeepSeekProvider
from .google import GoogleProvider
from .groq import GroqProvider
from .ollama import OllamaProvider
from .custom import CustomProvider
from .model_catalog import ModelCatalog


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._catalog = ModelCatalog()

    def register(self, provider: LLMProvider):
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> LLMProvider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> list[dict[str, str]]:
        return [
            {"id": p.id, "name": p.name, "requires_api_key": p.requires_api_key}
            for p in self._providers.values()
        ]

    def get_models(self, provider_id: str | None = None) -> dict[str, list[ModelInfo]]:
        if provider_id:
            provider = self._providers.get(provider_id)
            if provider:
                return {provider_id: self._catalog.get_provider_models(provider_id) or provider.get_models()}
            return {}
        result = {}
        for pid, provider in self._providers.items():
            models = self._catalog.get_provider_models(pid) or provider.get_models()
            if models:
                result[pid] = models
        return result

    def refresh_models(self):
        if self._catalog.load_cache() and not self._catalog.is_stale():
            return
        for pid, provider in self._providers.items():
            try:
                models = provider.get_models()
                if models:
                    self._catalog.update(pid, models)
            except Exception:
                pass

    def stream_chat(
        self,
        provider_id: str,
        model: str,
        messages: list[Message],
        **kwargs,
    ):
        provider = self._providers.get(provider_id)
        if not provider:
            yield StreamEvent(type=StreamEventType.ERROR, error=f"Unknown provider: {provider_id}")
            return
        yield from provider.stream_chat(model, messages, **kwargs)


registry = ProviderRegistry()
registry.register(OpenRouterProvider())
registry.register(OpenAIProvider())
registry.register(AnthropicProvider())
registry.register(DeepSeekProvider())
registry.register(GoogleProvider())
registry.register(GroqProvider())
registry.register(OllamaProvider())
registry.register(CustomProvider())
