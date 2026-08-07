"""
Chhoti Don - Hands Layer :: YouTube Hand

YouTube control on top of the shared Browser Hand (Playwright) — search, open,
playback control (keyboard shortcuts), volume/speed, and metadata reading.
Reuses the Browser Hand's engine rather than launching a second browser.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission
from .browser_hand import BrowserHand


class YouTubeHand(BaseHand):
    name = "youtube"
    description = "Search and control YouTube playback via the shared browser engine."

    def __init__(self, browser: Optional[BrowserHand] = None) -> None:
        super().__init__()
        self.browser = browser or BrowserHand()

        R, E = Permission.READ_ONLY, Permission.EXECUTE
        self.register("open_youtube", lambda **k: self.browser.open_url(url="https://www.youtube.com"), permission=E, doc="Open YouTube.")
        self.register("search_videos", self.search_videos, permission=E, doc="Search YouTube for a query.")
        self.register("open_video", self.open_video, permission=E, doc="Open a video by URL or first search result.")
        self.register("play", lambda **k: self._key("k"), permission=E, doc="Play (toggle).")
        self.register("pause", lambda **k: self._key("k"), permission=E, doc="Pause (toggle).")
        self.register("next", lambda **k: self._key("N", modifiers=["Shift"]), permission=E, doc="Next video.")
        self.register("previous", lambda **k: self._key("P", modifiers=["Shift"]), permission=E, doc="Previous video.")
        self.register("fullscreen", lambda **k: self._key("f"), permission=E, doc="Toggle fullscreen.")
        self.register("theater_mode", lambda **k: self._key("t"), permission=E, doc="Toggle theater mode.")
        self.register("volume", self.volume, permission=E, doc="Set volume 0..100.")
        self.register("playback_speed", self.playback_speed, permission=E, doc="Set playback speed, e.g. 1.5.")
        self.register("read_title", lambda **k: self._read("title"), permission=R, doc="Read the video title.")
        self.register("read_channel", lambda **k: self._read("channel"), permission=R, doc="Read the channel name.")
        self.register("read_description", lambda **k: self._read("description"), permission=R, doc="Read the description.")

    def _check_available(self) -> bool:
        return self.browser.is_available() and self.browser.engine == "playwright"

    def missing_dependencies(self) -> List[str]:
        return [] if self._check_available() else ["playwright"]

    # ── Helpers (reuse the browser engine) ───────────────────
    def _page(self):
        return self.browser._page()  # noqa: SLF001 - intentional reuse within the package

    def _key(self, key: str, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
        page = self._page()
        combo = "+".join((modifiers or []) + [key])
        page.keyboard.press(combo)
        return {"key": combo}

    def _read(self, what: str) -> Dict[str, Any]:
        page = self._page()
        selectors = {
            "title": ["h1.ytd-watch-metadata #title", "h1.title yt-formatted-string", "h1 .style-scope.ytd-watch-metadata"],
            "channel": ["#channel-name a", "ytd-channel-name a", "#owner #text a"],
            "description": ["#description-inline-expander", "#description", "ytd-text-inline-expander"],
        }[what]
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = (el.inner_text() or "").strip()
                    if text:
                        return {what: text}
            except Exception:
                continue
        return {what: None, "note": "Element not found (page may still be loading)."}

    # ── Actions ──────────────────────────────────────────────
    def search_videos(self, query: str) -> Dict[str, Any]:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        self.browser.open_url(url=url)
        return self.browser.dom_query(selector="a#video-title", limit=20)

    def open_video(self, url: str = "", query: str = "") -> Dict[str, Any]:
        if url:
            return self.browser.open_url(url=url)
        if query:
            self.search_videos(query=query)
            first = self._page().query_selector("a#video-title")
            if first:
                href = first.get_attribute("href")
                if href:
                    return self.browser.open_url(url="https://www.youtube.com" + href)
            return {"note": "No results to open."}
        raise ValueError("Provide a video 'url' or a 'query'.")

    def volume(self, level: int = 50) -> Dict[str, Any]:
        level = max(0, min(100, int(level)))
        self._page().evaluate(
            "(v) => { const el = document.querySelector('video'); if (el) el.volume = v/100; }", level
        )
        return {"volume": level}

    def playback_speed(self, rate: float = 1.0) -> Dict[str, Any]:
        self._page().evaluate(
            "(r) => { const el = document.querySelector('video'); if (el) el.playbackRate = r; }", float(rate)
        )
        return {"playback_speed": rate}
