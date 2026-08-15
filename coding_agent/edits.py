"""State-changing workspace operations (Phase 2), all path-jailed + gated.

Split into *plan* and *commit* so the guarded layer can show a unified diff and
obtain human approval BEFORE anything touches disk:

  * ``plan_*``   — resolve+validate through the sandbox, compute the new content
                   and a unified diff, and return a :class:`WritePlan` (or a
                   structured error). No disk mutation happens here.
  * ``commit_plan`` — re-resolve for TOCTOU safety, then apply the change. File
                   writes are ATOMIC (temp file in the same dir + ``os.replace``)
                   and UTF-8.

Nothing here executes shell commands or moves/copies files — Phase 2 is limited
to write / create / edit / make_dir / delete. Directory paths are jailed exactly
like reads via ``sandbox.resolve``; an escape raises ``SandboxViolation`` before
any validation or I/O.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import config, hitl
from .sandbox import WorkspaceSandbox


@dataclass
class WritePlan:
    """A validated, not-yet-applied filesystem change plus its diff."""

    action: str
    tier: str            # MEDIUM | HIGH
    rel_path: str        # workspace-relative, for display/logging
    real_path: str       # absolute, sandbox-resolved
    summary: str
    diff: str
    kind: str = "file"   # "file" | "dir" | "delete"
    warning: str = ""
    new_bytes: Optional[bytes] = None  # None for dir / delete


def _err(marker: str, path: str, **extra: Any) -> Dict[str, Any]:
    return {"error": {"status": "error", "marker": marker, "path": path, **extra}}


def _read_text_full(real_path: str) -> str:
    """Read a file whole as UTF-8 (errors replaced). Full read is required so
    edit-match counting and overwrite diffs are correct, never truncated."""
    with open(real_path, "rb") as fh:
        return fh.read().decode("utf-8", errors="replace")


# ── plans ─────────────────────────────────────────────────────────────────────
def plan_write_file(sandbox: WorkspaceSandbox, path: str, content: str) -> Dict[str, Any]:
    """Create-or-overwrite the full content of a file."""
    real = sandbox.resolve(path)
    rel = sandbox.relpath(real)
    if os.path.isdir(real):
        return _err("IS_A_DIRECTORY", rel)
    new_text = "" if content is None else str(content)
    existed = os.path.isfile(real)
    old_text = _read_text_full(real) if existed else ""
    diff = hitl.unified_diff(old_text, new_text, rel)
    summary = (f"overwrite existing file ({len(old_text)}→{len(new_text)} chars)"
               if existed else f"create new file ({len(new_text)} chars)")
    return {"plan": WritePlan("fs_write_file", "MEDIUM", rel, real, summary, diff,
                              kind="file", new_bytes=new_text.encode("utf-8"))}


def plan_create_file(sandbox: WorkspaceSandbox, path: str, content: str) -> Dict[str, Any]:
    """Create a file ONLY if it does not already exist."""
    real = sandbox.resolve(path)
    rel = sandbox.relpath(real)
    if os.path.exists(real):
        return _err("FILE_EXISTS", rel,
                    message="File already exists; use fs_write_file to overwrite.")
    new_text = "" if content is None else str(content)
    diff = hitl.unified_diff("", new_text, rel)
    summary = f"create new file ({len(new_text)} chars)"
    return {"plan": WritePlan("fs_create_file", "MEDIUM", rel, real, summary, diff,
                              kind="file", new_bytes=new_text.encode("utf-8"))}


def plan_edit_file(sandbox: WorkspaceSandbox, path: str,
                   old_str: str, new_str: str) -> Dict[str, Any]:
    """Surgical replace: ``old_str`` must match EXACTLY ONCE."""
    real = sandbox.resolve(path)
    rel = sandbox.relpath(real)
    if not os.path.exists(real):
        return _err("NOT_FOUND", rel)
    if not os.path.isfile(real):
        return _err("NOT_A_FILE", rel)
    if old_str is None or old_str == "":
        return _err("EMPTY_OLD_STR", rel,
                    message="old_str must be a non-empty string.")
    new_str = "" if new_str is None else str(new_str)
    old_text = _read_text_full(real)
    count = old_text.count(old_str)
    if count == 0:
        return _err("NO_MATCH", rel,
                    message="old_str not found in file.")
    if count > 1:
        return _err("MULTIPLE_MATCHES", rel, matches=count,
                    message=f"old_str matches {count} times; it must match exactly once.")
    new_text = old_text.replace(old_str, new_str, 1)
    # Per spec: diff the old_str region -> new_str.
    diff = hitl.unified_diff(str(old_str), new_str, rel)
    summary = f"replace 1 occurrence ({len(old_str)}→{len(new_str)} chars)"
    return {"plan": WritePlan("fs_edit_file", "MEDIUM", rel, real, summary, diff,
                              kind="file", new_bytes=new_text.encode("utf-8"))}


def plan_make_dir(sandbox: WorkspaceSandbox, path: str) -> Dict[str, Any]:
    """Create a directory (parents allowed)."""
    real = sandbox.resolve(path)
    rel = sandbox.relpath(real)
    if os.path.isdir(real):
        return _err("DIR_EXISTS", rel, message="Directory already exists.")
    if os.path.exists(real):
        return _err("PATH_IS_A_FILE", rel, message="A file already exists at this path.")
    summary = "create directory (with parents)"
    diff = f"+ (dir) {rel}/"
    return {"plan": WritePlan("fs_make_dir", "MEDIUM", rel, real, summary, diff,
                              kind="dir", new_bytes=None)}


def plan_delete_file(sandbox: WorkspaceSandbox, path: str) -> Dict[str, Any]:
    """Delete a single file (HIGH risk)."""
    real = sandbox.resolve(path)
    rel = sandbox.relpath(real)
    if not os.path.exists(real):
        return _err("NOT_FOUND", rel)
    if os.path.isdir(real):
        return _err("IS_A_DIRECTORY", rel,
                    message="Refusing to delete a directory (file delete only).")
    old_text = _read_text_full(real)
    diff = hitl.unified_diff(old_text, "", rel)
    summary = f"delete file ({os.path.getsize(real)} bytes)"
    warning = "This permanently deletes the file and cannot be undone."
    return {"plan": WritePlan("fs_delete_file", "HIGH", rel, real, summary, diff,
                              kind="delete", warning=warning, new_bytes=None)}


# ── commit ────────────────────────────────────────────────────────────────────
def _atomic_write(real_path: str, data: bytes) -> None:
    """Write ``data`` to ``real_path`` atomically: temp file in the SAME dir,
    fsync, then ``os.replace`` (atomic on the same filesystem)."""
    parent = os.path.dirname(real_path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".fs_tmp_", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, real_path)
    except BaseException:
        # Never leave a temp turd behind if the write/rename fails.
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def commit_plan(sandbox: WorkspaceSandbox, plan: WritePlan) -> Dict[str, Any]:
    """Apply an approved plan. Re-resolves the path so a jail escape can never
    slip in between planning and commit (raises SandboxViolation if so)."""
    real = sandbox.resolve(plan.rel_path)

    if plan.kind == "dir":
        os.makedirs(real, exist_ok=True)
        return {"status": "success", "action": plan.action, "path": plan.rel_path,
                "created_dir": True, "diff": plan.diff}

    if plan.kind == "delete":
        if not os.path.isfile(real):
            return {"status": "error", "marker": "NOT_FOUND", "path": plan.rel_path}
        os.remove(real)
        return {"status": "success", "action": plan.action, "path": plan.rel_path,
                "deleted": True, "diff": plan.diff}

    # file write (create / overwrite / edit)
    if plan.action == "fs_create_file" and os.path.exists(real):
        # TOCTOU re-check: something created the file after we planned.
        return {"status": "error", "marker": "FILE_EXISTS", "path": plan.rel_path}
    data = plan.new_bytes if plan.new_bytes is not None else b""
    _atomic_write(real, data)
    return {"status": "success", "action": plan.action, "path": plan.rel_path,
            "bytes_written": len(data), "diff": plan.diff}
