from ..providers.base import Message


class ContextCompressor:
    def __init__(self, protect_first_n: int = 3, protect_last_n: int = 10):
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n

    def should_compress(self, messages: list[Message], current_tokens: int, max_tokens: int, threshold: float = 0.5) -> bool:
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
            if isinstance(m.content, str):
                snippet = m.content[:200].replace("\n", " ")
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
        compressed.extend(protected_tail)

        return compressed
