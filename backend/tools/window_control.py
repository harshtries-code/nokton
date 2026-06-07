from .registry import tool


@tool(category="system_read")
def list_windows(filter: str = "") -> str:
    """List open windows, optionally filtered by title.
    Args:
        filter: Optional text to filter window titles by.
    Returns:
        List of window titles.
    """
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(filter) if filter else gw.getAllWindows()
        titles = sorted(set(w.title for w in windows if w.title.strip()))
        return "\n".join(titles) if titles else "No open windows found"
    except ImportError:
        return "Window listing requires pygetwindow package"
    except Exception as e:
        return f"Window list error: {e}"


@tool(category="system_write")
def focus_window(title: str) -> str:
    """Focus a window by title substring match.
    Args:
        title: Window title text to search for and focus.
    Returns:
        Confirmation message.
    """
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return f"No window found matching '{title}'"
        windows[0].activate()
        return f"Focused: {windows[0].title}"
    except ImportError:
        return "Window focus requires pygetwindow package"
    except Exception as e:
        return f"Window focus error: {e}"


@tool(category="system_write")
def minimize_window(title: str) -> str:
    """Minimize a window by title substring match.
    Args:
        title: Window title text to search for.
    Returns:
        Confirmation message.
    """
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return f"No window found matching '{title}'"
        windows[0].minimize()
        return f"Minimized: {windows[0].title}"
    except ImportError:
        return "Window minimize requires pygetwindow package"
    except Exception as e:
        return f"Window minimize error: {e}"


@tool(category="system_write")
def maximize_window(title: str) -> str:
    """Maximize a window by title substring match.
    Args:
        title: Window title text to search for.
    Returns:
        Confirmation message.
    """
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return f"No window found matching '{title}'"
        windows[0].maximize()
        return f"Maximized: {windows[0].title}"
    except ImportError:
        return "Window maximize requires pygetwindow package"
    except Exception as e:
        return f"Window maximize error: {e}"
