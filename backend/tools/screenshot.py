import os
import tempfile
from datetime import datetime
from .registry import tool


@tool(category="screenshot", requires_confirm=True)
def capture_screen(path: str = "") -> str:
    """Capture a screenshot of the entire screen or active window.
    Args:
        path: Optional file path to save the screenshot. If empty, saves to a temp file with timestamp.
    Returns:
        Path to the saved screenshot image.
    """
    try:
        from PIL import Image
        import mss

        if not path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(tempfile.gettempdir(), f"nokton_screenshot_{ts}.png")

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            img.save(path)

        return f"Screenshot saved to: {path} (resolution: {img.width}x{img.height})"
    except ImportError:
        return "Screenshot requires mss and Pillow packages"
    except Exception as e:
        return f"Screenshot error: {e}"


@tool(category="screenshot", requires_confirm=True)
def ocr_screen() -> str:
    """Extract text from the screen using OCR.
    Returns:
        Text extracted from the screen.
    """
    try:
        import pytesseract
        from PIL import Image
        import mss

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(tempfile.gettempdir(), f"nokton_ocr_{ts}.png")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            img.save(path)

        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "No text found on screen"
    except ImportError:
        return "OCR requires pytesseract and mss packages"
    except Exception as e:
        return f"OCR error: {e}"
