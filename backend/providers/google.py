from .base import LLMProvider, ModelInfo, ModelCapabilities, StreamEvent, StreamEventType, Message


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
            import google.generativeai as genai
        except ImportError:
            yield StreamEvent(type=StreamEventType.ERROR, error="google-generativeai package not installed")
            return

        genai.configure(api_key=self.api_key)
        gen_model = genai.GenerativeModel(model)

        converted = []
        for m in messages:
            if m.role == "system":
                converted.append({"role": "user", "parts": [m.content if isinstance(m.content, str) else str(m.content)]})
                converted.append({"role": "model", "parts": ["Understood. I will follow these instructions."]})
            else:
                role = "model" if m.role == "assistant" else "user"
                if isinstance(m.content, list):
                    parts = []
                    for part in m.content:
                        if part.type == "text":
                            parts.append(part.text)
                        elif part.type == "image":
                            parts.append(part.base64)
                    converted.append({"role": role, "parts": parts})
                else:
                    converted.append({"role": role, "parts": [m.content]})

        try:
            response = gen_model.generate_content(
                converted,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens or 8192,
                    temperature=temperature or 0.7,
                ),
            )
            for chunk in response:
                if chunk.text:
                    yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=chunk.text)
            yield StreamEvent(type=StreamEventType.FINISH, finish_reason="stop")
        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, error=str(e))
