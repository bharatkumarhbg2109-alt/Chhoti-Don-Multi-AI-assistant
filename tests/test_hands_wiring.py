"""
Tests for Hands Layer wiring into ManagerAgent.brain_task().

Verifies that:
- Low-tier hands (weather, time, news, search) execute directly
- High-tier hands (filesystem, terminal, windows) go through safe_tool_execute
- No match falls through to the existing brain pipeline
- Any hands failure is fail-open (falls through to brain)
- Memory is updated for hands responses
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch, call

from core.manager import ManagerAgent


def _make_manager():
    """Create a ManagerAgent with mocked internals for fast unit tests."""
    with patch("core.manager.Brain"), \
         patch("core.manager.Memory"), \
         patch("core.manager.ToolRegistry"), \
         patch("core.manager.OperatorGuard"):
        mgr = ManagerAgent()
    mgr.brain = MagicMock()
    mgr.memory = MagicMock()
    mgr.tool_registry = MagicMock()
    mgr.guardian = MagicMock()
    mgr.session_log = []
    return mgr


class HandsWeatherRoutingTest(unittest.TestCase):
    """Test A — Weather query routes through hands layer."""

    def test_weather_routes_through_hands(self):
        mgr = _make_manager()

        hand_result = {
            "matched": True,
            "hand": "weather",
            "action": "current_weather",
            "params": {"location": "Delhi"},
        }
        tool_result = {
            "status": "success",
            "result": "25\u00b0C, Sunny",
        }

        with patch("hands.intent_router.route_intent", return_value=hand_result), \
             patch("hands.tool_manager.get_tool_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.execute.return_value = tool_result
            mock_gtm.return_value = mock_tm

            result = mgr.brain_task("What's the weather in Delhi?")

        self.assertIn("25", result.get("response", ""))
        self.assertEqual(result.get("source"), "hands")
        self.assertEqual(result.get("hand"), "weather")
        self.assertEqual(result.get("action"), "current_weather")
        mock_tm.execute.assert_called_once_with(
            "weather", "current_weather", {"location": "Delhi"}
        )


class HandsTimeRoutingTest(unittest.TestCase):
    """Test B — Time query routes through hands layer."""

    def test_time_routes_through_hands(self):
        mgr = _make_manager()

        hand_result = {
            "matched": True,
            "hand": "time",
            "action": "current_time",
            "params": {},
        }
        tool_result = {
            "status": "success",
            "result": "10:30 AM IST",
        }

        with patch("hands.intent_router.route_intent", return_value=hand_result), \
             patch("hands.tool_manager.get_tool_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.execute.return_value = tool_result
            mock_gtm.return_value = mock_tm

            result = mgr.brain_task("What time is it?")

        self.assertIn("10:30", result.get("response", ""))
        self.assertEqual(result.get("source"), "hands")
        self.assertEqual(result.get("hand"), "time")


class HandsNoMatchFallthroughTest(unittest.TestCase):
    """Test C — No hands match → falls through to brain."""

    def test_no_match_falls_to_brain(self):
        mgr = _make_manager()
        mgr.brain.think.return_value = "I am qwen3.5"

        hand_result = {
            "matched": False,
            "hand": "",
            "action": "",
            "params": {},
        }

        with patch("hands.intent_router.route_intent", return_value=hand_result), \
             patch("hands.tool_manager.get_tool_manager"):
            result = mgr.brain_task("Explain quantum entanglement")

        # ToolManager.execute should NOT have been called
        # brain.think should have been called
        mgr.brain.think.assert_called_once()
        self.assertIn("Brain", result.get("agent", ""))


class HandsFailureFallthroughTest(unittest.TestCase):
    """Test D — Hands failure → falls through to brain (fail-open)."""

    def test_hands_failure_falls_to_brain(self):
        mgr = _make_manager()
        mgr.brain.think.return_value = "fallback answer"

        hand_result = {
            "matched": True,
            "hand": "weather",
            "action": "current_weather",
            "params": {},
        }

        with patch("hands.intent_router.route_intent", return_value=hand_result), \
             patch("hands.tool_manager.get_tool_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.execute.side_effect = RuntimeError("weather API down")
            mock_gtm.return_value = mock_tm

            # Should NOT raise — fail-open
            result = mgr.brain_task("weather today?")

        # brain.think was called (fell through)
        mgr.brain.think.assert_called_once()
        self.assertIn("Brain", result.get("agent", ""))


class HandsHighTierGatedTest(unittest.TestCase):
    """Test E — High-tier hand goes through safe_tool_execute."""

    def test_filesystem_hand_uses_safe_tool_execute(self):
        mgr = _make_manager()
        mgr.safe_tool_execute = MagicMock(
            return_value={"status": "success", "result": "file content"}
        )

        hand_result = {
            "matched": True,
            "hand": "filesystem",
            "action": "read_file",
            "params": {"path": "notes.txt"},
        }

        with patch("hands.intent_router.route_intent", return_value=hand_result), \
             patch("hands.tool_manager.get_tool_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.execute.return_value = {"status": "success", "result": "file content"}
            mock_gtm.return_value = mock_tm

            result = mgr.brain_task("read my notes.txt")

        # safe_tool_execute should have been called (not direct tm.execute)
        mgr.safe_tool_execute.assert_called_once()
        call_args = mgr.safe_tool_execute.call_args
        # First arg should be the tool name string
        self.assertIn("filesystem", call_args[0][0])


class HandsMemoryUpdateTest(unittest.TestCase):
    """Test F — Memory updated after hands response."""

    def test_memory_updated_for_hands_response(self):
        mgr = _make_manager()

        hand_result = {
            "matched": True,
            "hand": "weather",
            "action": "current_weather",
            "params": {"location": "Delhi"},
        }
        tool_result = {
            "status": "success",
            "result": "25\u00b0C, Sunny",
        }

        with patch("hands.intent_router.route_intent", return_value=hand_result), \
             patch("hands.tool_manager.get_tool_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.execute.return_value = tool_result
            mock_gtm.return_value = mock_tm

            mgr.brain_task("weather?")

        # memory.add should have been called for both user and assistant
        calls = mgr.memory.add.call_args_list
        user_calls = [c for c in calls if c[0][0] == "user"]
        assistant_calls = [c for c in calls if c[0][0] == "assistant"]
        self.assertTrue(len(user_calls) >= 1, "memory.add('user', ...) not called")
        self.assertTrue(len(assistant_calls) >= 1, "memory.add('assistant', ...) not called")


class HandsImportSmokeTest(unittest.TestCase):
    """Test G — Import smoke: ManagerAgent imports successfully."""

    def test_manager_import(self):
        from core.manager import ManagerAgent
        self.assertTrue(callable(ManagerAgent))


if __name__ == "__main__":
    unittest.main()
