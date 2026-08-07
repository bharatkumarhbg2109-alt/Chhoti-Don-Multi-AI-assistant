"""
Chhoti Don - Hands Layer :: News Hand

Headlines by category using Google News RSS (free, no API key). Categories map
to Google News topic feeds where they exist, and to search feeds otherwise
(finance, AI). Summarization reuses the project's existing local model
(core.local_model_engine / Ollama via the main model) and falls back to a
simple extractive summary when the model is offline — it never crashes.

    tm.execute("news", "latest_news", {"limit": 5})
    tm.execute("news", "technology", {})
    tm.execute("news", "ai", {})
    tm.execute("news", "summarize", {"text": "..."})
"""

from __future__ import annotations

import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission

# ── Provider (single place to configure) ─────────────────────────────
_RSS_BASE = os.environ.get("CHHOTI_DON_NEWS_RSS", "https://news.google.com/rss")
_NEWS_LANG = os.environ.get("CHHOTI_DON_NEWS_LANG", "en")
_NEWS_COUNTRY = os.environ.get("CHHOTI_DON_NEWS_COUNTRY", "US")
_HTTP_TIMEOUT = float(os.environ.get("CHHOTI_DON_NEWS_TIMEOUT", "10"))

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}

# Google News topic sections that have a direct feed.
_TOPICS: Dict[str, str] = {
    "technology": "TECHNOLOGY",
    "business": "BUSINESS",
    "sports": "SPORTS",
    "science": "SCIENCE",
    "health": "HEALTH",
    "entertainment": "ENTERTAINMENT",
    "world": "WORLD",
    "nation": "NATION",
}

# Categories without a direct topic feed → resolved via a search feed.
_SEARCH_CATEGORIES: Dict[str, str] = {
    "finance": "finance OR stock market OR economy",
    "ai": "artificial intelligence OR machine learning",
}


class NewsHand(BaseHand):
    """Latest headlines by category, plus summarization."""

    name = "news"
    description = "Latest news headlines by category (Google News RSS) with summarization."
    dependencies = ["requests"]

    def __init__(self) -> None:
        super().__init__()
        R = Permission.READ_ONLY
        self.register("latest_news", self.latest_news, permission=R, doc="Top / latest headlines.")
        self.register("trending", self.trending, permission=R, doc="Trending top stories.")
        self.register("technology", lambda **k: self.by_category(category="technology", **k), permission=R, doc="Technology news.")
        self.register("business", lambda **k: self.by_category(category="business", **k), permission=R, doc="Business news.")
        self.register("sports", lambda **k: self.by_category(category="sports", **k), permission=R, doc="Sports news.")
        self.register("finance", lambda **k: self.by_category(category="finance", **k), permission=R, doc="Finance / markets news.")
        self.register("science", lambda **k: self.by_category(category="science", **k), permission=R, doc="Science news.")
        self.register("ai", lambda **k: self.by_category(category="ai", **k), permission=R, doc="Artificial-intelligence news.")
        self.register("by_category", self.by_category, permission=R, doc="News for a named category.")
        self.register("search_news", self.search_news, permission=R, doc="Search news by free-text query.")
        self.register("summarize", self.summarize, permission=R, doc="Summarize text or a list of headlines.")
        self.register("categories", self.categories, permission=R, doc="List supported news categories.")

    # ── RSS plumbing ─────────────────────────────────────────
    def _ceid(self) -> Dict[str, str]:
        """Google News localization query params."""
        return {"hl": _NEWS_LANG, "gl": _NEWS_COUNTRY, "ceid": f"{_NEWS_COUNTRY}:{_NEWS_LANG}"}

    def _fetch_rss(self, url: str, limit: int) -> List[Dict[str, str]]:
        """Fetch and parse a Google News RSS feed into a list of items."""
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers=_HEADERS, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        # Prefer the XML parser; fall back to html.parser if lxml is absent.
        try:
            soup = BeautifulSoup(resp.text, "xml")
        except Exception:
            soup = BeautifulSoup(resp.text, "html.parser")

        items: List[Dict[str, str]] = []
        for node in soup.find_all("item")[:limit]:
            title_el = node.find("title")
            link_el = node.find("link")
            date_el = node.find("pubDate")
            source_el = node.find("source")
            # html.parser treats <link> as void; recover the URL from text/guid.
            link = ""
            if link_el is not None:
                link = link_el.get_text(strip=True) or (link_el.next_sibling or "")
            if not link:
                guid = node.find("guid")
                link = guid.get_text(strip=True) if guid else ""
            items.append({
                "title": title_el.get_text(strip=True) if title_el else "",
                "url": str(link).strip(),
                "published": date_el.get_text(strip=True) if date_el else "",
                "source": source_el.get_text(strip=True) if source_el else "",
            })
        return items

    def _topic_url(self, topic: str) -> str:
        qs = urllib.parse.urlencode(self._ceid())
        return f"{_RSS_BASE}/headlines/section/topic/{topic}?{qs}"

    def _search_url(self, query: str) -> str:
        params = {"q": query}
        params.update(self._ceid())
        return f"{_RSS_BASE}/search?{urllib.parse.urlencode(params)}"

    def _top_url(self) -> str:
        return f"{_RSS_BASE}?{urllib.parse.urlencode(self._ceid())}"

    # ── Capabilities ─────────────────────────────────────────
    def latest_news(self, limit: int = 10) -> Dict[str, Any]:
        """Return the latest top-story headlines."""
        items = self._fetch_rss(self._top_url(), limit)
        return {"category": "top", "count": len(items), "articles": items}

    def trending(self, limit: int = 10) -> Dict[str, Any]:
        """Alias for the top-stories feed (trending)."""
        items = self._fetch_rss(self._top_url(), limit)
        return {"category": "trending", "count": len(items), "articles": items}

    def by_category(self, category: str = "top", limit: int = 10) -> Dict[str, Any]:
        """Return headlines for a named category."""
        cat = (category or "top").strip().lower()
        if cat in ("top", "trending", "latest"):
            return self.latest_news(limit=limit)
        if cat in _TOPICS:
            items = self._fetch_rss(self._topic_url(_TOPICS[cat]), limit)
        elif cat in _SEARCH_CATEGORIES:
            items = self._fetch_rss(self._search_url(_SEARCH_CATEGORIES[cat]), limit)
        else:
            raise ValueError(f"Unknown category {category!r}. Options: {self._all_categories()}")
        return {"category": cat, "count": len(items), "articles": items}

    def search_news(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search news headlines by free-text query."""
        if not query or not str(query).strip():
            raise ValueError("query is required")
        items = self._fetch_rss(self._search_url(query), limit)
        return {"query": query, "count": len(items), "articles": items}

    def _all_categories(self) -> List[str]:
        return ["top", "trending"] + sorted(set(_TOPICS) | set(_SEARCH_CATEGORIES))

    def categories(self) -> Dict[str, Any]:
        """List the supported news categories."""
        return {"categories": self._all_categories()}

    # ── Summarization (reuses the existing local model) ──────
    def summarize(self, text: str = "", articles: Optional[List[Dict[str, Any]]] = None,
                  max_sentences: int = 3) -> Dict[str, Any]:
        """Summarize free text or a list of headline dicts.

        Uses the configured main model via core.local_model_engine when Ollama
        is reachable; otherwise returns a lightweight extractive summary.
        """
        body = text or ""
        if not body and articles:
            body = ". ".join(a.get("title", "") for a in articles if a.get("title"))
        if not body.strip():
            raise ValueError("Provide 'text' or 'articles' to summarize.")

        llm = self._summarize_with_model(body, max_sentences)
        if llm is not None:
            return {"engine": "local_model", "summary": llm}
        return {"engine": "extractive", "summary": self._extractive(body, max_sentences)}

    @staticmethod
    def _summarize_with_model(body: str, max_sentences: int) -> Optional[str]:
        """Try the local main model; return None if unavailable/offline."""
        try:
            from core import model_router
            from core.local_model_engine import execute as run_model

            status = model_router.check_model(model_router.MAIN_MODEL)
            if not status.get("available"):
                return None
            prompt = (
                f"Summarize the following news in at most {max_sentences} concise "
                f"sentences. Be factual and neutral.\n\n{body[:6000]}"
            )
            out = run_model({"model": model_router.MAIN_MODEL, "temperature": 0.3}, prompt)
            if out and not out.startswith("❌"):  # engine returns ❌-prefixed errors
                return out.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def _extractive(body: str, max_sentences: int) -> str:
        """Offline fallback: first N sentences, whitespace-normalized."""
        sentences = re.split(r"(?<=[.!?])\s+", body.strip())
        picked = [s.strip() for s in sentences if s.strip()][:max(1, max_sentences)]
        return " ".join(picked)
