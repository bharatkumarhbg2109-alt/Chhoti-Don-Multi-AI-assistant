"""Retry-on-empty guard in the Brain's local model path (Tuning pass 2).

qwen occasionally returned an empty generation ('') and stalled a whole agent
stage. think_fast now re-calls the single-shot generator a few times on an empty
result before giving up. These tests drive that WITHOUT a live model by patching
the single-call primitive (_local_generate).
"""

import unittest
from unittest.mock import patch

from core.brain import Brain
import core.brain as brain_mod


def _offline_brain():
    """Construct a Brain without touching the network, forced into local mode."""
    with patch("core.brain.requests.get", side_effect=Exception("no probe")):
        b = Brain()
    b.mode = "local"
    return b


class RetryOnEmptyTests(unittest.TestCase):
    def test_recovers_from_empty_then_valid(self):
        b = _offline_brain()
        seq = ["", '{"tool":"finish"}']  # first empty, then a valid action
        with patch.object(b, "_local_generate", side_effect=seq) as gen:
            out = b.think_fast("hi", brain_type="coding", system_prompt="x")
        self.assertEqual(out, '{"tool":"finish"}')
        self.assertEqual(gen.call_count, 2)   # retried exactly once

    def test_whitespace_only_counts_as_empty(self):
        b = _offline_brain()
        seq = ["   \n", "  ", "ok"]
        with patch.object(b, "_local_generate", side_effect=seq) as gen:
            out = b.think_fast("hi", brain_type="coding", system_prompt="x")
        self.assertEqual(out, "ok")
        self.assertEqual(gen.call_count, 3)

    def test_gives_up_cleanly_after_k_empties(self):
        b = _offline_brain()
        with patch.object(b, "_local_generate", return_value="") as gen:
            out = b.think_fast("hi", brain_type="coding", system_prompt="x")
        self.assertEqual(out, "")
        # default _EMPTY_RETRIES = 2 -> 1 initial + 2 retries.
        self.assertEqual(gen.call_count, brain_mod._EMPTY_RETRIES + 1)

    def test_no_retry_when_first_response_is_valid(self):
        b = _offline_brain()
        with patch.object(b, "_local_generate", return_value="good") as gen:
            out = b.think_fast("hi", brain_type="coding", system_prompt="x")
        self.assertEqual(out, "good")
        self.assertEqual(gen.call_count, 1)   # no wasted retries

    def test_retry_helper_direct_and_respects_retry_count(self):
        b = _offline_brain()
        with patch.object(b, "_local_generate", return_value="") as gen:
            out = b._local_generate_retry({"model": "x"}, retries=1)
        self.assertEqual(out, "")
        self.assertEqual(gen.call_count, 2)   # 1 + 1 retry


if __name__ == "__main__":
    unittest.main()
