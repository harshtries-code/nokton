from enum import Enum
from ..config import ToolsConfig


class PermissionLevel(Enum):
    AUTO = "auto"
    ASK = "ask"
    DENY = "deny"


CATEGORY_PERMISSION_MAP: dict[str, str] = {
    "file_read": "safe",
    "file": "safe",
    "file_write": "ask",
    "app_control": "ask",
    "system_read": "safe",
    "system_write": "ask",
    "system": "safe",
    "web": "safe",
    "clipboard_read": "safe",
    "clipboard_write": "safe",
    "clipboard": "safe",
    "screenshot": "ask",
    "terminal": "ask",
    "media": "ask",
    "general": "safe",
}


def get_permission_level(
    category: str,
    requires_confirm: bool,
    tools_config: ToolsConfig,
) -> PermissionLevel:
    if category in tools_config.deny_categories:
        return PermissionLevel.DENY

    if requires_confirm:
        return PermissionLevel.ASK

    if category in tools_config.ask_categories:
        return PermissionLevel.ASK

    if category in tools_config.safe_categories:
        return PermissionLevel.AUTO

    default = CATEGORY_PERMISSION_MAP.get(category, "ask")
    if default == "safe":
        return PermissionLevel.AUTO
    return PermissionLevel.ASK
