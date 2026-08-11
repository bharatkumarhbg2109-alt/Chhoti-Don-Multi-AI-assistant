"""Guarded, keyless web-search and page-reading capabilities.

Two complementary read-only layers, both behind the same Guardian gate:
  * ddgs + trafilatura (search.py)      -> cheap static-page search + read
  * Playwright headed browser (session) -> JS-heavy / render-required reads
See routing.py for when to prefer which.
"""

from .guarded import (
    open_page, web_search,
    browser_navigate, browser_read, browser_get_content,
)
from .routing import should_use_browser, is_browser_research_request
from .agent import BrowserResearchAgent, run_research

__all__ = [
    "web_search", "open_page",
    "browser_navigate", "browser_read", "browser_get_content",
    "should_use_browser", "is_browser_research_request",
    "BrowserResearchAgent", "run_research",
]
