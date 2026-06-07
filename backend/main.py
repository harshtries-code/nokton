import json
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import Config
from .providers import registry as provider_registry, ModelInfo
from .tools.registry import tool_registry, set_audit_logger
from .agent.engine import AgentEngine
from .agent.conversation_manager import ConversationManager
from .agent.cost_tracker import CostTracker
from .util.audit_logger import AuditLogger
from .providers.model_catalog import ModelCatalog
from .voice.pipeline import VoicePipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nokton")

config = Config.load()
conversation_manager = ConversationManager()
catalog = ModelCatalog()
catalog.load_cache()
cost_tracker = CostTracker(catalog=catalog)
audit_logger = AuditLogger()
set_audit_logger(audit_logger)
engine = AgentEngine(
    provider_registry=provider_registry,
    tool_registry=tool_registry,
    config=config,
    conversation_manager=conversation_manager,
    cost_tracker=cost_tracker,
)
voice_pipeline: VoicePipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global voice_pipeline
    logger.info("Nokton backend starting...")
    provider_registry.refresh_models()
    logger.info("Model catalog refreshed")
    voice_pipeline = VoicePipeline(config.voice)
    voice_pipeline.set_callbacks(
        on_state=_broadcast_voice_state,
        on_transcript=_handle_voice_transcript,
    )
    yield
    logger.info("Nokton backend shutting down")
    try:
        if voice_pipeline:
            voice_pipeline.stop()
    except Exception:
        pass
    try:
        from .tools.registry import _shutdown_thread_pool
        _shutdown_thread_pool()
    except Exception:
        pass


_active_voice_sockets: set = set()


def _broadcast_voice_state(state: str) -> None:
    for ws in list(_active_voice_sockets):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws.send_json({"type": "voice_event", "state": state}), loop,
                )
        except Exception:
            pass


async def _handle_voice_transcript(text: str) -> None:
    if not text or not text.strip():
        return
    if not conversation_manager.current:
        conversation_manager.create(
            provider=config.model.provider,
            model=config.model.model,
            reasoning_effort=config.model.reasoning_effort,
        )
    conversation_manager.add_message("user", text)
    _broadcast_voice_state("thinking")
    full_response = ""
    try:
        async for event in engine.run_conversation(text, []):
            evt_type = event.get("type") if isinstance(event, dict) else None
            if evt_type == "assistant_delta":
                full_response += event.get("text", "")
            elif evt_type == "assistant_done":
                if voice_pipeline and full_response.strip():
                    voice_pipeline.speak(full_response)
                _broadcast_voice_state("speaking")
            for ws in list(_active_voice_sockets):
                try:
                    await ws.send_json(event)
                except Exception:
                    pass
        _broadcast_voice_state("listening")
    except Exception as e:
        logger.error(f"voice conversation error: {e}")
        _broadcast_voice_state("error")


app = FastAPI(title="Nokton", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SettingsUpdate(BaseModel):
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    temperature: float | None = None
    api_key: str | None = None
    voice: dict | None = None
    ui: dict | None = None
    tools: dict | None = None
    conversation: dict | None = None


class SetApiKeyRequest(BaseModel):
    provider: str
    api_key: str


class MessageRequest(BaseModel):
    text: str
    images: list[str] = []
    conversation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


def _set_config_path(path: str, value):
    parts = path.split(".")
    if not parts:
        return False
    section = parts[0]
    if section == "model" and len(parts) == 2:
        if hasattr(config.model, parts[1]):
            setattr(config.model, parts[1], value)
            return True
    elif section == "ui" and len(parts) == 2:
        if hasattr(config.ui, parts[1]):
            setattr(config.ui, parts[1], value)
            return True
    elif section == "voice":
        if len(parts) == 3 and hasattr(config.voice, parts[1]):
            sub = getattr(config.voice, parts[1])
            if hasattr(sub, parts[2]):
                setattr(sub, parts[2], value)
                return True
    elif section == "tools":
        if len(parts) == 3 and parts[1] == "permissions" and hasattr(config.tools, parts[2]):
            setattr(config.tools, parts[2], value)
            return True
    elif section == "conversation" and len(parts) == 2:
        if hasattr(config.conversation, parts[1]):
            setattr(config.conversation, parts[1], value)
            return True
    return False


# REST endpoints

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/providers")
async def list_providers():
    return {"providers": provider_registry.list_providers()}


@app.get("/api/models")
async def get_models():
    models_by_provider = provider_registry.get_models()
    result = []
    for provider_id, models in models_by_provider.items():
        provider_info = provider_registry.get(provider_id)
        result.append({
            "id": provider_id,
            "name": provider_info.name if provider_info else provider_id,
            "requires_api_key": provider_info.requires_api_key if provider_info else True,
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "context_window": m.context_window,
                    "max_output": m.max_output,
                    "capabilities": {
                        "vision": m.capabilities.vision,
                        "tool_calling": m.capabilities.tool_calling,
                        "streaming": m.capabilities.streaming,
                        "reasoning": m.capabilities.reasoning,
                    },
                    "pricing": {
                        "input_per_1m": m.pricing.input_per_1m if m.pricing else 0,
                        "output_per_1m": m.pricing.output_per_1m if m.pricing else 0,
                        "is_free": m.pricing.is_free if m.pricing else False,
                    } if m.pricing else None,
                }
                for m in models
            ],
        })
    return {"providers": result}


@app.get("/api/settings")
async def get_settings():
    return config.to_dict()


@app.post("/api/settings")
async def update_settings(update: SettingsUpdate):
    if update.provider is not None:
        valid_ids = [p["id"] for p in provider_registry.list_providers()]
        if valid_ids and update.provider not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {update.provider}")
        config.model.provider = update.provider
    if update.model is not None:
        config.model.model = update.model
    if update.reasoning_effort is not None:
        if update.reasoning_effort not in ("off", "high", "xhigh"):
            raise HTTPException(status_code=400, detail=f"Invalid reasoning_effort: {update.reasoning_effort}")
        config.model.reasoning_effort = update.reasoning_effort
    if update.temperature is not None:
        if not 0.0 <= update.temperature <= 2.0:
            raise HTTPException(status_code=400, detail="temperature must be between 0.0 and 2.0")
        config.model.temperature = update.temperature
    if update.api_key is not None:
        if not update.provider:
            raise HTTPException(status_code=400, detail="provider is required when setting api_key")
        from .config import ProviderAuth
        if update.provider not in config.providers:
            config.providers[update.provider] = ProviderAuth()
        config.providers[update.provider].api_key = update.api_key
    if update.voice:
        for k, v in update.voice.items():
            if hasattr(config.voice, k):
                setattr(config.voice, k, v)
    if update.ui:
        for k, v in update.ui.items():
            if hasattr(config.ui, k):
                setattr(config.ui, k, v)
    if update.tools:
        for k, v in update.tools.items():
            if hasattr(config.tools, k):
                setattr(config.tools, k, v)
    if update.conversation:
        for k, v in update.conversation.items():
            if hasattr(config.conversation, k):
                setattr(config.conversation, k, v)
    config.save()
    return config.to_dict()


@app.post("/api/api-key")
async def set_api_key(req: SetApiKeyRequest):
    from .config import ProviderAuth
    valid_ids = [p["id"] for p in provider_registry.list_providers()]
    if valid_ids and req.provider not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")
    if req.provider not in config.providers:
        config.providers[req.provider] = ProviderAuth()
    config.providers[req.provider].api_key = req.api_key
    config.save()
    return {"ok": True, "provider": req.provider}


@app.get("/api/conversations")
async def list_conversations():
    return {"conversations": conversation_manager.list_conversations()}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = conversation_manager.load(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": conv.id,
        "title": conv.title,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "reasoning": m.reasoning,
                "timestamp": m.timestamp,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "args": tc.args,
                        "result": tc.result,
                        "duration_ms": tc.duration_ms,
                    }
                    for tc in m.tool_calls
                ],
            }
            for m in conv.messages
        ],
    }


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    success = conversation_manager.delete(conv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@app.post("/api/conversations/{conv_id}/export")
async def export_conversation(conv_id: str, fmt: str = "json"):
    data = conversation_manager.export(conv_id, fmt)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"data": data}


# WebSocket endpoint

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket client connected")
    _active_voice_sockets.add(ws)
    if voice_pipeline is not None:
        try:
            voice_pipeline.bind_loop(asyncio.get_event_loop())
        except Exception:
            pass

    agent_task: asyncio.Task | None = None
    send_lock = asyncio.Lock()

    async def _send(event: dict):
        async with send_lock:
            try:
                await ws.send_json(event)
            except Exception:
                pass

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "user_message":
                if agent_task is not None and not agent_task.done():
                    await _send({"type": "error", "code": "BUSY", "message": "Agent is already running; cancel first"})
                    continue

                text = data.get("text", "")
                images = data.get("images", [])

                if data.get("conversation_id"):
                    conv = conversation_manager.load(data["conversation_id"])
                    if conv:
                        conversation_manager.set_current(conv)

                if data.get("provider"):
                    config.model.provider = data["provider"]
                if data.get("model"):
                    config.model.model = data["model"]
                if data.get("reasoning_effort"):
                    config.model.reasoning_effort = data["reasoning_effort"]

                if not conversation_manager.current:
                    conversation_manager.create(
                        provider=config.model.provider,
                        model=config.model.model,
                        reasoning_effort=config.model.reasoning_effort,
                    )
                conversation_manager.add_message("user", text)

                async def stream_events():
                    try:
                        async for event in engine.run_conversation(text, images):
                            await _send(event)
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        try:
                            await _send({"type": "error", "code": "AGENT_ERROR", "message": str(e)})
                        except Exception:
                            pass
                    finally:
                        await _send({"type": "status", "state": "idle"})

                agent_task = asyncio.create_task(stream_events())

            elif msg_type == "cancel":
                engine.interrupt.cancel()
                if agent_task is not None and not agent_task.done():
                    agent_task.cancel()
                    try:
                        await agent_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    agent_task = None
                await _send({"type": "interrupted"})

            elif msg_type == "settings_update":
                key = data.get("key", "")
                value = data.get("value")
                if _set_config_path(key, value):
                    config.save()
                await ws.send_json({"type": "settings", **config.to_dict()})

            elif msg_type == "set_api_key":
                from .config import ProviderAuth
                pid = data.get("provider", "")
                key = data.get("api_key", "")
                valid_ids = [p["id"] for p in provider_registry.list_providers()]
                if valid_ids and pid not in valid_ids:
                    await ws.send_json({"type": "error", "code": "UNKNOWN_PROVIDER", "message": f"Unknown provider: {pid}"})
                    continue
                if pid not in config.providers:
                    config.providers[pid] = ProviderAuth()
                config.providers[pid].api_key = key
                config.save()
                await ws.send_json({"type": "api_key_saved", "provider": pid})

            elif msg_type == "confirm_tool":
                call_id = data.get("call_id", "")
                approved = data.get("approved", False)
                engine.confirm_tool(call_id, approved)

            elif msg_type == "set_model":
                if data.get("provider"):
                    valid_ids = [p["id"] for p in provider_registry.list_providers()]
                    if valid_ids and data["provider"] not in valid_ids:
                        await ws.send_json({"type": "error", "code": "UNKNOWN_PROVIDER", "message": f"Unknown provider: {data['provider']}"})
                        continue
                    config.model.provider = data["provider"]
                if data.get("model"):
                    config.model.model = data["model"]
                if data.get("reasoning_effort"):
                    config.model.reasoning_effort = data["reasoning_effort"]
                config.save()
                await ws.send_json({"type": "model_updated", **config.model.__dict__})

            elif msg_type == "get_models":
                models_by_provider = provider_registry.get_models()
                result = []
                for pid, models in models_by_provider.items():
                    provider_info = provider_registry.get(pid)
                    result.append({
                        "id": pid,
                        "name": provider_info.name if provider_info else pid,
                        "models": [{"id": m.id, "name": m.name} for m in models],
                    })
                await ws.send_json({"type": "models_list", "providers": result})

            elif msg_type == "voice_toggle":
                enabled = bool(data.get("enabled", False))
                config.voice.wake_word.enabled = enabled
                config.save()
                if voice_pipeline is not None:
                    try:
                        voice_pipeline.bind_loop(asyncio.get_event_loop())
                    except Exception:
                        pass
                    if enabled:
                        voice_pipeline.start()
                    else:
                        voice_pipeline.stop()
                await ws.send_json({
                    "type": "voice_event",
                    "state": "idle" if not enabled else "listening",
                })

            elif msg_type == "new_conversation":
                conv = conversation_manager.create(
                    provider=config.model.provider,
                    model=config.model.model,
                    reasoning_effort=config.model.reasoning_effort,
                )
                await ws.send_json({
                    "type": "conversation_created",
                    "id": conv.id,
                    "provider": conv.provider,
                    "model": conv.model,
                    "reasoning_effort": conv.reasoning_effort,
                })

            elif msg_type == "load_conversation":
                conv_id = data.get("conversation_id", "")
                conv = conversation_manager.load(conv_id)
                if not conv:
                    await ws.send_json({"type": "error", "code": "CONV_NOT_FOUND", "message": f"Conversation not found: {conv_id}"})
                else:
                    conversation_manager.set_current(conv)
                    await ws.send_json({
                        "type": "conversation_loaded",
                        "id": conv.id,
                        "title": conv.title,
                        "messages": [
                            {
                                "role": m.role,
                                "content": m.content,
                                "reasoning": m.reasoning,
                                "timestamp": m.timestamp,
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "name": tc.name,
                                        "args": tc.args,
                                        "result": tc.result,
                                        "duration_ms": tc.duration_ms,
                                    }
                                    for tc in m.tool_calls
                                ],
                            }
                            for m in conv.messages
                        ],
                    })

            elif msg_type == "list_conversations":
                convs = conversation_manager.list_conversations()
                await ws.send_json({"type": "conversations_list", "conversations": convs})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        _active_voice_sockets.discard(ws)
        engine.interrupt.cancel()
        if agent_task is not None and not agent_task.done():
            agent_task.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        _active_voice_sockets.discard(ws)
        try:
            await _send({"type": "error", "code": "WS_ERROR", "message": str(e)})
        except Exception:
            pass


def run():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    run()
