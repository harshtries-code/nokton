from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Any, Callable
from enum import Enum
import json


class StreamEventType(Enum):
    TEXT_DELTA = "text_delta"
    REASONING_DELTA = "reasoning_delta"
    TOOL_CALL = "tool_call"
    TOOL_CALL_PARTIAL = "tool_call_partial"
    FINISH = "finish"
    ERROR = "error"


@dataclass
class StreamEvent:
    type: StreamEventType
    text: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = ""
    usage: dict[str, int] | None = None
    error: str = ""


def _stream_openai_compatible(
    client,
    model: str,
    messages: list,
    tools: list | None = None,
    tool_choice: str = "auto",
    max_tokens: int | None = None,
    temperature: float | None = None,
    stop: list[str] | None = None,
    extra_body: dict | None = None,
) -> Generator[StreamEvent, None, None]:
    """Shared streaming implementation for OpenAI-compatible APIs."""
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if temperature is not None:
        body["temperature"] = temperature
    if stop:
        body["stop"] = stop
    if tools:
        body["tools"] = [t.to_schema() for t in tools]
        body["tool_choice"] = tool_choice
    if extra_body:
        body.update(extra_body)

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
                    yield StreamEvent(
                        type=StreamEventType.TOOL_CALL_PARTIAL,
                        tool_call_id=tc.id or "",
                        tool_name=tc.function.name or "",
                        tool_args={"__partial": tc.function.arguments or ""},
                    )
                    continue
                yield StreamEvent(
                    type=StreamEventType.TOOL_CALL,
                    tool_call_id=tc.id or "",
                    tool_name=tc.function.name or "",
                    tool_args=args,
                )

        if chunk.choices[0].finish_reason:
            usage = None
            if chunk.usage:
                usage = {
                    "input": chunk.usage.prompt_tokens,
                    "output": chunk.usage.completion_tokens,
                    "total": chunk.usage.total_tokens,
                }
            yield StreamEvent(
                type=StreamEventType.FINISH,
                finish_reason=chunk.choices[0].finish_reason,
                usage=usage,
            )


@dataclass
class ModelPricing:
    input_per_1m: float = 0.0
    output_per_1m: float = 0.0
    cache_read_per_1m: float | None = None
    is_free: bool = False


@dataclass
class ModelCapabilities:
    vision: bool = False
    tool_calling: bool = True
    streaming: bool = True
    reasoning: bool = False
    json_mode: bool = False
    fine_tuning: bool = False


@dataclass
class ModelInfo:
    id: str
    provider_id: str
    name: str
    family: str | None = None
    context_window: int = 128000
    max_output: int = 8192
    pricing: ModelPricing | None = None
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)


@dataclass
class ContentText:
    text: str
    type: str = "text"


@dataclass
class ContentImage:
    base64: str
    type: str = "image"
    mime_type: str = "image/jpeg"


ContentPart = ContentText | ContentImage


@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str | list[ContentPart] = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role}
        if isinstance(self.content, list):
            d["content"] = []
            for part in self.content:
                if part.type == "text":
                    d["content"].append({"type": "text", "text": part.text})
                elif part.type == "image":
                    d["content"].append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{part.mime_type};base64,{part.base64}"},
                    })
        else:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ToolDef:
    id: str
    description: str
    category: str = "general"
    handler: Callable = lambda **_: ""
    parameters: dict[str, Any] = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": [],
    })
    requires_confirm: bool = False
    timeout: int = 30
    check_fn: Callable | None = None

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class LLMProvider(ABC):

    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_models(self) -> list[ModelInfo]: ...

    @abstractmethod
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
    ) -> Generator[StreamEvent, None, None]: ...

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        for m in self.get_models():
            if m.id == model_id:
                return m
        return None

    @property
    def requires_api_key(self) -> bool:
        return True

    def check_health(self) -> bool:
        try:
            models = self.get_models()
            return len(models) > 0
        except Exception:
            return False

    def validate_api_key(self, key: str) -> bool:
        if not key or not key.strip():
            return False
        return self._probe_auth(key)

    def _probe_auth(self, key: str) -> bool:
        try:
            import requests
            url = (self.base_url or "").rstrip("/")
            if not url:
                return True
            for path in ("/models", "/auth/key", "/me"):
                try:
                    resp = requests.get(
                        f"{url}{path}",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        return True
                    if resp.status_code in (401, 403):
                        return False
                except requests.RequestException:
                    continue
            return bool(key)
        except Exception:
            return bool(key)
