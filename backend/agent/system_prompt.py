import os
import platform
from datetime import datetime


class SystemPromptBuilder:
    def __init__(self, identity: str = ""):
        self._identity = identity or self._default_identity()

    def _default_identity(self) -> str:
        return """You are Nokton, a desktop AI assistant with voice interaction and desktop automation capabilities.
You can control applications, manage files, search the web, and help with a wide range of tasks.
Be concise and natural in your responses. Use tools when they help fulfill requests.
If you cannot complete a request, explain why and offer alternatives."""

    def build(
        self,
        tool_descriptions: str = "",
        skill_descriptions: str = "",
        memory_context: str = "",
    ) -> str:
        parts = [self._identity]
        parts.append(self._build_environment())
        if tool_descriptions:
            parts.append(f"# Available Tools\n{tool_descriptions}")
        if skill_descriptions:
            parts.append(f"# Skills\n{skill_descriptions}")
        if memory_context:
            parts.append(f"# Context\n{memory_context}")
        parts.append("# Rules\n- Use tools to fulfill user requests."
                      "\n- For destructive operations (delete, shutdown), explain what you're doing."
                      "\n- If the user says 'stop' or 'cancel', immediately stop."
                      "\n- Be concise in voice responses; be detailed in chat responses.")
        return "\n\n".join(parts)

    def _build_environment(self) -> str:
        now = datetime.now()
        return (
            f"# Environment\n"
            f"Current OS: {platform.system()} {platform.release()}\n"
            f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Current user: {os.environ.get('USERNAME', 'unknown')}\n"
            f"Current directory: {os.getcwd()}"
        )
