import asyncio
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from ..config import TTSConfig


class TextToSpeech:
    def __init__(self, config: TTSConfig | None = None):
        self._config = config or TTSConfig()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._speaking = False
        self._stop_event = threading.Event()
        self._speak_lock = threading.Lock()
        self._tempdir = Path(tempfile.gettempdir()) / "nokton_tts"
        self._tempdir.mkdir(parents=True, exist_ok=True)

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def bind_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        if self._loop is None or not self._loop.is_running():
            self._speak_sync(text)
            return
        try:
            asyncio.run_coroutine_threadsafe(self._speak_async(text), self._loop)
        except Exception:
            self._speak_sync(text)

    def stop(self) -> None:
        self._stop_event.set()
        self._speaking = False

    def _speak_sync(self, text: str):
        with self._speak_lock:
            try:
                out_path = self._tempdir / f"nokton_tts_{threading.get_ident()}.mp3"
                asyncio.run(self._synthesize_to_file(text, str(out_path)))
                if out_path.exists() and out_path.stat().st_size > 0:
                    self._play_file(str(out_path))
            except Exception:
                pass

    async def _speak_async(self, text: str):
        self._stop_event.clear()
        self._speaking = True
        try:
            out_path = self._tempdir / f"nokton_tts_{id(self)}.mp3"
            await self._synthesize_to_file(text, str(out_path))
            if out_path.exists() and out_path.stat().st_size > 0:
                await asyncio.to_thread(self._play_file, str(out_path))
        except Exception:
            pass
        finally:
            self._speaking = False

    async def _synthesize_to_file(self, text: str, out_path: str) -> None:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text, self._config.voice, rate=self._config.rate,
            )
            await communicate.save(out_path)
        except ImportError:
            self._fallback_save(text, out_path)
        except Exception:
            self._fallback_save(text, out_path)

    def _fallback_save(self, text: str, out_path: str) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, out_path.replace(".mp3", ".wav"))
            engine.runAndWait()
        except Exception:
            try:
                with open(out_path, "wb") as f:
                    f.write(b"")
            except Exception:
                pass

    def _play_file(self, path: str) -> None:
        if self._stop_event.is_set():
            return
        try:
            from playsound import playsound
            playsound(path)
        except ImportError:
            self._play_native(path)
        except Exception:
            self._play_native(path)

    def _play_native(self, path: str) -> None:
        if self._stop_event.is_set():
            return
        try:
            if os.name == "nt":
                os.startfile(path)
            elif os.name == "posix":
                import subprocess
                subprocess.Popen(
                    ["xdg-open", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass
