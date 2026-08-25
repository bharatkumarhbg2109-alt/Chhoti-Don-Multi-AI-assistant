"""Test suite for the voice I/O layer (voice/ package).

All hardware dependencies (faster-whisper, piper-tts, sounddevice, webrtcvad)
are mocked.  No real audio or GPU is needed.
"""

import threading
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from voice.config import VoiceConfig


class TestVoiceConfig(unittest.TestCase):
    """(a) VoiceConfig defaults are sensible."""

    def test_sample_rate_positive(self):
        cfg = VoiceConfig()
        self.assertGreater(cfg.sample_rate, 0)
        self.assertEqual(cfg.sample_rate, 16000)

    def test_capture_rate_positive(self):
        cfg = VoiceConfig()
        self.assertGreater(cfg.capture_sample_rate, 0)

    def test_stt_model_set(self):
        cfg = VoiceConfig()
        self.assertTrue(len(cfg.stt_model_size) > 0)

    def test_vad_params_valid(self):
        cfg = VoiceConfig()
        self.assertIn(cfg.vad_aggressiveness, range(4))
        self.assertIn(cfg.vad_frame_ms, (10, 20, 30))

    def test_language_property(self):
        cfg = VoiceConfig(stt_language="auto")
        self.assertIsNone(cfg.language)
        cfg2 = VoiceConfig(stt_language="hi")
        self.assertEqual(cfg2.language, "hi")

    def test_to_dict_returns_dict(self):
        cfg = VoiceConfig()
        d = cfg.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("sample_rate", d)


class TestSTT(unittest.TestCase):
    """(b, c) SpeechToText loads and transcribes (mocked)."""

    @patch("faster_whisper.WhisperModel")
    def test_load_creates_model(self, MockModel):
        from voice.stt import SpeechToText
        cfg = VoiceConfig()
        stt = SpeechToText(cfg)
        stt.load()
        MockModel.assert_called_once()
        self.assertIsNotNone(stt._model)

    @patch("faster_whisper.WhisperModel")
    def test_transcribe_returns_string(self, MockModel):
        from voice.stt import SpeechToText
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (
            [MagicMock(text="hello world", language="en", avg_logprob=-0.3)],
            None,
        )
        MockModel.return_value = mock_model
        cfg = VoiceConfig()
        stt = SpeechToText(cfg)
        stt.load()
        audio = np.zeros(16000, dtype=np.int16)
        text, lang, logprob = stt.transcribe(audio)
        self.assertIsInstance(text, str)
        self.assertEqual(text, "hello world")

    @patch("faster_whisper.WhisperModel")
    def test_load_is_idempotent(self, MockModel):
        from voice.stt import SpeechToText
        cfg = VoiceConfig()
        stt = SpeechToText(cfg)
        stt.load()
        stt.load()  # second call should NOT create another model
        MockModel.assert_called_once()


class TestTTS(unittest.TestCase):
    """(d, e) TextToSpeech speaks and can be interrupted."""

    @patch("piper.PiperVoice")
    def test_speak_completes(self, MockPiper):
        from voice.tts import TextToSpeech
        mock_voice = MagicMock()
        MockPiper.load.return_value = mock_voice
        cfg = VoiceConfig()
        tts = TextToSpeech(cfg)
        tts.load()
        # Mock synthesize to return valid audio
        tts.synthesize = MagicMock(return_value=np.zeros(16000, dtype=np.int16))
        # Mock sounddevice at the sys.modules level
        import sys
        mock_sd = MagicMock()
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value.__enter__ = MagicMock(return_value=mock_stream)
        mock_sd.OutputStream.return_value.__exit__ = MagicMock(return_value=False)
        old = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = mock_sd
        try:
            result = tts.speak("hello")
        finally:
            if old:
                sys.modules["sounddevice"] = old
            else:
                sys.modules.pop("sounddevice", None)
        self.assertIsInstance(result, bool)

    @patch("piper.PiperVoice")
    def test_speak_can_be_interrupted(self, MockPiper):
        """(e) speak() returns False when interrupt event is set."""
        from voice.tts import TextToSpeech
        mock_voice = MagicMock()
        MockPiper.load.return_value = mock_voice
        cfg = VoiceConfig()
        tts = TextToSpeech(cfg)
        tts.load()
        tts.synthesize = MagicMock(return_value=np.zeros(16000, dtype=np.int16))
        # Pre-set the interrupt event -> _play detects it on first iteration
        stop_event = threading.Event()
        stop_event.set()
        import sys
        mock_sd = MagicMock()
        mock_stream = MagicMock()
        mock_sd.OutputStream.return_value.__enter__ = MagicMock(return_value=mock_stream)
        mock_sd.OutputStream.return_value.__exit__ = MagicMock(return_value=False)
        old = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = mock_sd
        try:
            result = tts.speak("hello", interrupt=stop_event)
        finally:
            if old:
                sys.modules["sounddevice"] = old
            else:
                sys.modules.pop("sounddevice", None)
        self.assertFalse(result)


class TestBrainClient(unittest.TestCase):
    """(f, g) BrainClient returns string on success, empty on failure."""

    @patch("requests.post")
    def test_ask_http_success(self, mock_post):
        from voice.brain_client import BrainClient
        cfg = VoiceConfig(brain_mode="http")
        client = BrainClient(cfg)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Hello from brain"}
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        result = client.ask("hi")
        self.assertEqual(result, "Hello from brain")

    @patch("requests.post")
    def test_ask_http_failure_returns_empty(self, mock_post):
        """(g) _call_api() returns empty string on failure, never raises."""
        from voice.brain_client import BrainClient
        cfg = VoiceConfig(brain_mode="http")
        client = BrainClient(cfg)
        mock_post.side_effect = ConnectionError("refused")
        result = client.ask("hi")
        # Should return empty string or error message, never raise
        self.assertIsInstance(result, str)

    @patch("requests.post")
    def test_ask_http_error_status(self, mock_post):
        from voice.brain_client import BrainClient
        cfg = VoiceConfig(brain_mode="http")
        client = BrainClient(cfg)
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("bad json")
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp
        result = client.ask("hi")
        self.assertIsInstance(result, str)


class TestVoiceAssistant(unittest.TestCase):
    """(h) VoiceAssistant __init__ completes (mock all I/O)."""

    @patch("voice.orchestrator.MicCapture")
    @patch("voice.orchestrator.BrainClient")
    @patch("voice.orchestrator.TextToSpeech")
    @patch("voice.orchestrator.SpeechToText")
    def test_init_completes(self, MockSTT, MockTTS, MockBrain, MockMic):
        from voice.orchestrator import VoiceAssistant
        cfg = VoiceConfig()
        va = VoiceAssistant(cfg)
        self.assertIsNotNone(va.cfg)
        self.assertIsNotNone(va.stt)
        self.assertIsNotNone(va.tts)
        self.assertIsNotNone(va.mic)
        self.assertIsNotNone(va.brain)

    @patch("voice.orchestrator.MicCapture")
    @patch("voice.orchestrator.BrainClient")
    @patch("voice.orchestrator.TextToSpeech")
    @patch("voice.orchestrator.SpeechToText")
    def test_handle_turn_rejects_empty_audio(self, MockSTT, MockTTS, MockBrain, MockMic):
        from voice.orchestrator import VoiceAssistant
        cfg = VoiceConfig()
        va = VoiceAssistant(cfg)
        va.tts.speak = MagicMock(return_value=True)
        result = va.handle_turn(None)
        self.assertFalse(result)
        result = va.handle_turn(np.array([], dtype=np.int16))
        self.assertFalse(result)


class TestVoiceImportSmoke(unittest.TestCase):
    """(i) All voice.* modules import cleanly."""

    def test_import_config(self):
        import voice.config
        self.assertTrue(hasattr(voice.config, "VoiceConfig"))

    def test_import_stt(self):
        import voice.stt
        self.assertTrue(hasattr(voice.stt, "SpeechToText"))

    def test_import_tts(self):
        import voice.tts
        self.assertTrue(hasattr(voice.tts, "TextToSpeech"))

    def test_import_brain_client(self):
        import voice.brain_client
        self.assertTrue(hasattr(voice.brain_client, "BrainClient"))

    def test_import_orchestrator(self):
        import voice.orchestrator
        self.assertTrue(hasattr(voice.orchestrator, "VoiceAssistant"))

    def test_import_capture(self):
        import voice.capture
        self.assertTrue(hasattr(voice.capture, "MicCapture"))


if __name__ == "__main__":
    unittest.main()
