import subprocess
import psutil
import platform
from .registry import tool
from datetime import datetime


@tool(category="system_read")
def get_system_info() -> str:
    """Get comprehensive system information: CPU, RAM, disk, battery, network.
    Returns:
        Formatted system info string.
    """
    cpu = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = datetime.fromtimestamp(psutil.boot_time())

    lines = [
        f"OS: {platform.system()} {platform.release()}",
        f"Hostname: {platform.node()}",
        f"CPU: {cpu}% used ({cpu_count} cores)",
        f"RAM: {ram.percent}% used ({_format_bytes(ram.used)} / {_format_bytes(ram.total)})",
        f"Disk: {disk.percent}% used ({_format_bytes(disk.used)} / {_format_bytes(disk.total)})",
        f"Uptime: {_format_duration((datetime.now() - boot_time).total_seconds())}",
    ]

    battery = psutil.sensors_battery()
    if battery:
        status = "charging" if battery.power_plugged else "discharging"
        lines.append(f"Battery: {battery.percent}% ({status})")

    return "\n".join(lines)


@tool(category="system_read")
def get_volume() -> str:
    """Get current system volume level (0-100).
    Returns:
        Current volume level as a string.
    """
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = round(volume.GetMasterVolumeLevelScalar() * 100)
        mute = volume.GetMute()
        status = " (muted)" if mute else ""
        return f"Volume: {current}%{status}"
    except ImportError:
        return "Volume control requires pycaw package"
    except Exception as e:
        return f"Error getting volume: {e}"


@tool(category="system_write")
def set_volume(level: int) -> str:
    """Set system volume level (0-100).
    Args:
        level: Volume level from 0 to 100.
    Returns:
        Confirmation message.
    """
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        level = max(0, min(100, int(level)))
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return f"Volume set to {level}%"
    except ImportError:
        return "Volume control requires pycaw package"
    except Exception as e:
        return f"Error setting volume: {e}"


@tool(category="system_read")
def get_uptime() -> str:
    """Get system uptime.
    Returns:
        Formatted uptime string.
    """
    boot = datetime.fromtimestamp(psutil.boot_time())
    uptime_secs = (datetime.now() - boot).total_seconds()
    return f"Uptime: {_format_duration(uptime_secs)} (since {boot.strftime('%Y-%m-%d %H:%M:%S')})"


@tool(category="system_write", requires_confirm=True)
def shutdown(delay_seconds: int = 60) -> str:
    """Shut down the computer after a delay.
    Args:
        delay_seconds: Delay in seconds before shutdown. Defaults to 60.
    Returns:
        Confirmation message.
    """
    try:
        delay = max(0, min(int(delay_seconds), 3600))
        subprocess.run(["shutdown", "/s", "/t", str(delay)], check=True)
        return f"Shutdown scheduled in {delay} seconds"
    except Exception as e:
        return f"Error initiating shutdown: {e}"


@tool(category="system_write", requires_confirm=True)
def restart(delay_seconds: int = 60) -> str:
    """Restart the computer after a delay.
    Args:
        delay_seconds: Delay in seconds before restart. Defaults to 60.
    Returns:
        Confirmation message.
    """
    try:
        delay = max(0, min(int(delay_seconds), 3600))
        subprocess.run(["shutdown", "/r", "/t", str(delay)], check=True)
        return f"Restart scheduled in {delay} seconds"
    except Exception as e:
        return f"Error initiating restart: {e}"


def _format_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


def _format_duration(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)
