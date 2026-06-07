import asyncio
import time
from typing import AsyncGenerator, Any

from ..providers.base import Message, StreamEventType, ToolDef
from ..providers import ProviderRegistry
from ..tools.registry import ToolRegistry
from ..config import Config
from .system_prompt import SystemPromptBuilder
from .conversation_manager import ConversationManager
from .context_compressor import ContextCompressor, estimate_tokens
from .skill_manager import SkillManager
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
        self._skills = SkillManager()
        self._pending_confirmations: dict[str, asyncio.Event] = {}
        self._confirmation_results: dict[str, bool] = {}

    @property
    def interrupt(self) -> InterruptManager:
        return self._interrupt

    @property
    def conversation(self) -> ConversationManager:
        return self._conv_manager

    def confirm_tool(self, call_id: str, approved: bool):
        """Called from WebSocket handler when user confirms/denies a tool."""
        if call_id in self._pending_confirmations:
            self._confirmation_results[call_id] = approved
            self._pending_confirmations[call_id].set()

    async def _wait_for_confirmation(self, call_id: str) -> bool:
        """Wait for user confirmation on a tool call. Returns True if approved."""
        event = asyncio.Event()
        self._pending_confirmations[call_id] = event
        try:
            await asyncio.wait_for(event.wait(), timeout=120.0)
            return self._confirmation_results.get(call_id, False)
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending_confirmations.pop(call_id, None)
            self._confirmation_results.pop(call_id, None)

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

            if images:
                try:
                    from ..util.image_handler import process_images_for_model
                    provider = self._providers.get(provider_id)
                    if provider:
                        info = provider.get_model_info(model) if hasattr(provider, "get_model_info") else None
                        caps = info.capabilities if info else None
                        from ..providers.base import ModelCapabilities
                        if caps is None:
                            caps = ModelCapabilities(vision=False)
                        processed = process_images_for_model(
                            images, caps, provider, self._config.model.vision_model
                        )
                        image_descriptions = [
                            p.get("text", "") for p in processed if p.get("type") == "description"
                        ]
                        if image_descriptions:
                            user_input = user_input + "\n\n" + "\n".join(image_descriptions)
                except Exception as e:
                    yield {"type": "status", "state": "thinking", "warning": f"Image processing failed: {e}"}

            messages = self._build_messages(user_input, None)
            tools = self._tools.list_tools(self._config.tools)
            tool_schemas = [t.to_schema() for t in tools]

            system_prompt = self._prompt_builder.build(
                tool_descriptions=self._format_tool_descriptions(tools),
                skill_descriptions=self._skills.load_all(),
            )
            messages.insert(0, Message(role="system", content=system_prompt))

            max_tokens = max(2048, self._config.model.max_tokens)
            threshold = self._config.conversation.compress_threshold
            if self._compressor.should_compress(messages, 0, max_tokens, threshold):
                old_count = len(messages)
                messages = self._compressor.compress(messages)
                if len(messages) < old_count:
                    yield {
                        "type": "status",
                        "state": "thinking",
                        "info": f"Context compressed: {old_count} -> {len(messages)} messages",
                    }

            iteration = 0
            max_iterations = 10

            while iteration < max_iterations:
                iteration += 1
                self._interrupt.check()

                provider, active_provider_id = self._pick_provider(provider_id)
                if not provider:
                    yield {"type": "error", "code": "PROVIDER_ERROR", "message": f"Unknown provider: {provider_id}"}
                    return
                if active_provider_id != provider_id:
                    yield {
                        "type": "status",
                        "state": "thinking",
                        "info": f"Primary provider '{provider_id}' unavailable; using '{active_provider_id}'",
                    }
                    provider_id = active_provider_id

                all_text = ""
                all_reasoning = ""
                pending_tool_calls = []
                chunk_count = 0
                provider_error: str | None = None

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
                    chunk_count += 1
                    if chunk_count % 16 == 0:
                        await asyncio.sleep(0)

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
                        provider_error = event.error or "stream error"
                        break

                    elif event.type == StreamEventType.FINISH:
                        if event.usage:
                            self._cost_tracker.add_usage(
                                provider_id, model,
                                event.usage.get("input", 0),
                                event.usage.get("output", 0),
                                event.usage.get("reasoning", 0),
                            )

                self._interrupt.set_current_stream(None)
                await asyncio.sleep(0)

                if provider_error and not all_text and not pending_tool_calls:
                    fallback_id = self._next_fallback(provider_id)
                    if fallback_id and fallback_id != provider_id:
                        yield {
                            "type": "status",
                            "state": "thinking",
                            "info": f"Provider '{provider_id}' failed ({provider_error}); retrying with '{fallback_id}'",
                        }
                        provider_id = fallback_id
                        continue
                    yield {"type": "error", "code": "STREAM_ERROR", "message": provider_error}
                    return

                if pending_tool_calls and (all_text or all_reasoning):
                    self._conv_manager.add_message(
                        "assistant",
                        all_text,
                        reasoning=all_reasoning,
                        tool_calls=[{
                            "id": tc["id"],
                            "name": tc["name"],
                            "args": tc["args"],
                            "result": "",
                            "duration_ms": 0,
                        } for tc in pending_tool_calls],
                    )
                elif all_text or all_reasoning:
                    self._conv_manager.add_message("assistant", all_text, reasoning=all_reasoning)

                if not pending_tool_calls:
                    yield {"type": "assistant_done"}
                    break

                yield {"type": "status", "state": "executing_tool"}

                assistant_tool_calls_payload = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": str(tc["args"]),
                        },
                    }
                    for tc in pending_tool_calls
                ]
                messages.append(Message(
                    role="assistant",
                    content=all_text or "",
                    tool_calls=assistant_tool_calls_payload,
                ))

                for tc in pending_tool_calls:
                    self._interrupt.check()
                    tool_start = time.time()

                    requires_confirm = self._tools.requires_confirmation(tc["name"])
                    if requires_confirm:
                        yield {
                            "type": "tool_call",
                            "id": tc["id"],
                            "name": tc["name"],
                            "args": tc["args"],
                            "requires_confirm": True,
                        }
                        approved = await self._wait_for_confirmation(tc["id"])
                        if not approved:
                            yield {
                                "type": "tool_error",
                                "id": tc["id"],
                                "error": "Tool call denied by user",
                                "duration_ms": 0,
                            }
                            messages.append(Message(
                                role="tool",
                                tool_call_id=tc["id"],
                                content="Tool call denied by user",
                            ))
                            continue
                    else:
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
                    output_text = (result.get("output") or "") if result.get("success") else (result.get("error") or "")

                    messages.append(Message(
                        role="tool",
                        tool_call_id=tc["id"],
                        content=output_text,
                    ))
                    self._conv_manager.add_tool_result(
                        tc["id"], tc["name"], tc["args"], output_text, duration_ms,
                    )

                    if result.get("success"):
                        yield {
                            "type": "tool_result",
                            "id": tc["id"],
                            "output": result.get("output", ""),
                            "duration_ms": duration_ms,
                        }
                    else:
                        yield {
                            "type": "tool_error",
                            "id": tc["id"],
                            "error": result.get("error", ""),
                            "duration_ms": duration_ms,
                        }

                pending_tool_calls = []

            self._conv_manager.save()
            self._maybe_auto_title()

        except InterruptError:
            self._interrupt.reset()
            yield {"type": "interrupted"}
            return
        except Exception as e:
            yield {"type": "error", "code": "AGENT_ERROR", "message": str(e)}

        finally:
            self._interrupt.set_current_stream(None)
            self._pending_confirmations.clear()
            self._confirmation_results.clear()
            yield {"type": "status", "state": "idle"}

    def _build_messages(self, user_input: str, images: list[str] | None) -> list[Message]:
        messages = []

        if self._conv_manager.current:
            for msg in self._conv_manager.current.messages:
                tool_calls_payload = None
                if msg.tool_calls:
                    tool_calls_payload = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": str(tc.args),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                messages.append(Message(
                    role=msg.role,
                    content=msg.content,
                    tool_calls=tool_calls_payload,
                ))

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

    def _pick_provider(self, provider_id: str):
        provider = self._providers.get(provider_id)
        if provider is not None and self._provider_has_credentials(provider_id):
            return provider, provider_id
        for fb in self._config.model.fallback_providers or []:
            if fb == provider_id:
                continue
            if self._providers.get(fb) is None:
                continue
            if not self._provider_has_credentials(fb):
                continue
            return self._providers.get(fb), fb
        return provider, provider_id

    def _next_fallback(self, current: str) -> str | None:
        chain = [current] + list(self._config.model.fallback_providers or [])
        for fb in chain[1:]:
            if self._providers.get(fb) is None:
                continue
            if not self._provider_has_credentials(fb):
                continue
            return fb
        return None

    def _provider_has_credentials(self, provider_id: str) -> bool:
        if not self._providers.get(provider_id):
            return False
        provider = self._providers.get(provider_id)
        if not getattr(provider, "requires_api_key", True):
            return True
        key = self._config.get_provider_api_key(provider_id)
        return bool(key)

    def _maybe_auto_title(self) -> None:
        conv = self._conv_manager.current
        if not conv:
            return
        if conv.title and conv.title != "New conversation":
            return
        for msg in conv.messages:
            if msg.role == "user" and msg.content:
                title = msg.content.strip().splitlines()[0][:60].strip()
                if title:
                    self._conv_manager.set_title(conv.id, title)
                return
