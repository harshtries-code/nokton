from openai import OpenAI
from .base import LLMProvider, ModelInfo, ModelCapabilities, ModelPricing, _stream_openai_compatible

REASONING_MAP = {
    "off": {},
    "low": {"reasoning_effort": "low"},
    "medium": {"reasoning_effort": "medium"},
    "high": {"reasoning_effort": "high"},
    "xhigh": {"reasoning_effort": "max"},
}


class OpenCodeProvider(LLMProvider):
    id = "opencode"
    name = "OpenCode Zen"
    requires_api_key = True
    base_url = "https://api.opencode.ai/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def get_models(self) -> list[ModelInfo]:
        client = OpenAI(api_key=self.api_key or "sk-placeholder", base_url=self.base_url)
        try:
            models = client.models.list()
            result = []
            for m in models:
                mid = m.id
                is_free = mid.endswith(":free")
                result.append(ModelInfo(
                    id=mid,
                    provider_id=self.id,
                    name=m.get("name", mid) if isinstance(m, dict) else getattr(m, "id", mid),
                    context_window=getattr(m, "context_window", 128000) if not isinstance(m, dict) else m.get("context_window", 128000),
                    capabilities=ModelCapabilities(
                        vision="vision" in mid.lower() or "image" in str(getattr(m, "capabilities", {})).lower(),
                        tool_calling=True,
                        reasoning="reasoning" in mid.lower() or "thinking" in str(getattr(m, "capabilities", {})).lower(),
                    ),
                    pricing=ModelPricing(is_free=is_free),
                ))
            return result
        except Exception:
            return [
                ModelInfo(id="opencode/deepseek-v4-flash:free", provider_id=self.id, name="DeepSeek V4 Flash (Free)", context_window=128000, capabilities=ModelCapabilities(tool_calling=True), pricing=ModelPricing(is_free=True)),
                ModelInfo(id="opencode/deepseek-v4-pro:free", provider_id=self.id, name="DeepSeek V4 Pro (Free)", context_window=128000, capabilities=ModelCapabilities(tool_calling=True, reasoning=True), pricing=ModelPricing(is_free=True)),
                ModelInfo(id="opencode/gpt-oss-20b:free", provider_id=self.id, name="GPT-OSS 20B (Free)", context_window=32768, capabilities=ModelCapabilities(tool_calling=True), pricing=ModelPricing(is_free=True)),
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

    def validate_api_key(self, key: str) -> bool:
        if not key or not key.strip():
            return False
        try:
            client = OpenAI(api_key=key, base_url=self.base_url)
            client.models.list()
            return True
        except Exception:
            return False
