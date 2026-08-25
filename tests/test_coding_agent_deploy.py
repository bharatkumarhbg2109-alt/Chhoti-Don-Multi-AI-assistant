"""Phase 6 tests: public deploy adapters, secret preflight, and the always-confirm
(approve_all-exempt) deploy gate. No real CLI is invoked and no real deploy happens
— shell.run is mocked and the deploy approver is injected.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from coding_agent import agent, deploy, guarded, hitl, shell


# ── mocks ─────────────────────────────────────────────────────────────────────
class ExecMock:
    """Mock shell executor: records calls, returns a scripted result."""

    def __init__(self, stdout="", stderr="", exit_code=0):
        self.result = {"exit_code": exit_code, "stdout": stdout, "stderr": stderr,
                       "timed_out": False}
        self.calls = []

    def __call__(self, argv, cwd, timeout, output_cap):
        self.calls.append({"argv": list(argv), "cwd": cwd})
        return dict(self.result)


def _exploding_exec(argv, cwd, timeout, output_cap):
    raise AssertionError(f"deploy must NOT run: {argv}")


class CountingApprover:
    def __init__(self, decision=True):
        self.decision = decision
        self.calls = []

    def __call__(self, proposal):
        self.calls.append(proposal)
        return self.decision


# ── adapter URL parsing ───────────────────────────────────────────────────────
class AdapterTests(unittest.TestCase):
    def test_vercel_url(self):
        v = deploy.get_adapter("vercel")
        self.assertEqual(v.parse_url("Preview: https://my-app.vercel.app", ""),
                         "https://my-app.vercel.app")
        self.assertEqual(v.parse_url("Deploying...\nhttps://my-app-abc123.vercel.app\nDone", ""),
                         "https://my-app-abc123.vercel.app")
        self.assertEqual(v.deploy_argv(False), ["vercel", "deploy", "--yes"])
        self.assertEqual(v.deploy_argv(True), ["vercel", "deploy", "--yes", "--prod"])

    def test_netlify_url(self):
        n = deploy.get_adapter("netlify")
        self.assertEqual(n.parse_url("Website URL: https://my-app.netlify.app", ""),
                         "https://my-app.netlify.app")
        self.assertIn("--prod", n.deploy_argv(True))
        self.assertNotIn("--prod", n.deploy_argv(False))

    def test_github_pages_url_and_always_live(self):
        g = deploy.get_adapter("github-pages")
        self.assertEqual(g.parse_url("Published to https://user.github.io/repo/", ""),
                         "https://user.github.io/repo/")
        self.assertFalse(g.supports_preview)   # Pages always publishes live

    def test_no_url_returns_none(self):
        self.assertIsNone(deploy.get_adapter("vercel").parse_url("Build complete.", ""))

    def test_auth_checks_are_read_only_no_login(self):
        # The agent must never log in — every auth-check is a read-only status cmd.
        for name in deploy.list_platforms():
            argv = deploy.get_adapter(name).auth_check
            self.assertNotIn("login", argv, name)
            self.assertIn(argv[-1], ("whoami", "status"), name)


# ── deploy_check (auth parsing via mocked shell.run) ──────────────────────────
class DeployCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def test_installed_and_authed(self):
        with shell.use_executor(ExecMock(stdout="my-user", exit_code=0)):
            res = guarded.deploy_check({"platform": "vercel"})
        self.assertTrue(res["installed"])
        self.assertTrue(res["authed"])

    def test_not_installed(self):
        with shell.use_executor(ExecMock(stderr="command not found: vercel", exit_code=127)):
            res = guarded.deploy_check({"platform": "vercel"})
        self.assertFalse(res["installed"])

    def test_installed_not_authed(self):
        with shell.use_executor(ExecMock(stderr="Error: not authenticated", exit_code=1)):
            res = guarded.deploy_check({"platform": "netlify"})
        self.assertTrue(res["installed"])
        self.assertFalse(res["authed"])

    def test_unknown_platform(self):
        res = guarded.deploy_check({"platform": "heroku"})
        self.assertEqual(res["marker"], "UNKNOWN_PLATFORM")

    def test_check_result_carries_no_token(self):
        with shell.use_executor(ExecMock(stdout="user", exit_code=0)):
            res = guarded.deploy_check({"platform": "vercel"})
        self.assertNotIn("token", res)
        self.assertNotIn("credentials", res)


# ── deploy_run gating (the core safety) ───────────────────────────────────────
class DeployRunGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        # a clean, secret-free file so preflight passes
        with open(os.path.join(self.root, "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<h1>hi</h1>\n")
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def test_deploy_never_auto_approved_under_approve_all(self):
        # approve_all is installed on the GENERIC channel; deploy must ignore it and
        # consult ITS OWN channel (here a denying approver) -> denied, never run.
        deploy_appr = CountingApprover(decision=False)
        with hitl.use_approver(hitl.approve_all), \
             hitl.use_deploy_approver(deploy_appr), \
             shell.use_executor(_exploding_exec):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")
        self.assertEqual(len(deploy_appr.calls), 1)   # deploy channel consulted

    def test_approve_all_alone_cannot_approve_deploy(self):
        # With ONLY the generic approve_all set (no deploy approver), deploy falls
        # back to the Guardian's human prompt — proving approve_all didn't approve it.
        with patch.object(guarded._guardian, "request_permission", return_value=False) as rp, \
             hitl.use_approver(hitl.approve_all), shell.use_executor(_exploding_exec):
            res = guarded.deploy_run({"platform": "vercel"})
        rp.assert_called_once()
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")

    def test_preview_deploy_approved_runs_and_returns_url(self):
        mock = ExecMock(stdout="Preview: https://my-app.vercel.app")
        appr = CountingApprover(True)
        with hitl.use_deploy_approver(appr), shell.use_executor(mock):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["ok"])
        self.assertFalse(res["prod"])
        self.assertEqual(res["url"], "https://my-app.vercel.app")
        self.assertEqual(len(appr.calls), 1)                     # preview = one confirm
        self.assertNotIn("--prod", mock.calls[0]["argv"])
        self.assertEqual(mock.calls[0]["cwd"], self.root)        # cwd pinned

    def test_production_requires_extra_confirmation(self):
        mock = ExecMock(stdout="Production: https://my-app.vercel.app")
        appr = CountingApprover(True)
        with hitl.use_deploy_approver(appr), shell.use_executor(mock):
            res = guarded.deploy_run({"platform": "vercel", "prod": True})
        self.assertTrue(res["prod"])
        self.assertEqual(len(appr.calls), 2)                     # preview + FINAL confirm
        self.assertIn("--prod", mock.calls[0]["argv"])

    def test_production_denied_on_final_confirm(self):
        # Approve the first confirm, deny the final production confirm -> no run.
        seq = [True, False]

        def appr(p):
            return seq.pop(0)

        with hitl.use_deploy_approver(appr), shell.use_executor(_exploding_exec):
            res = guarded.deploy_run({"platform": "vercel", "prod": True})
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")
        self.assertEqual(res.get("stage"), "production_final")

    def test_github_pages_forces_production_confirm(self):
        # Pages has no preview -> even prod=False needs the two-step prod confirm.
        mock = ExecMock(stdout="Published https://user.github.io/repo/")
        appr = CountingApprover(True)
        with hitl.use_deploy_approver(appr), shell.use_executor(mock):
            res = guarded.deploy_run({"platform": "github-pages"})
        self.assertTrue(res["prod"])
        self.assertEqual(len(appr.calls), 2)

    def test_no_workspace(self):
        guarded.revoke_workspace()
        with hitl.use_deploy_approver(hitl.approve_all):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["marker"], "NO_WORKSPACE")


# ── secret preflight ──────────────────────────────────────────────────────────
class SecretPreflightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def _write(self, rel, content):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(p) else None
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)

    def test_env_file_blocks_deploy(self):
        self._write(".env", "API_KEY=supersecretvalue1234567890\n")
        with hitl.use_deploy_approver(hitl.approve_all), shell.use_executor(_exploding_exec):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["marker"], "SECRETS_DETECTED")
        self.assertTrue(any(f["file"] == ".env" for f in res["findings"]))

    def test_env_file_ignored_is_clean(self):
        self._write(".env", "API_KEY=supersecretvalue1234567890\n")
        self._write(".gitignore", ".env\n")
        pf = deploy.secret_preflight(self.root)
        self.assertTrue(pf["clean"])          # ignored -> not a blocking finding
        mock = ExecMock(stdout="https://x.vercel.app")
        with hitl.use_deploy_approver(hitl.approve_all), shell.use_executor(mock):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["status"], "success")

    def test_credential_pattern_blocks(self):
        self._write("config.js", "const key = 'AKIAIOSFODNN7EXAMPLE';\n")
        with hitl.use_deploy_approver(hitl.approve_all), shell.use_executor(_exploding_exec):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["marker"], "SECRETS_DETECTED")

    def test_acknowledge_allows_despite_secrets(self):
        self._write(".env", "API_KEY=supersecretvalue1234567890\n")
        mock = ExecMock(stdout="https://x.vercel.app")
        with hitl.use_deploy_approver(hitl.approve_all), shell.use_executor(mock):
            res = guarded.deploy_run({"platform": "vercel", "acknowledge_secrets": True})
        self.assertEqual(res["status"], "success")

    def test_clean_workspace_is_allowed(self):
        self._write("app.py", "print('hello world')\n")
        mock = ExecMock(stdout="https://x.vercel.app")
        with hitl.use_deploy_approver(hitl.approve_all), shell.use_executor(mock):
            res = guarded.deploy_run({"platform": "vercel"})
        self.assertEqual(res["status"], "success")


# ── agent loop integration ────────────────────────────────────────────────────
def _act(tool, **args):
    return json.dumps({"tool": tool, "args": args})


def _plan(*items):
    return json.dumps([{"tool": t, "args": a} for t, a in items])


class ScriptedModel:
    def __init__(self, responses, default='{"finish":"done"}'):
        self.responses = list(responses)
        self.default = default

    def __call__(self, prompt):
        return self.responses.pop(0) if self.responses else self.default


class AgentDeployTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        with open(os.path.join(self.root, "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<h1>hi</h1>\n")
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def test_deploy_not_auto_approved_even_with_shell_approve_all(self):
        model = ScriptedModel([
            _plan(("deploy_run", {"platform": "vercel"})),
            _act("deploy_run", platform="vercel"),
            '{"finish":"tried"}',
        ])
        with shell.use_executor(_exploding_exec):
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    shell_approver=hitl.approve_all,   # generic auto-approve
                                    deploy_approver=hitl.deny_all).run("deploy it")
        denied = [t for t in res["trace"] if t.get("gate") == "DENY:GUARDIAN_DENIED"]
        self.assertTrue(denied)
        self.assertEqual(res["deploys"], [])

    def test_deploy_runs_with_explicit_deploy_approver_and_reports_url(self):
        model = ScriptedModel([
            _plan(("deploy_run", {"platform": "vercel"})),
            _act("deploy_run", platform="vercel"),
            '{"finish":"deployed"}',
        ])
        mock = ExecMock(stdout="Preview: https://my-app.vercel.app")
        with shell.use_executor(mock):
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    deploy_approver=hitl.approve_all).run("deploy it")
        self.assertEqual(res["stopped"], "finish")
        self.assertEqual(len(res["deploys"]), 1)
        self.assertEqual(res["deploys"][0]["url"], "https://my-app.vercel.app")

    def test_default_deploy_approver_denies(self):
        model = ScriptedModel([
            _plan(("deploy_run", {"platform": "vercel"})),
            _act("deploy_run", platform="vercel"),
            '{"finish":"done"}',
        ])
        with shell.use_executor(_exploding_exec):
            # no deploy_approver passed -> default deny_all
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    shell_approver=hitl.approve_all).run("deploy")
        self.assertEqual(res["deploys"], [])


if __name__ == "__main__":
    unittest.main()
