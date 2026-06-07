import asyncio
import threading
import time
from typing import Callable, Optional

import numpy as np

from .wake_word import WakeWordDetector
from .vad import VoiceActivityDetector
from .stt import SpeechToText
from .tts import TextToSpeech
from ..config import VoiceConfig


class VoicePipeline:
    def __init__(self, config: VoiceConfig):
        self._config = config
        self._wake = WakeWordDetector(
            sensitivity=config.wake_word.sensitivity,
            model=config.wake_word.model,
        )
        self._vad = VoiceActivityDetector(
            threshold=config.vad.threshold,
            silence_duration_ms=config.vad.silence_duration_ms,
        )
        self._stt = SpeechToText(config.stt)
        self._tts = TextToSpeech(config.tts)

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._capturing = False
        self._capture_buffer: list[np.ndarray] = []
        self._silence_chunks = 0
        self._max_capture_s = 30
        self._silence_threshold_chunks = int(
            config.vad.silence_duration_ms / 80
        ) or 10

        self._on_wake: Optional[Callable[[], None]] = None
        self._on_transcript: Optional[Callable[[str], None]] = None
        self._on_state: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    def set_callbacks(
        self,
        on_wake: Optional[Callable[[], None]] = None,
        on_transcript: Optional[Callable[[str], None]] = None,
        on_state: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._on_wake = on_wake
        self._on_transcript = on_transcript
        self._on_state = on_state
        self._on_error = on_error

    def bind_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._tts.bind_loop(loop)

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        self._loop = self._loop or asyncio.get_event_loop()
        self._tts.bind_loop(self._loop)
        try:
            self._stt.load()
        except Exception as e:
            self._emit_error(f"stt_load_failed: {e}")
        try:
            self._vad.load()
        except Exception:
            pass
        self._wake.set_callback(self._handle_wake)
        self._wake.start()
        self._running = True
        self._emit_state("listening")
        return True

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._capturing = False
        self._capture_buffer.clear()
        try:
            self._wake.stop()
        except Exception:
            pass
        try:
            self._tts.stop()
        except Exception:
            pass
        self._emit_state("idle")

    def push_audio(self, audio: np.ndarray):
        if not self._running or not self._capturing:
            return
        if audio is None or len(audio) == 0:
            return
        self._capture_buffer.append(audio)
        max_chunks = int(self._max_capture_s * 16000 / 1280)
        if len(self._capture_buffer) >= max_chunks:
            self._finalize_capture()
            return
        if self._vad.is_speech(audio):
            self._silence_chunks = 0
        else:
            self._silence_chunks += 1
            if self._silence_chunks >= self._silence_threshold_chunks:
                self._finalize_capture()

    def speak(self, text: str):
        if not text:
            return
        self._tts.speak(text)

    def stop_speaking(self):
        self._tts.stop()

    def _handle_wake(self, _payload: dict):
        if self._capturing:
            try:
                self._tts.stop()
            except Exception:
                pass
            if self._on_state:
                try:
                    self._on_state("interrupted")
                except Exception:
                    pass
        self._capturing = True
        self._capture_buffer.clear()
        self._silence_chunks = 0
        self._emit_state("listening")
        if self._on_wake:
            try:
                self._on_wake()
            except Exception as e:
                self._emit_error(f"on_wake_failed: {e}")

    def _finalize_capture(self):
        if not self._capturing:
            return
        self._capturing = False
        if not self._capture_buffer:
            self._emit_state("listening")
            return
        audio = np.concatenate(self._capture_buffer)
        self._capture_buffer.clear()
        self._silence_chunks = 0
        self._emit_state("thinking")
        threading.Thread(
            target=self._transcribe_worker, args=(audio,), daemon=True,
        ).start()

    def _transcribe_worker(self, audio: np.ndarray):
        try:
            text = self._stt.transcribe(audio, sample_rate=16000)
        except Exception as e:
            self._emit_error(f"stt_failed: {e}")
            text = ""
        if not text or not text.strip():
            self._emit_state("listening")
            return
        if self._on_transcript and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._async_invoke(self._on_transcript, text), self._loop,
                )
            except Exception:
                pass

    async def _async_invoke(self, cb, *args):
        try:
            cb(*args)
        except Exception as e:
            self._emit_error(f"callback_failed: {e}")

    def _emit_state(self, state: str):
        if not self._on_state:
            return
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._async_invoke(self._on_state, state), self._loop,
                )
                return
            except Exception:
                pass
        try:
            self._on_state(state)
        except Exception:
            pass

    def _emit_error(self, msg: str):
        if not self._on_error:
            return
        try:
            self._on_error(msg)
        except Exception:
            pass
