"""The single policy choke point for all coding-agent filesystem operations.

Mirrors ``browser/guarded.py``: the raw read-only tools in ``coding_agent.tools``
are NEVER called directly by the registry. Every call goes through a guarded
wrapper here, which:

  1. requires an explicitly granted workspace (the jail root),
  2. passes the action through the SAME Guardian as the browser layer
     (``OperatorGuard.assess_action``) — read-only fs actions are assigned the
     LOW risk tier and auto-allow, exactly like the ``web_`` read tools,
  3. logs the risk decision, then
  4. runs the raw tool with the active sandbox, converting any
     ``SandboxViolation`` into a structured, catchable error result.

Phase 1 is READ-ONLY. There is deliberately no write/delete/move/exec wrapper
here; adding one later must use a non-LOW action name so the Guardian forces a
confirmation, keeping this file the authoritative enforcement point.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from cyber_engine.guardian.operator_guard import OperatorGuard

from . import tools
from .sandbox import SandboxViolation, WorkspaceSandbox

logger = logging.getLogger("chhoti.coding_agent")

_guardian = OperatorGuard()

# Module-level active workspace (the jail root), set via grant_workspace(). Mirrors
# the module-level state browser/guarded.py keeps for its guardian/rate-limit.
_workspace: Optional[WorkspaceSandbox] = None


# ── workspace granting ────────────────────────────────────────────────────────
def grant_workspace(path: str) -> Dict[str, Any]:
    """Grant a folder as the coding agent's jail root.

    This is a control-plane operation (it DEFINES the sandbox), deliberately not
    one of the LOW-tier model tools. Returns the resolved absolute root or a
    structured error if the path is not an existing directory.
    """
    global _workspace
    try:
        _workspace = WorkspaceSandbox(path)
    except SandboxViolation as exc:
        return {"status": "error", "marker": "INVALID_WORKSPACE", "message": str(exc)}
    logger.info("[coding-agent] workspace granted root=%s", _workspace.root)
    return {"status": "success", "root": _workspace.root}


def revoke_workspace() -> None:
    """Clear the active workspace (used by tests and future session teardown)."""
    global _workspace
    _workspace = None


def active_workspace() -> Optional[WorkspaceSandbox]:
    return _workspace


# ── guarded gate ──────────────────────────────────────────────────────────────
def _gate(action: str, target: str) -> Optional[Dict[str, Any]]:
    """Guardian assessment + audit log. LOW-tier read-only fs actions auto-allow;
    only an action the Guardian flags for confirmation can be denied here."""
    assessment = _guardian.assess_action(action, target)
    decision = "ALLOW"
    if assessment["requires_confirmation"] and not _guardian.request_permission(action):
        decision = "GUARDIAN_DENIED"
    logger.info(
        "[coding-agent-guardian] action=%s target=%s risk=%s score=%s "
        "requires_confirmation=%s decision=%s",
        action, target, assessment["risk_level"], assessment["risk_score"],
        assessment["requires_confirmation"], decision,
    )
    if decision != "ALLOW":
        return {"status": "error", "marker": "GUARDIAN_DENIED", "guardian": assessment}
    return None


def _run(action: str, target: str, fn) -> Dict[str, Any]:
    """Shared wrapper body: require workspace, gate, run, trap SandboxViolation."""
    if _workspace is None:
        return {"status": "error", "marker": "NO_WORKSPACE",
                "message": "No workspace granted. Call grant_workspace(path) first."}
    blocked = _gate(action, target)
    if blocked:
        return blocked
    try:
        return fn(_workspace)
    except SandboxViolation as exc:
        # A jail escape attempt: deny cleanly, never touch the target path.
        logger.warning("[coding-agent-guardian] SANDBOX_VIOLATION action=%s target=%s -> %s",
                       action, target, exc)
        return {"status": "error", "marker": "SANDBOX_VIOLATION",
                "message": str(exc), "requested": exc.requested, "resolved": exc.resolved}


# ── LOW-tier read-only tools (registered in tools/registry.py with fs_ prefix) ──
def fs_list_dir(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded directory listing. LOW risk (auto-allow)."""
    data = input_data if isinstance(input_data, dict) else {"path": str(input_data)}
    path = str(data.get("path") or data.get("input") or ".")
    max_depth = data.get("max_depth")
    return _run("fs_list_dir", path,
                lambda sb: tools.list_dir(sb, path=path, max_depth=max_depth))


def fs_read_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded file read. LOW risk (auto-allow)."""
    data = input_data if isinstance(input_data, dict) else {"path": str(input_data)}
    path = str(data.get("path") or data.get("file_path") or data.get("input") or "")
    if not path:
        return {"status": "error", "marker": "MISSING_PATH",
                "message": "A 'path' is required for fs_read_file."}
    max_bytes = data.get("max_bytes")
    return _run("fs_read_file", path,
                lambda sb: tools.read_file(sb, path=path, max_bytes=max_bytes))


def fs_search(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded workspace search. LOW risk (auto-allow)."""
    data = input_data if isinstance(input_data, dict) else {"query": str(input_data)}
    query = str(data.get("query") or data.get("q") or data.get("input") or "")
    if not query:
        return {"status": "error", "marker": "EMPTY_QUERY",
                "message": "A 'query' is required for fs_search."}
    glob = data.get("glob")
    glob = str(glob) if glob else None
    return _run("fs_search", query,
                lambda sb: tools.search(sb, query=query, glob=glob))
