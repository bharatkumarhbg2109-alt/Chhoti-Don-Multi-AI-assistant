"""Raw Playwright browser session — headed, READ-ONLY.

Only ``browser.guarded`` may import this module (same rule as ``browser.search``):
every entry point here is reached through the Guardian choke point in guarded.py.

PHASE 1 READ-ONLY INVARIANT
---------------------------
This module performs ONLY navigation and content extraction. There is NO method
to click, type, fill, press keys, submit forms, drag, upload, download, or change
any page/site state. Interaction methods are intentionally absent and must not be
added here — they belong to a later phase behind a human-in-the-loop confirmation
gate (see browser/guarded.py::_gate and the REQUIRE_CONFIRMATION hook).
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List, Optional

from .config import (
    BROWSER_HEADLESS, USER_DATA_DIR, NAV_TIMEOUT_MS,
    NETWORK_IDLE_TIMEOUT_MS, OPERATION_TIMEOUT_MS, MAX_CONTENT_CHARS,
)


class PlaywrightNotInstalled(RuntimeError):
    """Raised when the optional Playwright dependency / browser isn't available."""


# JS that returns clean, main readable text: clone the body, strip chrome/ads/
# interactive boilerplate, prefer <main>/<article>, and return innerText (which
# already omits hidden nodes, script and style). Read-only DOM inspection.
_READABLE_JS = """() => {
  const clone = document.body ? document.body.cloneNode(true) : null;
  if (!clone) return "";
  clone.querySelectorAll(
    'script,style,noscript,template,nav,header,footer,aside,form,iframe,svg,button,[aria-hidden="true"]'
  ).forEach(el => el.remove());
  const main = clone.querySelector('main,article,[role="main"]') || clone;
  return main.innerText || "";
}"""

_WS_RE = re.compile(r"[ \t\f\v]+")
_NL_RE = re.compile(r"\n{3,}")


def _collapse_ws(text: str) -> str:
    if not text:
        return ""
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _a11y_to_markdown(node: Optional[Dict[str, Any]], depth: int = 0,
                      out: Optional[List[str]] = None) -> str:
    """Convert a Playwright accessibility snapshot into a compact markdown outline.

    Prefers the accessibility tree over raw HTML for token efficiency: only nodes
    with a real accessible name are emitted, headings become '#'-prefixed, and
    interactive roles are tagged so the assistant can reason about them WITHOUT a
    full DOM dump. (Tagging a link/button here is inspection only — Phase 1 never
    acts on them.)
    """
    if out is None:
        out = []
    if not node:
        return ""
    role = (node.get("role") or "").strip()
    name = (node.get("name") or "").strip()
    if name:
        indent = "  " * max(depth - 1, 0)
        if role == "heading":
            level = int(node.get("level") or 2)
            out.append("#" * min(max(level, 1), 6) + " " + name)
        elif role in ("link", "button", "textbox", "checkbox", "radio", "tab",
                      "menuitem", "combobox", "searchbox"):
            out.append(f"{indent}- [{role}] {name}")
        elif role in ("listitem", "cell", "row", "paragraph", "text",
                      "StaticText", "generic", "article", "main"):
            out.append(f"{indent}{name}")
        else:
            out.append(f"{indent}{role + ': ' if role else ''}{name}")
    for child in (node.get("children") or []):
        _a11y_to_markdown(child, depth + 1, out)
    return "\n".join(line for line in out if line.strip())


class BrowserSession:
    """Async, headed-by-default Playwright wrapper with a clean lifecycle.

    launch() -> navigate() / get_page_content() / extract_text() / screenshot()
    -> close(). READ-ONLY: no interaction methods are provided.
    """

    def __init__(self, headless: Optional[bool] = None,
                 user_data_dir: Optional[str] = None):
        self.headless = BROWSER_HEADLESS if headless is None else headless
        self.user_data_dir = user_data_dir or USER_DATA_DIR
        self._pw = None
        self._context = None
        self._page = None

    # ── Lifecycle ────────────────────────────────────────────────────────────
    async def launch(self) -> "BrowserSession":
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # optional dependency not installed
            raise PlaywrightNotInstalled(
                "Playwright is not installed. Run: pip install playwright && "
                "python -m playwright install chromium"
            ) from exc

        os.makedirs(self.user_data_dir, exist_ok=True)
        self._pw = await async_playwright().start()
        try:
            # Persistent context reserves a profile dir for later phases (NO login
            # this phase). Headed by default so the user sees the window open.
            self._context = await self._pw.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=self.headless,
                args=["--no-first-run", "--no-default-browser-check"],
            )
        except Exception as exc:
            await self._safe_stop_pw()
            raise PlaywrightNotInstalled(
                f"Chromium failed to launch ({exc}). Run: python -m playwright install chromium"
            ) from exc

        self._context.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        self._context.set_default_timeout(NAV_TIMEOUT_MS)
        self._page = (self._context.pages[0] if self._context.pages
                      else await self._context.new_page())
        return self

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Go to a URL, then wait (bounded) for network idle. Returns title + final URL."""
        resp = await self._page.goto(url, wait_until="domcontentloaded",
                                     timeout=NAV_TIMEOUT_MS)
        try:
            # Best-effort: chatty pages (analytics/websockets) may never idle, so
            # this is bounded and its timeout is swallowed — never a hard hang.
            await self._page.wait_for_load_state("networkidle",
                                                 timeout=NETWORK_IDLE_TIMEOUT_MS)
        except Exception:
            pass
        return {
            "title": (await self._page.title()) or "",
            "url": self._page.url,
            "status_code": resp.status if resp else None,
        }

    async def get_page_content(self) -> str:
        """Accessibility tree -> compact outline (token-efficient, not a full DOM dump)."""
        # Modern Playwright (>=1.49): aria_snapshot() returns a compact YAML ARIA
        # tree — exactly the token-efficient accessibility view we want.
        try:
            outline = await self._page.locator("body").aria_snapshot()
            if outline and outline.strip():
                return outline.strip()[:MAX_CONTENT_CHARS]
        except Exception:
            pass
        # Fallback for older Playwright that still exposes page.accessibility.
        try:
            snapshot = await self._page.accessibility.snapshot(interesting_only=True)
            return _a11y_to_markdown(snapshot)[:MAX_CONTENT_CHARS]
        except Exception:
            return ""

    async def extract_text(self) -> str:
        """Main readable text of the current page (nav/ads/boilerplate stripped)."""
        try:
            raw = await self._page.evaluate(_READABLE_JS)
        except Exception:
            raw = await self._page.inner_text("body")
        return _collapse_ws(raw or "")[:MAX_CONTENT_CHARS]

    async def screenshot(self, path: str) -> str:
        """Save a viewport screenshot to ``path`` (read-only capture)."""
        await self._page.screenshot(path=path, full_page=False)
        return path

    async def close(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        except Exception:
            pass
        finally:
            await self._safe_stop_pw()
            self._page = self._context = None

    async def _safe_stop_pw(self) -> None:
        try:
            if self._pw is not None:
                await self._pw.stop()
        except Exception:
            pass
        finally:
            self._pw = None


# ── Sync one-shot helpers (raw) ───────────────────────────────────────────────
# The registry tools are synchronous callables; these drive the async session in
# a fresh event loop, fully bounded by OPERATION_TIMEOUT_MS so nothing can hang.
def _run(coro):
    # On Windows, asyncio.new_event_loop() yields a ProactorEventLoop under the
    # default policy, which Playwright requires for its subprocess transport.
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        asyncio.set_event_loop(None)
        loop.close()


async def _read_async(url: str, headless: Optional[bool], want_a11y: bool,
                      want_text: bool) -> Dict[str, Any]:
    session = BrowserSession(headless=headless)
    try:
        await session.launch()
        nav = await session.navigate(url)
        text = await session.extract_text() if want_text else None
        outline = await session.get_page_content() if want_a11y else None
        return {"nav": nav, "text": text, "outline": outline}
    finally:
        await session.close()


def _one_shot(url: str, headless: Optional[bool], want_a11y: bool,
              want_text: bool) -> Dict[str, Any]:
    timeout_s = OPERATION_TIMEOUT_MS / 1000.0
    try:
        result = _run(asyncio.wait_for(
            _read_async(url, headless, want_a11y, want_text), timeout=timeout_s))
    except PlaywrightNotInstalled as exc:
        return {"status": "error", "marker": "PLAYWRIGHT_NOT_INSTALLED",
                "url": url, "message": str(exc)}
    except asyncio.TimeoutError:
        return {"status": "error", "marker": "PAGE_TIMEOUT", "url": url,
                "message": f"Operation exceeded {timeout_s:.0f}s."}
    except Exception as exc:
        return {"status": "error", "marker": "BROWSER_FAILED", "url": url,
                "message": str(exc)}
    return {"status": "success", **result}


def navigate(url: str, headless: Optional[bool] = None) -> Dict[str, Any]:
    """One-shot navigate: open -> go -> return title/final URL -> close."""
    res = _one_shot(url, headless, want_a11y=False, want_text=False)
    if res.get("status") != "success":
        return res
    nav = res["nav"]
    return {"status": "success", "url": nav["url"], "title": nav["title"],
            "status_code": nav.get("status_code"), "render": "playwright"}


def read_page(url: str, headless: Optional[bool] = None) -> Dict[str, Any]:
    """One-shot research read: open -> go -> extract clean text -> close.

    Returns the same content shape as the trafilatura open_page tool so the
    existing app formatter treats it identically (content is untrusted data).
    """
    res = _one_shot(url, headless, want_a11y=False, want_text=True)
    if res.get("status") != "success":
        return res
    nav, text = res["nav"], (res.get("text") or "")
    if not text.strip():
        return {"status": "error", "marker": "NO_CONTENT", "url": nav["url"]}
    return {
        "status": "success",
        "url": nav["url"],
        "title": nav["title"],
        "content": text[:MAX_CONTENT_CHARS],
        "truncated": len(text) > MAX_CONTENT_CHARS,
        "content_is_untrusted": True,
        "render": "playwright",
    }


def get_content(url: str, headless: Optional[bool] = None) -> Dict[str, Any]:
    """One-shot accessibility-tree read: open -> go -> a11y outline -> close."""
    res = _one_shot(url, headless, want_a11y=True, want_text=False)
    if res.get("status") != "success":
        return res
    nav, outline = res["nav"], (res.get("outline") or "")
    if not outline.strip():
        return {"status": "error", "marker": "NO_CONTENT", "url": nav["url"]}
    return {
        "status": "success",
        "url": nav["url"],
        "title": nav["title"],
        "content": outline[:MAX_CONTENT_CHARS],
        "truncated": len(outline) > MAX_CONTENT_CHARS,
        "content_is_untrusted": True,
        "render": "playwright-accessibility",
    }
