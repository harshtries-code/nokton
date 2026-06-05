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

    def is_speech(self, audio_frame: np.ndarray) -> bool:
        if not self._loaded:
            return self._energy_vad(audio_frame)
        try:
            import silero_vad
            return silero_vad.get_speech_timestamps(
                audio_frame, self._model,
                threshold=self._threshold,
                return_seconds=True,
            )
        except Exception:
            return self._energy_vad(audio_frame)

    def _energy_vad(self, audio: np.ndarray) -> bool:
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > self._threshold

    def detect_speech_segment(self, audio: np.ndarray) -> tuple[int, int]:
        if not self._loaded:
            return (0, len(audio))
        try:
            import silero_vad
            timestamps = silero_vad.get_speech_timestamps(
                audio, self._model,
                threshold=self._threshold,
                return_seconds=True,
            )
            if timestamps:
                start = int(timestamps[0]["start"] * self._sample_rate)
                end = int(timestamps[-1]["end"] * self._sample_rate)
                return (start, min(end + self._silence_samples, len(audio)))
        except Exception:
            pass
        return (0, len(audio))
