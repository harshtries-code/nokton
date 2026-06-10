"""
Fast-path command classifier for Nokton.

Matches common voice/text commands (open X, close X, volume up/down, etc.)
and executes them directly without calling the LLM, giving <1s response time
for simple desktop control tasks.

Falls through to the full LLM pipeline for anything complex.
"""
import re
from typing import Optional


# Patterns are (regex, tool_name, args_builder)
# args_builder is a callable that takes the regex match and returns tool args dict
_FAST_COMMANDS: list[tuple[re.Pattern, str, callable]] = []


def _register(pattern: str, tool_name: str, args_builder):
    """Register a fast-path command pattern."""
    _FAST_COMMANDS.append((re.compile(pattern, re.IGNORECASE), tool_name, args_builder))


# ──────────────────────────────────────────────
# App launch / close
# ──────────────────────────────────────────────
_APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "terminal": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "calculator": "calc",
    "calc": "calc",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "paint": "mspaint",
    "snipping tool": "snippingtool",
    "teams": "teams",
    "outlook": "outlook",
    "obs": "obs64",
    "steam": "steam",
    "zoom": "zoom",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
}


def _resolve_app(name: str) -> str:
    """Resolve common app names to executable names."""
    lower = name.strip().lower()
    return _APP_ALIASES.get(lower, lower)


_register(
    r"^(?:open|launch|start|run)\s+(.+?)(?:\s+(?:app|application|program))?$",
    "launch_app",
    lambda m: {"app_name": _resolve_app(m.group(1))},
)

_register(
    r"^(?:close|quit|exit|kill|stop)\s+(.+?)(?:\s+(?:app|application|program))?$",
    "close_app",
    lambda m: {"app_name": _resolve_app(m.group(1))},
)

# ──────────────────────────────────────────────
# Volume control
# ──────────────────────────────────────────────
_register(
    r"^(?:set\s+)?volume\s+(?:to\s+)?(\d+)(?:\s*%)?$",
    "set_volume",
    lambda m: {"level": int(m.group(1))},
)

_register(
    r"^(?:volume\s+up|turn\s+(?:up\s+)?(?:the\s+)?volume|louder|increase\s+volume)$",
    "set_volume",
    lambda m: {"level": "+10"},
)

_register(
    r"^(?:volume\s+down|turn\s+(?:down\s+)?(?:the\s+)?volume|quieter|decrease\s+volume|lower\s+volume)$",
    "set_volume",
    lambda m: {"level": "-10"},
)

_register(
    r"^(?:mute|silence|shut\s+up)$",
    "set_volume",
    lambda m: {"level": 0},
)

_register(
    r"^unmute$",
    "set_volume",
    lambda m: {"level": 50},
)

# ──────────────────────────────────────────────
# Screenshot
# ──────────────────────────────────────────────
_register(
    r"^(?:take\s+a?\s*)?screenshot$",
    "capture_screen",
    lambda m: {},
)

_register(
    r"^(?:what(?:'s| is)\s+on\s+(?:my\s+)?screen|read\s+(?:my\s+)?screen|screen\s+read)$",
    "ocr_screen",
    lambda m: {},
)

# ──────────────────────────────────────────────
# System info
# ──────────────────────────────────────────────
_register(
    r"^(?:system\s+info|system\s+information|what(?:'s| is)\s+my\s+(?:system|pc|computer)\s+info)$",
    "get_system_info",
    lambda m: {},
)

_register(
    r"^(?:what(?:'s| is)\s+(?:the\s+)?(?:current\s+)?volume|volume\s*\?)$",
    "get_volume",
    lambda m: {},
)

# ──────────────────────────────────────────────
# Window control
# ──────────────────────────────────────────────
_register(
    r"^(?:list|show)\s+(?:all\s+)?(?:open\s+)?windows$",
    "list_windows",
    lambda m: {},
)

_register(
    r"^(?:switch\s+to|focus(?:\s+on)?|go\s+to)\s+(.+?)(?:\s+window)?$",
    "focus_window",
    lambda m: {"title": m.group(1).strip()},
)

_register(
    r"^minimize\s+(.+?)(?:\s+window)?$",
    "minimize_window",
    lambda m: {"title": m.group(1).strip()},
)

_register(
    r"^maximize\s+(.+?)(?:\s+window)?$",
    "maximize_window",
    lambda m: {"title": m.group(1).strip()},
)

# ──────────────────────────────────────────────
# Clipboard
# ──────────────────────────────────────────────
_register(
    r"^(?:what(?:'s| is)\s+(?:in\s+)?(?:my\s+)?clipboard|clipboard\s+contents?|paste\s+clipboard|read\s+clipboard)$",
    "clipboard_get",
    lambda m: {},
)

_register(
    r"^(?:copy|clipboard\s+set)\s+[\"'](.+?)[\"']$",
    "clipboard_set",
    lambda m: {"text": m.group(1)},
)

_register(
    r"^type\s+[\"'](.+?)[\"']$",
    "type_text",
    lambda m: {"text": m.group(1)},
)

# ──────────────────────────────────────────────
# Process management
# ──────────────────────────────────────────────
_register(
    r"^(?:list|show)\s+(?:running\s+)?processes$",
    "list_processes",
    lambda m: {},
)

# ──────────────────────────────────────────────
# File operations
# ──────────────────────────────────────────────
_register(
    r"^(?:list|show|ls|dir)\s+(?:files\s+in\s+)?(.+)$",
    "list_dir",
    lambda m: {"path": m.group(1).strip()},
)

# ──────────────────────────────────────────────
# System power
# ──────────────────────────────────────────────
_register(
    r"^(?:what(?:'s| is)\s+(?:the\s+)?uptime|how\s+long\s+(?:has\s+)?(?:my\s+)?(?:pc|computer)\s+been\s+(?:on|running))$",
    "get_uptime",
    lambda m: {},
)


class FastCommandResult:
    """Result of a fast-path command match."""
    def __init__(self, tool_name: str, args: dict, original_text: str):
        self.tool_name = tool_name
        self.args = args
        self.original_text = original_text

    def __repr__(self):
        return f"FastCommandResult({self.tool_name}, {self.args})"


def match_fast_command(text: str) -> Optional[FastCommandResult]:
    """
    Try to match user text against fast-path commands.
    Returns FastCommandResult if matched, None if it should go to LLM.
    """
    cleaned = text.strip()

    # Remove common prefixes like "hey jarvis", "nokton", "please", etc.
    prefixes = [
        r"^(?:hey\s+)?(?:jarvis|nokton|assistant|computer)[,.]?\s*",
        r"^(?:please|can you|could you|would you)\s+",
    ]
    for prefix_re in prefixes:
        cleaned = re.sub(prefix_re, "", cleaned, flags=re.IGNORECASE).strip()

    if not cleaned:
        return None

    for pattern, tool_name, args_builder in _FAST_COMMANDS:
        match = pattern.match(cleaned)
        if match:
            try:
                args = args_builder(match)
                return FastCommandResult(tool_name, args, text)
            except Exception:
                continue

    return None
