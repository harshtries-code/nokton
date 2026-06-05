import subprocess
import psutil
from .registry import tool


@tool(category="app_control")
def launch_app(name_or_path: str) -> str:
    """Launch an application by name (searches PATH) or full path.
    Args:
        name_or_path: Application name (e.g., 'notepad') or full path to executable.
    Returns:
        Confirmation message.
    """
    try:
        subprocess.Popen(name_or_path, shell=True)
        return f"Launched: {name_or_path}"
    except Exception as e:
        return f"Error launching '{name_or_path}': {e}"


@tool(category="app_control", requires_confirm=True)
def close_app(name: str) -> str:
    """Close an application gracefully.
    Args:
        name: Application name or process name to close.
    Returns:
        Confirmation message.
    """
    closed = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if name.lower() in proc.info["name"].lower():
                proc.terminate()
                closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if closed > 0:
        return f"Closed {closed} instance(s) of '{name}'"
    return f"No running process found matching '{name}'"


@tool(category="app_control")
def list_processes(filter: str = "") -> str:
    """List running processes, optionally filtered by name.
    Args:
        filter: Optional process name filter.
    Returns:
        List of matching processes with PID and name.
    """
    results = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            name = proc.info["name"]
            if filter and filter.lower() not in name.lower():
                continue
            results.append(f"PID {proc.info['pid']}: {name} ({proc.info['memory_percent']:.1f}% mem)")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return "\n".join(results) if results else "No matching processes found"


@tool(category="app_control", requires_confirm=True)
def kill_process(pid: int | str) -> str:
    """Force-kill a process by PID.
    Args:
        pid: Process ID number.
    Returns:
        Confirmation message.
    """
    try:
        pid = int(pid)
        proc = psutil.Process(pid)
        name = proc.name()
        proc.kill()
        return f"Killed process '{name}' (PID {pid})"
    except psutil.NoSuchProcess:
        return f"Error: No process with PID {pid}"
    except psutil.AccessDenied:
        return f"Error: Access denied to kill PID {pid}"
    except ValueError:
        return f"Error: Invalid PID '{pid}'"
