"""Phase 3 tests: the autonomous coding builder loop (mocked model — no live LLM).

A scripted model feeds the agent a plan then a sequence of single actions. Tests
assert correct guarded dispatch + ordering, plan approve/reject, max_steps and
no-progress breaks, malformed-output corrective retry, jail-escape handling inside
the loop, plan-scope enforcement, HIGH-delete individual confirm, the opt-in
trigger, and registry wiring — all without a running Ollama.
"""

import json
import os
import tempfile
import unittest

from coding_agent import agent, guarded, hitl


class ScriptedModel:
    """Deterministic think_fn: returns queued responses in order, then `default`."""

    def __init__(self, responses, default='{"finish":"done"}'):
        self.responses = list(responses)
        self.default = default
        self.calls = []

    def __call__(self, prompt):
        self.calls.append(prompt)
        return self.responses.pop(0) if self.responses else self.default


def _act(tool, **args):
    return json.dumps({"tool": tool, "args": args})


def _plan(*items):
    return json.dumps([{"tool": t, "args": a} for t, a in items])


class LoopBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def _exists(self, rel):
        return os.path.exists(os.path.join(self.root, rel))

    def _read(self, rel):
        with open(os.path.join(self.root, rel), "r", encoding="utf-8") as fh:
            return fh.read()


class EndToEndTests(LoopBase):
    def test_scripted_build_produces_file_tree(self):
        model = ScriptedModel([
            _plan(("fs_create_file", {"path": "app/main.py"}),
                  ("fs_create_file", {"path": "app/util.py"})),
            _act("fs_create_file", path="app/main.py", content="print('hi')\n"),
            _act("fs_create_file", path="app/util.py", content="X = 1\n"),
            '{"finish":"created two files"}',
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True).run("scaffold app")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["stopped"], "finish")
        self.assertEqual(self._read("app/main.py"), "print('hi')\n")
        self.assertEqual(self._read("app/util.py"), "X = 1\n")
        self.assertEqual([e["path"] for e in res["executed"]],
                         ["app/main.py", "app/util.py"])

    def test_medium_writes_batched_no_per_file_prompt(self):
        # No hitl approver is installed by the test; the agent's session approver
        # must auto-approve in-scope MEDIUM writes (else this would block/deny).
        model = ScriptedModel([
            _plan(("fs_write_file", {"path": "a.txt"}), ("fs_write_file", {"path": "b.txt"})),
            _act("fs_write_file", path="a.txt", content="A"),
            _act("fs_write_file", path="b.txt", content="B"),
            '{"finish":"done"}',
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True).run("write two")
        self.assertEqual(res["status"], "success")
        self.assertTrue(self._exists("a.txt") and self._exists("b.txt"))


class ApprovalTests(LoopBase):
    def test_rejected_plan_writes_nothing(self):
        model = ScriptedModel([
            _plan(("fs_create_file", {"path": "should_not_exist.py"})),
            _act("fs_create_file", path="should_not_exist.py", content="x"),
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: False).run("build")
        self.assertEqual(res["status"], "rejected")
        self.assertEqual(res["stopped"], "rejected")
        self.assertFalse(self._exists("should_not_exist.py"))
        self.assertEqual(res["executed"], [])
        # Only the planning call happened — execution never started.
        self.assertEqual(len(model.calls), 1)

    def test_default_plan_approver_denies(self):
        model = ScriptedModel([_plan(("fs_create_file", {"path": "x.py"}))])
        res = agent.CodingAgent(model).run("build")  # no plan_approver -> fail safe
        self.assertEqual(res["status"], "rejected")
        self.assertFalse(self._exists("x.py"))

    def test_out_of_scope_write_is_denied(self):
        # Plan only covers a.txt; the loop tries to write b.txt (out of scope).
        model = ScriptedModel([
            _plan(("fs_write_file", {"path": "a.txt"})),
            _act("fs_write_file", path="b.txt", content="sneaky"),
            '{"finish":"done"}',
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True).run("build")
        self.assertFalse(self._exists("b.txt"))
        denied = [t for t in res["trace"] if t.get("gate") == "DENY:GUARDIAN_DENIED"]
        self.assertTrue(denied)


class SafetyGuardTests(LoopBase):
    def test_max_steps_enforced(self):
        model = ScriptedModel([
            _plan(("fs_create_file", {"path": "a.py"}), ("fs_create_file", {"path": "b.py"})),
            _act("fs_create_file", path="a.py", content="1"),
            _act("fs_create_file", path="b.py", content="2"),
        ], default=_act("fs_list_dir", path="."))  # would keep going, but cap stops it
        res = agent.CodingAgent(model, plan_approver=lambda p: True, max_steps=2).run("build")
        self.assertEqual(res["stopped"], "max_steps")
        self.assertEqual(res["steps"], 2)

    def test_no_progress_breaks(self):
        same = _act("fs_create_file", path="a.py", content="1")
        model = ScriptedModel([
            _plan(("fs_create_file", {"path": "a.py"})),
            same, same, same,
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True, max_steps=8).run("build")
        self.assertEqual(res["stopped"], "no_progress")
        self.assertIn("no progress", res["summary"].lower())

    def test_malformed_then_valid_triggers_corrective_retry(self):
        model = ScriptedModel([
            _plan(("fs_create_file", {"path": "a.py"})),
            "this is not json at all",          # step1 attempt1 -> retry
            '{"finish":"ok"}',                    # step1 attempt2 -> parsed
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True).run("build")
        self.assertEqual(res["stopped"], "finish")
        # plan + 2 step attempts = 3 model calls.
        self.assertEqual(len(model.calls), 3)

    def test_persistent_malformed_fails_gracefully(self):
        model = ScriptedModel([_plan(("fs_create_file", {"path": "a.py"}))],
                              default="still not json")
        res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                max_parse_retries=2, max_steps=5).run("build")
        self.assertEqual(res["stopped"], "parse_error")
        self.assertEqual(res["status"], "incomplete")

    def test_unparseable_plan_fails_cleanly(self):
        model = ScriptedModel([], default="not a plan")
        res = agent.CodingAgent(model, plan_approver=lambda p: True).run("build")
        self.assertEqual(res["stopped"], "plan_parse_error")
        # Approver never consulted / nothing executed.
        self.assertEqual(res["executed"], [])


class JailEscapeInLoopTests(LoopBase):
    def test_escape_blocked_and_loop_continues(self):
        model = ScriptedModel([
            _plan(("fs_create_file", {"path": "ok.txt"})),
            _act("fs_write_file", path="../evil.txt", content="pwn"),  # escape
            '{"finish":"stopped trying to escape"}',
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True).run("build")
        self.assertEqual(res["stopped"], "finish")   # loop ended cleanly
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.root), "evil.txt")))
        violation = [t for t in res["trace"] if t.get("gate") == "DENY:SANDBOX_VIOLATION"]
        self.assertTrue(violation)


class HighRiskDeleteTests(LoopBase):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.root, "old.py"), "w", encoding="utf-8") as fh:
            fh.write("legacy\n")

    def test_delete_needs_individual_approval_approve(self):
        model = ScriptedModel([
            _plan(("fs_delete_file", {"path": "old.py"})),
            _act("fs_delete_file", path="old.py"),
            '{"finish":"deleted"}',
        ])
        res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                delete_approver=hitl.approve_all).run("cleanup")
        self.assertEqual(res["stopped"], "finish")
        self.assertFalse(self._exists("old.py"))

    def test_delete_denied_by_individual_approver(self):
        model = ScriptedModel([
            _plan(("fs_delete_file", {"path": "old.py"})),
            _act("fs_delete_file", path="old.py"),
            '{"finish":"kept"}',
        ])
        # plan approved, but the per-delete approver denies -> file survives.
        res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                delete_approver=hitl.deny_all).run("cleanup")
        self.assertTrue(self._exists("old.py"))
        denied = [t for t in res["trace"] if t.get("gate") == "DENY:GUARDIAN_DENIED"]
        self.assertTrue(denied)


class TriggerGatingTests(unittest.TestCase):
    def test_build_requests_match(self):
        for t in ("scaffold a python flask project for me",
                  "create a new project: a todo CLI in python",
                  "build me a react app",
                  "project banao ek chatbot ka"):
            self.assertTrue(agent.is_build_request(t), t)

    def test_ordinary_and_question_messages_do_not_match(self):
        for t in ("hey how are you?",
                  "how do I scaffold a flask app?",
                  "what is the difference between build and create in docker?",
                  "explain how to create a project in react",
                  "summarize this pdf for me",
                  ""):
            self.assertFalse(agent.is_build_request(t), t)


class ShellSurfaceTests(unittest.TestCase):
    def test_agent_actions_are_fs_plus_gated_shell_and_local_servers(self):
        # Non-fs actions are exactly the gated shell + the LOCAL server tools.
        non_fs = sorted(t for t in agent.AGENT_TOOLS if not t.startswith("fs_"))
        self.assertEqual(non_fs, sorted(
            ["sh_run", "serve_start", "serve_status", "serve_logs", "serve_stop"]))
        # No raw exec/eval/spawn — and NO tunnel/deploy/external-hosting action.
        banned = ("exec", "eval", "popen", "spawn", "subprocess", "system",
                  "tunnel", "ngrok", "deploy", "publish", "expose", "cloudflare")
        for t in agent.AGENT_TOOLS:
            self.assertFalse(any(b in t for b in banned), t)


class RegistryBuildTests(unittest.TestCase):
    def setUp(self):
        from tools.registry import ToolRegistry
        self.registry = ToolRegistry()  # brain=None
        guarded.revoke_workspace()

    def tearDown(self):
        guarded.revoke_workspace()

    def test_fs_build_registered_with_definition(self):
        self.assertIn("fs_build", self.registry.list_tools())
        self.assertIn("fs_build", self.registry.get_tool_definitions())

    def test_fs_build_requires_brain(self):
        out = self.registry.execute("fs_build", {"task": "make a thing"})
        self.assertEqual(out["result"]["marker"], "NO_BRAIN")

    def test_fs_build_empty_task(self):
        out = self.registry.execute("fs_build", {"task": ""})
        self.assertEqual(out["result"]["marker"], "EMPTY_TASK")


if __name__ == "__main__":
    unittest.main()
