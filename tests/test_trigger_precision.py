"""Trigger-precision regression guard for the browser/shopping chat triggers.

Fixes the substring false-positives found in end-to-end testing: a bare brand
noun ("Amazon Web Services"), a coding help question ("add to cart button in
React"), or an automation-library question ("open a browser tab in Selenium")
must NOT divert an ordinary message into the Playwright browser/shopping flow —
while genuine explicit requests keep routing correctly. Fail toward NOT triggering
the browser when unsure. Pure matcher tests; no browser/guardian/HITL logic here.
"""

import unittest

from browser import routing


class ShoppingTriggerPrecision(unittest.TestCase):
    def test_brand_noun_alone_does_not_trigger(self):
        for msg in ["explain what Amazon Web Services S3 is",
                    "Amazon S3 bucket",
                    "how is amazon rainforest doing",
                    "flipkart ka stock price kya hai"]:
            self.assertFalse(routing.is_shopping_request(msg), msg)

    def test_coding_context_does_not_trigger(self):
        for msg in ["my add to cart button isn't working in React",
                    "add to cart button in React",
                    "how do I implement add to cart in my Next.js app"]:
            self.assertFalse(routing.is_shopping_request(msg), msg)

    def test_real_shopping_requests_trigger(self):
        for msg in ["flipkart pe wireless mouse dhundo",
                    "Amazon pe headphones dhundo",
                    "buy headphones on flipkart",
                    "shop for a laptop bag",
                    "add to cart the blue one",
                    "python books flipkart pe dhundo"]:   # lang noun, but real intent
            self.assertTrue(routing.is_shopping_request(msg), msg)


class ResearchTriggerPrecision(unittest.TestCase):
    def test_coding_automation_question_does_not_trigger(self):
        for msg in ["how do I open a browser tab in Selenium?",
                    "open a browser tab in Selenium",
                    "open a browser window with Playwright in Python",
                    "puppeteer script to open a browser"]:
            self.assertFalse(routing.is_browser_research_request(msg), msg)

    def test_explicit_research_requests_trigger(self):
        for msg in ["open the browser and find who won the world cup",
                    "use the browser to research quantum computing",
                    "browser me khol ke ye pata karo",
                    "browse the web for the latest llama benchmarks"]:
            self.assertTrue(routing.is_browser_research_request(msg), msg)

    def test_ordinary_messages_do_not_trigger(self):
        for msg in ["what is the capital of France", "kaise ho",
                    "write python code for fib", "render it as a table"]:
            self.assertFalse(routing.is_browser_research_request(msg), msg)


if __name__ == "__main__":
    unittest.main()
