"""Read-only workspace tools, all path-jailed through a WorkspaceSandbox.

These are the *raw* implementations (they take an explicit sandbox). The
guarded wrappers in ``coding_agent.guarded`` add the Guardian risk-tier gate and
are what the ToolRegistry actually registers. Nothing in this module can write,
delete, move, or execute anything — it only reads directory structure and file
text. Every path is validated by ``sandbox.resolve`` before any I/O, and every
result is bounded by the caps in ``coding_agent.config``.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from . import config
from .sandbox import SandboxViolation, WorkspaceSandbox


# ── list_dir ──────────────────────────────────────────────────────────────────
def list_dir(sandbox: WorkspaceSandbox, path: str = ".",
             max_depth: Optional[int] = None) -> Dict[str, Any]:
    """Walk a directory tree inside the workspace and return its structure.

    Heavy dirs (``node_modules``, ``.git``, ``__pycache__``, ``venv``, ``.venv``,
    …) are pruned. Output is capped at ``config.LIST_MAX_ENTRIES`` entries and
    ``config.LIST_MAX_DEPTH`` levels (both overridable via the ``max_depth`` arg /
    env). Symlinked directories are listed but never traversed, and any entry
    whose real path escapes the jail is skipped.
    """
    depth_cap = config.LIST_MAX_DEPTH if max_depth is None else max(0, int(max_depth))
    start = sandbox.resolve(path)
    if not os.path.isdir(start):
        return {"status": "error", "marker": "NOT_A_DIRECTORY",
                "path": sandbox.relpath(start) if os.path.exists(start) else str(path)}

    entries: List[Dict[str, Any]] = []
    truncated = False

    for root, dirs, files in os.walk(start, followlinks=False):
        rel_root = os.path.relpath(root, start)
        # depth == 1 for the immediate children of the workspace root, 2 for the
        # next level down, and so on (root itself is depth 0).
        seg = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        depth = seg + 1

        # Entries at this level are already deeper than the cap — should have been
        # pruned by the parent; skip as a safety net.
        if depth > depth_cap:
            dirs[:] = []
            continue

        # Prune heavy dirs, then keep only children that stay inside the jail.
        # `safe_dirs` drives BOTH listing and recursion, so os.walk can never
        # descend through a symlink/junction that points outside the workspace.
        safe_dirs: List[str] = []
        for name in sorted(d for d in dirs if d not in config.IGNORED_DIRS):
            full = os.path.join(root, name)
            try:
                real = sandbox.resolve(os.path.relpath(full, sandbox.root))
            except SandboxViolation:
                continue  # symlinked/junction dir pointing outside the jail — skip
            safe_dirs.append(name)
            entries.append({
                "path": sandbox.relpath(real),
                "type": "dir",
                "depth": depth,
                "symlink": os.path.islink(full),
            })
            if len(entries) >= config.LIST_MAX_ENTRIES:
                truncated = True
                break

        # At the depth cap we still listed these dirs but do not descend.
        dirs[:] = [] if (truncated or depth >= depth_cap) else safe_dirs
        if truncated:
            break

        for name in sorted(files):
            full = os.path.join(root, name)
            try:
                real = sandbox.resolve(os.path.relpath(full, sandbox.root))
            except SandboxViolation:
                continue
            try:
                size = os.path.getsize(full) if not os.path.islink(full) else None
            except OSError:
                size = None
            entries.append({
                "path": sandbox.relpath(real),
                "type": "file",
                "depth": depth,
                "size": size,
                "symlink": os.path.islink(full),
            })
            if len(entries) >= config.LIST_MAX_ENTRIES:
                truncated = True
                break
        if truncated:
            break

    return {
        "status": "success",
        "root": sandbox.relpath(start),
        "count": len(entries),
        "entries": entries,
        "max_depth": depth_cap,
        "truncated": truncated,
        "tree": _render_tree(entries),
    }


def _render_tree(entries: List[Dict[str, Any]]) -> str:
    """Render entries as an indented tree text (purely for readability)."""
    lines = []
    for e in entries:
        indent = "  " * max(0, e.get("depth", 1) - 1)
        name = e["path"].rstrip("/").split("/")[-1] or e["path"]
        suffix = "/" if e["type"] == "dir" else ""
        link = " -> (symlink)" if e.get("symlink") else ""
        lines.append(f"{indent}{name}{suffix}{link}")
    return "\n".join(lines)


# ── read_file ─────────────────────────────────────────────────────────────────
def read_file(sandbox: WorkspaceSandbox, path: str,
              max_bytes: Optional[int] = None) -> Dict[str, Any]:
    """Read a text file inside the workspace, size-capped and line-numbered.

    Reads at most ``max_bytes`` (default ``config.READ_MAX_BYTES``); larger files
    are truncated and flagged. Bytes are decoded as UTF-8 with ``errors="replace"``
    so binary/mixed content never raises.
    """
    cap = config.READ_MAX_BYTES if max_bytes is None else max(0, int(max_bytes))
    real = sandbox.resolve(path)
    if not os.path.exists(real):
        return {"status": "error", "marker": "NOT_FOUND", "path": str(path)}
    if not os.path.isfile(real):
        return {"status": "error", "marker": "NOT_A_FILE", "path": sandbox.relpath(real)}

    total_size = os.path.getsize(real)
    with open(real, "rb") as fh:
        raw = fh.read(cap)
    truncated = total_size > len(raw)
    text = raw.decode("utf-8", errors="replace")

    numbered_lines = []
    for i, line in enumerate(text.splitlines(), start=1):
        numbered_lines.append(f"{i:>6}\t{line}")
    numbered = "\n".join(numbered_lines)

    return {
        "status": "success",
        "path": sandbox.relpath(real),
        "content": text,
        "numbered": numbered,
        "bytes_read": len(raw),
        "file_size": total_size,
        "line_count": text.count("\n") + 1 if text else 0,
        "truncated": truncated,
    }


# ── search ────────────────────────────────────────────────────────────────────
def search(sandbox: WorkspaceSandbox, query: str,
           glob: Optional[str] = None) -> Dict[str, Any]:
    """Grep-style search across the workspace.

    Uses ripgrep when available (fast), otherwise a pure-Python walk. Returns a
    capped list of ``{"file", "line", "match"}`` rows (also formatted as
    ``file:line:match`` strings). Heavy dirs are excluded and symlinks are never
    followed, so results can never point outside the jail.
    """
    query = "" if query is None else str(query)
    if not query:
        return {"status": "error", "marker": "EMPTY_QUERY"}

    rg = shutil.which("rg")
    if rg:
        results, truncated, engine = _search_ripgrep(sandbox, rg, query, glob)
    else:
        results, truncated, engine = _search_python(sandbox, query, glob)

    return {
        "status": "success",
        "query": query,
        "glob": glob,
        "engine": engine,
        "count": len(results),
        "results": results,
        "formatted": [f"{r['file']}:{r['line']}:{r['match']}" for r in results],
        "truncated": truncated,
    }


def _search_ripgrep(sandbox: WorkspaceSandbox, rg: str, query: str,
                    glob: Optional[str]):
    """ripgrep backend. `--no-follow` keeps symlinks unfollowed; explicit `-g`
    excludes mirror the pure-Python ignore list so both engines agree."""
    cmd = [rg, "--line-number", "--no-heading", "--color", "never",
           "--fixed-strings", "--no-follow", "--no-messages", "-i"]
    for d in sorted(config.IGNORED_DIRS):
        cmd += ["-g", f"!{d}/**", "-g", f"!{d}"]
    if glob:
        cmd += ["-g", glob]
    cmd += ["--", query, sandbox.root]

    results: List[Dict[str, Any]] = []
    truncated = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30)
    except (subprocess.SubprocessError, OSError):
        # Any ripgrep failure falls back to the always-available Python path.
        return _search_python(sandbox, query, glob)

    for line in proc.stdout.splitlines():
        # Format: <path>:<lineno>:<text>
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        fpath, lineno, text = parts
        try:
            real = sandbox.resolve(os.path.relpath(fpath, sandbox.root))
        except (SandboxViolation, ValueError):
            continue  # defence in depth — never surface a path outside the jail
        results.append({
            "file": sandbox.relpath(real),
            "line": int(lineno) if lineno.isdigit() else lineno,
            "match": text[:config.SEARCH_MAX_LINE_CHARS].strip(),
        })
        if len(results) >= config.SEARCH_MAX_RESULTS:
            truncated = True
            break
    return results, truncated, "ripgrep"


def _search_python(sandbox: WorkspaceSandbox, query: str, glob: Optional[str]):
    """Pure-Python fallback: case-insensitive substring match, line by line."""
    needle = query.lower()
    results: List[Dict[str, Any]] = []
    truncated = False

    for root, dirs, files in os.walk(sandbox.root, followlinks=False):
        # Prune heavy dirs AND any link/junction that resolves outside the jail so
        # the walk never leaves the workspace (os.walk does not stop at junctions).
        safe_dirs = []
        for d in dirs:
            if d in config.IGNORED_DIRS:
                continue
            try:
                sandbox.resolve(os.path.relpath(os.path.join(root, d), sandbox.root))
            except SandboxViolation:
                continue
            safe_dirs.append(d)
        dirs[:] = sorted(safe_dirs)
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, sandbox.root)
            if glob and not (fnmatch.fnmatch(name, glob)
                             or fnmatch.fnmatch(rel.replace(os.sep, "/"), glob)):
                continue
            try:
                real = sandbox.resolve(rel)
            except SandboxViolation:
                continue
            if os.path.islink(full) or not os.path.isfile(real):
                continue
            try:
                if os.path.getsize(real) > config.SEARCH_MAX_FILE_BYTES:
                    continue
                with open(real, "r", encoding="utf-8", errors="ignore") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if needle in line.lower():
                            results.append({
                                "file": rel.replace(os.sep, "/"),
                                "line": lineno,
                                "match": line[:config.SEARCH_MAX_LINE_CHARS].strip(),
                            })
                            if len(results) >= config.SEARCH_MAX_RESULTS:
                                truncated = True
                                break
            except (OSError, UnicodeError):
                continue
            if truncated:
                break
        if truncated:
            break
    return results, truncated, "python"
