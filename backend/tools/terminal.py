import subprocess
import asyncio
from .registry import tool


@tool(category="terminal", requires_confirm=True)
def run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command and return its output.
    Args:
        command: Command to execute (uses cmd.exe on Windows).
        timeout: Maximum execution time in seconds. Defaults to 30.
    Returns:
        Command stdout and stderr output.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Command error: {e}"


@tool(category="terminal", requires_confirm=True)
def run_powershell(command: str, timeout: int = 30) -> str:
    """Run a PowerShell command and return its output.
    Args:
        command: PowerShell command to execute.
        timeout: Maximum execution time in seconds. Defaults to 30.
    Returns:
        Command stdout and stderr output.
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"PowerShell command timed out after {timeout}s"
    except Exception as e:
        return f"PowerShell error: {e}"
