import time
import threading
import queue
from enum import Enum
from typing import Callable, Optional

import numpy as np


class WakeWordState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"


_DEFAULT_MODEL = "alexa"

_VALID_MODELS = {
    "alexa", "hey_mycroft", "timer", "weather",
    "jarvis", "computer", "hey_siri", "ok_google",
}


class WakeWordDetector:
    def __init__(
        self,
        sensitivity: float = 0.7,
        model: str = _DEFAULT_MODEL,
        cooldown_s: float = 2.0,
        min_duration_s: float = 0.2,
    ):
        self._sensitivity = sensitivity
        self._model_name = model if model in _VALID_MODELS else _DEFAULT_MODEL
        self._cooldown_s = cooldown_s
        self._min_duration_s = min_duration_s
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._callback: Optional[Callable[[dict], None]] = None
        self._state = WakeWordState.IDLE
        self._engine = None
        self._loaded = False
        self._last_trigger_time: float = 0.0
        self._above_threshold_since: Optional[float] = None

    @property
    def state(self) -> WakeWordState:
        return self._state

    @property
    def model_name(self) -> str:
        return self._model_name

    def load(self) -> bool:
        try:
            from openwakeword.model import Model
            self._engine = Model(
                wakeword_models=[self._model_name],
                inference_framework="onnx",
            )
            self._loaded = True
        except ImportError:
            self._loaded = False
        except Exception:
            self._loaded = False
        return self._loaded

    def set_callback(self, callback: Callable[[dict], None]):
        self._callback = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="wake-word")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._state = WakeWordState.IDLE

    def feed_audio(self, audio: np.ndarray):
        try:
            self._audio_queue.put_nowait(audio)
        except queue.Full:
            pass

    def _run(self):
        import pyaudio

        CHUNK = 1280
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        if not self._loaded and not self.load():
            self._listen_with_energy(CHUNK, FORMAT, CHANNELS, RATE)
            return

        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=FORMAT, channels=CHANNELS, rate=RATE,
                input=True, frames_per_buffer=CHUNK,
            )
            try:
                stream.start_stream()
                self._state = WakeWordState.IDLE
                while self._running:
                    try:
                        raw = stream.read(CHUNK, exception_on_overflow=False)
                    except Exception:
                        continue
                    data = np.frombuffer(raw, dtype=np.int16)
                    audio_float = data.astype(np.float32) / 32768.0

                    try:
                        prediction = self._engine.predict(audio_float)
                    except Exception:
                        continue
                    score = float(prediction.get(self._model_name, 0.0) or 0.0)
                    self._maybe_trigger(score)
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        finally:
            try:
                p.terminate()
            except Exception:
                pass

    def _listen_with_energy(self, chunk, fmt, channels, rate):
        import pyaudio

        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=fmt, channels=channels, rate=rate,
                input=True, frames_per_buffer=chunk,
            )
            try:
                stream.start_stream()
                self._state = WakeWordState.IDLE
                while self._running:
                    try:
                        raw = stream.read(chunk, exception_on_overflow=False)
                    except Exception:
                        continue
                    data = np.frombuffer(raw, dtype=np.int16)
                    energy = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
                    norm = min(1.0, energy / 5000.0)
                    self._maybe_trigger(norm)
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        finally:
            try:
                p.terminate()
            except Exception:
                pass

    def _maybe_trigger(self, score: float):
        now = time.monotonic()
        if score > self._sensitivity:
            if self._above_threshold_since is None:
                self._above_threshold_since = now
            elif (now - self._above_threshold_since) >= self._min_duration_s:
                if (now - self._last_trigger_time) >= self._cooldown_s:
                    self._last_trigger_time = now
                    self._above_threshold_since = None
                    self._state = WakeWordState.LISTENING
                    if self._callback:
                        try:
                            self._callback({"event": "wake", "score": float(score)})
                        except Exception:
                            pass
        else:
            self._above_threshold_since = None
            if self._state == WakeWordState.LISTENING:
                self._state = WakeWordState.IDLE
