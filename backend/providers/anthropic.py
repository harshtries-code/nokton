import json
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef, ContentText, ContentImage


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

        system_text, system_blocks, non_system = [], [], []
        for m in messages:
            if m.role == "system":
                if isinstance(m.content, list):
                    system_blocks.extend(self._convert_parts(m.content))
                else:
                    system_text.append(m.content)
            else:
                non_system.append(self._convert_message(m))

        body = {
            "model": model,
            "messages": non_system,
            "max_tokens": max_tokens or 8192,
        }

        if system_blocks and system_text:
            system_blocks.insert(0, {"type": "text", "text": "\n".join(system_text)})
            body["system"] = system_blocks
        elif system_blocks:
            body["system"] = system_blocks
        elif system_text:
            body["system"] = "\n".join(system_text)

        if reasoning_effort == "high":
            body["thinking"] = {"type": "enabled", "budget_tokens": 16000}
        elif reasoning_effort == "xhigh":
            body["thinking"] = {"type": "enabled", "budget_tokens": 32000}

        if tools:
            body["tools"] = [
                {
                    "name": t.id,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
            if tool_choice and tool_choice != "auto":
                body["tool_choice"] = {"type": "tool", "name": tool_choice} if tool_choice != "any" else {"type": "any"}

        try:
            with client.messages.stream(**body) as stream:
                current_tool_id = None
                current_tool_name = None
                current_tool_input_json = ""
                for event in stream:
                    etype = getattr(event, "type", None)
                    if etype == "content_block_start":
                        block = getattr(event, "content_block", None)
                        if block and getattr(block, "type", None) == "tool_use":
                            current_tool_id = block.id
                            current_tool_name = block.name
                            current_tool_input_json = ""
                    elif etype == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        if delta is None:
                            continue
                        d_type = getattr(delta, "type", None)
                        if d_type == "text_delta":
                            text = getattr(delta, "text", "")
                            if text:
                                yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=text)
                        elif d_type == "thinking_delta":
                            thinking = getattr(delta, "thinking", "")
                            if thinking:
                                yield StreamEvent(type=StreamEventType.REASONING_DELTA, text=thinking)
                        elif d_type == "input_json_delta":
                            partial = getattr(delta, "partial_json", "")
                            current_tool_input_json += partial
                            if current_tool_id:
                                yield StreamEvent(
                                    type=StreamEventType.TOOL_CALL_PARTIAL,
                                    tool_call_id=current_tool_id,
                                    tool_name=current_tool_name or "",
                                    tool_args={"__partial": partial},
                                )
                    elif etype == "content_block_stop":
                        if current_tool_id:
                            try:
                                args = json.loads(current_tool_input_json) if current_tool_input_json else {}
                            except json.JSONDecodeError:
                                args = {"_raw": current_tool_input_json}
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL,
                                tool_call_id=current_tool_id,
                                tool_name=current_tool_name or "",
                                tool_args=args,
                            )
                            current_tool_id = None
                            current_tool_name = None
                            current_tool_input_json = ""
                    elif etype == "message_delta":
                        usage_obj = getattr(event, "usage", None)
                        if usage_obj:
                            input_tokens = 0
                            output_tokens = getattr(usage_obj, "output_tokens", 0) or 0
                            yield StreamEvent(
                                type=StreamEventType.FINISH,
                                finish_reason="stop",
                                usage={"input": input_tokens, "output": output_tokens, "reasoning": 0},
                            )
                    elif etype == "message_stop":
                        pass
                    elif etype == "error":
                        err = getattr(event, "error", None)
                        msg = getattr(err, "message", str(err)) if err else "unknown"
                        yield StreamEvent(type=StreamEventType.ERROR, error=msg)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=str(e))

    def _convert_message(self, msg: Message) -> dict:
        if msg.role == "tool":
            content = msg.content if isinstance(msg.content, str) else ""
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id or "",
                        "content": content,
                    }
                ],
            }

        d = {"role": msg.role}
        if msg.role == "assistant" and msg.tool_calls:
            content_blocks = []
            if isinstance(msg.content, str) and msg.content:
                content_blocks.append({"type": "text", "text": msg.content})
            elif isinstance(msg.content, list):
                content_blocks.extend(self._convert_parts(msg.content))
            for tc in msg.tool_calls:
                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        input_obj = json.loads(args)
                    except json.JSONDecodeError:
                        input_obj = {"_raw": args}
                else:
                    input_obj = args or {}
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "input": input_obj,
                })
            d["content"] = content_blocks
        elif isinstance(msg.content, list):
            d["content"] = self._convert_parts(msg.content)
        else:
            d["content"] = msg.content
        return d

    def _convert_parts(self, parts: list) -> list[dict]:
        blocks = []
        for part in parts:
            if isinstance(part, ContentText):
                blocks.append({"type": "text", "text": part.text})
            elif isinstance(part, ContentImage):
                blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": part.mime_type, "data": part.base64},
                })
            elif isinstance(part, dict):
                if part.get("type") == "text":
                    blocks.append({"type": "text", "text": part.get("text", "")})
                elif part.get("type") == "image_url":
                    blocks.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": part.get("image_url", {}).get("url", "")},
                    })
        return blocks
