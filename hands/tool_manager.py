"""
Chhoti Don - Hands Layer :: Tool Manager

The single entry point between the Brain and the operating system. The Brain
never touches OS / browser / process APIs directly — it asks the Tool Manager,
which routes the request to the correct Hand.

    manager.execute("filesystem", "read_file", {"path": "..."})
    manager.execute("windows", "kill_process", {"pid": 123}, confirm=True)
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission, tool_result, logger


class ToolManager:
    """Central registry + router for all Hands."""

    def __init__(self, default_timeout: float = 60.0) -> None:
        self._hands: Dict[str, BaseHand] = {}
        self.default_timeout = default_timeout

    # ── Registration & discovery ─────────────────────────────
    def register(self, hand: BaseHand) -> "ToolManager":
        """Register a Hand. Every tool registers itself here."""
        self._hands[hand.name] = hand
        logger.info("registered hand=%s available=%s", hand.name, hand.is_available())
        return self

    def unregister(self, name: str) -> None:
        self._hands.pop(name, None)

    def hands(self) -> List[str]:
        return list(self._hands.keys())

    def get_hand(self, name: str) -> Optional[BaseHand]:
        return self._hands.get(name)

    def discover(self) -> Dict[str, Any]:
        """Full catalogue of hands, actions, permissions and availability."""
        return {
            "hands": {name: hand.describe() for name, hand in self._hands.items()},
            "total_hands": len(self._hands),
            "total_actions": sum(len(h.list_actions()) for h in self._hands.values()),
        }

    def list_actions(self, hand: Optional[str] = None) -> Dict[str, List[str]]:
        if hand:
            h = self._hands.get(hand)
            return {hand: h.list_actions() if h else []}
        return {name: h.list_actions() for name, h in self._hands.items()}

    # ── Health / status ──────────────────────────────────────
    def health_check(self) -> Dict[str, Any]:
        results = {name: hand.health() for name, hand in self._hands.items()}
        available = sum(1 for r in results.values() if r["available"])
        return {
            "status": "ok",
            "hands_total": len(results),
            "hands_available": available,
            "hands": results,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "hands": self.hands(),
            "available": [n for n, h in self._hands.items() if h.is_available()],
            "unavailable": [n for n, h in self._hands.items() if not h.is_available()],
        }

    # ── Permission preview (without executing) ───────────────
    def check_permission(self, hand: str, action: str) -> Dict[str, Any]:
        h = self._hands.get(hand)
        if not h:
            return {"ok": False, "error": f"Unknown hand '{hand}'"}
        act = h._actions.get(action)  # noqa: SLF001 - internal read for introspection
        if not act:
            return {"ok": False, "error": f"Unknown action '{action}'"}
        return {
            "ok": True,
            "permission": act.permission.name,
            "destructive": act.destructive,
            "requires_confirmation": act.destructive or act.permission >= Permission.DANGEROUS,
        }

    # ── Execution routing ────────────────────────────────────
    def execute(
        self,
        hand: str,
        action: str,
        params: Optional[Dict] = None,
        *,
        confirm: bool = False,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Route an action to a Hand with a bounded (soft) timeout. Never raises."""
        h = self._hands.get(hand)
        if not h:
            return tool_result(hand, action, status="error",
                               error=f"Unknown hand '{hand}'. Registered: {self.hands()}")

        timeout = self.default_timeout if timeout is None else timeout
        box: Dict[str, Any] = {}

        def _worker() -> None:
            box["result"] = h.run(action, params, confirm=confirm)

        worker = threading.Thread(target=_worker, name=f"hand-{hand}-{action}", daemon=True)
        started = time.time()
        worker.start()
        worker.join(timeout)

        if worker.is_alive():
            # Soft timeout: the worker keeps running in the background but we
            # return control to the caller so nothing hangs.
            env = tool_result(hand, action, status="timeout",
                              error=f"Action exceeded {timeout}s timeout.",
                              duration_ms=(time.time() - started) * 1000)
            logger.info("hand=%s action=%s status=timeout", hand, action)
            return env

        return box.get("result") or tool_result(
            hand, action, status="error", error="No result produced.",
        )


# ── Default singleton wiring ──────────────────────────────────
_MANAGER: Optional[ToolManager] = None


def build_tool_manager() -> ToolManager:
    """Construct a ToolManager and register every available Hand."""
    from .filesystem_hand import FileSystemHand
    from .terminal_hand import TerminalHand
    from .windows_hand import WindowsHand
    from .input_hand import InputHand
    from .browser_hand import BrowserHand
    from .search_hand import SearchHand
    from .youtube_hand import YouTubeHand
    from .vision_hand import VisionHand
    from .weather_hand import WeatherHand
    from .news_hand import NewsHand
    from .time_hand import TimeHand

    manager = ToolManager()

    # Browser + YouTube share a single browser engine (no duplicate browser).
    browser = BrowserHand()
    # Search Hand is reused by the Weather Hand as its browser-search fallback.
    search = SearchHand()
    hands: list = [
        FileSystemHand(),
        TerminalHand(),
        WindowsHand(),
        InputHand(),
        browser,
        search,
        YouTubeHand(browser=browser),
        VisionHand(),
        WeatherHand(search_hand=search),
        NewsHand(),
        TimeHand(),
    ]
    for hand in hands:
        try:
            manager.register(hand)
        except Exception as exc:  # a broken hand must not break the whole layer
            logger.warning("failed to register %s: %s", type(hand).__name__, exc)
    return manager


def get_tool_manager() -> ToolManager:
    """Process-wide singleton Tool Manager."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = build_tool_manager()
    return _MANAGER
