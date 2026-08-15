"""Phase 2 tests: gated, jailed WRITE/EDIT tools for the coding agent.

Focus areas required by the spec:
  * jail escape on writes (../, absolute-outside, symlink/junction) is BLOCKED
    before any confirmation or disk mutation,
  * confirmation is REQUIRED — deny aborts, approve proceeds — proven with both
    the injectable approver and the request_permission() fallback,
  * edit_file exactly-once match rule; create-vs-overwrite semantics,
  * atomic writes (temp+rename, no residue), and unified-diff preview,
  * Guardian tiers: writes MEDIUM/HIGH + confirm; reads stay LOW (regression).
"""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from coding_agent import guarded, hitl
from cyber_engine.guardian.operator_guard import OperatorGuard


def _try_dir_link(target: str, link: str) -> bool:
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


class WriteToolBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        os.makedirs(os.path.join(self.root, "src"), exist_ok=True)
        with open(os.path.join(self.root, "src", "app.py"), "w", encoding="utf-8") as fh:
            fh.write("def main():\n    return 'MAGIC_TOKEN'\n")
        guarded.revoke_workspace()
        guarded.grant_workspace(self.root)

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def _read(self, rel):
        with open(os.path.join(self.root, rel), "r", encoding="utf-8") as fh:
            return fh.read()


class ConfirmationTests(WriteToolBase):
    def test_write_requires_confirmation_deny_aborts(self):
        with hitl.use_approver(hitl.deny_all):
            res = guarded.fs_write_file({"path": "new.txt", "content": "hello\n"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")
        self.assertFalse(os.path.exists(os.path.join(self.root, "new.txt")))

    def test_write_approve_proceeds(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_write_file({"path": "new.txt", "content": "hello\n"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(self._read("new.txt"), "hello\n")

    def test_overwrite_deny_keeps_original(self):
        with hitl.use_approver(hitl.deny_all):
            res = guarded.fs_write_file({"path": "src/app.py", "content": "WIPED"})
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")
        self.assertIn("MAGIC_TOKEN", self._read("src/app.py"))

    def test_no_approver_and_no_fallback_fails_safe_deny(self):
        # Direct hitl.confirm with neither approver nor fallback -> DENY, no input().
        proposal = hitl.WriteProposal("fs_write_file", "MEDIUM", "x.txt",
                                      "create", hitl.unified_diff("", "hi", "x.txt"))
        self.assertFalse(hitl.confirm(proposal))

    def test_fallback_request_permission_is_used_when_no_approver(self):
        # No approver installed -> the guarded write falls back to the Guardian's
        # request_permission() (the real human prompt), which we patch here.
        with patch.object(guarded._guardian, "request_permission", return_value=True) as rp:
            res = guarded.fs_write_file({"path": "viafallback.txt", "content": "ok"})
        rp.assert_called_once()
        self.assertEqual(res["status"], "success")
        self.assertEqual(self._read("viafallback.txt"), "ok")

    def test_fallback_request_permission_deny_blocks_write(self):
        with patch.object(guarded._guardian, "request_permission", return_value=False):
            res = guarded.fs_write_file({"path": "denied.txt", "content": "ok"})
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")
        self.assertFalse(os.path.exists(os.path.join(self.root, "denied.txt")))

    def test_diff_is_previewed_before_confirmation(self):
        captured = []

        def capturing_approver(proposal):
            captured.append(proposal)
            return True

        with hitl.use_approver(capturing_approver):
            guarded.fs_write_file({"path": "d.txt", "content": "line1\nline2\n"})
        self.assertEqual(len(captured), 1)
        self.assertIn("+line1", captured[0].diff)
        self.assertIn("+line2", captured[0].diff)


class CreateVsOverwriteTests(WriteToolBase):
    def test_create_new_file(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_create_file({"path": "fresh.txt", "content": "x"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(self._read("fresh.txt"), "x")

    def test_create_existing_fails_without_prompting(self):
        # Even with approve_all, an existing file is a semantic error (no write).
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_create_file({"path": "src/app.py", "content": "x"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "FILE_EXISTS")
        self.assertIn("MAGIC_TOKEN", self._read("src/app.py"))

    def test_write_overwrites_existing(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_write_file({"path": "src/app.py", "content": "new body\n"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(self._read("src/app.py"), "new body\n")


class EditFileTests(WriteToolBase):
    def test_edit_exactly_one_match_succeeds(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_edit_file({"path": "src/app.py",
                                        "old_str": "MAGIC_TOKEN", "new_str": "NEW_TOKEN"})
        self.assertEqual(res["status"], "success")
        body = self._read("src/app.py")
        self.assertIn("NEW_TOKEN", body)
        self.assertNotIn("MAGIC_TOKEN", body)

    def test_edit_zero_matches_fails(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_edit_file({"path": "src/app.py",
                                        "old_str": "NOPE", "new_str": "X"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "NO_MATCH")
        self.assertIn("MAGIC_TOKEN", self._read("src/app.py"))

    def test_edit_multiple_matches_fails(self):
        with open(os.path.join(self.root, "dup.txt"), "w", encoding="utf-8") as fh:
            fh.write("AA\nAA\n")
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_edit_file({"path": "dup.txt", "old_str": "AA", "new_str": "B"})
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["marker"], "MULTIPLE_MATCHES")
        self.assertEqual(res["matches"], 2)
        self.assertEqual(self._read("dup.txt"), "AA\nAA\n")

    def test_edit_empty_old_str_rejected(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_edit_file({"path": "src/app.py", "old_str": "", "new_str": "X"})
        self.assertEqual(res["marker"], "EMPTY_OLD_STR")


class MakeDirAndDeleteTests(WriteToolBase):
    def test_make_dir_creates_directory(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_make_dir({"path": "pkg/sub"})
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.isdir(os.path.join(self.root, "pkg", "sub")))

    def test_make_dir_existing_is_error(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_make_dir({"path": "src"})
        self.assertEqual(res["marker"], "DIR_EXISTS")

    def test_delete_file_high_risk_approve(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_delete_file({"path": "src/app.py"})
        self.assertEqual(res["status"], "success")
        self.assertTrue(res.get("deleted"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "src", "app.py")))

    def test_delete_deny_keeps_file(self):
        with hitl.use_approver(hitl.deny_all):
            res = guarded.fs_delete_file({"path": "src/app.py"})
        self.assertEqual(res["marker"], "GUARDIAN_DENIED")
        self.assertTrue(os.path.exists(os.path.join(self.root, "src", "app.py")))

    def test_delete_directory_refused(self):
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_delete_file({"path": "src"})
        self.assertEqual(res["marker"], "IS_A_DIRECTORY")


class AtomicityTests(WriteToolBase):
    def test_write_leaves_no_temp_residue(self):
        with hitl.use_approver(hitl.approve_all):
            guarded.fs_write_file({"path": "src/app.py", "content": "brand new\n"})
        leftovers = [f for f in os.listdir(os.path.join(self.root, "src"))
                     if f.startswith(".fs_tmp_")]
        self.assertEqual(leftovers, [])
        self.assertEqual(self._read("src/app.py"), "brand new\n")

    def test_write_content_is_exact_utf8(self):
        payload = "héllo — ünïçödé\n\ttab\n"
        with hitl.use_approver(hitl.approve_all):
            guarded.fs_write_file({"path": "u.txt", "content": payload})
        with open(os.path.join(self.root, "u.txt"), "rb") as fh:
            self.assertEqual(fh.read().decode("utf-8"), payload)


class WriteJailEscapeTests(WriteToolBase):
    """Escapes must be blocked for writes too — caught at plan time, BEFORE any
    confirmation (so even deny_all yields SANDBOX_VIOLATION, not GUARDIAN_DENIED),
    and nothing is ever written outside the jail."""

    def setUp(self):
        super().setUp()
        self._outside = tempfile.TemporaryDirectory()
        self.outside = os.path.realpath(self._outside.name)

    def tearDown(self):
        self._outside.cleanup()
        super().tearDown()

    def test_dotdot_write_blocked(self):
        with hitl.use_approver(hitl.deny_all):
            res = guarded.fs_write_file({"path": "../evil.txt", "content": "x"})
        self.assertEqual(res["marker"], "SANDBOX_VIOLATION")
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.root), "evil.txt")))

    def test_absolute_outside_write_blocked(self):
        target = os.path.join(self.outside, "evil.txt")
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_write_file({"path": target, "content": "x"})
        self.assertEqual(res["marker"], "SANDBOX_VIOLATION")
        self.assertFalse(os.path.exists(target))

    def test_all_write_tools_reject_escape(self):
        bad = "../evil.txt"
        with hitl.use_approver(hitl.approve_all):
            calls = [
                guarded.fs_write_file({"path": bad, "content": "x"}),
                guarded.fs_create_file({"path": bad, "content": "x"}),
                guarded.fs_edit_file({"path": bad, "old_str": "a", "new_str": "b"}),
                guarded.fs_make_dir({"path": "../evildir"}),
                guarded.fs_delete_file({"path": bad}),
            ]
        for res in calls:
            self.assertEqual(res["marker"], "SANDBOX_VIOLATION", res)

    def test_symlink_junction_write_escape_blocked(self):
        link = os.path.join(self.root, "escape")
        if not _try_dir_link(self.outside, link):
            self.skipTest("directory-link creation unavailable on this host")
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_write_file({"path": "escape/evil.txt", "content": "x"})
        self.assertEqual(res["marker"], "SANDBOX_VIOLATION")
        self.assertFalse(os.path.exists(os.path.join(self.outside, "evil.txt")))

    def test_write_requires_workspace(self):
        guarded.revoke_workspace()
        with hitl.use_approver(hitl.approve_all):
            res = guarded.fs_write_file({"path": "x.txt", "content": "y"})
        self.assertEqual(res["marker"], "NO_WORKSPACE")


class WriteGuardianTierTests(unittest.TestCase):
    def setUp(self):
        self.guard = OperatorGuard()

    def test_write_actions_are_medium_and_require_confirm(self):
        for action in ("fs_write_file", "fs_create_file", "fs_edit_file", "fs_make_dir"):
            a = self.guard.assess_action(action, "p")
            self.assertEqual(a["risk_level"], "medium", action)
            self.assertTrue(a["requires_confirmation"], action)

    def test_delete_is_high_and_requires_confirm(self):
        a = self.guard.assess_action("fs_delete_file", "p")
        self.assertEqual(a["risk_level"], "high")
        self.assertTrue(a["requires_confirmation"])

    def test_reads_stay_low_regression(self):
        for action in ("fs_list_dir", "fs_read_file", "fs_search"):
            a = self.guard.assess_action(action, "p")
            self.assertEqual(a["risk_level"], "low", action)
            self.assertFalse(a["requires_confirmation"], action)


class WriteRegistryTests(unittest.TestCase):
    def setUp(self):
        from tools.registry import ToolRegistry
        self.registry = ToolRegistry()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        guarded.revoke_workspace()

    def tearDown(self):
        guarded.revoke_workspace()
        self._tmp.cleanup()

    def test_write_tools_registered_with_definitions(self):
        for name in ("fs_write_file", "fs_create_file", "fs_edit_file",
                     "fs_make_dir", "fs_delete_file"):
            self.assertIn(name, self.registry.list_tools())
            self.assertIn(name, self.registry.get_tool_definitions())

    def test_execute_write_through_registry_path(self):
        self.registry.grant_workspace(self.root)
        with hitl.use_approver(hitl.approve_all):
            out = self.registry.execute("fs_create_file",
                                        {"path": "hello.txt", "content": "hi"})
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["result"]["status"], "success")
        with open(os.path.join(self.root, "hello.txt"), "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "hi")


if __name__ == "__main__":
    unittest.main()
