"""
Tests for the Hands Layer (Tool Execution Layer).

Fast + offline-tolerant: network/model tests assert the result envelope shape
and never fail on missing connectivity; unavailable hands (playwright/pyautogui
absent) are expected to report `unavailable` gracefully.
"""

import logging
import os
import sys
import tempfile

import pytest

from hands import get_tool_manager, get_intent_router, Permission

_ALL_HANDS = (
    "filesystem", "terminal", "windows", "input", "browser", "search",
    "youtube", "vision", "weather", "news", "time",
)


@pytest.fixture(scope="module")
def tm():
    return get_tool_manager()


@pytest.fixture(scope="module")
def router():
    return get_intent_router()


# ── Manager / discovery ───────────────────────────────────────
def test_manager_builds_and_discovers(tm):
    d = tm.discover()
    assert d["total_hands"] == 11
    assert d["total_actions"] > 50
    for name in _ALL_HANDS:
        assert name in d["hands"]


def test_health_check(tm):
    h = tm.health_check()
    assert h["status"] == "ok"
    assert h["hands_total"] == 11
    # Dependency-free hands must always be ready.
    assert h["hands"]["filesystem"]["available"] is True
    assert h["hands"]["terminal"]["available"] is True
    assert h["hands"]["time"]["available"] is True


def test_unknown_hand_and_action_do_not_crash(tm):
    assert tm.execute("nope", "x")["status"] == "error"
    assert tm.execute("filesystem", "no_such_action")["status"] == "error"


# ── File System ───────────────────────────────────────────────
def test_filesystem_roundtrip_and_confirmation(tm):
    d = os.path.join(tempfile.gettempdir(), "hands_pytest")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "t.txt")

    assert tm.execute("filesystem", "write_file", {"path": f, "content": "abc"})["status"] == "success"
    r = tm.execute("filesystem", "read_file", {"path": f})
    assert r["status"] == "success" and r["result"]["text"] == "abc"
    assert tm.execute("filesystem", "list_directory", {"path": d})["status"] == "success"

    # Destructive delete is gated behind confirmation.
    assert tm.execute("filesystem", "delete", {"path": f})["status"] == "confirmation_required"
    assert tm.execute("filesystem", "delete", {"path": f}, confirm=True)["status"] == "success"


# ── Terminal ──────────────────────────────────────────────────
def test_terminal_execute(tm):
    r = tm.execute("terminal", "execute", {"command": "echo hands"})
    assert r["status"] == "success"
    assert "hands" in r["result"]["stdout"]
    assert r["result"]["returncode"] == 0


# ── Windows ───────────────────────────────────────────────────
def test_windows_metrics(tm):
    for action in ("system_info", "cpu_usage", "ram_usage", "disk_usage"):
        r = tm.execute("windows", action, {})
        if sys.platform.startswith("win"):
            assert r["status"] == "success", (action, r)
        else:
            assert r["status"] in ("success", "unavailable")


def test_windows_kill_process_requires_confirmation(tm):
    r = tm.execute("windows", "kill_process", {"pid": 999999})
    # Either the confirmation gate (available) or unavailable (non-Windows).
    assert r["status"] in ("confirmation_required", "unavailable")


# ── Search (network-tolerant) ─────────────────────────────────
def test_search_envelope(tm):
    r = tm.execute("search", "duckduckgo_search", {"query": "chhoti don", "limit": 2}, timeout=15)
    assert r["status"] in ("success", "error")  # never crashes; offline -> error
    if r["status"] == "success":
        assert "results" in r["result"]


# ── Vision (existing model, exposed) ──────────────────────────
def test_vision_status(tm):
    r = tm.execute("vision", "vision_status", {})
    assert r["status"] == "success"
    assert "available" in r["result"]  # reports whether llava is installed


# ── Unavailable hands degrade gracefully ──────────────────────
@pytest.mark.parametrize("hand,action,params", [
    ("browser", "open_url", {"url": "https://example.com"}),
    ("youtube", "play", {}),
    ("input", "mouse_click", {"x": 1, "y": 1}),
])
def test_optional_hands_graceful(tm, hand, action, params):
    r = tm.execute(hand, action, params)
    # If the optional dependency is installed it may run; otherwise it must be
    # a clean "unavailable" — never an exception/crash.
    assert r["status"] in ("success", "unavailable", "error", "simulated", "confirmation_required")
    assert "hand" in r and "action" in r


# ── Time & Calendar (offline, always available) ───────────────
def test_time_hand_core(tm):
    assert tm.health_check()["hands"]["time"]["available"] is True
    for action in ("current_time", "current_date", "day", "month", "year",
                   "week_number", "is_leap_year"):
        r = tm.execute("time", action, {})
        assert r["status"] == "success", (action, r)

    cal = tm.execute("time", "calendar_month", {"year": 2026, "month": 7})
    assert cal["status"] == "success"
    assert cal["result"]["month_name"] == "July"
    assert len(cal["result"]["weeks"]) >= 4

    # Named timezone resolves (tzdata present) or degrades with a note — never crashes.
    tz = tm.execute("time", "current_time", {"timezone": "Asia/Kolkata"})
    assert tz["status"] == "success"

    fest = tm.execute("time", "festival_lookup", {"upcoming": True})
    assert fest["status"] == "success" and "festivals" in fest["result"]


# ── Weather (network-tolerant) ────────────────────────────────
def test_weather_envelope(tm):
    r = tm.execute("weather", "current_weather", {"location": "London"}, timeout=20)
    # Live data, graceful search-fallback, or a clean error — never a crash.
    assert r["status"] in ("success", "unavailable", "error")
    assert r["hand"] == "weather"
    if r["status"] == "success":
        assert "current" in r["result"] or "fallback" in r["result"]


def test_weather_status(tm):
    r = tm.execute("weather", "weather_status", {}, timeout=20)
    assert r["status"] == "success"
    assert r["result"]["provider"] == "open-meteo"


# ── News (network-tolerant) ───────────────────────────────────
def test_news_categories_are_listed(tm):
    r = tm.execute("news", "categories", {})
    assert r["status"] == "success"
    assert "technology" in r["result"]["categories"]
    assert "ai" in r["result"]["categories"]


def test_news_latest_envelope(tm):
    r = tm.execute("news", "latest_news", {"limit": 3}, timeout=20)
    assert r["status"] in ("success", "error")  # offline -> error, never crash
    if r["status"] == "success":
        assert "articles" in r["result"]


def test_news_summarize_offline_fallback(tm, monkeypatch):
    # Force the model "offline" so this deterministically exercises the extractive
    # fallback it is named for — independent of whether Ollama happens to be running
    # (a live model can exceed the action timeout, which is not what this test checks).
    monkeypatch.setattr(
        "hands.news_hand.NewsHand._summarize_with_model",
        staticmethod(lambda body, max_sentences: None),
    )
    text = "Alpha shipped. Beta improved speed. Gamma raised prices. Delta hired staff."
    r = tm.execute("news", "summarize", {"text": text, "max_sentences": 2}, timeout=30)
    assert r["status"] == "success"
    assert r["result"]["engine"] == "extractive"
    assert r["result"]["summary"]


# ── Intent Router ─────────────────────────────────────────────
@pytest.mark.parametrize("text,hand,action", [
    ("Open YouTube", "browser", "open_youtube"),
    ("Search AI News", "search", "duckduckgo_search"),
    ("Will it rain tomorrow?", "weather", "rain_probability"),
    ("Open VS Code", "windows", "open_vscode"),
    ("Run git status", "terminal", "execute"),
    ("Read this folder", "filesystem", "list_directory"),
    ("What time is it?", "time", "current_time"),
    ("latest AI news", "news", "by_category"),
    ("weather in Paris", "weather", "current_weather"),
    ("take a screenshot of the screen", "vision", "screenshot_analysis"),
])
def test_intent_router_routing_table(router, text, hand, action):
    d = router.route(text)
    assert d["matched"] is True, (text, d)
    assert d["hand"] == hand and d["action"] == action, (text, d)


def test_intent_router_params_extracted(router):
    assert router.route("Run git status")["params"] == {"command": "git status"}
    assert router.route("weather in Tokyo")["params"].get("location") == "tokyo"
    assert router.route("Search AI News")["params"].get("query") == "AI News"


def test_intent_router_no_match_defers(router):
    d = router.route("tell me a joke about cats")
    assert d["matched"] is False  # Brain/LLM handles it


def test_intent_router_execute_roundtrip(tm, router):
    out = router.route_and_execute(tm, "what time is it")
    assert out["routed"]["hand"] == "time"
    assert out["execution"]["status"] == "success"

    miss = router.route_and_execute(tm, "compose a poem")
    assert miss["routed"]["matched"] is False
    assert miss["execution"] is None


# ── Logging ───────────────────────────────────────────────────
class _CaptureHandler(logging.Handler):
    """Logging handler that records formatted messages for assertions."""

    def __init__(self, sink):
        super().__init__()
        self.sink = sink

    def emit(self, record):
        self.sink.append(record.getMessage())


def test_execution_is_logged(tm):
    import hands.base as base

    records: list = []
    handler = _CaptureHandler(records)
    base.logger.addHandler(handler)
    try:
        tm.execute("time", "current_date", {})
    finally:
        base.logger.removeHandler(handler)
    joined = " ".join(records)
    assert "hand=time" in joined and "action=current_date" in joined and "status=success" in joined


# ── Permissions ───────────────────────────────────────────────
def test_permission_preview(tm):
    p = tm.check_permission("filesystem", "delete")
    assert p["ok"] and p["destructive"] and p["requires_confirmation"]
    p2 = tm.check_permission("filesystem", "read_file")
    assert p2["ok"] and not p2["requires_confirmation"]
    assert Permission.DANGEROUS > Permission.READ_ONLY

    # Read-only hands never require confirmation.
    for action in ("current_time", "latest_news", "current_weather"):
        hand = {"current_time": "time", "latest_news": "news", "current_weather": "weather"}[action]
        assert tm.check_permission(hand, action)["requires_confirmation"] is False
