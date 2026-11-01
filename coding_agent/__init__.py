"""Chhoti Don — Coding Agent (Phase 1 read-only + Phase 2 gated writes).

A self-extension of the assistant that can read, reason about, and edit a granted
code folder. Shipped so far:

  * WorkspaceSandbox — a symlink-resolving path jail around one granted folder.
  * Read-only tools (LOW, auto-allow) — list_dir / read_file / search.
  * Write tools (Phase 2) — write / create / edit / make_dir (MEDIUM) and
    delete (HIGH). Every write is path-jailed AND passes the guarded choke point,
    which shows a unified diff and requires human confirmation (never auto-allow).

There is still NO shell execution and NO agent loop. The guarded wrappers are the
only sanctioned entry points and are what tools/registry.py registers; write
confirmation is made testable via coding_agent.hitl's injectable approver.
"""

from .sandbox import SandboxViolation, WorkspaceSandbox
from . import hitl, shell, server, deploy, interactive
from .guarded import (
    fs_list_dir, fs_read_file, fs_search,
    fs_write_file, fs_create_file, fs_edit_file, fs_make_dir, fs_delete_file,
    sh_run,
    serve_start, serve_status, serve_logs, serve_stop,
    deploy_check, deploy_run,
    grant_workspace, revoke_workspace, active_workspace,
)
from .agent import CodingAgent, run_build, is_build_request, AGENT_SYSTEM_PROMPT

__all__ = [
    "SandboxViolation", "WorkspaceSandbox", "hitl", "shell", "server", "deploy", "interactive",
    # read-only (LOW)
    "fs_list_dir", "fs_read_file", "fs_search",
    # writes (MEDIUM/HIGH, confirmed)
    "fs_write_file", "fs_create_file", "fs_edit_file", "fs_make_dir", "fs_delete_file",
    # gated shell (Phase 4: MEDIUM/HIGH, CRITICAL hard-blocked)
    "sh_run",
    # gated local servers (Phase 5: serve_start gated; status/logs/stop LOW)
    "serve_start", "serve_status", "serve_logs", "serve_stop",
    # public deploy (Phase 6: deploy_run ALWAYS individual-confirm; check is read-only)
    "deploy_check", "deploy_run",
    # workspace control-plane
    "grant_workspace", "revoke_workspace", "active_workspace",
    # Phase 3 builder loop + Phase 4 self-heal
    "CodingAgent", "run_build", "is_build_request", "AGENT_SYSTEM_PROMPT",
]
