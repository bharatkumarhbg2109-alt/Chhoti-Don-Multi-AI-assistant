"""Routing rule: when to use the Playwright browser vs the cheap static path.

Phase 1 is DETERMINISTIC — no LLM decision loop. This module documents and
encodes the single routing rule; it does NOT hook itself into the chat pipeline
(that stays untouched this phase). A later phase's agent loop, or an explicit
tool call, consults ``should_use_browser`` to choose a path.

ROUTING RULE
------------
Prefer the EXISTING cheap path (browser.open_page / web_search = ddgs +
trafilatura) for ordinary static/simple pages — it is far cheaper (a plain HTTP
fetch, no browser process).

Use the Playwright browser (browser.browser_read / browser_navigate /
browser_get_content) ONLY when:
  1. the user EXPLICITLY asks the assistant to open the browser
     ("open the browser", "browser me kholo", "browser kholke dekho", "render it"),
     OR
  2. the static path cannot render the page — i.e. trafilatura returned a
     FETCH_FAILED / NO_CONTENT marker, which is the signal of a JS-heavy /
     interaction-required page.

The two layers are COMPLEMENTARY; this never duplicates the existing search.
"""

from __future__ import annotations

# Explicit "open the browser" phrasings (English + Hinglish).
_EXPLICIT_BROWSER_PHRASES = (
    "open the browser", "open a browser", "open browser", "in the browser",
    "use the browser", "browser me khol", "browser mein khol", "browser kholo",
    "browser kholke", "browser khol ke", "browser open karo", "render the page",
    "render it", "use playwright", "headed browser", "browser se dekho",
)


def user_requested_browser(text: str) -> bool:
    """True if the user EXPLICITLY asked for the real browser (rule #1)."""
    t = (text or "").lower()
    return any(phrase in t for phrase in _EXPLICIT_BROWSER_PHRASES)


# Phase 2 chat trigger: fire the multi-step research agent ONLY on an explicit
# request to use the browser. Deliberately STRICT so ordinary chat never diverts —
# these exact phrases don't occur in normal questions. (Distinct from
# user_requested_browser, which is broader and includes "render it".)
_RESEARCH_TRIGGERS = (
    "open the browser", "open a browser", "use the browser to", "using the browser",
    "browser me khol", "browser mein khol", "browser kholo", "browser kholke",
    "browser khol ke", "browser se dhoond", "browser se search", "browser se research",
    "research using the browser", "browse the web for", "browser se pata",
)


def is_browser_research_request(text: str) -> bool:
    """True only when the user EXPLICITLY asks to use the browser to research.

    This is the documented, opt-in trigger for the Phase-2 agent loop. It is
    intentionally narrow: ordinary chat/coding/RAG messages never match, so the
    default chat path is byte-for-byte unchanged for everything else.
    """
    t = (text or "").lower()
    return any(phrase in t for phrase in _RESEARCH_TRIGGERS)


def should_use_browser(text: str = "", static_result: dict | None = None) -> bool:
    """Encode the routing rule. Returns True when the Playwright browser should be
    used instead of the cheap static path.

    Args:
        text:          the user's message (checked for an explicit browser ask).
        static_result: an optional prior result from browser.open_page; if it
                       failed to render (FETCH_FAILED / NO_CONTENT), fall back to
                       the browser (rule #2).
    """
    if user_requested_browser(text):
        return True
    if isinstance(static_result, dict) and static_result.get("status") == "error":
        if static_result.get("marker") in {"FETCH_FAILED", "NO_CONTENT"}:
            return True
    return False
