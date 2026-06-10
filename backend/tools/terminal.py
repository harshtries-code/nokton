import subprocess
import shlex
from .registry import tool


ALLOWED_EXECUTABLES = {
    "ipconfig", "dir", "echo", "type", "where", "systeminfo", "tasklist",
    "ping", "tracert", "nslookup", "hostname", "whoami", "ver", "date", "time",
    "cd", "cls", "copy", "move", "ren", "del", "find", "findstr", "sort",
    "fc", "comp", "xcopy", "robocopy", "attrib", "tree", "more",
}

BANNED_POWERSHELL_TOKENS = {
    "Invoke-Expression", "iex", "IEX",
    "Invoke-WebRequest", "iwr", "IWR",
    "Invoke-RestMethod", "irm", "IRM",
    "Start-BitsTransfer",
    "Start-Process", "-encodedcommand", "-enc", "-EncodedCommand",
    "Remove-Item", "rm", "del", "ri", "rmdir",
    "Set-ExecutionPolicy", "New-Object", "Net.WebClient",
    "[System.Net.WebClient]", "DownloadString", "DownloadFile",
}


@tool(category="terminal", requires_confirm=True)
def run_command(exe: str, args: list[str] | None = None, timeout: int = 30) -> str:
    """Run an allowlisted command and return its output.
    Args:
        exe: Executable name (must be in the allowlist).
        args: Optional list of arguments.
        timeout: Maximum execution time in seconds. Defaults to 30.
    Returns:
        Command stdout and stderr output.
    """
    if not exe or exe.lower() not in ALLOWED_EXECUTABLES:
        return f"Error: '{exe}' is not in the allowlist of permitted commands"

    cmd = [exe] + (args or [])
    try:
        result = subprocess.run(
            cmd,
            shell=False,
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
    except FileNotFoundError:
        return f"Error: executable '{exe}' not found on PATH"
    except Exception as e:
        return f"Command error: {e}"


@tool(category="terminal", requires_confirm=True)
def run_powershell(command: str, timeout: int = 30) -> str:
    """Run a sanitized PowerShell command. Blocks dangerous cmdlets.
    Args:
        command: PowerShell command to execute.
        timeout: Maximum execution time in seconds. Defaults to 30.
    Returns:
        Command stdout and stderr output.
    """
    if not command:
        return "Error: empty command"

    tokens = shlex.split(command, posix=False)
    for token in tokens:
        clean = token.strip("'\"").lower()
        if any(banned.lower() in clean for banned in BANNED_POWERSHELL_TOKENS):
            return f"Error: blocked token '{token}' — dangerous PowerShell command not allowed"

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
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
