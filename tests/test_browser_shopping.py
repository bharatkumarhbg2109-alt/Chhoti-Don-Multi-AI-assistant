"""Phase 4 shopping-assist tests: product parsing, add-to-cart gating (approve/
deny), payment CRITICAL hard-block (incl. shopping labels + ambiguous), credential
-field refusal, CAPTCHA/bot-wall handoff, and the max-cart-additions cap.

Hermetic: the raw browser one-shots (do_action / search_products) are mocked — no
real browser. These prove the gate + shopping safety rules.
"""

import unittest
from unittest.mock import patch

from browser import guarded, hitl, shopping, routing
from browser.config import MAX_CART_ADDITIONS


class ProductParsingTests(unittest.TestCase):
    def test_clean_products_dedupes_and_normalizes_rating(self):
        rows = [
            {"title": "A Light in the Attic", "price": "£51.77",
             "rating": "star-rating Three", "url": "https://s/a"},
            {"title": "Dup", "price": "£10", "rating": "", "url": "https://s/a"},   # dup url
            {"title": "", "price": "£9", "rating": "", "url": "https://s/b"},        # no title
            {"title": "Tipping the Velvet", "price": "£53.74",
             "rating": "star-rating One", "url": "https://s/c"},
        ]
        out = shopping.clean_products(rows)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["rating"], "Three stars")
        self.assertEqual(out[0]["title"], "A Light in the Attic")

    def test_build_search_url_and_parse(self):
        site, query = shopping.parse_shopping_request("Flipkart pe ek wireless mouse dhundo")
        self.assertEqual(site, "flipkart")
        self.assertIn("wireless", query)
        self.assertIn("mouse", query)
        url = shopping.build_search_url(query, site)
        self.assertTrue(url.startswith("https://www.flipkart.com/search?q="))
        self.assertIn("wireless", url)

    def test_shopping_trigger_precision(self):
        self.assertTrue(routing.is_shopping_request("flipkart pe mouse dhundo"))
        self.assertTrue(routing.is_shopping_request("add to cart the blue one"))
        self.assertFalse(routing.is_shopping_request("what is the capital of France"))
        self.assertFalse(routing.is_shopping_request("write python code"))


class AddToCartGatingTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()
        shopping.reset_cart()

    def test_add_to_cart_is_high_and_executes_on_approve(self):
        with patch.object(guarded._raw_session, "do_action",
                          return_value={"status": "success", "action": "add_to_cart",
                                        "url": "https://shop.test/p/1"}) as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_add_to_cart({"url": "https://shop.test/p/1",
                                                   "target": {"text": "Add to cart"},
                                                   "product": "Wireless Mouse"})
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["cart_count"], 1)
        do.assert_called_once()

    def test_add_to_cart_blocked_on_deny(self):
        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(hitl.deny_all):
                out = guarded.browser_add_to_cart({"url": "https://shop.test/p/1",
                                                   "target": {"text": "Add to cart"}})
        self.assertEqual(out["marker"], "GUARDIAN_DENIED")
        do.assert_not_called()
        self.assertEqual(shopping.cart_count(), 0)  # denied addition does not count


class PaymentHardBlockTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()
        shopping.reset_cart()

    def test_shopping_payment_labels_are_critical(self):
        labels = ["Buy Now", "Place Order", "Proceed to checkout", "Continue to payment",
                  "Pay Now", "Proceed to Pay", "Complete purchase"]
        for lbl in labels:
            with patch.object(guarded._raw_session, "do_action") as do:
                with hitl.use_provider(hitl.approve_all):  # even "approve all" must not run it
                    out = guarded.browser_click({"url": "https://shop.test/p/1", "target": {"text": lbl}})
            self.assertEqual(out["marker"], "CRITICAL_BLOCKED", lbl)
            do.assert_not_called()

    def test_add_to_cart_with_payment_target_is_critical(self):
        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_add_to_cart({"url": "https://shop.test/p/1",
                                                   "target": {"text": "Buy Now"}})
        self.assertEqual(out["marker"], "CRITICAL_BLOCKED")
        do.assert_not_called()

    def test_checkout_url_makes_click_critical_even_generic_label(self):
        # ambiguous 'Continue' past the cart (on a checkout URL) -> fail-safe CRITICAL
        with patch.object(guarded._raw_session, "do_action") as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_click({"url": "https://flipkart.com/checkout/init",
                                             "target": {"text": "Continue"}})
        self.assertEqual(out["marker"], "CRITICAL_BLOCKED")
        do.assert_not_called()


class CredentialSafetyTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_never_types_into_credential_fields(self):
        for fld in [{"name": "password"}, {"label": "OTP"}, {"placeholder": "Card number"},
                    {"name": "cvv"}, {"label": "UPI ID"}]:
            with patch.object(guarded._raw_session, "do_action") as do:
                with hitl.use_provider(hitl.approve_all):
                    out = guarded.browser_type({"url": "https://shop.test/login",
                                                "target": fld, "text": "secret"})
            self.assertEqual(out["marker"], "CRITICAL_BLOCKED", fld)
            do.assert_not_called()

    def test_ordinary_search_field_is_medium_and_allowed(self):
        with patch.object(guarded._raw_session, "do_action",
                          return_value={"status": "success", "value": "mouse"}) as do:
            with hitl.use_provider(hitl.approve_all):
                out = guarded.browser_type({"url": "https://shop.test/", "target": {"name": "q"},
                                            "text": "mouse"})
        self.assertEqual(out["status"], "success")
        do.assert_called_once()


class BotWallHandoffTests(unittest.TestCase):
    def setUp(self):
        guarded._calls_by_domain.clear()

    def test_detect_bot_wall_patterns(self):
        self.assertEqual(shopping.detect_bot_wall("Please solve the reCAPTCHA"), "captcha_or_bot_check")
        self.assertEqual(shopping.detect_bot_wall("We detected unusual traffic"), "captcha_or_bot_check")
        self.assertEqual(shopping.detect_bot_wall("Please sign in to continue"), "login_required")
        self.assertIsNone(shopping.detect_bot_wall("Wireless Mouse - ₹499 - Add to cart"))

    def test_search_products_returns_handoff_on_bot_wall(self):
        with patch.object(guarded._raw_session, "search_products",
                          return_value={"status": "handoff", "marker": "BOT_WALL",
                                        "reason": "captcha_or_bot_check", "url": "https://shop.test/s"}) as sp:
            out = guarded.browser_search_products({"url": "https://shop.test/search?q=mouse"})
        self.assertEqual(out["status"], "handoff")
        self.assertEqual(out["reason"], "captcha_or_bot_check")
        sp.assert_called_once()


class MaxCartCapAndReadAutoTests(unittest.TestCase):
    def setUp(self):
        shopping.reset_cart()

    def test_max_cart_additions_cap(self):
        with patch.object(guarded._raw_session, "do_action",
                          return_value={"status": "success", "action": "add_to_cart"}):
            with hitl.use_provider(hitl.approve_all):
                for i in range(MAX_CART_ADDITIONS):
                    guarded._calls_by_domain.clear()  # isolate cap from the rate limiter
                    out = guarded.browser_add_to_cart({"url": "https://shop.test/p/%d" % i,
                                                       "target": {"text": "Add to cart"}})
                    self.assertEqual(out["status"], "success", f"add #{i + 1}")
                guarded._calls_by_domain.clear()
                capped = guarded.browser_add_to_cart({"url": "https://shop.test/p/x",
                                                      "target": {"text": "Add to cart"}})
        self.assertEqual(capped["marker"], "CART_CAP_REACHED")
        self.assertEqual(shopping.cart_count(), MAX_CART_ADDITIONS)

    def test_product_search_auto_allows_without_confirmation(self):
        # read/extraction still auto-allows — even with a DENY provider set.
        guarded._calls_by_domain.clear()
        with patch.object(guarded._raw_session, "search_products",
                          return_value={"status": "success", "url": "https://shop.test/s",
                                        "products": [{"title": "Mouse", "price": "₹499",
                                                      "rating": "", "url": "https://shop.test/p/1"}]}) as sp:
            with hitl.use_provider(hitl.deny_all):
                out = guarded.browser_search_products({"url": "https://shop.test/search?q=mouse"})
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["products"]), 1)
        sp.assert_called_once()


if __name__ == "__main__":
    unittest.main()
