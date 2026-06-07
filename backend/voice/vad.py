import numpy as np


class VoiceActivityDetector:
    def __init__(self, threshold: float = 0.5, silence_duration_ms: int = 800, sample_rate: int = 16000):
        self._threshold = threshold
        self._silence_samples = int(sample_rate * silence_duration_ms / 1000)
        self._sample_rate = sample_rate
        self._model = None
        self._loaded = False

    def load(self):
        try:
            import silero_vad
            self._model = silero_vad.load_silero_vad()
            self._loaded = True
        except ImportError:
            self._loaded = False
        except Exception:
            self._loaded = False

    def is_speech(self, audio_frame: np.ndarray) -> bool:
        if not self._loaded:
            return self._energy_vad(audio_frame)
        try:
            import silero_vad
            return bool(silero_vad.get_speech_timestamps(
                audio_frame, self._model,
                threshold=self._threshold,
            ))
        except Exception:
            return self._energy_vad(audio_frame)

    def get_speech_timestamps(self, audio: np.ndarray, return_seconds: bool = True) -> list[dict]:
        if not self._loaded:
            return self._energy_timestamps(audio)
        try:
            import silero_vad
            return silero_vad.get_speech_timestamps(
                audio, self._model,
                threshold=self._threshold,
                return_seconds=return_seconds,
            )
        except Exception:
            return self._energy_timestamps(audio)

    def detect_speech_segment(self, audio: np.ndarray) -> tuple[int, int]:
        timestamps = self.get_speech_timestamps(audio, return_seconds=False)
        if timestamps:
            start = int(timestamps[0]["start"])
            end = int(timestamps[-1]["end"])
            return (start, min(end + self._silence_samples, len(audio)))
        return (0, len(audio))

    def _energy_vad(self, audio: np.ndarray) -> bool:
        energy = self._energy(audio)
        return energy > self._threshold

    def _energy_timestamps(self, audio: np.ndarray) -> list[dict]:
        energy = self._energy(audio)
        if energy > self._threshold:
            return [{"start": 0, "end": len(audio)}]
        return []

    def _energy(self, audio: np.ndarray) -> float:
        a = audio.astype(np.float32) if audio.dtype != np.float32 else audio
        return float(np.sqrt(np.mean(a ** 2)))
