import json
from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message, ToolDef, ContentText, ContentImage


class GoogleProvider(LLMProvider):
    id = "google"
    name = "Google Gemini"
    requires_api_key = True

    def __init__(self, api_key: str = "", base_url: str | None = None):
        self.api_key = api_key

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="gemini-2.5-pro", provider_id=self.id, name="Gemini 2.5 Pro", context_window=1000000, capabilities=ModelCapabilities(vision=True, tool_calling=True, reasoning=True)),
            ModelInfo(id="gemini-2.5-flash", provider_id=self.id, name="Gemini 2.5 Flash", context_window=1000000, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
            ModelInfo(id="gemini-2.0-flash", provider_id=self.id, name="Gemini 2.0 Flash", context_window=1000000, capabilities=ModelCapabilities(vision=True, tool_calling=True)),
        ]

    def stream_chat(self, model, messages, tools=None, tool_choice="auto", reasoning_effort=None, max_tokens=None, temperature=None, stop=None):
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError:
            yield StreamEvent(type=StreamEventType.ERROR, error="google-genai package not installed")
            return

        try:
            client = genai.Client(api_key=self.api_key)
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=f"google-genai client init failed: {e}")
            return

        system_text_parts = []
        contents = []
        for m in messages:
            if m.role == "system":
                if isinstance(m.content, list):
                    for p in m.content:
                        if isinstance(p, ContentText):
                            system_text_parts.append(p.text)
                else:
                    system_text_parts.append(m.content)
                continue
            role = "model" if m.role == "assistant" else "user"
            if m.role == "tool":
                role = "user"
            if isinstance(m.content, list):
                parts = []
                for p in m.content:
                    if isinstance(p, ContentText):
                        parts.append({"text": p.text})
                    elif isinstance(p, ContentImage):
                        parts.append({
                            "inline_data": {
                                "mime_type": p.mime_type,
                                "data": p.base64,
                            }
                        })
            else:
                parts = [{"text": str(m.content) if m.content is not None else ""}]
            contents.append({"role": role, "parts": parts})

        config_dict = {}
        if max_tokens is not None:
            config_dict["max_output_tokens"] = int(max_tokens)
        if temperature is not None:
            config_dict["temperature"] = float(temperature)
        if system_text_parts:
            config_dict["system_instruction"] = "\n".join(system_text_parts)
        if tools:
            function_decls = []
            for t in tools:
                function_decls.append({
                    "name": t.id,
                    "description": t.description,
                    "parameters": t.parameters,
                })
            config_dict["tools"] = [{"function_declarations": function_decls}]

        try:
            gen_config = genai_types.GenerateContentConfig(**config_dict) if config_dict else None
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=f"google-genai config error: {e}")
            return

        try:
            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=gen_config,
            )
            for chunk in response:
                text = self._extract_text(chunk)
                if text:
                    yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=text)
                for tc_id, tc_name, tc_args in self._extract_tool_calls(chunk):
                    yield StreamEvent(
                        type=StreamEventType.TOOL_CALL,
                        tool_call_id=tc_id,
                        tool_name=tc_name,
                        tool_args=tc_args,
                    )
                usage = self._extract_usage(chunk)
                if usage:
                    yield StreamEvent(type=StreamEventType.FINISH, finish_reason="stop", usage=usage)
                    return
            yield StreamEvent(type=StreamEventType.FINISH, finish_reason="stop")
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=str(e))

    def _extract_text(self, chunk) -> str:
        try:
            candidates = getattr(chunk, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", None) or []
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        texts.append(t)
                if texts:
                    return "".join(texts)
        except Exception:
            pass
        return ""

    def _extract_tool_calls(self, chunk) -> list[tuple[str, str, dict]]:
        out = []
        try:
            candidates = getattr(chunk, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    fc = getattr(p, "function_call", None)
                    if fc:
                        name = getattr(fc, "name", "") or ""
                        args = getattr(fc, "args", None)
                        if args is None:
                            args = {}
                        elif not isinstance(args, dict):
                            try:
                                args = json.loads(str(args))
                            except Exception:
                                args = {"_raw": str(args)}
                        out.append((f"call_{len(out)}", name, args))
        except Exception:
            pass
        return out

    def _extract_usage(self, chunk) -> dict | None:
        meta = getattr(chunk, "usage_metadata", None)
        if not meta:
            return None
        return {
            "input": getattr(meta, "prompt_token_count", 0) or 0,
            "output": getattr(meta, "candidates_token_count", 0) or 0,
            "reasoning": getattr(meta, "thoughts_token_count", 0) or 0,
        }
