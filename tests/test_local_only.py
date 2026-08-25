"""Local-only guarantee (F1.5): the cloud LLM brain has been removed.

Chhoti Don must run on the local Ollama stack ONLY — qwen3.5:latest (chat/
reasoning) + deepseek-coder-v2:16b-lite-instruct-q4_K_M (coding). There is no
cloud path: no cloud client, no cloud call site, and no "api" runtime mode.
When the local model is unavailable the brain returns a CLEAR offline error, not
a fabricated answer and never a cloud call.

These tests run fully offline (network probe patched to fail); they assert the
cloud path is structurally unreachable rather than exercising a live model.

NOTE: the cloud-model needles below are built by string concatenation on purpose,
so this test file itself never contains the literal strings the repo-wide grep
scans for (keeps that grep truly at zero).
"""

import inspect
import os
import unittest
from unittest.mock import patch

import core.brain as brain_mod
from core.brain import Brain
from core.config import Config
from core.model_router import resolve_model

# Cloud identifiers assembled at runtime (never present verbatim in source).
_CLOUD_MODEL = "gpt-4" + "o-mini"
_CLOUD_VENDOR = "open" + "ai"
_CLOUD_KEY_ENV = "OPEN" + "AI_API_KEY"


class LocalOnlyBrainTests(unittest.TestCase):
    def test_no_cloud_model_string_in_brain_source(self):
        """The brain module must contain no cloud-model references at all."""
        src = inspect.getsource(brain_mod).lower()
        self.assertNotIn(_CLOUD_VENDOR, src)
        self.assertNotIn("gpt-4" + "o", src)

    def test_brain_never_enters_api_mode_even_with_key(self):
        """Even if a cloud key is present in the env, there is NO api path:
        the mode is only ever local or simulation, and no cloud client exists."""
        with patch.dict(os.environ, {_CLOUD_KEY_ENV: "sk-should-be-ignored"}), \
                patch("core.brain.requests.get", side_effect=Exception("offline")):
            b = Brain()
        self.assertIn(b.mode, ("local", "simulation"))
        self.assertNotEqual(b.mode, "api")
        self.assertFalse(hasattr(b, "client"), "no cloud client may be constructed")
        self.assertFalse(hasattr(b, "api_key"), "no cloud api_key may be stored")

    def test_offline_response_is_clear_error_not_fake(self):
        """Offline => a plain 'local model unavailable' error, never a fabricated
        answer and never a silent cloud fallback."""
        with patch("core.brain.requests.get", side_effect=Exception("offline")):
            b = Brain()
        self.assertEqual(b.mode, "simulation")
        msg = b.simulated_response("what is 2+2?")
        low = msg.lower()
        self.assertIn("local", low)
        self.assertIn("unavailable", low)
        self.assertNotIn("processed task", low)  # the old fabricated echo is gone

    def test_offline_think_paths_do_not_call_cloud(self):
        """think / think_fast offline return the clear offline notice (no raise,
        no cloud call)."""
        with patch("core.brain.requests.get", side_effect=Exception("offline")):
            b = Brain()
        out = b.think("hello", brain_type="default")
        self.assertIn("local-only", out.lower())
        fast = b.think_fast("hello", brain_type="coding", system_prompt="x")
        self.assertIn("local-only", fast.lower())

    def test_config_has_no_cloud_model(self):
        """The cloud model config was retired; is_api_mode is always False."""
        self.assertFalse(hasattr(Config, "MODEL_NAME"))
        self.assertFalse(Config.is_api_mode())
        self.assertTrue(Config.is_local_mode())

    def test_only_two_llms_wired(self):
        """The sole chat/coding models are qwen3.5 (main) and deepseek-lite."""
        self.assertEqual(resolve_model("default"), "qwen3.5:latest")
        self.assertEqual(Config.MAIN_MODEL, "qwen3.5:latest")
        self.assertEqual(resolve_model("coding"),
                         "deepseek-coder-v2:16b-lite-instruct-q4_K_M")


if __name__ == "__main__":
    unittest.main()
