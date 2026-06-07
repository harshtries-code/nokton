import numpy as np
from ..config import STTConfig


def _to_float32(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.float32:
        return audio
    if audio.dtype == np.int16:
        return audio.astype(np.float32) / 32768.0
    if audio.dtype == np.int32:
        return audio.astype(np.float32) / 2147483648.0
    if audio.dtype == np.uint8:
        return (audio.astype(np.float32) - 128.0) / 128.0
    return audio.astype(np.float32)


class SpeechToText:
    def __init__(self, config: STTConfig | None = None):
        self._config = config or STTConfig()
        self._model = None
        self._loaded = False

    def load(self) -> bool:
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
        return self._loaded

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self._loaded:
            try:
                self.load()
            except Exception:
                return ""

        if audio is None or len(audio) == 0:
            return ""

        if self._model is not None:
            try:
                audio_f = _to_float32(audio)
                segments, _ = self._model.transcribe(
                    audio_f, beam_size=1, language="en",
                )
                return " ".join(seg.text.strip() for seg in segments if seg.text)
            except Exception:
                pass

        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            if audio.dtype != np.int16:
                audio = (audio * 32768.0).astype(np.int16)
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

        if self._model is not None:
            try:
                segments, _ = self._model.transcribe(
                    audio_path, beam_size=1, language="en",
                )
                return " ".join(seg.text.strip() for seg in segments if seg.text)
            except Exception:
                pass
        return ""
