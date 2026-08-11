"""Phase 3 HITL tests: risk tiering, approve/deny paths, GATE-level enforcement
(not prompt), CRITICAL hard-block (incl. ambiguous->CRITICAL), timeout->deny,
audit trail, and read-still-auto-allowed.

Hermetic: the raw one-shot browser action (session.do_action) is mocked, so NO
real browser launches. These prove the guarded gate — not the LLM — is the
enforcement point.
"""

import threading
import time
import unittest
from unittest.mock import patch

from browser import guarded, hitl


class RiskTierTests(unittest.TestCase):
    def test_read_is_low(self):
        for a in ("search", "navigate", "read_page", "get_content"):
            self.assertEqual(hitl.classify(a, url="https://x.com")["tier"], "LOW")

    def test_type_and_select_are_medium(self):
        self.assertEqual(hitl.classify("type_text", target={"name": "q"}, url="https://x.com")["tier"], "MEDIUM")
        self.assertEqual(hitl.classify("select_option", target={"name": "sz"}, url="https://x.com")["tier"], "MEDIUM")

    def test_click_and_press_are_high(self):
        self.assertEqual(hitl.classify("click", target={"name": "Next"}, url="https://quotes.toscrape.com/")["tier"], "HIGH")
        self.assertEqual(hitl.classify("press_key", target={"name": "q"}, url="https://x.com")["tier"], "HIGH")

    def test_payment_text_is_critical(self):
        for txt in ("Place order", "Checkout", "Pay now", "Buy now", "Submit order", "Confirm purchase"):
            c = hitl.classify("click", target={"text": txt}, url="https://shop.example.com/x")
            self.assertEqual(c["tier"], "CRITICAL", txt)
            self.assertFalse(c["requires_confirmation"])  # never offered

    def test_commerce_url_is_critical(self):
        self.assertEqual(hitl.classify("click", target={"name": "Go"}, url="https://shop.example.com/checkout")["tier"], "CRITICAL")

    def test_ambiguous_target_fails_safe_to_critical(self):
        self.assertEqual(hitl.classify("click", target={}, url="https://x.com")["tier"], "CRITICAL")
        self.assertEqual(hitl.classify("type_text", target=None, value="hi", url="https://x.com")["tier"], "CRITICAL")


class ApprovePathTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_type_executes_after_approval(self):
        with patch.object(guarded._raw_session, "do_action",
                          return_value={"status": "success", "action": "type_text",
                                        "value": "demo"}) as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_type({"url": "https://quotes.toscrape.com/login",
                                            "target": {"name": "username"}, "text": "demo"})
        self.assertEqual(out["status"], "success")
        do.assert_called_once()
        self.assertEqual(do.call_args.kwargs.get("value"), "demo")

    def test_click_executes_after_approval(self):
        with patch.object(guarded._raw_session, "do_action",
                          return_value={"status": "success", "action": "click",
                                        "url": "https://quotes.toscrape.com/page/2/"}) as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_click({"url": "https://quotes.toscrape.com/",
                                             "target": {"text": "Next"}})
        self.assertEqual(out["status"], "success")
        do.assert_called_once()


class DenyPathTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_denied_action_is_not_executed(self):
        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(hitl.deny_all):
                out = guarded.browser_click({"url": "https://quotes.toscrape.com/",
                                             "target": {"text": "Next"}})
        self.assertEqual(out["marker"], "GUARDIAN_DENIED")
        do.assert_not_called()


class GateEnforcedTests(unittest.TestCase):
    """CHECK C: the GATE blocks a HIGH/MEDIUM action with no approval, even if the
    caller never asked the user (no provider installed => fail-safe DENY)."""

    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_high_action_without_provider_is_blocked_at_gate(self):
        # No use_provider(...) context at all -> hitl.confirm defaults to DENY.
        with patch.object(guarded._raw_session, "do_action") as do:
            out = guarded.browser_click({"url": "https://quotes.toscrape.com/",
                                         "target": {"text": "Next"}})
        self.assertEqual(out["marker"], "GUARDIAN_DENIED")
        do.assert_not_called()

    def test_medium_action_without_provider_is_blocked_at_gate(self):
        with patch.object(guarded._raw_session, "do_action") as do:
            out = guarded.browser_type({"url": "https://quotes.toscrape.com/login",
                                        "target": {"name": "username"}, "text": "x"})
        self.assertEqual(out["marker"], "GUARDIAN_DENIED")
        do.assert_not_called()


class CriticalHardBlockTests(unittest.TestCase):
    """CHECK D: submit/checkout/pay (and ambiguous) are refused outright and are
    NEVER offered for confirmation."""

    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_critical_is_blocked_and_confirm_never_consulted(self):
        calls = {"n": 0}

        def _counting_provider(_proposal):
            calls["n"] += 1
            return True  # even an "approve everything" provider must NOT be asked

        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(_counting_provider):
                out = guarded.browser_click({"url": "https://shop.example.com/product",
                                             "target": {"text": "Place order"}})
        self.assertEqual(out["marker"], "CRITICAL_BLOCKED")
        do.assert_not_called()
        self.assertEqual(calls["n"], 0, "CRITICAL action must not reach the confirmation provider")

    def test_ambiguous_click_fails_safe_to_critical(self):
        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_click({"url": "https://quotes.toscrape.com/", "target": {}})
        self.assertEqual(out["marker"], "CRITICAL_BLOCKED")
        do.assert_not_called()

    def test_commerce_url_type_is_critical(self):
        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_type({"url": "https://shop.example.com/checkout",
                                            "target": {"name": "card"}, "text": "4111"})
        self.assertEqual(out["marker"], "CRITICAL_BLOCKED")
        do.assert_not_called()


class TimeoutAndResumeTests(unittest.TestCase):
    """CHECK E: a pending action with no answer defaults to DENY."""

    def _proposal(self):
        return hitl.make_proposal("click", {"text": "Next"}, None,
                                  "https://quotes.toscrape.com/", "HIGH")

    def test_timeout_defaults_to_deny(self):
        run = hitl.InteractiveRun(confirm_timeout=0.4)
        provider = run.provider()
        out = {}
        th = threading.Thread(target=lambda: out.__setitem__("d", provider(self._proposal())))
        th.start()
        th.join(5)
        self.assertFalse(th.is_alive())
        self.assertFalse(out["d"])  # no response within timeout -> DENY

    def test_resume_approve_and_deny(self):
        for decision in (True, False):
            run = hitl.InteractiveRun(confirm_timeout=5)
            provider = run.provider()
            out = {}
            th = threading.Thread(target=lambda: out.__setitem__("d", provider(self._proposal())))
            th.start()
            for _ in range(100):  # wait until the provider is actually pending
                if run.state == "pending":
                    break
                time.sleep(0.01)
            run.respond(decision)
            th.join(5)
            self.assertEqual(out["d"], decision)


class AuditAndReadAutoTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_risky_action_emits_propose_decision_result_audit(self):
        with patch.object(guarded._raw_session, "do_action",
                          return_value={"status": "success", "action": "click"}):
            with self.assertLogs("chhoti.browser.audit", level="INFO") as cm:
                with hitl.use_provider(hitl.approve_all):
                    guarded.browser_click({"url": "https://quotes.toscrape.com/",
                                           "target": {"text": "Next"}})
        blob = "\n".join(cm.output)
        self.assertIn("PROPOSE", blob)
        self.assertIn("APPROVE", blob)
        self.assertIn("RESULT", blob)

    def test_reads_auto_allow_without_confirmation(self):
        # CHECK F: read/navigate still auto-allow — even with a DENY provider set,
        # the read path never consults confirm and executes normally.
        with patch.object(guarded._raw_session, "navigate",
                          return_value={"status": "success", "url": "https://quotes.toscrape.com/",
                                        "title": "Quotes"}) as nav:
            with hitl.use_provider(hitl.deny_all):
                out = guarded.browser_navigate({"url": "https://quotes.toscrape.com/"})
        self.assertEqual(out["status"], "success")
        nav.assert_called_once()


if __name__ == "__main__":
    unittest.main()
