import sys
import numpy as np


def test_vad_is_speech_returns_bool():
    from backend.voice.vad import VoiceActivityDetector
    vad = VoiceActivityDetector()
    audio = np.zeros(16000, dtype=np.int16)
    result = vad.is_speech(audio)
    assert isinstance(result, bool), f"is_speech should return bool, got {type(result)}"
    audio2 = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
    result2 = vad.is_speech(audio2)
    assert isinstance(result2, bool)


def test_vad_get_speech_timestamps_returns_list():
    from backend.voice.vad import VoiceActivityDetector
    vad = VoiceActivityDetector()
    audio = np.zeros(16000, dtype=np.int16)
    result = vad.get_speech_timestamps(audio)
    assert isinstance(result, list), f"get_speech_timestamps should return list, got {type(result)}"


def test_stt_int16_to_float32():
    from backend.voice.stt import _to_float32
    a = np.array([100, 200, 300, -32768], dtype=np.int16)
    b = _to_float32(a)
    assert b.dtype == np.float32
    assert abs(b[0] - 100 / 32768.0) < 1e-6
    assert abs(b[3] - (-1.0)) < 1e-6


def test_stt_float32_passthrough():
    from backend.voice.stt import _to_float32
    a = np.array([0.1, 0.2, -0.3], dtype=np.float32)
    b = _to_float32(a)
    assert b.dtype == np.float32
    assert b[0] == 0.1


def test_stt_empty_audio():
    from backend.voice.stt import SpeechToText
    stt = SpeechToText()
    result = stt.transcribe(np.array([], dtype=np.int16))
    assert result == ""


def test_wake_word_default_model():
    from backend.voice.wake_word import WakeWordDetector, _VALID_MODELS
    w = WakeWordDetector(model="hey_nokton")
    assert w.model_name in _VALID_MODELS
    assert w.model_name == "alexa"


def test_wake_word_valid_model():
    from backend.voice.wake_word import WakeWordDetector
    w = WakeWordDetector(model="hey_mycroft")
    assert w.model_name == "hey_mycroft"


def test_wake_word_cooldown_state():
    from backend.voice.wake_word import WakeWordDetector
    callbacks = []
    w = WakeWordDetector(sensitivity=0.5, cooldown_s=2.0, min_duration_s=0.1)
    w.set_callback(lambda ev: callbacks.append(ev))
    w._maybe_trigger(0.0)
    assert w.state.value == "idle"
    w._maybe_trigger(0.6)
    assert w._above_threshold_since is not None
    import time
    time.sleep(0.15)
    w._maybe_trigger(0.6)
    assert len(callbacks) == 1
    w._maybe_trigger(0.6)
    w._maybe_trigger(0.0)
    assert len(callbacks) == 1, "cooldown should prevent re-trigger"
    w._last_trigger_time = 0.0
    w._above_threshold_since = None
    w._maybe_trigger(0.6)
    import time as _t
    _t.sleep(0.15)
    w._maybe_trigger(0.6)
    w._maybe_trigger(0.0)
    assert len(callbacks) == 2, f"after cooldown, should trigger again (got {len(callbacks)})"


def test_tts_constructed():
    from backend.voice.tts import TextToSpeech
    tts = TextToSpeech()
    assert tts.is_speaking is False
    tts.stop()
    assert tts.is_speaking is False


def test_pipeline_constructed():
    from backend.voice.pipeline import VoicePipeline
    from backend.config import VoiceConfig
    pipe = VoicePipeline(VoiceConfig())
    assert pipe.is_running is False
    assert pipe._wake is not None
    assert pipe._vad is not None
    assert pipe._stt is not None
    assert pipe._tts is not None


def test_pipeline_push_audio_noop_when_idle():
    from backend.voice.pipeline import VoicePipeline
    from backend.config import VoiceConfig
    pipe = VoicePipeline(VoiceConfig())
    audio = np.zeros(1280, dtype=np.int16)
    pipe.push_audio(audio)
    assert pipe._capture_buffer == []


def test_main_imports_voice_pipeline():
    from backend import main
    assert hasattr(main, "voice_pipeline")
    assert hasattr(main, "_active_voice_sockets")
    assert hasattr(main, "_handle_voice_transcript")
    assert hasattr(main, "_broadcast_voice_state")


def main():
    print("=== Phase 2 smoke tests ===")
    tests = [
        test_vad_is_speech_returns_bool,
        test_vad_get_speech_timestamps_returns_list,
        test_stt_int16_to_float32,
        test_stt_float32_passthrough,
        test_stt_empty_audio,
        test_wake_word_default_model,
        test_wake_word_valid_model,
        test_wake_word_cooldown_state,
        test_tts_constructed,
        test_pipeline_constructed,
        test_pipeline_push_audio_noop_when_idle,
        test_main_imports_voice_pipeline,
    ]
    for t in tests:
        try:
            t()
            print(f"  OK: {t.__name__}")
        except Exception as e:
            print(f"  FAIL: {t.__name__}: {e}")
            return 1
    print("All Phase 2 tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
