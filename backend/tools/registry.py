import asyncio
import atexit
import concurrent.futures
import logging
import time
from functools import wraps
from typing import Any, Callable

from .schema import func_to_json_schema
from .permission import get_permission_level, PermissionLevel
from ..providers.base import ToolDef
from ..config import ToolsConfig

logger = logging.getLogger(__name__)


_registry: dict[str, ToolDef] = {}
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
_audit_logger = None


def set_audit_logger(audit):
    global _audit_logger
    _audit_logger = audit


def _shutdown_thread_pool():
    try:
        _thread_pool.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass


atexit.register(_shutdown_thread_pool)


def tool(
    name: str | None = None,
    category: str = "general",
    requires_confirm: bool = False,
    timeout: int = 30,
    check_fn: Callable[[], bool] | None = None,
):
    def decorator(func):
        tool_id = name or func.__name__
        t = ToolDef(
            id=tool_id,
            description=func.__doc__ or "",
            category=category,
            handler=func,
            parameters=func_to_json_schema(func),
            requires_confirm=requires_confirm,
            timeout=timeout,
            check_fn=check_fn,
        )
        _registry[tool_id] = t

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool_def: ToolDef):
        self._tools[tool_def.id] = tool_def

    def get(self, tool_id: str) -> ToolDef | None:
        return self._tools.get(tool_id) or _registry.get(tool_id)

    def list_tools(self, tools_config: ToolsConfig | None = None) -> list[ToolDef]:
        result = []
        for t in {**_registry, **self._tools}.values():
            if t.check_fn is not None and not t.check_fn():
                continue
            if tools_config:
                perm = get_permission_level(t.category, t.requires_confirm, tools_config)
                if perm == PermissionLevel.DENY:
                    continue
            result.append(t)
        return result

    def get_tool_schemas(self, tools_config: ToolsConfig | None = None) -> list[dict]:
        return [t.to_schema() for t in self.list_tools(tools_config)]

    async def execute(
        self,
        tool_id: str,
        args: dict[str, Any],
        tools_config: ToolsConfig | None = None,
    ) -> dict[str, Any]:
        tool_def = self.get(tool_id)
        if not tool_def:
            return {"success": False, "error": f"Unknown tool: {tool_id}"}

        if tools_config:
            perm = get_permission_level(tool_def.category, tool_def.requires_confirm, tools_config)
            if perm == PermissionLevel.DENY:
                return {"success": False, "error": "Tool is disabled by policy", "permission": "deny"}

        timeout = tool_def.timeout or (tools_config.timeout if tools_config else 30)
        call_id = f"call_{int(time.time() * 1000)}_{id(args)}"
        start = time.time()
        approved = True
        result: dict[str, Any] = {"success": False, "error": "unreachable"}
        try:
            if asyncio.iscoroutinefunction(tool_def.handler):
                value = await asyncio.wait_for(
                    tool_def.handler(**args),
                    timeout=timeout,
                )
            else:
                loop = asyncio.get_event_loop()
                value = await asyncio.wait_for(
                    loop.run_in_executor(_thread_pool, lambda: tool_def.handler(**args)),
                    timeout=timeout,
                )
            output = "" if value is None else str(value)
            result = {"success": True, "output": output}
            return result
        except asyncio.TimeoutError:
            result = {"success": False, "error": f"Tool '{tool_id}' timed out after {timeout}s"}
            return result
        except Exception as e:
            result = {"success": False, "error": f"Tool '{tool_id}' error: {str(e)}"}
            return result
        finally:
            if _audit_logger is not None:
                try:
                    _audit_logger.log_tool_call(
                        call_id=call_id,
                        tool=tool_id,
                        args=args,
                        approved=approved,
                        result=result,
                        duration=time.time() - start,
                    )
                except Exception:
                    pass

    def requires_confirmation(self, tool_id: str) -> bool:
        tool_def = self.get(tool_id)
        return tool_def.requires_confirm if tool_def else False


tool_registry = ToolRegistry()
