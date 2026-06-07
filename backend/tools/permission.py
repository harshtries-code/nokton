import logging
from enum import Enum
from ..config import ToolsConfig

logger = logging.getLogger(__name__)


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

    if category in tools_config.safe_categories:
        return PermissionLevel.AUTO

    if category in tools_config.ask_categories:
        return PermissionLevel.ASK

    if category not in CATEGORY_PERMISSION_MAP:
        logger.warning(f"Unknown tool category '{category}', defaulting to AUTO")

    if requires_confirm:
        return PermissionLevel.ASK

    default = CATEGORY_PERMISSION_MAP.get(category, "safe")
    if default == "safe":
        return PermissionLevel.AUTO
    return PermissionLevel.ASK
