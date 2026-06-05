import numpy as np
import threading
import queue
from enum import Enum


class WakeWordState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"


class WakeWordDetector:
    def __init__(self, sensitivity: float = 0.7, model: str = "hey_nokton"):
        self._sensitivity = sensitivity
        self._model_name = model
        self._running = False
        self._thread: threading.Thread | None = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._callback = None
        self._state = WakeWordState.IDLE
        self._engine = None
        self._loaded = False

    @property
    def state(self) -> WakeWordState:
        return self._state

    def load(self):
        try:
            import openwakeword
            self._engine = openwakeword.Model(
                wakeword_models=[self._model_name],
                inference_framework="onnx",
            )
            self._loaded = True
        except ImportError:
            self._loaded = False
        except Exception:
            self._loaded = False

    def set_callback(self, callback):
        self._callback = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def feed_audio(self, audio: np.ndarray):
        self._audio_queue.put(audio)

    def _run(self):
        import pyaudio

        CHUNK = 1280
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        if not self._loaded:
            self._listen_with_energy(CHUNK, FORMAT, CHANNELS, RATE)
            return

        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)
            stream.start_stream()

            while self._running:
                data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
                audio_float = data.astype(np.float32) / 32768.0

                prediction = self._engine.predict(audio_float)
                score = prediction.get(self._model_name, 0)

                if score > self._sensitivity:
                    self._state = WakeWordState.LISTENING
                    if self._callback:
                        self._callback({"event": "wake", "score": float(score)})
                else:
                    self._state = WakeWordState.IDLE

            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception:
            self._listen_with_energy(CHUNK, FORMAT, CHANNELS, RATE)

    def _listen_with_energy(self, chunk, fmt, channels, rate):
        import pyaudio
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=fmt, channels=channels, rate=rate,
                            input=True, frames_per_buffer=chunk)
            stream.start_stream()

            while self._running:
                data = np.frombuffer(stream.read(chunk, exception_on_overflow=False), dtype=np.int16)
                energy = np.sqrt(np.mean(data.astype(np.float32) ** 2))
                if energy > 0.1:
                    self._state = WakeWordState.LISTENING
                    if self._callback:
                        self._callback({"event": "wake", "score": float(energy)})
                else:
                    self._state = WakeWordState.IDLE

            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception:
            pass
