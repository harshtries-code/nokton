# Import all tool modules to register tools via @tool decorator
from . import file_ops
from . import app_control
from . import system_info
from . import web_ops
from . import clipboard_ops
from . import screenshot
from . import window_control
from . import terminal

from .registry import tool_registry, tool
