import asyncio
import time
from typing import AsyncGenerator, Any

from ..providers.base import Message, StreamEventType, ToolDef
from ..providers import ProviderRegistry
from ..tools.registry import ToolRegistry
from ..config import Config
from .system_prompt import SystemPromptBuilder
from .conversation_manager import ConversationManager
from .context_compressor import ContextCompressor
from .interrupt_manager import InterruptManager, InterruptError
from .cost_tracker import CostTracker


class AgentEngine:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        tool_registry: ToolRegistry,
        config: Config,
        conversation_manager: ConversationManager | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        self._providers = provider_registry
        self._tools = tool_registry
        self._config = config
        self._conv_manager = conversation_manager or ConversationManager()
        self._cost_tracker = cost_tracker or CostTracker()
        self._interrupt = InterruptManager()
        self._prompt_builder = SystemPromptBuilder()
        self._compressor = ContextCompressor(
            protect_first_n=3,
            protect_last_n=config.conversation.protect_last_n,
        )

    @property
    def interrupt(self) -> InterruptManager:
        return self._interrupt

    @property
    def conversation(self) -> ConversationManager:
        return self._conv_manager

    async def run_conversation(
        self,
        user_input: str,
        images: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        self._interrupt.reset()

        provider_id = self._config.model.provider
        model = self._config.model.model

        try:
            conv = self._conv_manager.current
            if not conv:
                conv = self._conv_manager.create(
                    provider=provider_id,
                    model=model,
                    reasoning_effort=self._config.model.reasoning_effort,
                )

            messages = self._build_messages(user_input, images)
            tools = self._tools.list_tools(self._config.tools)
            tool_schemas = [t.to_schema() for t in tools]

            system_prompt = self._prompt_builder.build(
                tool_descriptions=self._format_tool_descriptions(tools),
            )
            messages.insert(0, Message(role="system", content=system_prompt))

            iteration = 0
            max_iterations = 10

            while iteration < max_iterations:
                iteration += 1
                self._interrupt.check()

                provider = self._providers.get(provider_id)
                if not provider:
                    yield {"type": "error", "code": "PROVIDER_ERROR", "message": f"Unknown provider: {provider_id}"}
                    return

                all_text = ""
                all_reasoning = ""
                pending_tool_calls = []

                yield {"type": "status", "state": "thinking"}

                stream = provider.stream_chat(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    reasoning_effort=self._config.model.reasoning_effort,
                    max_tokens=self._config.model.max_tokens,
                    temperature=self._config.model.temperature,
                )
                self._interrupt.set_current_stream(stream)

                for event in stream:
                    self._interrupt.check()

                    if event.type == StreamEventType.TEXT_DELTA:
                        all_text += event.text
                        yield {"type": "assistant_delta", "text": event.text}

                    elif event.type == StreamEventType.REASONING_DELTA:
                        all_reasoning += event.text
                        yield {"type": "reasoning_delta", "text": event.text}

                    elif event.type == StreamEventType.TOOL_CALL:
                        pending_tool_calls.append({
                            "id": event.tool_call_id,
                            "name": event.tool_name,
                            "args": event.tool_args,
                        })
                        yield {
                            "type": "tool_call",
                            "id": event.tool_call_id,
                            "name": event.tool_name,
                            "args": event.tool_args,
                            "requires_confirm": self._tools.requires_confirmation(event.tool_name),
                        }

                    elif event.type == StreamEventType.ERROR:
                        yield {"type": "error", "code": "STREAM_ERROR", "message": event.error}
                        return

                    elif event.type == StreamEventType.FINISH:
                        if event.usage:
                            self._cost_tracker.add_usage(
                                provider_id, model,
                                event.usage.get("input", 0),
                                event.usage.get("output", 0),
                                event.usage.get("reasoning", 0),
                            )

                self._interrupt.set_current_stream(None)

                if all_text:
                    self._conv_manager.add_message("assistant", all_text, reasoning=all_reasoning)

                if not pending_tool_calls:
                    yield {"type": "assistant_done"}
                    break

                yield {"type": "status", "state": "executing_tool"}

                for tc in pending_tool_calls:
                    self._interrupt.check()
                    tool_start = time.time()

                    yield {
                        "type": "tool_call_start",
                        "id": tc["id"],
                        "name": tc["name"],
                        "args": tc["args"],
                    }

                    result = await self._tools.execute(
                        tc["name"],
                        tc["args"],
                        self._config.tools,
                    )

                    duration_ms = int((time.time() - tool_start) * 1000)

                    messages.append(Message(
                        role="assistant",
                        content=all_text,
                        tool_calls=[{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": str(tc["args"])}}],
                    ))
                    messages.append(Message(
                        role="tool",
                        tool_call_id=tc["id"],
                        content=result.get("output", "") if result["success"] else result.get("error", ""),
                    ))

                    if result["success"]:
                        yield {
                            "type": "tool_result",
                            "id": tc["id"],
                            "output": result["output"],
                            "duration_ms": duration_ms,
                        }
                    else:
                        yield {
                            "type": "tool_error",
                            "id": tc["id"],
                            "error": result["error"],
                            "duration_ms": duration_ms,
                        }

                pending_tool_calls = []

            self._conv_manager.save()

        except InterruptError:
            self._interrupt.reset()
            yield {"type": "interrupted"}
            return
        except Exception as e:
            yield {"type": "error", "code": "AGENT_ERROR", "message": str(e)}

        finally:
            yield {"type": "status", "state": "idle"}

    def _build_messages(self, user_input: str, images: list[str] | None) -> list[Message]:
        messages = []

        if self._conv_manager.current:
            for msg in self._conv_manager.current.messages:
                messages.append(Message(role=msg.role, content=msg.content))

        if images:
            from ..providers.base import ContentText, ContentImage
            content_parts = [ContentText(text=user_input)]
            for img_b64 in images:
                content_parts.append(ContentImage(base64=img_b64))
            messages.append(Message(role="user", content=content_parts))
        else:
            messages.append(Message(role="user", content=user_input))

        return messages

    def _format_tool_descriptions(self, tools: list[ToolDef]) -> str:
        lines = []
        for t in tools:
            lines.append(f"- {t.id}: {t.description}")
        return "\n".join(lines) if lines else "No tools available."
