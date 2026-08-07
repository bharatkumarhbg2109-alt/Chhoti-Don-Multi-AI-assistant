"""Raw blocking browser operations. Only browser.guarded may import this module."""

from typing import Any, Dict

from ddgs import DDGS
import trafilatura

from .config import MAX_CONTENT_CHARS


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Return DDGS links and snippets only; never synthesize an answer."""
    if not isinstance(query, str) or not query.strip():
        return {"status": "error", "marker": "INVALID_QUERY", "results": []}
    try:
        results = DDGS().text(
            query.strip(),
            region="in-en",
            safesearch="moderate",
            backend="auto",
            max_results=max(1, min(int(max_results), 10)),
        )
        return {
            "status": "success",
            "query": query.strip(),
            "results": [
                {"title": item.get("title", ""), "url": item.get("href", ""), "snippet": item.get("body", "")}
                for item in (results or [])
                if item.get("href")
            ],
        }
    except Exception as exc:
        return {"status": "error", "marker": "SEARCH_FAILED", "message": str(exc), "results": []}


def open_page(url: str) -> Dict[str, Any]:
    """Fetch and extract readable page text, returning markers instead of raising."""
    try:
        downloaded = trafilatura.fetch_url(url)
    except Exception as exc:
        return {"status": "error", "marker": "FETCH_FAILED", "url": url, "message": str(exc)}
    if not downloaded:
        return {"status": "error", "marker": "FETCH_FAILED", "url": url}
    try:
        text = trafilatura.extract(downloaded, include_links=True, output_format="txt")
    except Exception as exc:
        return {"status": "error", "marker": "NO_CONTENT", "url": url, "message": str(exc)}
    if not text or not text.strip():
        return {"status": "error", "marker": "NO_CONTENT", "url": url}
    return {
        "status": "success",
        "url": url,
        "content": text.strip()[:MAX_CONTENT_CHARS],
        "truncated": len(text.strip()) > MAX_CONTENT_CHARS,
        "content_is_untrusted": True,
    }
