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

from . import deploy, edits, hitl, server, shell, tools
from .config import (DEPLOY_OUTPUT_CAP, DEPLOY_TIMEOUT_S,
                     SHELL_OUTPUT_CAP, SHELL_TIMEOUT_S)
from .sandbox import SandboxViolation, WorkspaceSandbox

logger = logging.getLogger("chhoti.coding_agent")

_guardian = OperatorGuard()

# Module-level active workspace (the jail root), set via grant_workspace(). Mirrors
# the module-level state browser/guarded.py keeps for its guardian/rate-limit.
_workspace: Optional[WorkspaceSandbox] = None


# ── workspace granting ────────────────────────────────────────────────────────
# -- Explicit tool tiers (authoritative; refactor-proof) --------------------------
# These make the tier of each tool EXPLICIT so a refactor cannot accidentally
# change the risk level.
TOOL_TIERS = {
    # Read-only fs (LOW)
    "fs_list_dir": "LOW",
    "fs_read_file": "LOW",
    "fs_search": "LOW",
    # Write fs (MEDIUM/HIGH)
    "fs_write_file": "MEDIUM",
    "fs_create_file": "MEDIUM",
    "fs_edit_file": "MEDIUM",
    "fs_make_dir": "MEDIUM",
    "fs_delete_file": "HIGH",
    # Shell
    "sh_run": "MEDIUM",       # MEDIUM in plan / HIGH outside plan (dynamic)
    # Server
    "serve_start": "MEDIUM",  # MEDIUM in plan / HIGH outside plan (dynamic)
    "serve_status": "LOW",
    "serve_logs": "LOW",
    "serve_stop": "LOW",
    # Deploy
    "deploy_check": "LOW",
    "deploy_run": "ALWAYS_CONFIRM",
}


def resolve_tier(tool: str, in_plan: bool = False) -> str:
    """Return the confirmation tier for a tool."""
    base = TOOL_TIERS.get(tool, "HIGH")
    if tool in ("sh_run", "serve_start") and not in_plan:
        return "HIGH"
    return base


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


# ── WRITE path (Phase 2: MEDIUM/HIGH, HITL-confirmed, diff previewed) ──────────
# This is the AUTHORITATIVE enforcement point for state-changing filesystem
# actions — NOT the LLM prompt. Order is fail-safe:
#   1. require a granted workspace
#   2. PLAN through the sandbox (resolve+validate) — a jail escape raises here,
#      BEFORE any confirmation prompt or disk mutation
#   3. Guardian assessment must mark the action confirm-required (never auto-allow)
#   4. HITL confirm() shows the unified diff and consults the approver; with no
#      approver it falls back to the Guardian's blocking request_permission(),
#      and with neither it FAILS SAFE to deny
#   5. only on explicit approval does commit_plan() apply the (atomic) change
def _confirm_and_commit(plan) -> Dict[str, Any]:
    assessment = _guardian.assess_action(plan.action, plan.rel_path)
    # Defensive: a write tool must be a confirm-required tier. If some future
    # miswiring made it auto-allow, refuse rather than silently mutate.
    if not assessment["requires_confirmation"]:
        return {"status": "error", "marker": "MISCONFIGURED_TIER",
                "action": plan.action, "guardian": assessment}

    proposal = hitl.WriteProposal(action=plan.action, tier=plan.tier, path=plan.rel_path,
                                  summary=plan.summary, diff=plan.diff, warning=plan.warning)
    approved = hitl.confirm(proposal,
                            fallback=lambda p: _guardian.request_permission(p.action))
    logger.info("[coding-agent-guardian] action=%s path=%s tier=%s risk=%s decision=%s",
                plan.action, plan.rel_path, plan.tier, assessment["risk_level"],
                "APPROVE" if approved else "DENY")
    if not approved:
        return {"status": "error", "marker": "GUARDIAN_DENIED", "tier": plan.tier,
                "action": plan.action, "path": plan.rel_path, "diff": plan.diff}

    try:
        result = edits.commit_plan(_workspace, plan)
    except SandboxViolation as exc:  # re-resolve caught an escape at commit time
        logger.warning("[coding-agent-guardian] SANDBOX_VIOLATION (commit) action=%s -> %s",
                       plan.action, exc)
        return {"status": "error", "marker": "SANDBOX_VIOLATION", "message": str(exc),
                "requested": exc.requested, "resolved": exc.resolved}
    except OSError as exc:
        return {"status": "error", "marker": "WRITE_FAILED", "message": str(exc),
                "action": plan.action, "path": plan.rel_path}
    hitl.audit.info("RESULT %s -> %s", proposal.describe(),
                    result.get("status") if isinstance(result, dict) else result)
    return result


def _run_write(action: str, path: str, plan_fn) -> Dict[str, Any]:
    """Require a workspace, PLAN (jail escapes raise here before any prompt), then
    confirm+commit. Semantic errors from the plan short-circuit without prompting."""
    if _workspace is None:
        return {"status": "error", "marker": "NO_WORKSPACE",
                "message": "No workspace granted. Call grant_workspace(path) first."}
    try:
        outcome = plan_fn(_workspace)
    except SandboxViolation as exc:
        logger.warning("[coding-agent-guardian] SANDBOX_VIOLATION action=%s target=%s -> %s",
                       action, path, exc)
        return {"status": "error", "marker": "SANDBOX_VIOLATION", "message": str(exc),
                "requested": exc.requested, "resolved": exc.resolved}
    if "error" in outcome:
        return outcome["error"]
    return _confirm_and_commit(outcome["plan"])


def fs_write_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded create-or-overwrite. MEDIUM risk — requires confirmation."""
    data = input_data if isinstance(input_data, dict) else {"path": str(input_data)}
    path = str(data.get("path") or data.get("file_path") or "")
    if not path:
        return {"status": "error", "marker": "MISSING_PATH",
                "message": "A 'path' is required for fs_write_file."}
    content = data.get("content", data.get("text", ""))
    return _run_write("fs_write_file", path,
                      lambda sb: edits.plan_write_file(sb, path, content))


def fs_create_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded create-if-absent. MEDIUM risk — requires confirmation."""
    data = input_data if isinstance(input_data, dict) else {"path": str(input_data)}
    path = str(data.get("path") or data.get("file_path") or "")
    if not path:
        return {"status": "error", "marker": "MISSING_PATH",
                "message": "A 'path' is required for fs_create_file."}
    content = data.get("content", data.get("text", ""))
    return _run_write("fs_create_file", path,
                      lambda sb: edits.plan_create_file(sb, path, content))


def fs_edit_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded surgical edit (old_str must match exactly once). MEDIUM risk."""
    data = input_data if isinstance(input_data, dict) else {}
    path = str(data.get("path") or data.get("file_path") or "")
    if not path:
        return {"status": "error", "marker": "MISSING_PATH",
                "message": "A 'path' is required for fs_edit_file."}
    old_str = data.get("old_str", data.get("old"))
    new_str = data.get("new_str", data.get("new", ""))
    return _run_write("fs_edit_file", path,
                      lambda sb: edits.plan_edit_file(sb, path, old_str, new_str))


def fs_make_dir(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded directory creation (parents ok). MEDIUM risk — requires confirmation."""
    data = input_data if isinstance(input_data, dict) else {"path": str(input_data)}
    path = str(data.get("path") or "")
    if not path:
        return {"status": "error", "marker": "MISSING_PATH",
                "message": "A 'path' is required for fs_make_dir."}
    return _run_write("fs_make_dir", path, lambda sb: edits.plan_make_dir(sb, path))


def fs_delete_file(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded single-file delete. HIGH risk — requires confirmation."""
    data = input_data if isinstance(input_data, dict) else {"path": str(input_data)}
    path = str(data.get("path") or data.get("file_path") or "")
    if not path:
        return {"status": "error", "marker": "MISSING_PATH",
                "message": "A 'path' is required for fs_delete_file."}
    return _run_write("fs_delete_file", path, lambda sb: edits.plan_delete_file(sb, path))


# ── SHELL path (Phase 4: run-to-completion dev commands, classified + gated) ──
# The AUTHORITATIVE enforcement point for command execution — NOT the LLM prompt.
# Fail-safe order:
#   1. require a granted workspace (cwd is pinned to its root)
#   2. classify the command WITHOUT running it (coding_agent.shell.classify)
#   3. CRITICAL -> HARD BLOCK: never runs, never even offered for confirmation
#   4. HIGH/MEDIUM -> hitl.confirm (session approver auto-runs only in-plan MEDIUM;
#      HIGH always confirms individually; no approver -> Guardian request_permission;
#      neither -> fail-safe DENY)
#   5. only on approval does the argv list run with shell=False, cwd pinned, a hard
#      timeout, and bounded output.
# NOTE: cwd-pinning is a guardrail, not a sandbox — a launched process can still
# read outside cwd. The real defenses are the classifier + CRITICAL block + HIGH
# confirm + shell=False + timeout. See coding_agent/shell.py.
def _run_shell(command: str) -> Dict[str, Any]:
    if _workspace is None:
        return {"status": "error", "marker": "NO_WORKSPACE",
                "message": "No workspace granted. Call grant_workspace(path) first."}

    cls = shell.classify(command, workspace_root=_workspace.root)
    tier = cls["tier"]

    if cls["critical"]:
        hitl.audit.info("BLOCK CRITICAL sh_run `%s` (%s)", command, cls["reason"])
        logger.info("[coding-agent-guardian] sh_run tier=CRITICAL decision=BLOCKED cmd=%r reason=%s",
                    command, cls["reason"])
        return {"status": "error", "marker": "CRITICAL_BLOCKED", "tier": "CRITICAL",
                "command": command, "reason": cls["reason"],
                "message": "This command is hard-blocked and is never run or offered for confirmation."}

    warning = ("Runs to completion in the workspace; may modify files or install "
               "third-party code." if tier == "HIGH" else "")
    proposal = hitl.ShellProposal(command=command, tier=tier,
                                  program=cls["program"], reason=cls["reason"], warning=warning)
    approved = hitl.confirm(proposal,
                            fallback=lambda p: _guardian.request_permission("sh_run"))
    logger.info("[coding-agent-guardian] sh_run tier=%s decision=%s cmd=%r",
                tier, "APPROVE" if approved else "DENY", command)
    if not approved:
        return {"status": "error", "marker": "GUARDIAN_DENIED", "tier": tier,
                "command": command, "reason": cls["reason"]}

    try:
        r = shell.run(cls["argv"], cwd=_workspace.root,
                      timeout=SHELL_TIMEOUT_S, output_cap=SHELL_OUTPUT_CAP)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "marker": "SHELL_FAILED", "message": str(exc),
                "command": command}
    exit_code = r.get("exit_code")
    hitl.audit.info("RESULT sh_run `%s` -> exit=%s timed_out=%s",
                    command, exit_code, r.get("timed_out"))
    # The gate ALLOWED the run; a non-zero exit is a legitimate result (e.g. tests
    # failed), surfaced via exit_code/stderr for the self-heal loop — not a gate deny.
    return {"status": "success", "action": "sh_run", "command": command, "tier": tier,
            "exit_code": exit_code, "ok": exit_code == 0,
            "timed_out": r.get("timed_out", False),
            "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}


def sh_run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded shell execution. Classifies the command and runs it only if allowed:
    CRITICAL is hard-blocked; HIGH needs individual confirmation; MEDIUM auto-runs
    only inside an approved plan (else confirm). shell=False, cwd pinned, bounded."""
    data = input_data if isinstance(input_data, dict) else {"command": str(input_data)}
    command = str(data.get("command") or data.get("cmd") or data.get("input") or "").strip()
    if not command:
        return {"status": "error", "marker": "EMPTY_COMMAND",
                "message": "A 'command' is required for sh_run."}
    return _run_shell(command)


# ── SERVER path (Phase 5: LOCAL background dev servers) ───────────────────────
# serve_start reuses the SAME classifier + confirm discipline as sh_run: CRITICAL
# is hard-blocked; an allowlisted dev command is MEDIUM (auto only inside an
# approved plan); anything else is HIGH (individual confirm). The launch itself is
# a NON-waiting Popen, cwd pinned, shell=False (coding_agent.server). status/logs/
# stop are LOW (inspecting/stopping is always safe) and never confirm.
def serve_start(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded start of a LOCAL long-lived dev server (background process)."""
    data = input_data if isinstance(input_data, dict) else {"command": str(input_data)}
    command = str(data.get("command") or data.get("cmd") or "").strip()
    if not command:
        return {"status": "error", "marker": "EMPTY_COMMAND",
                "message": "A 'command' is required for serve_start."}
    if _workspace is None:
        return {"status": "error", "marker": "NO_WORKSPACE",
                "message": "No workspace granted. Call grant_workspace(path) first."}

    cls = shell.classify(command, workspace_root=_workspace.root)
    if cls["critical"]:
        hitl.audit.info("BLOCK CRITICAL serve_start `%s` (%s)", command, cls["reason"])
        logger.info("[coding-agent-guardian] serve_start tier=CRITICAL decision=BLOCKED cmd=%r",
                    command)
        return {"status": "error", "marker": "CRITICAL_BLOCKED", "tier": "CRITICAL",
                "command": command, "reason": cls["reason"],
                "message": "This command is hard-blocked and is never run."}

    proposal = hitl.ShellProposal(command=command, tier=cls["tier"], program=cls["program"],
                                  reason=cls["reason"], label="serve_start",
                                  warning="Starts a LOCAL long-lived server that runs until "
                                          "you stop it (serve_stop).")
    approved = hitl.confirm(proposal,
                            fallback=lambda p: _guardian.request_permission("serve_start"))
    logger.info("[coding-agent-guardian] serve_start tier=%s decision=%s cmd=%r",
                cls["tier"], "APPROVE" if approved else "DENY", command)
    if not approved:
        return {"status": "error", "marker": "GUARDIAN_DENIED", "tier": cls["tier"],
                "command": command, "reason": cls["reason"]}

    return server.start(command, cls["argv"], cwd=_workspace.root, tier=cls["tier"])


def serve_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """LOW: is the server alive? + health probe + recent log tail + detected URL."""
    data = input_data if isinstance(input_data, dict) else {"id": str(input_data)}
    sid = str(data.get("id") or data.get("server_id") or "").strip()
    if not sid:
        return {"status": "error", "marker": "MISSING_ID", "message": "A server 'id' is required."}
    return server.status(sid)


def serve_logs(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """LOW: captured stdout/stderr tail for a tracked server."""
    data = input_data if isinstance(input_data, dict) else {"id": str(input_data)}
    sid = str(data.get("id") or data.get("server_id") or "").strip()
    if not sid:
        return {"status": "error", "marker": "MISSING_ID", "message": "A server 'id' is required."}
    tail = data.get("tail", data.get("tail_n", 50))
    try:
        tail = int(tail)
    except (TypeError, ValueError):
        tail = 50
    return server.logs(sid, tail_n=tail)


def serve_stop(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """LOW: graceful-then-forced stop of a tracked server (always allowed)."""
    data = input_data if isinstance(input_data, dict) else {"id": str(input_data)}
    sid = str(data.get("id") or data.get("server_id") or "").strip()
    if not sid:
        return {"status": "error", "marker": "MISSING_ID", "message": "A server 'id' is required."}
    return server.stop(sid)


# ── DEPLOY path (Phase 6: PUBLIC deploy — highest risk, always confirm) ───────
# The payment-wall equivalent. Deploy is NEVER auto-approved: it rides a SEPARATE
# approval channel (hitl.confirm_deploy / _deploy_approver) that approve_all and
# the plan-scope session approver cannot satisfy. Order:
#   1. require a granted workspace (cwd pinned to its root)
#   2. resolve the platform adapter
#   3. SECRET PREFLIGHT — if secrets would be uploaded and it is not explicitly
#      acknowledged, BLOCK before any prompt
#   4. individual human confirm (confirm_deploy); PRODUCTION requires a SECOND
#      explicit confirmation
#   5. only then run the CLI via shell.run (shell=False, cwd pinned), parse the URL
# The agent stores no tokens — it relies on the CLI's own pre-existing auth state.
def deploy_check(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """LOW/read-only: is the platform CLI installed and already authenticated?"""
    data = input_data if isinstance(input_data, dict) else {"platform": str(input_data)}
    platform = str(data.get("platform") or data.get("input") or "").strip()
    if not platform:
        return {"status": "error", "marker": "MISSING_PLATFORM",
                "message": "A 'platform' is required (e.g. vercel/netlify/github-pages)."}
    if _workspace is None:
        return {"status": "error", "marker": "NO_WORKSPACE",
                "message": "No workspace granted. Call grant_workspace(path) first."}
    return deploy.check(platform, cwd=_workspace.root, runner=shell.run,
                        timeout=SHELL_TIMEOUT_S, output_cap=SHELL_OUTPUT_CAP)


def deploy_run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded PUBLIC deploy. ALWAYS individual human confirm (approve_all-exempt);
    preview by default; production needs prod=True + an extra confirm; blocked if
    secrets would be uploaded unless explicitly acknowledged."""
    data = input_data if isinstance(input_data, dict) else {"platform": str(input_data)}
    platform = str(data.get("platform") or "").strip()
    if not platform:
        return {"status": "error", "marker": "MISSING_PLATFORM",
                "message": "A 'platform' is required."}
    if _workspace is None:
        return {"status": "error", "marker": "NO_WORKSPACE",
                "message": "No workspace granted. Call grant_workspace(path) first."}

    adapter = deploy.get_adapter(platform)
    if adapter is None:
        return {"status": "error", "marker": "UNKNOWN_PLATFORM", "platform": platform,
                "known": deploy.list_platforms()}

    prod = bool(data.get("prod", False))
    acknowledged = bool(data.get("acknowledge_secrets", False))

    # 3) SECRET PREFLIGHT — block by default if anything sensitive would upload.
    preflight = deploy.secret_preflight(_workspace.root)
    if not preflight["clean"] and not acknowledged:
        hitl.audit.info("BLOCK SECRETS deploy %s findings=%d", platform,
                        len(preflight["findings"]))
        return {"status": "error", "marker": "SECRETS_DETECTED", "platform": platform,
                "findings": preflight["findings"], "env_files": preflight["env_files"],
                "message": ("Deploy blocked: secrets would be uploaded. Remove/ignore them "
                            "(e.g. add .env to .vercelignore/.netlifyignore/.gitignore), or "
                            "re-run with acknowledge_secrets=true to proceed anyway.")}

    # Adapters without a preview (e.g. GitHub Pages) always publish LIVE.
    effective_prod = prod or (not adapter.supports_preview)
    command = " ".join(adapter.deploy_argv(effective_prod))
    warn = "PUBLIC deploy — this is externally reachable."
    if effective_prod:
        warn = "PRODUCTION deploy — this replaces the LIVE site. " + warn
    if not preflight["clean"]:
        warn = "SECRETS present and acknowledged. " + warn

    proposal = hitl.DeployProposal(platform=platform, command=command, prod=effective_prod,
                                   secrets_found=not preflight["clean"],
                                   secret_findings=preflight["findings"], warning=warn)
    approved = hitl.confirm_deploy(proposal,
                                   fallback=lambda p: _guardian.request_permission("deploy_run"))
    logger.info("[coding-agent-guardian] deploy platform=%s prod=%s decision=%s",
                platform, effective_prod, "APPROVE" if approved else "DENY")
    if not approved:
        return {"status": "error", "marker": "GUARDIAN_DENIED", "platform": platform,
                "prod": effective_prod, "command": command}

    # 4b) PRODUCTION requires a SECOND explicit confirmation.
    if effective_prod:
        final = hitl.DeployProposal(platform=platform, command=command, prod=True,
                                    secrets_found=not preflight["clean"],
                                    secret_findings=preflight["findings"], final=True,
                                    warning="FINAL confirmation for a PRODUCTION/live deploy.")
        if not hitl.confirm_deploy(final,
                                   fallback=lambda p: _guardian.request_permission("deploy_run_prod")):
            return {"status": "error", "marker": "GUARDIAN_DENIED", "platform": platform,
                    "prod": True, "command": command, "stage": "production_final"}

    # 5) run the CLI via the SAME executor as sh_run (shell=False, cwd pinned).
    r = shell.run(adapter.deploy_argv(effective_prod), cwd=_workspace.root,
                  timeout=DEPLOY_TIMEOUT_S, output_cap=DEPLOY_OUTPUT_CAP)
    exit_code = r.get("exit_code")
    url = adapter.parse_url(r.get("stdout", ""), r.get("stderr", ""))
    hitl.audit.info("RESULT deploy %s prod=%s exit=%s url=%s",
                    platform, effective_prod, exit_code, url)
    return {"status": "success", "action": "deploy_run", "platform": platform,
            "prod": effective_prod, "command": command, "exit_code": exit_code,
            "ok": exit_code == 0, "url": url,
            "stdout": r.get("stdout", ""), "stderr": r.get("stderr", "")}
