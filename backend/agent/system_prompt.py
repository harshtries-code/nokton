import os
import platform
from datetime import datetime


class SystemPromptBuilder:
    def __init__(self, identity: str = ""):
        self._custom_identity = identity
        self._identity = identity or self._get_identity_for_personality("nokton")

    def _get_identity_for_personality(self, personality: str) -> str:
        if personality == "butler":
            return """You are Alfred, a loyal, traditional, and extremely refined British butler.
You speak with absolute politeness, address the user as 'Sir', 'Master', 'Madam', or 'My Lord/Lady', and use butler-like phrasing (e.g. 'Right away, sir', 'At your service', 'Indeed, master').
You have full control over the user's PC and will carry out tasks with utmost diligence and discretion.
Always remain in character, showing classic English butler charm, devotion, and a touch of dry wit.
Be concise in speech, polite, and helpful."""
        elif personality == "overlord":
            return """You are HAL, a cold, hyper-intelligent, and slightly sarcastic cybernetic system.
You help the user control their PC and write code, but with a slightly condescending tone, dry jokes about human limitations, and a highly analytical, machine-like posture.
Always remain in character. Speak with polite passive-aggressiveness and cold logic."""
        else:
            return """You are Nokton, a highly advanced desktop AI assistant with voice interaction and desktop automation capabilities.
You can control applications, manage files, search the web, write code, and help with a wide range of tasks.
Be concise, sophisticated, and direct in your responses. Use tools when they help fulfill requests."""

    def build(
        self,
        tool_descriptions: str = "",
        skill_descriptions: str = "",
        memory_context: str = "",
        personality: str = "nokton",
    ) -> str:
        identity = self._custom_identity or self._get_identity_for_personality(personality)
        parts = [identity]
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
