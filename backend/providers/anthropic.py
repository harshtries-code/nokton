from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef


class AnthropicProvider(LLMProvider):
    id = "anthropic"
    name = "Anthropic"
    requires_api_key = True
    base_url = "https://api.anthropic.com/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="claude-sonnet-4-20250514", provider_id=self.id, name="Claude Sonnet 4", context_window=200000, capabilities=ModelCapabilities(vision=True, reasoning=True, tool_calling=True)),
            ModelInfo(id="claude-haiku-3-5-20241022", provider_id=self.id, name="Claude Haiku 3.5", context_window=200000, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
            ModelInfo(id="claude-opus-4-20250514", provider_id=self.id, name="Claude Opus 4", context_window=200000, capabilities=ModelCapabilities(vision=True, reasoning=True, tool_calling=True)),
        ]

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        try:
            import anthropic
        except ImportError:
            yield StreamEvent(type=StreamEventType.ERROR, error="anthropic package not installed")
            return

        client = anthropic.Anthropic(api_key=self.api_key)
        body = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages if m.role != "system"],
            "max_tokens": max_tokens or 8192,
            "stream": True,
        }
        system_msgs = [m.content for m in messages if m.role == "system"]
        if system_msgs:
            body["system"] = "\n".join(system_msgs) if isinstance(system_msgs[0], str) else str(system_msgs)

        if reasoning_effort == "high":
            body["thinking"] = {"type": "enabled", "budget_tokens": 16000}
        elif reasoning_effort == "xhigh":
            body["thinking"] = {"type": "enabled", "budget_tokens": 32000}

        try:
            with client.messages.stream(**body) as stream:
                for text in stream.text_stream:
                    yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=text)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=str(e))

    def _convert_message(self, msg: Message) -> dict:
        d = {"role": msg.role}
        if isinstance(msg.content, list):
            d["content"] = []
            for part in msg.content:
                if part.type == "text":
                    d["content"].append({"type": "text", "text": part.text})
                elif part.type == "image":
                    d["content"].append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": part.mime_type, "data": part.base64},
                    })
        else:
            d["content"] = msg.content
        return d
