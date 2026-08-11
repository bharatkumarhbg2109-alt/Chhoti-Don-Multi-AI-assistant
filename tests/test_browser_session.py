"""Phase 1 browser-agent tests: guardian routing, read-only invariant, a11y
conversion, routing rule, and a real (headless) session lifecycle + extraction.

These are additive and hermetic: the guardian-routing tests mock the raw session
(no browser launched); the one live test uses a headless Chromium on a local
file:// page in a throwaway profile dir, and SKIPS cleanly if Chromium can't run.
"""

import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from browser import guarded, routing, session as bsession


class BrowserGuardianRoutingTests(unittest.TestCase):
    """Every browser tool call must pass through the Guardian gate."""

    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_browser_read_passes_through_guardian_and_logs_decision(self):
        with patch.object(guarded._raw_session, "read_page",
                          return_value={"status": "success", "url": "https://example.com",
                                        "content": "hi", "content_is_untrusted": True}) as raw:
            with self.assertLogs("chhoti.browser", level="INFO") as cm:
                result = guarded.browser_read({"url": "https://example.com/article"})
        self.assertEqual(result["status"], "success")
        raw.assert_called_once()
        logged = "\n".join(cm.output)
        # The risk decision is logged: low tier, auto-allow.
        self.assertIn("action=web_read", logged)
        self.assertIn("risk=low", logged)
        self.assertIn("requires_confirmation=False", logged)
        self.assertIn("decision=ALLOW", logged)

    def test_browser_read_low_risk_never_requires_confirmation(self):
        # web_-prefixed browser reads must be the LOW tier (no input() prompt).
        assessment = guarded._guardian.assess_action("web_read", "https://example.com")
        self.assertEqual(assessment["risk_level"], "low")
        self.assertFalse(assessment["requires_confirmation"])

    def test_blocked_domain_refused_before_browser_launch(self):
        with patch.object(guarded._raw_session, "read_page") as raw:
            result = guarded.browser_read({"url": "https://127.0.0.1/secret"})
        self.assertEqual(result["marker"], "BLOCKED_DOMAIN")
        raw.assert_not_called()  # browser never launched for a blocked target

    def test_rate_limit_applies_to_browser_reads(self):
        with patch.object(guarded._raw_session, "read_page",
                          return_value={"status": "success", "content": "ok"}):
            for _ in range(5):
                self.assertEqual(
                    guarded.browser_read({"url": "https://ratelimit-demo.test/x"})["status"],
                    "success")
            blocked = guarded.browser_read({"url": "https://ratelimit-demo.test/x"})
        self.assertEqual(blocked["marker"], "RATE_LIMITED")

    def test_invalid_url_rejected(self):
        for fn in (guarded.browser_navigate, guarded.browser_read, guarded.browser_get_content):
            self.assertEqual(fn({"url": "not-a-url"})["marker"], "INVALID_URL")
            self.assertEqual(fn({"url": "file:///etc/passwd"})["marker"], "INVALID_URL")

    def test_navigate_and_get_content_route_through_guardian(self):
        with patch.object(guarded._raw_session, "navigate",
                          return_value={"status": "success", "url": "https://example.com",
                                        "title": "T"}) as nav:
            with self.assertLogs("chhoti.browser", level="INFO") as cm:
                guarded.browser_navigate({"url": "https://example.com"})
        nav.assert_called_once()
        self.assertIn("action=web_navigate", "\n".join(cm.output))


class ReadOnlyInvariantTests(unittest.TestCase):
    """Phase 1 must contain NO clicking/typing/state-changing code."""

    FORBIDDEN = (".click(", ".dblclick(", ".fill(", ".type(", ".press(",
                 ".check(", ".uncheck(", ".select_option(", ".set_input_files(",
                 ".tap(", ".drag_to(", ".hover(", "mouse.", "keyboard.")

    def test_browser_session_exposes_no_interaction_methods(self):
        forbidden_attrs = {"click", "type", "fill", "press", "check", "select_option",
                           "set_input_files", "tap", "dblclick", "drag", "hover"}
        present = forbidden_attrs & set(dir(bsession.BrowserSession))
        self.assertEqual(present, set(), f"interaction methods leaked: {present}")

    def test_browser_sources_contain_no_interaction_calls(self):
        pkg = pathlib.Path(bsession.__file__).parent
        for name in ("session.py", "guarded.py", "routing.py"):
            src = (pkg / name).read_text(encoding="utf-8")
            for bad in self.FORBIDDEN:
                self.assertNotIn(bad, src, f"{name} contains forbidden interaction call {bad!r}")


class AccessibilityConversionTests(unittest.TestCase):
    def test_a11y_snapshot_becomes_compact_markdown(self):
        snap = {
            "role": "WebArea", "name": "Doc",
            "children": [
                {"role": "heading", "name": "Title", "level": 1},
                {"role": "paragraph", "name": "Some body text."},
                {"role": "link", "name": "Home"},
                {"role": "generic", "name": ""},  # unnamed -> dropped
            ],
        }
        md = bsession._a11y_to_markdown(snap)
        self.assertIn("# Title", md)
        self.assertIn("Some body text.", md)
        self.assertIn("[link] Home", md)
        self.assertNotIn("generic", md)  # unnamed nodes are omitted

    def test_collapse_ws(self):
        self.assertEqual(bsession._collapse_ws("a   b\n\n\n\nc  "), "a b\n\nc")


class RoutingRuleTests(unittest.TestCase):
    def test_explicit_browser_request_prefers_browser(self):
        self.assertTrue(routing.should_use_browser("please open the browser and read this"))
        self.assertTrue(routing.should_use_browser("ye page browser me kholo"))

    def test_plain_text_prefers_static_path(self):
        self.assertFalse(routing.should_use_browser("what is the capital of France"))

    def test_static_failure_falls_back_to_browser(self):
        self.assertTrue(routing.should_use_browser("", {"status": "error", "marker": "NO_CONTENT"}))
        self.assertTrue(routing.should_use_browser("", {"status": "error", "marker": "FETCH_FAILED"}))
        self.assertFalse(routing.should_use_browser("", {"status": "success", "content": "x"}))


class LiveSessionLifecycleTests(unittest.TestCase):
    """Real headless Chromium on a local file:// page; skips if it can't launch."""

    def test_launch_navigate_extract_screenshot_close(self):
        import asyncio

        html = ("<html><head><title>Phase1 Demo</title></head><body>"
                "<nav>SKIP NAV MENU</nav>"
                "<main><h1>Hello Chhoti Don</h1>"
                "<p>Readable article body about local browsing.</p>"
                "<a href='https://example.com'>Example Link</a></main>"
                "<footer>SKIP FOOTER</footer></body></html>")

        with tempfile.TemporaryDirectory() as tmp:
            page_path = pathlib.Path(tmp) / "page.html"
            page_path.write_text(html, encoding="utf-8")
            file_url = page_path.as_uri()
            shot = pathlib.Path(tmp) / "shot.png"
            profile = pathlib.Path(tmp) / "profile"

            async def run():
                s = bsession.BrowserSession(headless=True, user_data_dir=str(profile))
                await s.launch()
                try:
                    nav = await s.navigate(file_url)
                    text = await s.extract_text()
                    outline = await s.get_page_content()
                    await s.screenshot(str(shot))
                    return nav, text, outline
                finally:
                    await s.close()

            try:
                nav, text, outline = bsession._run(run())
            except bsession.PlaywrightNotInstalled as exc:
                self.skipTest(f"Chromium unavailable: {exc}")

            # Assertions INSIDE the tempdir block (screenshot lives here).
            self.assertEqual(nav["title"], "Phase1 Demo")
            self.assertIn("Hello Chhoti Don", text)
            self.assertIn("Readable article body", text)
            self.assertNotIn("SKIP NAV MENU", text)     # boilerplate stripped
            self.assertNotIn("SKIP FOOTER", text)
            self.assertIn("Hello Chhoti Don", outline)  # a11y outline has the heading
            self.assertTrue(shot.exists() and shot.stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
