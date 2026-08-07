"""
Chhoti Don - Hands Layer :: Browser Search Hand

Web search without API keys, using requests + BeautifulSoup. DuckDuckGo,
Wikipedia and Google-News provide reliable key-free results; Google/Bing HTML
are best-effort (they gracefully fall back to the search URL when scraping is
blocked). Purely local client — no cloud service accounts.
"""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Any, Dict, List

from .base import BaseHand, Permission

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}


class SearchHand(BaseHand):
    name = "search"
    description = "Web search (DuckDuckGo, Wikipedia, Bing, Google, News) and open results."
    dependencies = ["requests", "bs4"]

    def __init__(self) -> None:
        super().__init__()
        R, E = Permission.READ_ONLY, Permission.EXECUTE
        self.register("duckduckgo_search", self.duckduckgo_search, permission=R, doc="Search DuckDuckGo.")
        self.register("google_search", self.google_search, permission=R, doc="Search Google (best-effort).")
        self.register("bing_search", self.bing_search, permission=R, doc="Search Bing (best-effort).")
        self.register("wikipedia_search", self.wikipedia_search, permission=R, doc="Search Wikipedia.")
        self.register("news_search", self.news_search, permission=R, doc="Search news (Google News RSS).")
        self.register("extract_results", self.duckduckgo_search, permission=R, doc="Alias: extract search results.")
        self.register("open_result", self.open_result, permission=E, doc="Open a result URL in the default browser.")

    # ── DuckDuckGo (reliable, key-free) ──────────────────────
    def duckduckgo_search(self, query: str, limit: int = 8) -> Dict[str, Any]:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query}, headers=_HEADERS, timeout=8,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Dict[str, str]] = []
        for res in soup.select(".result__body, .web-result")[:limit]:
            a = res.select_one("a.result__a")
            if not a:
                continue
            href = a.get("href", "")
            # DuckDuckGo wraps links in a redirect with the real url in uddg=
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get("uddg", [href])[0]
            snippet_el = res.select_one(".result__snippet")
            results.append({
                "title": a.get_text(strip=True),
                "url": url,
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
        return {"engine": "duckduckgo", "query": query, "count": len(results), "results": results}

    # ── Wikipedia (reliable, key-free) ───────────────────────
    def wikipedia_search(self, query: str, limit: int = 6, lang: str = "en") -> Dict[str, Any]:
        import requests
        resp = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": query, "limit": limit, "format": "json"},
            headers=_HEADERS, timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        titles, descs, urls = data[1], data[2], data[3]
        results = [
            {"title": t, "snippet": d, "url": u}
            for t, d, u in zip(titles, descs, urls)
        ]
        return {"engine": "wikipedia", "query": query, "count": len(results), "results": results}

    # ── News (Google News RSS, key-free) ─────────────────────
    def news_search(self, query: str, limit: int = 8) -> Dict[str, Any]:
        import requests
        from bs4 import BeautifulSoup
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        results = []
        for item in soup.find_all("item")[:limit]:
            results.append({
                "title": item.title.get_text(strip=True) if item.title else "",
                "url": item.link.get_text(strip=True) if item.link else "",
                "published": item.pubDate.get_text(strip=True) if item.pubDate else "",
            })
        return {"engine": "google_news", "query": query, "count": len(results), "results": results}

    # ── Google / Bing (best-effort HTML) ─────────────────────
    def _best_effort(self, engine: str, url: str, selector: str, query: str, limit: int) -> Dict[str, Any]:
        import requests
        from bs4 import BeautifulSoup
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for a in soup.select(selector)[: limit * 3]:
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if href.startswith("http") and text and "google" not in href and "bing" not in href:
                    results.append({"title": text, "url": href, "snippet": ""})
                if len(results) >= limit:
                    break
            if results:
                return {"engine": engine, "query": query, "count": len(results), "results": results}
        except Exception as exc:  # scraping blocked / no network
            return {"engine": engine, "query": query, "count": 0, "results": [],
                    "note": f"Live results unavailable ({exc}). Use search_url.",
                    "search_url": url}
        return {"engine": engine, "query": query, "count": 0, "results": [],
                "note": "No parseable results (engine may block scraping).",
                "search_url": url}

    def google_search(self, query: str, limit: int = 8) -> Dict[str, Any]:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
        return self._best_effort("google", url, "a", query, limit)

    def bing_search(self, query: str, limit: int = 8) -> Dict[str, Any]:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        return self._best_effort("bing", url, "li.b_algo h2 a", query, limit)

    # ── Open a result ────────────────────────────────────────
    def open_result(self, url: str) -> Dict[str, Any]:
        if not url or not str(url).startswith("http"):
            raise ValueError("A valid http(s) 'url' is required.")
        opened = webbrowser.open(url)
        return {"url": url, "opened": bool(opened)}
