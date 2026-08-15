"""Behavioural + integration tests for the coding-agent read-only tools.

Covers: the three tools working inside a granted workspace, the guarded layer
converting jail escapes into structured errors (never raising), Guardian LOW-tier
assignment for the fs_ read actions, registry registration, and — importantly —
that NO write / delete / shell capability exists in this phase.
"""

import os
import subprocess
import tempfile
import unittest

from coding_agent import guarded
from cyber_engine.guardian.operator_guard import OperatorGuard


def _try_dir_link(target: str, link: str) -> bool:
    """Best-effort directory link (symlink, else Windows junction). False if none."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError, AttributeError):
        pass
    if os.name == "nt":
        proc = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                              capture_output=True, text=True)
        return proc.returncode == 0 and os.path.exists(link)
    return False


def _build_workspace(root: str) -> None:
    """Create a small sample project inside `root`."""
    os.makedirs(os.path.join(root, "src"), exist_ok=True)
    os.makedirs(os.path.join(root, "node_modules", "left-pad"), exist_ok=True)
    os.makedirs(os.path.join(root, ".git"), exist_ok=True)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# Sample\nTODO: write docs\n")
    with open(os.path.join(root, "src", "app.py"), "w", encoding="utf-8") as fh:
        fh.write("def main():\n    return 'MAGIC_TOKEN'\n")
    with open(os.path.join(root, "node_modules", "left-pad", "index.js"), "w",
              encoding="utf-8") as fh:
        fh.write("// MAGIC_TOKEN should be ignored under node_modules\n")


class CodingAgentToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        _build_workspace(self.root)
        guarded.revoke_workspace()

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    # ── granting ────────────────────────────────────────────────────────────────
    def test_grant_workspace_success(self):
        res = guarded.grant_workspace(self.root)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["root"], self.root)

    def test_grant_invalid_workspace(self):
        res = guarded.grant_workspace(os.path.join(self.root, "nope"))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "INVALID_WORKSPACE")

    def test_tools_require_a_granted_workspace(self):
        # No grant in this test -> every tool refuses cleanly.
        for res in (guarded.fs_list_dir({}), guarded.fs_read_file({"path": "README.md"}),
                    guarded.fs_search({"query": "x"})):
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["marker"], "NO_WORKSPACE")

    # ── fs_list_dir ─────────────────────────────────────────────────────────────
    def test_list_dir_lists_and_skips_heavy_dirs(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_list_dir({"path": "."})
        self.assertEqual(res["status"], "success")
        paths = {e["path"] for e in res["entries"]}
        self.assertIn("README.md", paths)
        self.assertIn("src", paths)
        self.assertIn("src/app.py", paths)
        # Heavy dirs pruned entirely.
        self.assertNotIn("node_modules", paths)
        self.assertFalse(any(p.startswith("node_modules") for p in paths))
        self.assertFalse(any(p.startswith(".git") for p in paths))

    def test_list_dir_respects_max_depth(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_list_dir({"path": ".", "max_depth": 1})
        # Depth 1 shows top-level dir `src` but not its children.
        paths = {e["path"] for e in res["entries"]}
        self.assertIn("src", paths)
        self.assertNotIn("src/app.py", paths)

    # ── fs_read_file ────────────────────────────────────────────────────────────
    def test_read_file_returns_numbered_content(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_read_file({"path": "src/app.py"})
        self.assertEqual(res["status"], "success")
        self.assertIn("MAGIC_TOKEN", res["content"])
        self.assertIn("     1\t", res["numbered"])
        self.assertFalse(res["truncated"])

    def test_read_file_enforces_max_bytes(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_read_file({"path": "src/app.py", "max_bytes": 5})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["bytes_read"], 5)
        self.assertTrue(res["truncated"])

    def test_read_missing_file(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_read_file({"path": "src/missing.py"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "NOT_FOUND")

    # ── fs_search ───────────────────────────────────────────────────────────────
    def test_search_finds_matches_as_file_line_match(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_search({"query": "MAGIC_TOKEN"})
        self.assertEqual(res["status"], "success")
        files = {r["file"] for r in res["results"]}
        self.assertIn("src/app.py", files)
        # node_modules hit must be excluded.
        self.assertFalse(any("node_modules" in f for f in files))
        # Formatted rows look like file:line:match.
        self.assertTrue(all(row.count(":") >= 2 for row in res["formatted"]))

    def test_search_glob_filter(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_search({"query": "TODO", "glob": "*.md"})
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["results"])
        self.assertTrue(all(r["file"].endswith(".md") for r in res["results"]))

    def test_search_empty_query(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_search({"query": ""})
        self.assertEqual(res["marker"], "EMPTY_QUERY")

    # ── guarded layer converts jail escapes to structured errors ────────────────
    def test_guarded_read_escape_returns_violation_marker(self):
        guarded.grant_workspace(self.root)
        for bad in ("../../etc/passwd", "..\\..\\secret", "/etc/passwd"):
            res = guarded.fs_read_file({"path": bad})
            self.assertEqual(res["status"], "error", bad)
            # Either it escaped the jail (violation) or simply doesn't exist inside
            # it — never a success, never an unhandled raise.
            self.assertIn(res["marker"], {"SANDBOX_VIOLATION", "NOT_FOUND"}, bad)

    def test_guarded_list_escape_returns_violation_marker(self):
        guarded.grant_workspace(self.root)
        res = guarded.fs_list_dir({"path": ".."})
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "SANDBOX_VIOLATION")

    def test_link_escape_never_surfaces_outside_content(self):
        # Defence in depth: a link inside the workspace that points OUTSIDE must
        # not leak the outside file's contents through any read-only tool.
        outside = tempfile.TemporaryDirectory()
        try:
            outside_root = os.path.realpath(outside.name)
            with open(os.path.join(outside_root, "secret.txt"), "w", encoding="utf-8") as fh:
                fh.write("TOP_SECRET_LEAK\n")
            link = os.path.join(self.root, "escape")
            if not _try_dir_link(outside_root, link):
                self.skipTest("directory-link creation unavailable on this host")

            guarded.grant_workspace(self.root)
            # list_dir must not include the escaping link's outside children.
            listing = guarded.fs_list_dir({"path": "."})
            self.assertEqual(listing["status"], "success")
            self.assertFalse(any("secret.txt" in e["path"] for e in listing["entries"]))
            # reading through the link is rejected (escape) — never returns content.
            read = guarded.fs_read_file({"path": "escape/secret.txt"})
            self.assertEqual(read["status"], "error")
            self.assertEqual(read["marker"], "SANDBOX_VIOLATION")
            # search must not surface the outside secret either.
            found = guarded.fs_search({"query": "TOP_SECRET_LEAK"})
            self.assertEqual(found["count"], 0)
        finally:
            outside.cleanup()


class GuardianTierTests(unittest.TestCase):
    """The three fs_ read actions must be LOW-tier auto-allow; write actions not."""

    def setUp(self):
        self.guard = OperatorGuard()

    def test_readonly_fs_actions_are_low_and_autoallow(self):
        for action in ("fs_list_dir", "fs_read_file", "fs_search"):
            a = self.guard.assess_action(action, "some/path")
            self.assertEqual(a["risk_level"], "low", action)
            self.assertEqual(a["risk_score"], 10, action)
            self.assertFalse(a["requires_confirmation"], action)

    def test_state_changing_fs_actions_are_never_low(self):
        # Guards the safety posture: sharing an fs_ prefix must NOT grant the LOW
        # (auto-allow) tier. Real writes are medium/high; unknown fs_ actions are
        # "unknown" — but never "low".
        for action in ("fs_write_file", "fs_delete_file", "fs_move", "fs_exec"):
            a = self.guard.assess_action(action, "x")
            self.assertNotEqual(a["risk_level"], "low", action)

    def test_web_actions_still_low_regression(self):
        a = self.guard.assess_action("web_read", "https://example.com")
        self.assertEqual(a["risk_level"], "low")


class RegistryIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tools.registry import ToolRegistry
        self.registry = ToolRegistry()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        _build_workspace(self.root)
        guarded.revoke_workspace()

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def test_fs_tools_are_registered(self):
        for name in ("fs_list_dir", "fs_read_file", "fs_search"):
            self.assertIn(name, self.registry.list_tools())
            self.assertIn(name, self.registry.get_tool_definitions())

    def test_execute_through_registry_path(self):
        self.registry.grant_workspace(self.root)
        out = self.registry.execute("fs_read_file", {"path": "README.md"})
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["result"]["status"], "success")
        self.assertIn("Sample", out["result"]["content"])

    def test_only_gated_sh_run_shell_tool_exists(self):
        # Phase 4 adds command execution — but ONLY through the gated, classified
        # sh_run. No RAW/ungated exec tool may exist.
        registered = set(self.registry.list_tools())
        self.assertIn("sh_run", registered)
        forbidden = ("fs_exec", "fs_shell", "fs_system", "fs_spawn", "fs_popen",
                     "fs_eval", "run_shell", "shell_exec", "exec_command", "raw_run")
        self.assertTrue(registered.isdisjoint(forbidden),
                        f"unexpected raw shell/exec tool(s): {registered & set(forbidden)}")

    def test_local_server_tools_exist_but_no_tunnel_or_deploy(self):
        # Phase 5 adds LOCAL background servers via serve_*; there must be NO
        # tunnel / external-hosting / deploy tool anywhere.
        registered = set(self.registry.list_tools())
        for name in ("serve_start", "serve_status", "serve_logs", "serve_stop"):
            self.assertIn(name, registered)
        forbidden = ("tunnel", "ngrok", "cloudflared", "deploy", "publish",
                     "expose", "port_forward", "serve_public", "serve_remote")
        offenders = [t for t in registered if any(b in t for b in forbidden)]
        self.assertEqual(offenders, [], f"unexpected external/deploy tool(s): {offenders}")

    def test_coding_agent_exposes_only_gated_shell(self):
        import coding_agent
        exported = set(coding_agent.__all__)
        # The gated shell surface (sh_run) and the shell package are expected in
        # Phase 4; what must NEVER appear is a RAW/ungated command-exec helper.
        self.assertIn("sh_run", exported)
        raw_exec = ("os_system", "system_call", "run_shell", "shell_exec",
                    "exec_command", "raw_run", "popen", "subprocess_run", "spawn")
        offenders = [n for n in exported if any(b in n.lower() for b in raw_exec)]
        self.assertEqual(offenders, [], f"unexpected raw exec exports: {offenders}")


if __name__ == "__main__":
    unittest.main()
