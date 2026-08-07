"""
Chhoti Don - Hands Layer :: Intent Router

A deterministic, offline rule engine that maps a natural-language request to a
(hand, action, params) tuple. It is the fast, predictable path that sits in
front of the Tool Manager — the Qwen3 Brain remains free to make its own tool
choices, but the router lets simple, unambiguous commands ("Open YouTube",
"What time is it?") route without a model round-trip.

    router = IntentRouter()
    decision = router.route("Open YouTube")
    # -> {"matched": True, "hand": "browser", "action": "open_youtube", ...}

    router.route_and_execute(get_tool_manager(), "will it rain tomorrow in Delhi")

Rules are tried in order; the first match wins. Nothing here executes anything
by itself unless `route_and_execute` is called explicitly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

# ── Keyword tables ───────────────────────────────────────────────────
# Apps handled by the Windows Hand (local desktop apps).
_WINDOWS_APPS: Dict[str, str] = {
    "vs code": "open_vscode", "vscode": "open_vscode", "visual studio code": "open_vscode",
    "notepad": "open_notepad",
    "calculator": "open_calculator", "calc": "open_calculator",
    "file explorer": "open_file_explorer", "explorer": "open_file_explorer",
    "chrome": "open_chrome",
}
# Sites handled by the Browser Hand.
_BROWSER_SITES: Dict[str, str] = {
    "youtube": "open_youtube",
    "google": "open_google",
    "gmail": "open_gmail",
}
# News categories the News Hand understands.
_NEWS_CATEGORIES = ("technology", "tech", "business", "sports", "sport", "finance",
                    "science", "ai", "artificial intelligence", "world", "health",
                    "entertainment")


@dataclass
class Route:
    """The outcome of routing a single request."""
    matched: bool
    hand: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly representation."""
        return {
            "matched": self.matched,
            "hand": self.hand,
            "action": self.action,
            "params": self.params,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
        }


# A rule is a callable that inspects the lowercased text and returns a Route or None.
_Rule = Callable[[str, str], Optional[Route]]


class IntentRouter:
    """Rule-based intent → (hand, action, params) router."""

    def __init__(self) -> None:
        # Order matters: earlier rules take priority. Verb-driven commands
        # (open/run/search) are checked around the topic detectors so that,
        # e.g., "Search AI News" routes to Search while "AI news" routes to News.
        self._rules: List[Tuple[str, _Rule]] = [
            ("apps", self._rule_apps),
            ("terminal", self._rule_terminal),
            ("weather", self._rule_weather),
            ("time", self._rule_time),
            ("search", self._rule_search),
            ("news", self._rule_news),
            ("filesystem", self._rule_filesystem),
            ("vision", self._rule_vision),
            ("youtube", self._rule_youtube),
        ]

    # ── Public API ───────────────────────────────────────────
    def route(self, text: str) -> Dict[str, Any]:
        """Return the best routing decision for a request (never raises)."""
        raw = (text or "").strip()
        low = raw.lower()
        if not low:
            return Route(False, reason="empty input").to_dict()
        for _name, rule in self._rules:
            try:
                result = rule(raw, low)
            except Exception:
                result = None
            if result is not None:
                return result.to_dict()
        return Route(False, reason="no rule matched; defer to Brain/LLM").to_dict()

    def explain(self) -> Dict[str, Any]:
        """Describe the routing table (for diagnostics / documentation)."""
        return {
            "rules_in_order": [name for name, _ in self._rules],
            "windows_apps": sorted(set(_WINDOWS_APPS.values())),
            "browser_sites": sorted(set(_BROWSER_SITES.values())),
            "news_categories": sorted(set(_NEWS_CATEGORIES)),
        }

    def route_and_execute(self, manager: Any, text: str, *, confirm: bool = False,
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """Route a request and execute it through the Tool Manager.

        Returns {"routed": <decision>, "execution": <envelope|None>}. When no
        rule matches, execution is None so the caller can fall back to the Brain.
        """
        decision = self.route(text)
        if not decision.get("matched"):
            return {"routed": decision, "execution": None}
        env = manager.execute(decision["hand"], decision["action"],
                              decision.get("params", {}), confirm=confirm, timeout=timeout)
        return {"routed": decision, "execution": env}

    # ── Extraction helpers ───────────────────────────────────
    @staticmethod
    def _after(patterns: Pattern[str], text: str) -> str:
        """Return the trimmed remainder captured by a regex, or ''."""
        m = patterns.search(text)
        return (m.group(1).strip() if m and m.group(1) else "").strip(" ?.!")

    @staticmethod
    def _location(low: str) -> str:
        """Extract a location following 'in/at/for', else ''."""
        m = re.search(r"\b(?:in|at|for)\s+([a-z][a-z\s,.-]{1,40})$", low)
        if m:
            return m.group(1).strip(" ?.!,")
        return ""

    # ── Rules ────────────────────────────────────────────────
    def _rule_apps(self, raw: str, low: str) -> Optional[Route]:
        """'open/launch/start <app-or-site>' and 'task manager'."""
        if re.search(r"\btask manager\b", low):
            return Route(True, "windows", "open_application", {"name": "taskmgr"},
                         0.9, "task manager → Windows Hand")
        if not re.search(r"^\s*(open|launch|start|go to|visit)\b", low):
            return None
        # Browser sites first (youtube/google/gmail), then local Windows apps.
        for key, action in _BROWSER_SITES.items():
            if key in low:
                return Route(True, "browser", action, {}, 0.95, f"open {key} → Browser Hand")
        for key, action in _WINDOWS_APPS.items():
            if key in low:
                return Route(True, "windows", action, {}, 0.95, f"open {key} → Windows Hand")
        # A bare URL → browser open_url.
        m = re.search(r"(https?://\S+|\b[\w-]+\.(?:com|org|net|io|dev|ai|in)\b\S*)", low)
        if m:
            url = m.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return Route(True, "browser", "open_url", {"url": url}, 0.8, "open URL → Browser Hand")
        # Otherwise assume a desktop application name for the Windows Hand.
        name = self._after(re.compile(r"^\s*(?:open|launch|start)\s+(.+)$"), low)
        if name:
            return Route(True, "windows", "open_application", {"name": name}, 0.6,
                         "open <app> → Windows Hand")
        return None

    def _rule_terminal(self, raw: str, low: str) -> Optional[Route]:
        """'run/execute <command>' and 'git ...' → Terminal Hand."""
        m = re.search(r"^\s*(?:run|execute|exec)\s+(?:the\s+)?(?:command\s+)?(.+)$", raw, re.I)
        if m:
            return Route(True, "terminal", "execute", {"command": m.group(1).strip()},
                         0.9, "run <command> → Terminal Hand")
        if re.search(r"^\s*(?:git|npm|pip|python|ls|dir|cd|echo)\b", low):
            return Route(True, "terminal", "execute", {"command": raw.strip()},
                         0.7, "shell command → Terminal Hand")
        return None

    def _rule_weather(self, raw: str, low: str) -> Optional[Route]:
        """Weather / rain / forecast / AQI → Weather Hand."""
        if not re.search(r"\b(weather|forecast|temperature|rain|humid|humidity|"
                         r"sunrise|sunset|uv|wind|climate|aqi|air quality|how (hot|cold))\b", low):
            return None
        location = self._location(low)
        params: Dict[str, Any] = {"location": location} if location else {}
        if re.search(r"\b(aqi|air quality)\b", low):
            return Route(True, "weather", "air_quality", params, 0.9, "air quality → Weather Hand")
        if re.search(r"\brain\b", low):
            params["day"] = "tomorrow" if "tomorrow" in low else "today"
            return Route(True, "weather", "rain_probability", params, 0.9, "rain → Weather Hand")
        if "tomorrow" in low:
            return Route(True, "weather", "tomorrow_weather", params, 0.9, "tomorrow → Weather Hand")
        if re.search(r"\b(forecast|7[\s-]?day|week|next few days)\b", low):
            params.setdefault("days", 7)
            return Route(True, "weather", "forecast", params, 0.85, "forecast → Weather Hand")
        if "humid" in low:
            return Route(True, "weather", "humidity", params, 0.8, "humidity → Weather Hand")
        if "wind" in low:
            return Route(True, "weather", "wind", params, 0.8, "wind → Weather Hand")
        if "sunrise" in low:
            return Route(True, "weather", "sunrise", params, 0.8, "sunrise → Weather Hand")
        if "sunset" in low:
            return Route(True, "weather", "sunset", params, 0.8, "sunset → Weather Hand")
        if "uv" in low:
            return Route(True, "weather", "uv_index", params, 0.8, "uv index → Weather Hand")
        return Route(True, "weather", "current_weather", params, 0.8, "weather → Weather Hand")

    def _rule_time(self, raw: str, low: str) -> Optional[Route]:
        """Time / date / day / calendar / festival → Time Hand."""
        tz = ""
        m = re.search(r"\bin\s+([A-Za-z]+/[A-Za-z_]+)\b", raw)  # e.g. Asia/Kolkata
        if m:
            tz = m.group(1)
        params = {"timezone": tz} if tz else {}
        if re.search(r"\bfestival|holiday\b", low):
            return Route(True, "time", "festival_lookup", {"upcoming": True}, 0.85,
                         "festival → Time Hand")
        if re.search(r"\bcalendar\b", low):
            return Route(True, "time", "calendar_month", {}, 0.85, "calendar → Time Hand")
        if re.search(r"\bweek number\b", low):
            return Route(True, "time", "week_number", {}, 0.85, "week number → Time Hand")
        # Weekday question — kept specific so "today"/"date" don't false-match.
        if re.search(r"\b(what day is it|which day is it|day of (?:the )?week|what.?s the day)\b", low):
            return Route(True, "time", "day", params, 0.85, "day → Time Hand")
        if re.search(r"\b(date|today|what.*month|what.*year)\b", low) and "time" not in low:
            return Route(True, "time", "current_date", params, 0.85, "date → Time Hand")
        if re.search(r"\b(time|clock)\b", low):
            return Route(True, "time", "current_time", params, 0.9, "time → Time Hand")
        return None

    def _rule_search(self, raw: str, low: str) -> Optional[Route]:
        """Explicit web-search verbs → Search Hand (spec: 'Search AI News')."""
        m = re.search(r"^\s*(?:search(?:\s+for)?|google|look up|find out|web search)\s+(.+)$",
                      raw, re.I)
        if m:
            return Route(True, "search", "duckduckgo_search",
                         {"query": m.group(1).strip(" ?.!")}, 0.85, "search <q> → Search Hand")
        if re.search(r"^\s*(?:who|what|when|where|why|how)\b", low) and "?" in raw:
            return Route(True, "search", "duckduckgo_search", {"query": raw.strip(" ?.!")},
                         0.5, "question → Search Hand")
        if re.search(r"\bwikipedia\b", low):
            q = re.sub(r".*wikipedia\s*(?:for|of|on)?\s*", "", low).strip(" ?.!")
            return Route(True, "search", "wikipedia_search", {"query": q or raw.strip()},
                         0.7, "wikipedia → Search Hand")
        return None

    def _rule_news(self, raw: str, low: str) -> Optional[Route]:
        """'... news / headlines' → News Hand (category-aware)."""
        if not re.search(r"\b(news|headlines?)\b", low):
            return None
        if re.search(r"\b(latest|trending|top)\b", low) and not any(c in low for c in _NEWS_CATEGORIES):
            action = "trending" if "trending" in low else "latest_news"
            return Route(True, "news", action, {}, 0.85, "latest/trending news → News Hand")
        # Category detection.
        category_map = {
            "artificial intelligence": "ai", "ai": "ai", "tech": "technology",
            "technology": "technology", "business": "business", "sport": "sports",
            "sports": "sports", "finance": "finance", "science": "science",
            "world": "world", "health": "health", "entertainment": "entertainment",
        }
        for kw, cat in category_map.items():
            if re.search(rf"\b{re.escape(kw)}\b", low):
                return Route(True, "news", "by_category", {"category": cat}, 0.85,
                             f"{cat} news → News Hand")
        return Route(True, "news", "latest_news", {}, 0.7, "news → News Hand")

    def _rule_filesystem(self, raw: str, low: str) -> Optional[Route]:
        """File/folder operations → File System Hand."""
        if re.search(r"\b(list|read|show|open)\b.*\b(folder|directory|dir)\b", low):
            path = self._path_after(raw)
            return Route(True, "filesystem", "list_directory",
                         {"path": path} if path else {"path": "."}, 0.8,
                         "list folder → File System Hand")
        m = re.search(r"\bread\s+(?:the\s+)?file\s+(.+)$", raw, re.I)
        if m:
            return Route(True, "filesystem", "read_file", {"path": m.group(1).strip()},
                         0.85, "read file → File System Hand")
        m = re.search(r"\b(?:create|make)\s+(?:a\s+)?(?:folder|directory)\s+(.+)$", raw, re.I)
        if m:
            return Route(True, "filesystem", "create_folder", {"path": m.group(1).strip()},
                         0.85, "create folder → File System Hand")
        m = re.search(r"\bsearch\s+(?:for\s+)?files?\b", low)
        if m:
            return Route(True, "filesystem", "search_files", {}, 0.6,
                         "search files → File System Hand")
        return None

    @staticmethod
    def _path_after(raw: str) -> str:
        """Extract a path following folder/directory keywords."""
        m = re.search(r"\b(?:folder|directory|dir)\s+(?:at\s+|named\s+|called\s+)?(.+)$", raw, re.I)
        if m:
            cand = m.group(1).strip(" ?.!")
            if cand and cand.lower() not in ("this", "here", "current"):
                return cand
        return ""

    def _rule_vision(self, raw: str, low: str) -> Optional[Route]:
        """Screen / screenshot / popup analysis → Vision Hand."""
        if re.search(r"\b(screenshot|screen shot)\b", low) or \
           re.search(r"\b(what.?s|analyze|analyse|look at|describe).*\bscreen\b", low):
            return Route(True, "vision", "screenshot_analysis", {}, 0.8,
                         "screen analysis → Vision Hand")
        if re.search(r"\b(popup|pop-up|dialog|dialogue)\b", low):
            return Route(True, "vision", "popup_detection", {}, 0.8,
                         "popup detection → Vision Hand")
        return None

    def _rule_youtube(self, raw: str, low: str) -> Optional[Route]:
        """Playback / 'on youtube' → YouTube Hand."""
        if "youtube" not in low:
            return None
        m = re.search(r"\bplay\s+(.+?)\s+(?:on|in)\s+youtube\b", raw, re.I) or \
            re.search(r"\byoutube\s+play\s+(.+)$", raw, re.I)
        if m:
            return Route(True, "youtube", "open_video", {"query": m.group(1).strip(" ?.!")},
                         0.85, "play on YouTube → YouTube Hand")
        m = re.search(r"\bsearch\s+(.+?)\s+on\s+youtube\b", raw, re.I)
        if m:
            return Route(True, "youtube", "search_videos", {"query": m.group(1).strip(" ?.!")},
                         0.85, "search YouTube → YouTube Hand")
        for word, action in (("pause", "pause"), ("play", "play"), ("mute", "volume"),
                             ("fullscreen", "fullscreen")):
            if re.search(rf"\b{word}\b", low):
                return Route(True, "youtube", action, {}, 0.6, f"youtube {action} → YouTube Hand")
        return None


# ── Module-level singleton + convenience ─────────────────────────────
_ROUTER: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """Process-wide singleton Intent Router."""
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = IntentRouter()
    return _ROUTER


def route_intent(text: str) -> Dict[str, Any]:
    """Convenience: route a request using the singleton router."""
    return get_intent_router().route(text)
