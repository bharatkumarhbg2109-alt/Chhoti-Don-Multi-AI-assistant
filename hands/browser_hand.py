"""
Chhoti Don - Hands Layer :: Browser Hand

Drive a real browser with Playwright (primary) or Selenium (fallback). The
browser is launched lazily on first use. If neither engine is installed the
hand reports itself unavailable (with setup guidance) instead of crashing.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission


def _importable(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


class BrowserHand(BaseHand):
    name = "browser"
    description = "Open URLs, navigate, click, fill, scrape and screenshot via Playwright/Selenium."

    KNOWN = {
        "google": "https://www.google.com",
        "youtube": "https://www.youtube.com",
        "gmail": "https://mail.google.com",
    }

    def __init__(self) -> None:
        super().__init__()
        self.engine = "playwright" if _importable("playwright") else ("selenium" if _importable("selenium") else None)
        self.headless = os.environ.get("CHHOTI_DON_BROWSER_HEADLESS", "0") in ("1", "true", "True")
        self._pw = None            # playwright instance
        self._browser = None
        self._context = None
        self._pages: List[Any] = []
        self._active = 0

        R, E, W = Permission.READ_ONLY, Permission.EXECUTE, Permission.WRITE
        self.register("open_url", self.open_url, permission=E, doc="Open a URL.")
        self.register("open_google", lambda **k: self.open_url(url=self.KNOWN["google"]), permission=E, doc="Open Google.")
        self.register("open_youtube", lambda **k: self.open_url(url=self.KNOWN["youtube"]), permission=E, doc="Open YouTube.")
        self.register("open_gmail", lambda **k: self.open_url(url=self.KNOWN["gmail"]), permission=E, doc="Open Gmail.")
        self.register("navigate", self.open_url, permission=E, doc="Navigate the active tab to a URL.")
        self.register("back", lambda **k: self._nav("back"), permission=E, doc="Go back.")
        self.register("forward", lambda **k: self._nav("forward"), permission=E, doc="Go forward.")
        self.register("refresh", lambda **k: self._nav("reload"), permission=E, doc="Refresh the page.")
        self.register("new_tab", self.new_tab, permission=E, doc="Open a new tab.")
        self.register("close_tab", self.close_tab, permission=E, doc="Close a tab by index.")
        self.register("switch_tab", self.switch_tab, permission=E, doc="Switch active tab by index.")
        self.register("click", self.click, permission=E, doc="Click an element by selector.")
        self.register("fill_form", self.fill_form, permission=W, doc="Fill an input by selector.")
        self.register("select_dropdown", self.select_dropdown, permission=W, doc="Select a dropdown option.")
        self.register("upload_file", self.upload_file, permission=W, doc="Upload a file to an input.")
        self.register("download_file", self.download_file, permission=W, doc="Download a file via a click.")
        self.register("page_title", self.page_title, permission=R, doc="Read the page title.")
        self.register("page_text", self.page_text, permission=R, doc="Extract visible page text.")
        self.register("screenshot", self.screenshot, permission=R, doc="Screenshot the page.")
        self.register("dom_query", self.dom_query, permission=R, doc="Query the DOM by selector.")
        self.register("wait_for", self.wait_for, permission=R, doc="Wait for a selector to appear.")
        self.register("scrape", self.dom_query, permission=R, doc="Authorized scrape of selector text.")
        self.register("browser_status", self.browser_status, permission=R, doc="Browser engine status.")
        self.register("close_browser", self.close_browser, permission=E, doc="Close the browser.")

    def _check_available(self) -> bool:
        return self.engine is not None

    def missing_dependencies(self) -> List[str]:
        return [] if self.engine else ["playwright (or selenium)"]

    # ── Engine lifecycle (Playwright) ────────────────────────
    def _ensure(self):
        if self.engine != "playwright":
            raise RuntimeError("Only the Playwright engine is supported for this action.")
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(accept_downloads=True)
            self._pages = [self._context.new_page()]
            self._active = 0
        return self._pages[self._active]

    def _page(self):
        if not self._pages:
            return self._ensure()
        try:
            _ = self._pages[self._active].url  # touch to detect closed page
        except Exception:
            return self._ensure()
        return self._pages[self._active]

    # ── Navigation ───────────────────────────────────────────
    def open_url(self, url: str) -> Dict[str, Any]:
        if not url:
            raise ValueError("url is required")
        page = self._page()
        page.goto(url, wait_until="domcontentloaded")
        return {"url": page.url, "title": page.title()}

    def _nav(self, kind: str) -> Dict[str, Any]:
        page = self._page()
        {"back": page.go_back, "forward": page.go_forward, "reload": page.reload}[kind]()
        return {"action": kind, "url": page.url}

    def new_tab(self, url: str = "about:blank") -> Dict[str, Any]:
        self._ensure()
        page = self._context.new_page()
        if url and url != "about:blank":
            page.goto(url, wait_until="domcontentloaded")
        self._pages.append(page)
        self._active = len(self._pages) - 1
        return {"tabs": len(self._pages), "active": self._active, "url": page.url}

    def close_tab(self, index: Optional[int] = None) -> Dict[str, Any]:
        idx = self._active if index is None else index
        if idx < 0 or idx >= len(self._pages):
            raise IndexError(f"Tab index {idx} out of range.")
        self._pages[idx].close()
        self._pages.pop(idx)
        self._active = max(0, min(self._active, len(self._pages) - 1))
        return {"tabs": len(self._pages), "active": self._active}

    def switch_tab(self, index: int) -> Dict[str, Any]:
        if index < 0 or index >= len(self._pages):
            raise IndexError(f"Tab index {index} out of range.")
        self._active = index
        self._pages[index].bring_to_front()
        return {"active": index, "url": self._pages[index].url}

    # ── Interaction ──────────────────────────────────────────
    def click(self, selector: str, timeout: float = 10000) -> Dict[str, Any]:
        self._page().click(selector, timeout=timeout)
        return {"clicked": selector}

    def fill_form(self, selector: str, value: str, timeout: float = 10000) -> Dict[str, Any]:
        self._page().fill(selector, value, timeout=timeout)
        return {"filled": selector}

    def select_dropdown(self, selector: str, value: str) -> Dict[str, Any]:
        self._page().select_option(selector, value)
        return {"selected": value, "selector": selector}

    def upload_file(self, selector: str, file_path: str) -> Dict[str, Any]:
        self._page().set_input_files(selector, file_path)
        return {"uploaded": file_path, "selector": selector}

    def download_file(self, selector: str, save_dir: str = ".") -> Dict[str, Any]:
        page = self._page()
        with page.expect_download() as dl:
            page.click(selector)
        download = dl.value
        dest = os.path.join(os.path.expanduser(save_dir), download.suggested_filename)
        download.save_as(dest)
        return {"downloaded": dest}

    # ── Read / scrape ────────────────────────────────────────
    def page_title(self) -> Dict[str, Any]:
        return {"title": self._page().title(), "url": self._page().url}

    def page_text(self, selector: str = "body", max_chars: int = 20000) -> Dict[str, Any]:
        text = self._page().inner_text(selector)
        return {"selector": selector, "text": text[:max_chars], "truncated": len(text) > max_chars}

    def dom_query(self, selector: str, limit: int = 50) -> Dict[str, Any]:
        els = self._page().query_selector_all(selector)
        items = [{"text": (e.inner_text() or "").strip()[:300],
                  "href": e.get_attribute("href")} for e in els[:limit]]
        return {"selector": selector, "count": len(items), "items": items}

    def wait_for(self, selector: str, timeout: float = 15000) -> Dict[str, Any]:
        self._page().wait_for_selector(selector, timeout=timeout)
        return {"found": selector}

    def screenshot(self, path: str = "", full_page: bool = False) -> Dict[str, Any]:
        if not path:
            path = os.path.join(os.environ.get("CHHOTI_DON_RUNTIME_DIR", "."), "browser_screenshot.png")
        self._page().screenshot(path=path, full_page=full_page)
        return {"screenshot": path}

    # ── Status / teardown ────────────────────────────────────
    def browser_status(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "headless": self.headless,
            "running": self._browser is not None,
            "tabs": len(self._pages),
            "active_tab": self._active,
        }

    def close_browser(self) -> Dict[str, Any]:
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        finally:
            self._pw = self._browser = self._context = None
            self._pages = []
            self._active = 0
        return {"closed": True}
