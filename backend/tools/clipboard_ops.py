from .registry import tool


@tool(category="clipboard_read")
def clipboard_get() -> str:
    """Get the current clipboard contents.
    Returns:
        Current text in the clipboard.
    """
    try:
        import pyperclip
        text = pyperclip.paste()
        return f"Clipboard: {text[:500]}" if text else "Clipboard is empty"
    except ImportError:
        return "Clipboard access requires pyperclip package"
    except Exception as e:
        return f"Clipboard error: {e}"


@tool(category="clipboard_write")
def clipboard_set(text: str) -> str:
    """Set clipboard contents with the given text.
    Args:
        text: Text to copy to clipboard.
    Returns:
        Confirmation message.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return f"Copied {len(text)} characters to clipboard"
    except ImportError:
        return "Clipboard access requires pyperclip package"
    except Exception as e:
        return f"Clipboard error: {e}"


@tool(category="clipboard_write")
def type_text(text: str, interval: float = 0.05) -> str:
    """Type text into the currently focused application.
    Args:
        text: Text to type.
        interval: Delay between keystrokes in seconds. Defaults to 0.05.
    Returns:
        Confirmation message.
    """
    try:
        import pyautogui
        pyautogui.write(text, interval=interval)
        return f"Typed {len(text)} characters"
    except ImportError:
        return "Typing requires pyautogui package"
    except Exception as e:
        return f"Typing error: {e}"
