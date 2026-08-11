"""Phase 2 agent-loop tests: planning step, max_steps cap, action-parse
resilience, read-only enforcement, guardian-in-path, and the chat trigger.

Hermetic: the LLM is a scripted fake `think_fn` and the guarded browser tools are
monkeypatched, so NO real browser or Ollama is used here.
"""

import pathlib
import unittest
from unittest.mock import patch

from browser import agent as A
from browser import routing


def _canned_search(_input):
    return {"status": "success", "results": [
        {"title": "2022 FIFA World Cup", "url": "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup",
         "snippet": "Argentina won the 2022 FIFA World Cup."}]}


def _canned_read(_input):
    return {"status": "success", "url": "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup",
            "title": "2022 FIFA World Cup", "content": "Argentina won, captained by Lionel Messi.",
            "content_is_untrusted": True}


class PlanningStepTests(unittest.TestCase):
    def test_agent_plans_acts_observes_then_finishes(self):
        script = iter([
            '{"thought":"find winner","tool":"search","args":{"query":"world cup 2022 winner"}}',
            '{"tool":"read_page","args":{"url":"https://en.wikipedia.org/wiki/2022_FIFA_World_Cup"}}',
            '{"tool":"finish","args":{"answer":"Argentina won; captain Lionel Messi."}}',
        ])
        think = lambda prompt: next(script)
        with patch.object(A.guarded, "web_search", side_effect=_canned_search) as s, \
             patch.object(A.guarded, "browser_read", side_effect=_canned_read) as r:
            res = A.run_research("Who won the 2022 World Cup and the captain?", think_fn=think)
        self.assertEqual(res["stopped"], "finish")
        self.assertEqual(res["steps"], 3)
        self.assertIn("Argentina", res["answer"])
        s.assert_called_once()
        r.assert_called_once()
        # Trace records action + observation for each step (observability).
        actions = [t.get("action") for t in res["trace"]]
        self.assertEqual(actions, ["search", "read_page", "finish"])


class MaxStepsCapTests(unittest.TestCase):
    def test_loop_terminates_cleanly_at_cap(self):
        # Model NEVER finishes — always navigates: must stop at the hard cap.
        think = lambda prompt: '{"tool":"navigate","args":{"url":"https://example.com"}}'
        synth = lambda prompt: "Could not conclude within the step budget."
        with patch.object(A.guarded, "browser_navigate",
                          return_value={"status": "success", "title": "Example", "url": "https://example.com"}) as n:
            res = A.run_research("unsatisfiable looping goal", think_fn=think, synth_fn=synth, max_steps=3)
        self.assertEqual(res["stopped"], "max_steps")
        self.assertEqual(res["steps"], 3)
        self.assertEqual(n.call_count, 3)                 # exactly the cap, no runaway
        self.assertIn("step budget", res["answer"])       # clean synthesized fallback


class ActionParseResilienceTests(unittest.TestCase):
    def test_recovers_from_one_bad_reply_with_corrective_retry(self):
        script = iter([
            "sure! here you go (no json at all)",                    # step1 attempt1: garbage
            '{"tool":"finish","args":{"answer":"done"}}',           # step1 attempt2: valid
        ])
        think = lambda prompt: next(script)
        res = A.run_research("goal", think_fn=think, max_steps=3)
        self.assertEqual(res["stopped"], "finish")
        self.assertEqual(res["answer"], "done")

    def test_parser_tolerates_messy_json(self):
        cases = [
            '```json\n{"tool":"search","args":{"query":"x"}}\n```',       # fenced
            'Thinking... {"tool":"search","args":{"query":"x"}} done',    # prose around
            "{'tool':'search','args':{'query':'x'},}",                    # single quotes + trailing comma
            '{"tool":"search","query":"x"}',                             # flat args
        ]
        for c in cases:
            a = A._parse_action(c)
            self.assertIsNotNone(a, f"failed to parse: {c!r}")
            self.assertEqual(a["tool"], "search")
        # finish with flat answer
        f = A._parse_action('{"tool":"finish","answer":"hi"}')
        self.assertEqual(f["tool"], "finish")
        self.assertEqual(f["args"].get("answer"), "hi")

    def test_totally_unparseable_after_retries_stops_cleanly(self):
        think = lambda prompt: "never json"
        res = A.run_research("goal", think_fn=think, max_steps=8)
        self.assertEqual(res["stopped"], "parse_error")


class ActionSurfaceTests(unittest.TestCase):
    # agent.py must never call raw Playwright primitives directly — it dispatches
    # ONLY to the guarded wrappers, which remain the enforcement point.
    FORBIDDEN = (".click(", ".dblclick(", ".fill(", ".type(", ".press(", ".check(",
                 ".uncheck(", ".select_option(", ".set_input_files(", ".tap(",
                 ".drag_to(", ".hover(", "mouse.", "keyboard.")

    def test_action_set_is_read_plus_gated_interactive(self):
        self.assertEqual(set(A.READ_ACTIONS), {"search", "navigate", "read_page", "get_content"})
        self.assertEqual(set(A.INTERACTIVE_ACTIONS),
                         {"click", "type_text", "select_option", "press_key"})
        self.assertIn("finish", A.AGENT_ACTIONS)

    def test_parser_accepts_interactive_actions_but_rejects_unknown(self):
        # Phase 3: interactive actions are now valid loop actions (they get gated
        # downstream in the guarded wrappers, not rejected at parse time).
        for good in ('{"tool":"click","args":{"target":{"text":"Next"},"url":"https://x"}}',
                     '{"tool":"type_text","args":{"target":{"name":"q"},"text":"hi","url":"https://x"}}'):
            self.assertIsNotNone(A._parse_action(good))
        # Genuinely unknown / non-exposed tools are still rejected.
        for bad in ('{"tool":"pay","args":{}}',
                    '{"tool":"download_file","args":{}}',
                    '{"tool":"evaluate_js","args":{}}'):
            self.assertIsNone(A._parse_action(bad))

    def test_dispatch_rejects_unknown_tool(self):
        out = A._dispatch("delete_everything", {"selector": "#buy"})
        self.assertEqual(out["marker"], "UNKNOWN_TOOL")

    def test_agent_source_calls_only_guarded_wrappers(self):
        src = pathlib.Path(A.__file__).read_text(encoding="utf-8")
        for bad in self.FORBIDDEN:
            self.assertNotIn(bad, src, f"agent.py calls a raw interaction primitive {bad!r}")


class GuardianInPathTests(unittest.TestCase):
    def test_read_action_goes_through_guarded_wrapper(self):
        script = iter([
            '{"tool":"read_page","args":{"url":"https://example.com"}}',
            '{"tool":"finish","args":{"answer":"ok"}}',
        ])
        think = lambda prompt: next(script)
        # Patch the GUARDED wrapper (not the raw session): proves the loop routes
        # through browser.guarded, so browser.guarded._gate stays in the path.
        with patch.object(A.guarded, "browser_read",
                          return_value={"status": "success", "url": "https://example.com",
                                        "title": "Example", "content": "hello"}) as r:
            res = A.run_research("read example", think_fn=think, max_steps=3)
        r.assert_called_once()
        self.assertEqual(res["stopped"], "finish")


class ChatTriggerTests(unittest.TestCase):
    def test_ordinary_messages_do_not_trigger_research(self):
        for msg in ["what is the capital of France", "kaise ho", "write python code for fib",
                    "explain ddos attack", "render it as a table"]:
            self.assertFalse(routing.is_browser_research_request(msg), msg)

    def test_explicit_browser_requests_trigger_research(self):
        for msg in ["open the browser and find who won the world cup",
                    "use the browser to research quantum computing",
                    "browser me khol ke ye pata karo"]:
            self.assertTrue(routing.is_browser_research_request(msg), msg)


class ManagerWiringTests(unittest.TestCase):
    def test_brain_task_diverts_only_explicit_requests(self):
        from core.manager import ManagerAgent
        mgr = ManagerAgent()
        with patch.object(mgr, "research_task",
                          return_value={"agent": "BrowserResearchAgent", "output": "X"}) as rt:
            # ordinary message must NOT call research_task
            with patch.object(mgr.brain, "decide_tool", return_value=None), \
                 patch.object(mgr.brain, "think", return_value="normal reply"):
                out = mgr.brain_task("what is 2 plus 2 conceptually")
            rt.assert_not_called()
            self.assertEqual(out["agent"], "Brain")
            # explicit research message MUST call research_task
            out2 = mgr.brain_task("open the browser and find the latest news")
            rt.assert_called_once()
            self.assertEqual(out2["agent"], "BrowserResearchAgent")


if __name__ == "__main__":
    unittest.main()
