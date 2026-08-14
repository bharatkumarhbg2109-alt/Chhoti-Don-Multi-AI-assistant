"""Chhoti Don — Coding Agent (Phase 1: sandboxed read-only workspace tools).

A self-extension of the assistant that can eventually read, reason about, and
(in later phases) edit a granted code folder. Phase 1 ships ONLY the security
core and read-only capabilities:

  * WorkspaceSandbox — a symlink-resolving path jail around one granted folder.
  * Three read-only tools — list_dir / read_file / search — all path-jailed.
  * Guarded wrappers — the single choke point, routed through the same Guardian
    as the browser layer; these read-only fs actions are LOW risk (auto-allow).

There is intentionally NO file-writing, NO shell execution, and NO agent loop in
this phase. The guarded wrappers (fs_list_dir / fs_read_file / fs_search) are the
only sanctioned entry points and are what tools/registry.py registers.
"""

from .sandbox import SandboxViolation, WorkspaceSandbox
from .guarded import (
    fs_list_dir, fs_read_file, fs_search,
    grant_workspace, revoke_workspace, active_workspace,
)

__all__ = [
    "SandboxViolation", "WorkspaceSandbox",
    "fs_list_dir", "fs_read_file", "fs_search",
    "grant_workspace", "revoke_workspace", "active_workspace",
]
