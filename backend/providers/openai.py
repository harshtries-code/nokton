import re

from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, Message, ToolDef, _stream_openai_compatible

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
                        vision=("vision" in mid.lower()) or ("gpt-4" in mid.lower() and "mini" not in mid.lower()),
                        tool_calling=True,
                        reasoning=bool(re.match(r'^o[134]', mid.lower())),
                    ),
                ))
            return result if result else self._default_models()
        except Exception:
            return self._default_models()

    def _default_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="gpt-4o", provider_id=self.id, name="GPT-4o", context_window=128000, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
            ModelInfo(id="gpt-4o-mini", provider_id=self.id, name="GPT-4o Mini", context_window=128000, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
            ModelInfo(id="o3-mini", provider_id=self.id, name="o3 Mini", context_window=200000, capabilities=ModelCapabilities(reasoning=True, tool_calling=True)),
            ModelInfo(id="gpt-4.1", provider_id=self.id, name="GPT-4.1", context_window=1048576, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
            ModelInfo(id="gpt-4.1-mini", provider_id=self.id, name="GPT-4.1 Mini", context_window=1048576, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
            ModelInfo(id="gpt-4.1-nano", provider_id=self.id, name="GPT-4.1 Nano", context_window=1048576, capabilities=ModelCapabilities(tool_calling=True)),
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
