import json
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any


CONVERSATIONS_DIR = Path.home() / ".nokton" / "conversations"


@dataclass
class ToolCallRecord:
    id: str = ""
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    duration_ms: int = 0


@dataclass
class MessageRecord:
    role: str = ""
    content: str = ""
    reasoning: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    timestamp: str = ""


@dataclass
class Conversation:
    id: str = ""
    title: str = "New conversation"
    provider: str = ""
    model: str = ""
    reasoning_effort: str = ""
    created_at: str = ""
    updated_at: str = ""
    messages: list[MessageRecord] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def summary(self) -> str:
        return f"{self.title} ({self.message_count} messages)"


class ConversationManager:
    def __init__(self, storage_dir: str | None = None):
        self._dir = Path(storage_dir) if storage_dir else CONVERSATIONS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._current: Conversation | None = None

    def create(self, provider: str = "", model: str = "", reasoning_effort: str = "") -> Conversation:
        conv = Conversation(
            id=f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self._current = conv
        return conv

    @property
    def current(self) -> Conversation | None:
        return self._current

    def set_current(self, conv: Conversation):
        self._current = conv

    def add_message(self, role: str, content: str, reasoning: str = "", tool_calls: list[dict] | None = None):
        if not self._current:
            raise RuntimeError(
                "No active conversation; call create() or set_current() before add_message()"
            )

        msg = MessageRecord(
            role=role,
            content=content,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat(),
        )
        if tool_calls:
            msg.tool_calls = [
                ToolCallRecord(
                    id=tc.get("id", ""),
                    name=tc.get("name", ""),
                    args=tc.get("args", {}),
                    result=tc.get("result", ""),
                    duration_ms=tc.get("duration_ms", 0),
                )
                for tc in tool_calls
            ]
        self._current.messages.append(msg)
        self._current.updated_at = datetime.now().isoformat()

    def add_tool_result(self, call_id: str, tool_name: str, args: dict, result: str, duration_ms: int):
        if not self._current:
            return
        for msg in reversed(self._current.messages):
            if msg.role == "assistant":
                for tc in msg.tool_calls:
                    if tc.id == call_id:
                        tc.result = result
                        tc.duration_ms = duration_ms
                        return
        self.add_message("tool", result, tool_calls=[{
            "id": call_id,
            "name": tool_name,
            "args": args,
            "result": result,
            "duration_ms": duration_ms,
        }])

    def save(self):
        if not self._current:
            return
        path = self._dir / f"{self._current.id}.json"
        data = {
            "id": self._current.id,
            "title": self._current.title,
            "provider": self._current.provider,
            "model": self._current.model,
            "reasoning_effort": self._current.reasoning_effort,
            "created_at": self._current.created_at,
            "updated_at": self._current.updated_at,
            "messages": [asdict(m) for m in self._current.messages],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, conv_id: str) -> Conversation | None:
        path = self._dir / f"{conv_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        conv = Conversation(
            id=data["id"],
            title=data.get("title", ""),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            reasoning_effort=data.get("reasoning_effort", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
        for md in data.get("messages", []):
            msg = MessageRecord(
                role=md["role"],
                content=md.get("content", ""),
                reasoning=md.get("reasoning", ""),
                timestamp=md.get("timestamp", ""),
            )
            for tc in md.get("tool_calls", []):
                msg.tool_calls.append(ToolCallRecord(**tc))
            conv.messages.append(msg)
        return conv

    def list_conversations(self) -> list[dict]:
        conversations = []
        for path in sorted(self._dir.glob("conv_*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "title": data.get("title", "New conversation"),
                    "message_count": len(data.get("messages", [])),
                    "updated_at": data.get("updated_at", ""),
                })
            except Exception:
                pass
        return sorted(conversations, key=lambda c: c["updated_at"], reverse=True)

    def delete(self, conv_id: str) -> bool:
        path = self._dir / f"{conv_id}.json"
        if path.exists():
            path.unlink()
            if self._current and self._current.id == conv_id:
                self._current = None
            return True
        return False

    def export(self, conv_id: str, fmt: str = "json") -> str:
        conv = self.load(conv_id)
        if not conv:
            return ""
        if fmt == "json":
            path = self._dir / f"{conv_id}.json"
            return path.read_text(encoding="utf-8")
        lines = [f"# {conv.title}", f"Model: {conv.model}\n"]
        for msg in conv.messages:
            prefix = "## You" if msg.role == "user" else "## Nokton"
            lines.append(f"\n{prefix}\n{msg.content}")
        return "\n".join(lines)

    def set_title(self, conv_id: str, title: str) -> bool:
        if self._current and self._current.id == conv_id:
            self._current.title = title[:200] if title else self._current.title
            self._current.updated_at = datetime.now().isoformat()
        path = self._dir / f"{conv_id}.json"
        if not path.exists():
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["title"] = title[:200] if title else data.get("title", "")
            data["updated_at"] = datetime.now().isoformat()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def search(self, query: str, limit: int = 20) -> list[dict]:
        if not query or not query.strip():
            return []
        q = query.strip().lower()
        results = []
        for path in self._dir.glob("conv_*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            title = (data.get("title") or "").lower()
            messages_text = " ".join(
                m.get("content", "") for m in data.get("messages", [])
            ).lower()
            score = 0
            if q in title:
                score += 10
            if q in messages_text:
                score += 1
            if score == 0:
                continue
            results.append({
                "id": data.get("id", path.stem),
                "title": data.get("title", ""),
                "message_count": len(data.get("messages", [])),
                "updated_at": data.get("updated_at", ""),
                "score": score,
            })
        results.sort(key=lambda r: (r["score"], r["updated_at"]), reverse=True)
        return results[:limit]
