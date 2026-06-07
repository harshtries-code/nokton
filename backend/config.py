import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "nokton.json"
USER_CONFIG_PATH = Path.home() / ".nokton" / "nokton.json"


@dataclass
class ModelConfig:
    provider: str = "openrouter"
    model: str = "deepseek/deepseek-v4-flash:free"
    small_model: str = "openrouter/gpt-oss-20b:free"
    vision_model: str = "openrouter/google/gemma-3-27b-it:free"
    reasoning_effort: str = "high"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class ProviderAuth:
    api_key: str = ""
    base_url: str = ""


@dataclass
class ToolsConfig:
    safe_categories: list[str] = field(default_factory=lambda: ["file_read", "web", "system_read", "clipboard_read"])
    ask_categories: list[str] = field(default_factory=lambda: ["file_write", "app_control", "system_write"])
    deny_categories: list[str] = field(default_factory=list)
    timeout: int = 30


@dataclass
class STTConfig:
    engine: str = "faster-whisper"
    model_size: str = "small"
    device: str = "cpu"


@dataclass
class TTSConfig:
    engine: str = "edge-tts"
    voice: str = "en-US-JennyNeural"
    rate: str = "+0%"


@dataclass
class WakeWordConfig:
    enabled: bool = False
    sensitivity: float = 0.7
    model: str = "hey_nokton"


@dataclass
class VADConfig:
    threshold: float = 0.5
    silence_duration_ms: int = 800


@dataclass
class VoiceConfig:
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    vad: VADConfig = field(default_factory=VADConfig)


@dataclass
class ConversationConfig:
    max_turns: int = 100
    compress_threshold: float = 0.5
    protect_last_n: int = 10


@dataclass
class UIConfig:
    theme: str = "dark"
    font_size: int = 14
    streaming_animation: bool = True
    show_reasoning: bool = False
    show_tool_calls: bool = True


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    providers: dict[str, ProviderAuth] = field(default_factory=dict)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    @classmethod
    def load(cls) -> "Config":
        config = cls()

        defaults = _load_json_file(DEFAULT_CONFIG_PATH)
        if defaults:
            config._merge(defaults)

        user = _load_json_file(USER_CONFIG_PATH)
        if user:
            config._merge(user)

        config._apply_env_overrides()
        return config

    def _merge(self, data: dict[str, Any]):
        if "model" in data:
            for k, v in data["model"].items():
                if hasattr(self.model, k):
                    setattr(self.model, k, v)
        if "providers" in data:
            for prov, auth in data["providers"].items():
                if prov not in self.providers:
                    self.providers[prov] = ProviderAuth()
                if "api_key" in auth:
                    self.providers[prov].api_key = auth["api_key"]
                if "base_url" in auth:
                    self.providers[prov].base_url = auth["base_url"]
        if "tools" in data:
            if "permissions" in data["tools"]:
                perm = data["tools"]["permissions"]
                if "safe_categories" in perm:
                    self.tools.safe_categories = perm["safe_categories"]
                if "ask_categories" in perm:
                    self.tools.ask_categories = perm["ask_categories"]
                if "deny_categories" in perm:
                    self.tools.deny_categories = perm["deny_categories"]
            if "timeout" in data["tools"]:
                self.tools.timeout = data["tools"]["timeout"]
        if "voice" in data:
            if "wake_word" in data["voice"]:
                for k, v in data["voice"]["wake_word"].items():
                    if hasattr(self.voice.wake_word, k):
                        setattr(self.voice.wake_word, k, v)
            if "stt" in data["voice"]:
                for k, v in data["voice"]["stt"].items():
                    if hasattr(self.voice.stt, k):
                        setattr(self.voice.stt, k, v)
            if "tts" in data["voice"]:
                for k, v in data["voice"]["tts"].items():
                    if hasattr(self.voice.tts, k):
                        setattr(self.voice.tts, k, v)
            if "vad" in data["voice"]:
                for k, v in data["voice"]["vad"].items():
                    if hasattr(self.voice.vad, k):
                        setattr(self.voice.vad, k, v)
        if "conversation" in data:
            for k, v in data["conversation"].items():
                if hasattr(self.conversation, k):
                    setattr(self.conversation, k, v)
        if "ui" in data:
            for k, v in data["ui"].items():
                if hasattr(self.ui, k):
                    setattr(self.ui, k, v)

    def _apply_env_overrides(self):
        env_map = {
            "NOKTON_PROVIDER": ("model", "provider"),
            "NOKTON_MODEL": ("model", "model"),
            "OPENROUTER_API_KEY": ("providers", "openrouter", "api_key"),
            "OPENAI_API_KEY": ("providers", "openai", "api_key"),
            "ANTHROPIC_API_KEY": ("providers", "anthropic", "api_key"),
            "DEEPSEEK_API_KEY": ("providers", "deepseek", "api_key"),
            "GROQ_API_KEY": ("providers", "groq", "api_key"),
        }
        for env_var, path in env_map.items():
            value = os.environ.get(env_var)
            if value:
                self._set_nested(path, value)

    def _set_nested(self, path: tuple, value: Any):
        if path[0] == "model" and len(path) == 2:
            if hasattr(self.model, path[1]):
                setattr(self.model, path[1], value)
        elif path[0] == "providers" and len(path) == 3:
            prov, key = path[1], path[2]
            if prov not in self.providers:
                self.providers[prov] = ProviderAuth()
            if hasattr(self.providers[prov], key):
                setattr(self.providers[prov], key, value)

    def get_provider_api_key(self, provider_id: str) -> str:
        auth = self.providers.get(provider_id)
        return auth.api_key if auth else ""

    def get_provider_base_url(self, provider_id: str) -> str:
        auth = self.providers.get(provider_id)
        return auth.base_url if auth else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": {
                "provider": self.model.provider,
                "model": self.model.model,
                "small_model": self.model.small_model,
                "vision_model": self.model.vision_model,
                "reasoning_effort": self.model.reasoning_effort,
                "temperature": self.model.temperature,
                "max_tokens": self.model.max_tokens,
            },
            "tools": {
                "permissions": {
                    "safe_categories": self.tools.safe_categories,
                    "ask_categories": self.tools.ask_categories,
                    "deny_categories": self.tools.deny_categories,
                },
                "timeout": self.tools.timeout,
            },
            "voice": {
                "wake_word": {
                    "enabled": self.voice.wake_word.enabled,
                    "sensitivity": self.voice.wake_word.sensitivity,
                },
                "stt": {
                    "engine": self.voice.stt.engine,
                    "model_size": self.voice.stt.model_size,
                    "device": self.voice.stt.device,
                },
                "tts": {
                    "engine": self.voice.tts.engine,
                    "voice": self.voice.tts.voice,
                    "rate": self.voice.tts.rate,
                },
                "vad": {
                    "threshold": self.voice.vad.threshold,
                    "silence_duration_ms": self.voice.vad.silence_duration_ms,
                },
            },
            "conversation": {
                "max_turns": self.conversation.max_turns,
                "compress_threshold": self.conversation.compress_threshold,
                "protect_last_n": self.conversation.protect_last_n,
            },
            "ui": {
                "theme": self.ui.theme,
                "font_size": self.ui.font_size,
                "streaming_animation": self.ui.streaming_animation,
                "show_reasoning": self.ui.show_reasoning,
                "show_tool_calls": self.ui.show_tool_calls,
            },
        }

    def save(self):
        USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def _load_json_file(path: Path) -> dict | None:
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None
