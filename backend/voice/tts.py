import asyncio
import threading
import queue
from ..config import TTSConfig


class TextToSpeech:
    def __init__(self, config: TTSConfig | None = None):
        self._config = config or TTSConfig()
        self._speaking = False
        self._stop_event = threading.Event()
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._speaking = False
        with self._queue.mutex:
            self._queue.queue.clear()

    def speak(self, text: str):
        self._queue.put(text)

    def _run(self):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._speak_loop())
        except Exception:
            pass

    async def _speak_loop(self):
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                break

            self._speaking = True
            await self._speak_text(text)
            self._speaking = False

    async def _speak_text(self, text: str):
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, self._config.voice, rate=self._config.rate)
            await communicate.say()
        except ImportError:
            self._fallback_tts(text)
        except Exception:
            self._fallback_tts(text)

    def _fallback_tts(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass
