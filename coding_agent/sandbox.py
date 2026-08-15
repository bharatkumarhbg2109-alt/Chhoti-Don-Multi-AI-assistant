"""Workspace sandbox — the security core of the coding agent.

Every filesystem path the coding agent touches is funnelled through a single
``WorkspaceSandbox.resolve`` call. The sandbox pins one granted folder as the
jail *root* (stored as an absolute, symlink-resolved realpath) and guarantees
that any resolved path stays strictly inside that root.

Three escape classes are blocked, and each is covered by a security test:

  1. ``../`` traversal   — ``os.path.realpath`` normalises the ``..`` segments,
                           then the containment check rejects anything above root.
  2. absolute-outside    — ``os.path.join(root, "/etc/passwd")`` (POSIX) or
                           ``os.path.join(root, r"C:\\Windows")`` (Windows) drops
                           the root; realpath + containment reject it.
  3. symlink escape      — realpath resolves *every* component, so a symlink that
                           points outside the jail resolves to its real target
                           and is rejected.

On any escape attempt the sandbox raises :class:`SandboxViolation` — a clear,
catchable error — and never performs I/O on the offending path.
"""

from __future__ import annotations

import os


class SandboxViolation(Exception):
    """Raised when a path resolves outside the granted workspace root.

    Carries the offending input and the resolved absolute path so callers can
    log/return a precise reason without re-deriving it.
    """

    def __init__(self, message: str, *, requested: str | None = None,
                 resolved: str | None = None) -> None:
        super().__init__(message)
        self.requested = requested
        self.resolved = resolved


def strip_bare_root(path: str) -> str:
    """Turn a BARE POSIX-root path into a workspace-relative one.

    Local models routinely emit paths like ``/src/main.py`` meaning "under the
    project root". A bare leading ``/`` (or lone ``\\``) has NO drive letter, so it
    is treated as workspace-relative: the leading slash(es) are stripped. Genuine
    drive-letter absolutes (``E:\\...``, ``C:/...``) and UNC paths (``\\\\server``,
    ``//server``) are left UNCHANGED so they remain real escapes — the caller's
    realpath-containment check still rejects them. This normalizes intent; it does
    NOT weaken the jail (``/../../../etc/passwd`` becomes ``../../../etc/passwd``,
    which realpath still resolves outside the root and blocks).
    """
    if not path:
        return path
    p = str(path)
    if len(p) >= 2 and p[1] == ":":       # drive-letter absolute (E:\, C:/) -> leave
        return p
    if p[:2] in ("\\\\", "//"):           # UNC (\\server, //server) -> leave
        return p
    if p[:1] in ("/", "\\"):              # bare POSIX root -> workspace-relative
        return p.lstrip("/\\")
    return p


class WorkspaceSandbox:
    """A path jail rooted at one granted folder.

    Args:
        root: The granted folder. Stored as ``os.path.realpath`` of its absolute,
            user-expanded form. Must be an existing directory.

    Raises:
        SandboxViolation: if ``root`` does not exist or is not a directory.
    """

    def __init__(self, root: str) -> None:
        if not root or not str(root).strip():
            raise SandboxViolation("Workspace root must be a non-empty path.")
        real_root = os.path.realpath(os.path.abspath(os.path.expanduser(str(root))))
        if not os.path.isdir(real_root):
            raise SandboxViolation(
                f"Workspace root is not an existing directory: {real_root}",
                requested=str(root), resolved=real_root,
            )
        self.root = real_root
        # Case/へ-normalised form used ONLY for containment comparison. On Windows
        # this lowercases the drive+path so a case-different escape can't slip by;
        # on POSIX normcase is a no-op. The proper-case ``self.root`` is what we
        # actually return to callers.
        self._root_cmp = os.path.normcase(real_root)

    # ------------------------------------------------------------------
    def _is_within(self, real_path: str) -> bool:
        """True iff ``real_path`` is the root itself or strictly beneath it."""
        cmp = os.path.normcase(real_path)
        if cmp == self._root_cmp:
            return True
        # The trailing separator is essential: without it "/rootX" would falsely
        # match a "/root" prefix. os.sep is '\\' on Windows, '/' on POSIX.
        return cmp.startswith(self._root_cmp + os.sep)

    def resolve(self, path: str = ".") -> str:
        """Resolve ``path`` against the jail root and assert it stays inside.

        ``path`` may be relative (joined onto the root) or absolute. Either way
        the result is passed through ``os.path.realpath`` — which normalises
        ``..`` segments AND resolves every symlink component — before the
        containment check. Non-existent tails are allowed (realpath simply
        normalises them); existence is the individual tool's concern.

        Returns:
            The absolute, symlink-resolved path, guaranteed inside the root.

        Raises:
            SandboxViolation: if the resolved path escapes the root.
        """
        requested = "." if path is None else str(path)
        # Normalize a bare POSIX-root path (/src -> src) to workspace-relative
        # FIRST; genuine drive-letter/UNC absolutes are left as-is and still fail
        # the containment check below. `.. ` traversal survives normalization and
        # is still caught by realpath containment.
        normalized = strip_bare_root(os.path.expanduser(requested)) or "."
        # os.path.join drops the root if `normalized` is (still) absolute — that is
        # intentional here: an absolute path outside the jail then fails the
        # containment check below rather than being silently re-rooted.
        candidate = os.path.join(self.root, normalized)
        real_path = os.path.realpath(candidate)
        if not self._is_within(real_path):
            raise SandboxViolation(
                f"Path escapes workspace root: {requested!r} -> {real_path}",
                requested=requested, resolved=real_path,
            )
        return real_path

    # ------------------------------------------------------------------
    def relpath(self, real_path: str) -> str:
        """Return ``real_path`` expressed relative to the jail root (POSIX-style).

        Used purely for presenting tool output; ``real_path`` is assumed to have
        already been produced by :meth:`resolve`.
        """
        rel = os.path.relpath(real_path, self.root)
        return "." if rel == "." else rel.replace(os.sep, "/")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"WorkspaceSandbox(root={self.root!r})"
