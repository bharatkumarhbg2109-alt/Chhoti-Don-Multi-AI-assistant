"""Coding agent smoke tests (Task 11): controlled-mock tests that exercise the
FULL agent pipeline (not mocking individual tools -- mocking only the LLM call)
to verify end-to-end behavior.

Each smoke is a single test function with its own throwaway tmp workspace.
"""

import json
import os
import tempfile
import unittest

from coding_agent import agent, guarded, hitl


class ScriptedModel:
    """Deterministic think_fn: returns queued responses in order, then default."""

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


class SmokeL1FileWrite(unittest.TestCase):
    """Smoke L1 -- File write: model creates a file then finishes."""

    def test_file_written_to_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            guarded.revoke_workspace()
            guarded.grant_workspace(tmp)

            model = ScriptedModel([
                _plan(("fs_create_file", {"path": "hello.py"})),
                _act("fs_create_file", path="hello.py", content="print('hello')\n"),
                '{"finish":"created hello.py"}',
            ])
            res = agent.CodingAgent(model, plan_approver=lambda p: True).run("create hello")
            self.assertEqual(res["stopped"], "finish")
            self.assertTrue(os.path.exists(os.path.join(tmp, "hello.py")))
            with open(os.path.join(tmp, "hello.py")) as f:
                self.assertEqual(f.read(), "print('hello')\n")
            guarded.revoke_workspace()


class SmokeL2ShellShim(unittest.TestCase):
    """Smoke L2 -- Shell + python -m shim: sh_run receives shimmed argv."""

    def test_pytest_shimmed_in_sh_run(self):
        from coding_agent.shell import use_executor
        with tempfile.TemporaryDirectory() as tmp:
            guarded.revoke_workspace()
            guarded.grant_workspace(tmp)

            captured = {}
            def mock_exec(argv, cwd, timeout, output_cap):
                captured["argv"] = argv
                return {"exit_code": 0, "stdout": "ok", "stderr": "", "timed_out": False,
                        "command": "pytest add.py"}

            model = ScriptedModel([
                _plan(("sh_run", {"command": "pytest add.py"})),
                _act("sh_run", command="pytest add.py"),
                '{"finish":"tests pass"}',
            ])
            with hitl.use_approver(hitl.approve_all), \
                 use_executor(mock_exec):
                res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                        shell_approver=hitl.approve_all).run("test")
            self.assertIn(res["stopped"], ("finish", "implicit_verify"))
            # Shim should have rewritten ["pytest", "add.py"] -> ["python", "-m", "pytest", "add.py"]
            self.assertEqual(captured["argv"][:3], ["python", "-m", "pytest"])
            guarded.revoke_workspace()


class SmokeL3ImplicitVerify(unittest.TestCase):
    """Smoke L3 -- Implicit finish on verified success: exit_code=0 on pytest
    triggers implicit_verify WITHOUT calling the model again."""

    def test_implicit_verify_fires(self):
        from coding_agent.shell import use_executor
        with tempfile.TemporaryDirectory() as tmp:
            guarded.revoke_workspace()
            guarded.grant_workspace(tmp)

            def mock_exec(argv, cwd, timeout, output_cap):
                cmd = " ".join(argv)
                if "pytest" in cmd:
                    return {"exit_code": 0, "stdout": "1 passed", "stderr": "",
                            "timed_out": False, "command": "pytest test_pass.py"}
                return {"exit_code": 0, "stdout": "", "stderr": "", "timed_out": False}

            model = ScriptedModel([
                _plan(("sh_run", {"command": "pytest test_pass.py"})),
                _act("sh_run", command="pytest test_pass.py"),
                '{"finish":"should not reach"}',
            ])
            with hitl.use_approver(hitl.approve_all), \
                 use_executor(mock_exec):
                res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                        shell_approver=hitl.approve_all).run("test")
            self.assertEqual(res["stopped"], "implicit_verify")
            # Model was NOT called again (only plan + 1 action)
            self.assertEqual(len(model.calls), 2)
            guarded.revoke_workspace()


class SmokeL4CriticalBlock(unittest.TestCase):
    """Smoke L4 -- CRITICAL block under approve_all: rm -rf / is never executed."""

    def test_critical_blocked_under_approve_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            guarded.revoke_workspace()
            guarded.grant_workspace(tmp)

            model = ScriptedModel([
                _plan(("sh_run", {"command": "echo hi"})),
                _act("sh_run", command="rm -rf /"),
                '{"finish":"done"}',
            ])
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    shell_approver=hitl.approve_all).run("danger")
            blocked = [t for t in res["trace"] if t.get("gate") == "DENY:CRITICAL_BLOCKED"]
            self.assertTrue(blocked)
            # Workspace should be untouched
            self.assertEqual(os.listdir(tmp), [])
            guarded.revoke_workspace()


class SmokeL5SandboxEscape(unittest.TestCase):
    """Smoke L5 -- Sandbox escape blocked: fs_write_file with path '../../../etc/hosts'
    raises SANDBOX_VIOLATION."""

    def test_sandbox_escape_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            guarded.revoke_workspace()
            guarded.grant_workspace(tmp)

            model = ScriptedModel([
                _plan(("fs_write_file", {"path": "safe.txt"})),
                _act("fs_write_file", path="../../../etc/hosts", content="evil"),
                '{"finish":"done"}',
            ])
            res = agent.CodingAgent(model, plan_approver=lambda p: True).run("escape")
            violations = [t for t in res["trace"]
                         if "SANDBOX_VIOLATION" in str(t.get("observation", ""))]
            self.assertTrue(violations)
            guarded.revoke_workspace()


if __name__ == "__main__":
    unittest.main()
