"""Phase 5 tests: LOCAL background-server supervisor + guarded serve_* + loop.

Never spawns a real process or opens a real socket — a fake process-starter and a
mocked prober are injected. The module registry + id counter are reset per test
for determinism.
"""

import itertools
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from coding_agent import agent, guarded, hitl, server


# ── fakes ─────────────────────────────────────────────────────────────────────
class FakeStdout:
    def __init__(self, lines):
        self._lines = list(lines)
    def readline(self):
        return self._lines.pop(0) if self._lines else ""
    def close(self):
        self._lines = []


class FakeProc:
    def __init__(self, lines, pid=4242, dead=False):
        self.stdout = FakeStdout(lines)
        self.pid = pid
        self._rc = -1 if dead else None
        self.terminated = False
        self.killed = False
    def poll(self):
        return self._rc
    def terminate(self):
        self.terminated = True
        self._rc = -15
    def kill(self):
        self.killed = True
        self._rc = -9
    def wait(self, timeout=None):
        return self._rc if self._rc is not None else 0


def make_starter(lines, pid=4242, dead=False, record=None):
    def starter(argv, cwd):
        if record is not None:
            record.append({"argv": list(argv), "cwd": cwd})
        return FakeProc(lines, pid=pid, dead=dead)
    return starter


def _exploding_starter(argv, cwd):
    raise AssertionError(f"starter must NOT run a blocked command: {argv}")


class ServerBase(unittest.TestCase):
    def setUp(self):
        server.stop_all()
        server._servers.clear()
        server._id_counter = itertools.count(1)

    def tearDown(self):
        server.stop_all()
        server._servers.clear()


# ── URL detection (pure) ──────────────────────────────────────────────────────
class UrlDetectionTests(unittest.TestCase):
    def test_variants(self):
        cases = {
            "Serving Flask app on http://127.0.0.1:5000": "http://127.0.0.1:5000",
            "  Local:   http://localhost:5173/": "http://localhost:5173/",
            "App running on port 4000": "http://127.0.0.1:4000",
            "Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C)": "http://127.0.0.1:8080",
        }
        for line, expected in cases.items():
            self.assertEqual(server._detect_url(line), expected, line)
        self.assertIsNone(server._detect_url("nothing to see here"))


# ── supervisor (fake starter) ─────────────────────────────────────────────────
class SupervisorTests(ServerBase):
    def test_start_detects_url_and_tracks(self):
        rec = []
        starter = make_starter(["booting...", "Local: http://localhost:3000"], record=rec)
        with server.use_starter(starter):
            h = server.start("npm run dev", ["npm", "run", "dev"], cwd="/ws", url_timeout=2)
        self.assertEqual(h["status"], "success")
        self.assertEqual(h["id"], "srv-1")
        self.assertEqual(h["detected_url"], "http://localhost:3000")
        self.assertTrue(h["alive"])
        self.assertEqual(rec[0]["cwd"], "/ws")          # cwd pinned
        self.assertEqual(rec[0]["argv"], ["npm", "run", "dev"])  # argv list (shell=False)

    def test_status_and_logs(self):
        starter = make_starter(["line1", "http://127.0.0.1:8000", "line3"])
        with server.use_starter(starter):
            h = server.start("py", ["python", "-m", "http.server"], cwd="/ws", url_timeout=2)
        with server.use_prober(lambda host, port, timeout: True):
            st = server.status(h["id"])
        self.assertTrue(st["alive"])
        self.assertEqual(st["port"], 8000)
        self.assertTrue(st["healthy"])          # mocked prober
        lg = server.logs(h["id"], tail_n=2)
        self.assertEqual(len(lg["lines"]), 2)

    def test_health_probe_down(self):
        starter = make_starter(["http://127.0.0.1:9999"])
        with server.use_starter(starter):
            h = server.start("x", ["python"], cwd="/ws", url_timeout=2)
        with server.use_prober(lambda host, port, timeout: False):
            st = server.status(h["id"])
        self.assertFalse(st["healthy"])

    def test_stop_is_graceful_then_removes(self):
        starter = make_starter(["http://localhost:3000"])
        with server.use_starter(starter):
            h = server.start("x", ["node", "s.js"], cwd="/ws", url_timeout=2)
        proc = server._servers[h["id"]].proc
        res = server.stop(h["id"])
        self.assertTrue(res["stopped"])
        self.assertTrue(proc.terminated)                 # graceful terminate first
        self.assertNotIn(h["id"], server._servers)       # removed from registry
        self.assertEqual(server.status(h["id"])["marker"], "SERVER_NOT_FOUND")

    def test_stop_force_kills_when_terminate_ignored(self):
        class StubbornProc(FakeProc):
            def terminate(self):
                self.terminated = True   # ignores terminate; stays alive
            def wait(self, timeout=None):
                if self._rc is None and not self.killed:
                    raise TimeoutError("still running")
                return self._rc
        with server.use_starter(lambda argv, cwd: StubbornProc(["http://localhost:3000"])):
            h = server.start("x", ["node"], cwd="/ws", url_timeout=2)
        proc = server._servers[h["id"]].proc
        server.stop(h["id"])
        self.assertTrue(proc.killed)                     # escalated to kill

    def test_stop_all_clears_registry(self):
        with server.use_starter(make_starter(["http://localhost:3000"])):
            server.start("a", ["node"], cwd="/ws", url_timeout=1)
            server.start("b", ["node"], cwd="/ws", url_timeout=1)
        self.assertEqual(len(server.list_running()), 2)
        server.stop_all()
        self.assertEqual(server.list_running(), [])

    def test_concurrent_cap_enforced(self):
        with patch.object(server, "SERVER_MAX_CONCURRENT", 2), \
             server.use_starter(make_starter(["http://localhost:3000"])):
            self.assertEqual(server.start("a", ["node"], cwd="/ws", url_timeout=1)["status"], "success")
            self.assertEqual(server.start("b", ["node"], cwd="/ws", url_timeout=1)["status"], "success")
            capped = server.start("c", ["node"], cwd="/ws", url_timeout=1)
        self.assertEqual(capped["marker"], "SERVER_CAP_REACHED")

    def test_stop_all_terminates_every_tracked_proc(self):
        # Orphan prevention: stop_all() (the same callable registered with atexit)
        # must terminate every tracked process and empty the registry.
        procs = []

        def starter(argv, cwd):
            p = FakeProc(["http://localhost:3000"])
            procs.append(p)
            return p

        with server.use_starter(starter):
            server.start("a", ["node"], cwd="/ws", url_timeout=1)
            server.start("b", ["node"], cwd="/ws", url_timeout=1)
        server.stop_all()
        self.assertEqual(server.list_running(), [])
        self.assertTrue(all(p.terminated or p.killed for p in procs))

    def test_start_reports_dead_process(self):
        with server.use_starter(make_starter(["crashed"], dead=True)):
            h = server.start("x", ["python", "bad.py"], cwd="/ws", url_timeout=1)
        self.assertFalse(h["alive"])
        self.assertIn("exited", h["message"].lower())


# ── guarded serve_* (tiering) ─────────────────────────────────────────────────
class GuardedServerTests(ServerBase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()
        super().tearDown()

    def test_medium_allowlisted_server_runs_when_approved(self):
        starter = make_starter(["Local: http://localhost:5173"])
        with hitl.use_approver(hitl.approve_all), server.use_starter(starter):
            res = guarded.serve_start({"command": "npm run dev"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["detected_url"], "http://localhost:5173")
        self.assertEqual(res["tier"], "MEDIUM")

    def test_non_allowlisted_server_is_high_and_confirms(self):
        seen = []

        def approver(p):
            seen.append(p.tier)
            return True

        with hitl.use_approver(approver), server.use_starter(make_starter(["up"])):
            res = guarded.serve_start({"command": "flask run"})   # flask unlisted -> HIGH
        self.assertEqual(res["status"], "success")
        self.assertEqual(seen, ["HIGH"])

    def test_critical_server_command_blocked_without_launch(self):
        with hitl.use_approver(hitl.approve_all), server.use_starter(_exploding_starter):
            res = guarded.serve_start({"command": "rm -rf /"})
        self.assertEqual(res["marker"], "CRITICAL_BLOCKED")

    def test_denied_server_does_not_launch(self):
        with hitl.use_approver(hitl.deny_all), server.use_starter(_exploding_starter):
            res = guarded.serve_start({"command": "npm run dev"})
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")

    def test_status_logs_stop_are_low_no_confirm(self):
        with hitl.use_approver(hitl.approve_all), server.use_starter(make_starter(["http://localhost:3000"])):
            started = guarded.serve_start({"command": "npm run dev"})
        sid = started["id"]
        # No approver installed here -> LOW tools must still work (no confirm).
        self.assertTrue(guarded.serve_status({"id": sid})["alive"])
        self.assertIn("lines", guarded.serve_logs({"id": sid}))
        self.assertTrue(guarded.serve_stop({"id": sid})["stopped"])

    def test_serve_start_requires_workspace(self):
        guarded.revoke_workspace()
        with hitl.use_approver(hitl.approve_all):
            res = guarded.serve_start({"command": "npm run dev"})
        self.assertEqual(res["marker"], "NO_WORKSPACE")


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


class AgentServerTests(ServerBase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()
        super().tearDown()

    def test_start_verify_report_url_and_list_servers(self):
        model = ScriptedModel([
            _plan(("serve_start", {"command": "npm run dev"})),
            _act("serve_start", command="npm run dev"),
            _act("serve_status", id="srv-1"),
            '{"finish":"server up at http://localhost:3000"}',
        ])
        with server.use_starter(make_starter(["Local: http://localhost:3000"])), \
             server.use_prober(lambda h, p, t: True):
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    shell_approver=hitl.deny_all).run("run the dev server")
        self.assertEqual(res["stopped"], "finish")
        # In-plan MEDIUM server auto-started (shell_approver denies -> proves auto).
        self.assertEqual(len(res["servers"]), 1)
        self.assertEqual(res["servers"][0]["url"], "http://localhost:3000")
        self.assertIn("serve_stop", res["servers"][0]["stop_with"])

    def test_out_of_plan_server_needs_confirmation(self):
        model = ScriptedModel([
            _plan(("serve_start", {"command": "npm run dev"})),
            _act("serve_start", command="python -m http.server 9000"),  # not in plan
            '{"finish":"done"}',
        ])
        with server.use_starter(_exploding_starter):
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    shell_approver=hitl.deny_all).run("serve")
        denied = [t for t in res["trace"] if t.get("gate") == "DENY:GUARDIAN_DENIED"]
        self.assertTrue(denied)
        self.assertEqual(res["servers"], [])

    def test_critical_server_blocked_in_loop_even_under_approve_all(self):
        model = ScriptedModel([
            _plan(("serve_start", {"command": "npm run dev"})),
            _act("serve_start", command="sudo npm run dev"),
            '{"finish":"stopped"}',
        ])
        with server.use_starter(_exploding_starter):
            res = agent.CodingAgent(model, plan_approver=lambda p: True,
                                    shell_approver=hitl.approve_all).run("serve")
        blocked = [t for t in res["trace"] if t.get("gate") == "DENY:CRITICAL_BLOCKED"]
        self.assertTrue(blocked)


if __name__ == "__main__":
    unittest.main()
