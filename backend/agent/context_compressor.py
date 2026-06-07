import json
from ..providers.base import Message


def estimate_tokens(messages: list[Message]) -> int:
    total = 0
    for m in messages:
        c = m.content
        if isinstance(c, str):
            total += max(1, len(c) // 4)
        else:
            try:
                total += max(1, len(json.dumps(c, default=str)) // 4)
            except Exception:
                total += 256
        if m.tool_calls:
            try:
                total += max(1, len(json.dumps(m.tool_calls, default=str)) // 4)
            except Exception:
                total += 256
    return total


class ContextCompressor:
    def __init__(self, protect_first_n: int = 3, protect_last_n: int = 10):
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n

    def should_compress(self, messages: list[Message], current_tokens: int, max_tokens: int, threshold: float = 0.5) -> bool:
        if current_tokens <= 0:
            current_tokens = estimate_tokens(messages)
        return current_tokens >= int(max_tokens * threshold)

    def compress(self, messages: list[Message]) -> list[Message]:
        if len(messages) <= self.protect_first_n + self.protect_last_n + 2:
            return messages

        system_msgs = [m for m in messages[:self.protect_first_n] if m.role == "system"]
        first_user = [m for m in messages[:self.protect_first_n] if m.role != "system"]

        protected_tail = messages[-self.protect_last_n:]

        middle = messages[self.protect_first_n:-self.protect_last_n]

        summary_parts = []
        for m in middle:
            content = m.content if isinstance(m.content, str) else str(m.content)
            snippet = content[:200].replace("\n", " ")
            if m.tool_calls:
                names = ",".join(tc.get("function", {}).get("name", "?") for tc in m.tool_calls)
                summary_parts.append(f"[{m.role}](tools:{names}): {snippet}")
            else:
                summary_parts.append(f"[{m.role}]: {snippet}")

        compressed = []
        compressed.extend(system_msgs)
        compressed.extend(first_user)
        if summary_parts:
            compressed.append(
                Message(
                    role="user",
                    content=f"[Context summary of previous conversation:\n" + "\n".join(summary_parts) + "\n]"
                )
            )
        compressed.append(
            Message(
                role="assistant",
                content="Understood. I'll use the summary as context for the next turn."
            )
        )
        compressed.extend(protected_tail)

        return compressed

