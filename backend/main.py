import json
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import Config
from .providers import registry as provider_registry, ModelInfo
from .tools.registry import tool_registry
from .agent.engine import AgentEngine
from .agent.conversation_manager import ConversationManager
from .agent.cost_tracker import CostTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nokton")

config = Config.load()
conversation_manager = ConversationManager()
cost_tracker = CostTracker()
engine = AgentEngine(
    provider_registry=provider_registry,
    tool_registry=tool_registry,
    config=config,
    conversation_manager=conversation_manager,
    cost_tracker=cost_tracker,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Nokton backend starting...")
    provider_registry.refresh_models()
    logger.info("Model catalog refreshed")
    yield
    logger.info("Nokton backend shutting down")


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


class MessageRequest(BaseModel):
    text: str
    images: list[str] = []
    conversation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


# REST endpoints

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


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
        config.model.provider = update.provider
    if update.model is not None:
        config.model.model = update.model
    if update.reasoning_effort is not None:
        config.model.reasoning_effort = update.reasoning_effort
    if update.temperature is not None:
        config.model.temperature = update.temperature
    config.save()
    return config.to_dict()


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

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "user_message":
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

                conversation_manager.add_message("user", text)

                async for event in engine.run_conversation(text, images):
                    try:
                        await ws.send_json(event)
                    except Exception:
                        break

            elif msg_type == "cancel":
                engine.interrupt.cancel()
                await ws.send_json({"type": "interrupted"})

            elif msg_type == "settings_update":
                key = data.get("key", "")
                value = data.get("value")
                if hasattr(config.model, key):
                    setattr(config.model, key, value)
                config.save()
                await ws.send_json({"type": "settings", **config.to_dict()})

            elif msg_type == "confirm_tool":
                call_id = data.get("call_id", "")
                approved = data.get("approved", False)
                engine.confirm_tool(call_id, approved)

            elif msg_type == "set_model":
                if data.get("provider"):
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
                enabled = data.get("enabled", False)
                config.voice.wake_word.enabled = enabled
                config.save()
                await ws.send_json({
                    "type": "voice_event",
                    "state": "idle" if not enabled else "listening",
                })

            elif msg_type == "new_conversation":
                conversation_manager.create(
                    provider=config.model.provider,
                    model=config.model.model,
                    reasoning_effort=config.model.reasoning_effort,
                )
                await ws.send_json({"type": "conversation_created"})

            elif msg_type == "list_conversations":
                convs = conversation_manager.list_conversations()
                await ws.send_json({"type": "conversations_list", "conversations": convs})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        engine.interrupt.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await ws.send_json({"type": "error", "code": "WS_ERROR", "message": str(e)})
        except Exception:
            pass


def run():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    run()
