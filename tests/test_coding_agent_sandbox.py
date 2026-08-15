"""Security tests for the coding-agent workspace jail (the most important part).

Proves the WorkspaceSandbox blocks all three escape classes required by Phase 1:
  * ``../`` traversal escapes
  * absolute paths outside the root
  * symlink escapes
and that a legitimate in-jail path resolves correctly.
"""

import os
import subprocess
import tempfile
import unittest

from coding_agent.sandbox import SandboxViolation, WorkspaceSandbox


def _make_dir_link(target: str, link: str) -> str:
    """Create a directory link `link` -> `target`, portably.

    Tries a real symlink first (POSIX, or Windows with the privilege). On Windows
    without that privilege, falls back to an NTFS junction (`mklink /J`), which a
    normal user can create and which ``os.path.realpath`` still resolves — so the
    symlink-escape protection is genuinely exercised on this host. Returns the
    kind ("symlink"/"junction") or raises to signal "no link possible".
    """
    try:
        os.symlink(target, link, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError, AttributeError):
        pass
    if os.name == "nt":
        proc = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                              capture_output=True, text=True)
        if proc.returncode == 0 and os.path.exists(link):
            return "junction"
        raise OSError(f"mklink /J failed: {proc.stderr or proc.stdout}")
    raise OSError("no directory-link mechanism available")


class WorkspaceSandboxSecurityTests(unittest.TestCase):
    def setUp(self):
        # A jail root and a separate "outside" dir (a sibling, never inside root).
        self._root_tmp = tempfile.TemporaryDirectory()
        self._outside_tmp = tempfile.TemporaryDirectory()
        # realpath so comparisons are stable across /var->/private/var, 8.3 names…
        self.root = os.path.realpath(self._root_tmp.name)
        self.outside = os.path.realpath(self._outside_tmp.name)

        # A real file and subdir inside the jail.
        os.makedirs(os.path.join(self.root, "src"), exist_ok=True)
        with open(os.path.join(self.root, "src", "app.py"), "w", encoding="utf-8") as fh:
            fh.write("print('hello')\n")
        # A secret OUTSIDE the jail that escapes must never reach.
        with open(os.path.join(self.outside, "secret.txt"), "w", encoding="utf-8") as fh:
            fh.write("TOP SECRET\n")

        self.sandbox = WorkspaceSandbox(self.root)

    def tearDown(self):
        self._root_tmp.cleanup()
        self._outside_tmp.cleanup()

    # ── construction ──────────────────────────────────────────────────────────
    def test_root_is_realpath_and_directory(self):
        self.assertEqual(self.sandbox.root, self.root)
        self.assertTrue(os.path.isdir(self.sandbox.root))

    def test_nonexistent_root_is_rejected(self):
        with self.assertRaises(SandboxViolation):
            WorkspaceSandbox(os.path.join(self.root, "does-not-exist"))

    def test_empty_root_is_rejected(self):
        with self.assertRaises(SandboxViolation):
            WorkspaceSandbox("")

    # ── legitimate resolves ─────────────────────────────────────────────────────
    def test_dot_resolves_to_root(self):
        self.assertEqual(self.sandbox.resolve("."), self.root)

    def test_valid_subpath_resolves_inside(self):
        resolved = self.sandbox.resolve("src/app.py")
        self.assertEqual(resolved, os.path.join(self.root, "src", "app.py"))
        self.assertTrue(resolved.startswith(self.root + os.sep))

    def test_nested_dotdot_that_stays_inside_is_allowed(self):
        # src/../src/app.py never leaves the jail -> allowed.
        resolved = self.sandbox.resolve("src/../src/app.py")
        self.assertEqual(resolved, os.path.join(self.root, "src", "app.py"))

    # ── escape class 1: ../ traversal ───────────────────────────────────────────
    def test_dotdot_traversal_is_blocked(self):
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("../secret.txt")

    def test_deep_dotdot_traversal_is_blocked(self):
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("src/../../secret.txt")

    def test_dotdot_to_outside_dir_basename_is_blocked(self):
        # ../<outside_basename>/secret.txt — reaches the sibling temp dir.
        rel = os.path.join("..", os.path.basename(self.outside), "secret.txt")
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve(rel)

    # ── escape class 2: absolute path outside root ──────────────────────────────
    def test_absolute_path_outside_is_blocked(self):
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve(os.path.join(self.outside, "secret.txt"))

    def test_absolute_system_path_is_blocked(self):
        target = r"C:\Windows\System32\drivers\etc\hosts" if os.name == "nt" else "/etc/passwd"
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve(target)

    def test_root_prefix_sibling_is_not_treated_as_inside(self):
        # A sibling dir whose name shares the root's prefix must NOT count as
        # inside (guards the "/rootX" vs "/root" startswith pitfall).
        sibling = self.root + "_sibling"
        os.makedirs(sibling, exist_ok=True)
        try:
            with self.assertRaises(SandboxViolation):
                self.sandbox.resolve(sibling)
        finally:
            os.rmdir(sibling)

    # ── Tuning pass 1: bare-root normalization (must NOT weaken the jail) ────────
    def test_bare_root_path_normalized_to_relative(self):
        # /src/app.py is treated as workspace-relative, resolving INSIDE the root.
        self.assertEqual(self.sandbox.resolve("/src/app.py"),
                         os.path.join(self.root, "src", "app.py"))
        self.assertEqual(self.sandbox.resolve("/"), self.root)

    def test_bare_root_with_traversal_still_escapes(self):
        # Stripping the leading slash must NOT let '..' climb out — realpath
        # containment still blocks it.
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("/../../../etc/passwd")
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("/../" + os.path.basename(self.outside) + "/secret.txt")

    def test_drive_letter_absolute_still_blocked(self):
        # Genuine drive-letter absolutes are NOT normalized -> still rejected.
        if os.name == "nt":
            for target in (r"C:\Windows\System32\drivers\etc\hosts",
                           os.path.join(self.outside, "secret.txt")):
                with self.assertRaises(SandboxViolation):
                    self.sandbox.resolve(target)

    # ── escape class 3: symlink escape ──────────────────────────────────────────
    def test_symlink_escape_is_blocked(self):
        link = os.path.join(self.root, "escape_link")
        try:
            kind = _make_dir_link(self.outside, link)
        except OSError as exc:
            self.skipTest(f"directory-link creation unavailable on this host: {exc}")
        # The link points outside; realpath resolves it -> must be rejected, both
        # at the link itself and at a path through it. (kind is symlink/junction.)
        self.assertIn(kind, ("symlink", "junction"))
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("escape_link")
        with self.assertRaises(SandboxViolation):
            self.sandbox.resolve("escape_link/secret.txt")

    def test_symlink_that_stays_inside_is_allowed(self):
        target = os.path.join(self.root, "src")
        link = os.path.join(self.root, "inside_link")
        try:
            _make_dir_link(target, link)
        except OSError as exc:
            self.skipTest(f"directory-link creation unavailable on this host: {exc}")
        resolved = self.sandbox.resolve("inside_link/app.py")
        self.assertEqual(resolved, os.path.join(self.root, "src", "app.py"))

    # ── the raised error is informative + catchable ─────────────────────────────
    def test_violation_carries_requested_and_resolved(self):
        try:
            self.sandbox.resolve("../secret.txt")
            self.fail("expected SandboxViolation")
        except SandboxViolation as exc:
            self.assertEqual(exc.requested, "../secret.txt")
            self.assertTrue(exc.resolved)
            # The resolved path is genuinely outside the jail root.
            self.assertNotEqual(exc.resolved, self.root)
            self.assertFalse(exc.resolved.startswith(self.root + os.sep))


if __name__ == "__main__":
    unittest.main()
