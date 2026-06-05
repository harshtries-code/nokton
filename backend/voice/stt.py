import numpy as np
from ..config import STTConfig


class SpeechToText:
    def __init__(self, config: STTConfig | None = None):
        self._config = config or STTConfig()
        self._model = None
        self._loaded = False

    def load(self):
        model_size = self._config.model_size
        device = self._config.device

        try:
            from faster_whisper import WhisperModel
            compute_type = "int8" if device == "cpu" else "float16"
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
            self._loaded = True
        except ImportError:
            self._loaded = False
        except Exception:
            self._loaded = False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self._loaded:
            try:
                self.load()
            except Exception:
                return ""

        if self._model:
            try:
                segments, _ = self._model.transcribe(audio, beam_size=1, language="en")
                return " ".join(seg.text for seg in segments)
            except Exception:
                pass

        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            audio_data = sr.AudioData(audio.tobytes(), sample_rate, 2)
            return recognizer.recognize_google(audio_data)
        except Exception:
            return ""

    def transcribe_file(self, audio_path: str) -> str:
        if not self._loaded:
            try:
                self.load()
            except Exception:
                return ""

        if self._model:
            try:
                segments, _ = self._model.transcribe(audio_path, beam_size=1, language="en")
                return " ".join(seg.text for seg in segments)
            except Exception:
                pass
        return ""
