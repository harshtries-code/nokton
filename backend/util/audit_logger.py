import json
from datetime import datetime
from pathlib import Path
from typing import Any

TOOL_LOG_PATH = Path.home() / ".nokton" / "logs" / "tool_calls.log"
APP_LOG_PATH = Path.home() / ".nokton" / "logs" / "app.log"
COST_LOG_PATH = Path.home() / ".nokton" / "logs" / "cost.log"


class AuditLogger:
    def __init__(self):
        self._ensure_dirs()

    def _ensure_dirs(self):
        TOOL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def log_tool_call(self, call_id: str, tool: str, args: dict, approved: bool, result: dict | None, duration: float):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "call_id": call_id,
            "tool": tool,
            "args": self._sanitize(args),
            "approved": approved,
            "success": result.get("success", False) if result else False,
            "duration_ms": int(duration * 1000),
        }
        self._append(TOOL_LOG_PATH, entry)

    def log_app(self, level: str, message: str, **extra):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **extra,
        }
        self._append(APP_LOG_PATH, entry)

    def log_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int, cost_usd: float):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        }
        self._append(COST_LOG_PATH, entry)

    def _sanitize(self, args: dict) -> dict[str, Any]:
        sensitive_keys = {"api_key", "password", "secret", "token", "key"}
        return {k: ("***" if k.lower() in sensitive_keys else v) for k, v in args.items()}

    def _append(self, path: Path, entry: dict):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
