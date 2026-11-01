"""Phase 3: autonomous coding builder — a bounded plan→act→observe loop.

Given a natural-language TASK, the coding brain (deepseek-coder-v2:lite via the
existing ``think_fast`` path) first proposes an ordered PLAN of intended file
actions. The plan is shown to the user ONCE for approval. On approval the agent
runs a ReAct loop — one guarded ``fs_`` action per step — until it emits
``finish`` or a HARD step cap is reached, then reports what it built.

INVARIANTS (non-negotiable)
---------------------------
* fs_ TOOLS ONLY (read + write). There is NO shell / command execution / process
  spawning here, and none may be added — that is a later phase.
* Every action is dispatched through ``coding_agent.guarded`` (the same choke
  point as Phases 1–2). Reads auto-allow; writes stay gated. Under an APPROVED
  plan a session approver auto-approves MEDIUM writes *within the plan's scope*
  (no per-file spam), HIGH deletes are confirmed individually, and anything
  out-of-scope or any jail escape is denied by the existing gate.
* The loop never bypasses the sandbox jail; an escape ends that action with the
  usual violation marker and the loop continues (or breaks on no-progress).

CONTEXT BUDGET (protects the local model / 8GB VRAM)
----------------------------------------------------
Only the last ``AGENT_MAX_OBS`` observations stay verbatim (each truncated to
``AGENT_OBS_CHARS``); older steps fold into a short running summary. Write
observations are just "wrote N bytes to <path>" — file content is NEVER echoed
back into context.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import guarded, hitl, server
from .config import (AGENT_HEAL_BUDGET, AGENT_MAX_OBS, AGENT_MAX_PARSE_RETRIES,
                     AGENT_MAX_REPEAT, AGENT_MAX_STEPS, AGENT_OBS_CHARS,
                     AGENT_READ_MAX_LINES, AGENT_SUMMARY_MAX_LINES)
from .sandbox import SandboxViolation, strip_bare_root

logger = logging.getLogger("chhoti.coding_agent.agent")

READ_TOOLS = ("fs_list_dir", "fs_read_file", "fs_search")
WRITE_TOOLS = ("fs_write_file", "fs_create_file", "fs_edit_file",
               "fs_make_dir", "fs_delete_file")
FS_TOOLS = READ_TOOLS + WRITE_TOOLS
# Phase 4: the ONE gated shell action. Distinct prefix so "no raw shell" invariant
# tests read cleanly (the only command path is this classified, gated tool).
SHELL_TOOLS = ("sh_run",)
# Phase 5: LOCAL background dev servers. serve_start is gated (reuses the shell
# classifier); status/logs/stop are LOW.
SERVER_TOOLS = ("serve_start", "serve_status", "serve_logs", "serve_stop")
# Phase 6: PUBLIC deploy. deploy_check is read-only; deploy_run is ALWAYS an
# individual human confirm (never auto-approved — see _react/_session_approver).
DEPLOY_TOOLS = ("deploy_check", "deploy_run")
AGENT_TOOLS = FS_TOOLS + SHELL_TOOLS + SERVER_TOOLS + DEPLOY_TOOLS

_DENY_MARKERS = {"GUARDIAN_DENIED", "SANDBOX_VIOLATION", "NO_WORKSPACE",
                 "MISCONFIGURED_TIER", "WRITE_FAILED", "UNKNOWN_TOOL",
                 "CRITICAL_BLOCKED"}

# Short aliases the model might emit -> canonical tool names.
_ALIASES = {
    "list_dir": "fs_list_dir", "ls": "fs_list_dir", "read_file": "fs_read_file",
    "read": "fs_read_file", "search": "fs_search", "grep": "fs_search",
    "write_file": "fs_write_file", "write": "fs_write_file",
    "create_file": "fs_create_file", "create": "fs_create_file",
    "edit_file": "fs_edit_file", "edit": "fs_edit_file",
    "make_dir": "fs_make_dir", "mkdir": "fs_make_dir",
    "delete_file": "fs_delete_file", "delete": "fs_delete_file",
    "sh": "sh_run", "shell": "sh_run", "run": "sh_run", "bash": "sh_run",
    "exec_command": "sh_run", "run_command": "sh_run",
    "start_server": "serve_start", "serve": "serve_start", "server_start": "serve_start",
    "server_status": "serve_status", "status": "serve_status",
    "server_logs": "serve_logs", "server_stop": "serve_stop", "stop_server": "serve_stop",
    "deploy": "deploy_run", "publish": "deploy_run", "deploy_status": "deploy_check",
}

# System prompt for the coding brain — passed explicitly to think_fast so the
# coding brain's default Hinglish/web-tool suffixes never corrupt the JSON.
AGENT_SYSTEM_PROMPT = (
    "You are Chhoti Don's autonomous coding builder. You scaffold, edit, and "
    "verify a project. Available tools: fs_list_dir, fs_read_file, fs_search, "
    "fs_write_file(path,content), fs_create_file(path,content), "
    "fs_edit_file(path,old_str,new_str), fs_make_dir(path), fs_delete_file(path), "
    "and sh_run(command) to run tests/build/install/lint/git commands to completion. "
    "sh_run cannot start background servers, and dangerous commands (rm -rf, sudo, "
    "pipes) are blocked. To run a LOCAL dev server use serve_start(command) (a "
    "background process), then serve_status(id) to check it is up and read its local "
    "URL, serve_logs(id) for output, and serve_stop(id) to stop it. There is no "
    "deploy or public/tunnel hosting. SELF-HEAL: when sh_run returns a non-zero exit "
    "code, read the exit code and stderr/traceback, use fs_edit_file to fix the cause, "
    "then re-run. Do not repeat a fix that already failed. When you serve_start a "
    "server, verify it is up with serve_status and report its local URL; do NOT stop "
    "a server the user asked to run. "
    "DEPLOY: only on the user's EXPLICIT request. First deploy_check(platform) to "
    "confirm the CLI is installed+authenticated, then deploy_run(platform) — which "
    "defaults to a PREVIEW deploy and requires the user's individual confirmation "
    "(you cannot auto-approve it). Use prod=true ONLY when the user explicitly asks "
    "to go to production. Never put secrets in files you deploy. Always report the "
    "deployed URL. "
    "PATHS ARE RELATIVE to the workspace root: write 'src/app.py', NEVER '/src/app.py' "
    "or an absolute path. After an action succeeds, do NOT repeat it — take the next "
    "step, and once the whole task is done respond with finish. "
    "EXAMPLE trajectory:\n"
    'Step -> {"tool":"fs_create_file","args":{"path":"hello.txt","content":"hi\\n"}}\n'
    "Observation -> wrote 3 bytes to hello.txt\n"
    'Step -> {"finish":"Created hello.txt"}\n'
    "Always respond with STRICT JSON and nothing else — no prose, no code fences."
)


# ── dispatch (guarded wrappers only — the choke point stays in path) ──────────
def _dispatch(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool == "fs_list_dir":
        return guarded.fs_list_dir({"path": args.get("path", "."),
                                    "max_depth": args.get("max_depth")})
    if tool == "fs_read_file":
        return guarded.fs_read_file({"path": args.get("path", ""),
                                     "max_bytes": args.get("max_bytes")})
    if tool == "fs_search":
        return guarded.fs_search({"query": args.get("query", args.get("q", "")),
                                  "glob": args.get("glob")})
    if tool == "fs_write_file":
        return guarded.fs_write_file({"path": args.get("path", ""),
                                      "content": args.get("content", args.get("text", ""))})
    if tool == "fs_create_file":
        return guarded.fs_create_file({"path": args.get("path", ""),
                                       "content": args.get("content", args.get("text", ""))})
    if tool == "fs_edit_file":
        return guarded.fs_edit_file({"path": args.get("path", ""),
                                     "old_str": args.get("old_str", args.get("old")),
                                     "new_str": args.get("new_str", args.get("new", ""))})
    if tool == "fs_make_dir":
        return guarded.fs_make_dir({"path": args.get("path", "")})
    if tool == "fs_delete_file":
        return guarded.fs_delete_file({"path": args.get("path", "")})
    if tool == "sh_run":
        return guarded.sh_run({"command": args.get("command", args.get("cmd", ""))})
    if tool == "serve_start":
        return guarded.serve_start({"command": args.get("command", args.get("cmd", ""))})
    if tool == "serve_status":
        return guarded.serve_status({"id": args.get("id", args.get("server_id"))})
    if tool == "serve_logs":
        return guarded.serve_logs({"id": args.get("id", args.get("server_id")),
                                   "tail": args.get("tail", args.get("tail_n", 50))})
    if tool == "serve_stop":
        return guarded.serve_stop({"id": args.get("id", args.get("server_id"))})
    if tool == "deploy_check":
        return guarded.deploy_check({"platform": args.get("platform", "")})
    if tool == "deploy_run":
        return guarded.deploy_run({"platform": args.get("platform", ""),
                                   "prod": bool(args.get("prod", False)),
                                   "acknowledge_secrets": bool(args.get("acknowledge_secrets", False))})
    return {"status": "error", "marker": "UNKNOWN_TOOL", "tool": tool}


# ── parsing (defensive; mirrors browser.agent) ────────────────────────────────
def _canonical_tool(name: str) -> str:
    n = (name or "").strip().lower()
    if n in AGENT_TOOLS or n == "finish":
        return n
    return _ALIASES.get(n, n)


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _loads_lenient(blob: str) -> Optional[Any]:
    try:
        return json.loads(blob)
    except Exception:
        try:  # tolerate trailing commas / single quotes
            return json.loads(re.sub(r",\s*([}\]])", r"\1", blob).replace("'", '"'))
        except Exception:
            return None


def _parse_action(raw: str) -> Optional[Dict[str, Any]]:
    """Parse ONE action object from possibly-messy model output. None -> retry."""
    text = _strip_fences(raw)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    obj = _loads_lenient(text[start:end + 1])
    if not isinstance(obj, dict):
        return None
    # finish shapes: {"finish":"..."} or {"tool":"finish","args":{"summary":..}}
    if "finish" in obj and "tool" not in obj and "action" not in obj:
        return {"tool": "finish", "args": {"summary": str(obj.get("finish", ""))}, "note": ""}
    tool = _canonical_tool(str(obj.get("tool") or obj.get("action") or ""))
    if tool not in AGENT_TOOLS and tool != "finish":
        return None
    args = obj.get("args")
    if not isinstance(args, dict):
        args = {k: v for k, v in obj.items() if k not in ("tool", "action", "note", "thought")}
    return {"tool": tool, "args": args, "note": str(obj.get("note", obj.get("thought", "")))[:200]}


def _parse_plan(raw: str) -> Optional[List[Dict[str, Any]]]:
    """Parse an ordered plan (JSON array of actions, or {"plan":[...]})."""
    text = _strip_fences(raw)
    arr = None
    s, e = text.find("["), text.rfind("]")
    if s != -1 and e != -1 and e > s:
        arr = _loads_lenient(text[s:e + 1])
    if arr is None:
        o = _loads_lenient(text)
        if isinstance(o, dict) and isinstance(o.get("plan"), list):
            arr = o["plan"]
    if not isinstance(arr, list):
        return None
    plan: List[Dict[str, Any]] = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        tool = _canonical_tool(str(item.get("tool") or item.get("action") or ""))
        if tool not in AGENT_TOOLS:
            continue
        args = item.get("args")
        if not isinstance(args, dict):
            args = {k: v for k, v in item.items()
                    if k not in ("tool", "action", "note", "thought")}
        # Normalize a bare-root path in the plan (/src -> src) so we stop echoing
        # the model's own '/'-prefixed paths back at it, and so plan-scope matches
        # the (normalized) paths the guarded layer will actually resolve to.
        if isinstance(args.get("path"), str):
            args = dict(args, path=strip_bare_root(args["path"]))
        plan.append({"tool": tool, "args": args, "note": str(item.get("note", ""))[:160]})
    return plan or None


# ── observation summarizer (compact; never echoes written content) ────────────
def _summarize(tool: str, args: Dict[str, Any], result: Dict[str, Any],
               obs_chars: int, read_max_lines: int) -> str:
    if not isinstance(result, dict):
        return str(result)[:obs_chars]
    if result.get("status") == "error":
        return f"ERROR {result.get('marker', '')}: {result.get('message', '')}".strip()[:obs_chars]
    if tool == "fs_read_file":
        content = result.get("content", "") or ""
        lines = content.splitlines()
        head = "\n".join(lines[:read_max_lines])
        if len(lines) > read_max_lines:
            head += f"\n…truncated ({len(lines)} lines total)"
        return f"read {result.get('path')} ({result.get('bytes_read')}B):\n{head}"[:obs_chars]
    if tool == "fs_list_dir":
        ents = result.get("entries", []) or []
        names = ", ".join(e.get("path", "") for e in ents[:20])
        more = "" if len(ents) <= 20 else f" …(+{len(ents) - 20} more)"
        return f"list {result.get('root')}: {result.get('count')} entries: {names}{more}"[:obs_chars]
    if tool == "fs_search":
        rows = result.get("formatted", []) or []
        body = "\n".join(rows[:10])
        return f"search '{result.get('query')}' -> {result.get('count')} hits:\n{body}"[:obs_chars]
    if tool in ("fs_write_file", "fs_create_file"):
        return f"wrote {result.get('bytes_written')} bytes to {result.get('path')}"
    if tool == "fs_edit_file":
        return f"edited {result.get('path')} ({result.get('bytes_written')} bytes)"
    if tool == "fs_make_dir":
        return f"created dir {result.get('path')}"
    if tool == "fs_delete_file":
        return f"deleted {result.get('path')}"
    if tool == "sh_run":
        # ERROR-AWARE: keep the TAIL of stderr/stdout (where the traceback/error is)
        # rather than the head, so the model can localize the fix.
        code = result.get("exit_code")
        status = "OK (exit 0)" if code == 0 else f"FAILED (exit {code})"
        if result.get("timed_out"):
            status = f"TIMED OUT (killed); {status}"
        err = (result.get("stderr") or "").strip()
        out = (result.get("stdout") or "").strip()
        body = err or out or "(no output)"
        tail = body[-obs_chars:]
        head_note = "…" if len(body) > obs_chars else ""
        return f"$ {result.get('command', '')} -> {status}\n{head_note}{tail}"
    if tool == "serve_start":
        url = result.get("detected_url") or "no URL detected yet"
        return (f"started server {result.get('id')} pid={result.get('pid')} "
                f"alive={result.get('alive')} url={url}. Stop with serve_stop id={result.get('id')}."
                )[:obs_chars]
    if tool == "serve_status":
        tail = "\n".join(result.get("log_tail", []) or [])[:obs_chars // 2]
        return (f"server {result.get('id')} alive={result.get('alive')} "
                f"healthy={result.get('healthy')} url={result.get('detected_url')}\n{tail}")[:obs_chars]
    if tool == "serve_logs":
        return "\n".join(result.get("lines", []) or [])[-obs_chars:]
    if tool == "serve_stop":
        return f"stopped server {result.get('id')}"
    if tool == "deploy_check":
        return (f"deploy_check {result.get('platform')}: installed={result.get('installed')} "
                f"authed={result.get('authed')}. If missing: {result.get('install_hint')} / "
                f"{result.get('auth_hint')}")[:obs_chars]
    if tool == "deploy_run":
        env = "PRODUCTION" if result.get("prod") else "preview"
        if result.get("ok"):
            return f"deployed ({env}) to {result.get('platform')} -> {result.get('url') or 'URL not detected'}"
        return (f"deploy ({env}) FAILED on {result.get('platform')} exit={result.get('exit_code')}: "
                f"{(result.get('stderr') or '').strip()[-obs_chars // 2:]}")[:obs_chars]
    return json.dumps(result)[:obs_chars]


def _arg_label(args: Dict[str, Any]) -> str:
    return str(args.get("path") or args.get("command") or args.get("query")
               or args.get("q") or "")[:80]


# Verify-style commands: when these exit 0 the task is likely done.
# Matches: python -m pytest, pytest, python -m unittest, unittest,
# and any script whose name ends with "test" or "check".
_VERIFY_PROGRAMS = {"pytest", "unittest"}

def _is_verify_command(argv: List[str]) -> bool:
    """True when argv is a verify-style command (pytest, unittest, test_*, etc.)."""
    if not argv:
        return False
    prog = (argv[0] or "").lower().rstrip(".py")
    # bare: pytest, pytest-3, unittest
    if prog in _VERIFY_PROGRAMS or prog.startswith("pytest"):
        return True
    # python -m pytest / python -m unittest
    if prog == "python" and "-m" in argv:
        idx = argv.index("-m")
        if idx + 1 < len(argv) and argv[idx + 1].lower() in _VERIFY_PROGRAMS:
            return True
    # Script name ends with test/check or starts with test_ (strip .py first)
    name = (argv[-1] if argv else "").lower()
    if name.endswith(".py"):
        name = name[:-3]
    if (name.endswith("test") or name.endswith("check") or name.endswith("tests")
            or name.startswith("test_") or name.startswith("test-")):
        return True
    return False


def _norm_cmd(command: str) -> str:
    """Normalize a command for plan-scope matching (collapse whitespace)."""
    return " ".join(str(command or "").split())


# ── the agent ─────────────────────────────────────────────────────────────────
class CodingAgent:
    """Bounded plan→approve→(act→observe)*→finish loop over the guarded fs tools.

    All disk mutation flows through ``coding_agent.guarded``; this class only
    decides WHICH guarded action to run next and keeps a compact scratchpad.
    """

    def __init__(self, think_fn: Callable[[str], str],
                 plan_approver: Optional[Callable[[List[Dict[str, Any]]], bool]] = None,
                 delete_approver: Optional[Callable[[Any], bool]] = None,
                 shell_approver: Optional[Callable[[Any], bool]] = None,
                 deploy_approver: Optional[Callable[[Any], bool]] = None,
                 max_steps: int = AGENT_MAX_STEPS, obs_chars: int = AGENT_OBS_CHARS,
                 max_obs: int = AGENT_MAX_OBS, max_parse_retries: int = AGENT_MAX_PARSE_RETRIES,
                 max_repeat: int = AGENT_MAX_REPEAT, read_max_lines: int = AGENT_READ_MAX_LINES,
                 summary_max_lines: int = AGENT_SUMMARY_MAX_LINES,
                 heal_budget: int = AGENT_HEAL_BUDGET,
                 on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.think_fn = think_fn
        self.on_event = on_event
        # Fail-safe defaults: no plan approval -> reject (write nothing); deletes and
        # HIGH/out-of-plan commands deny unless an explicit approver is supplied.
        self.plan_approver = plan_approver or (lambda plan: False)
        self.delete_approver = delete_approver or hitl.deny_all
        self.shell_approver = shell_approver or hitl.deny_all
        # Deploy is the payment-wall equivalent: default DENY, and it rides its own
        # channel (hitl.confirm_deploy) so approve_all/session approval can't reach it.
        self.deploy_approver = deploy_approver or hitl.deny_all
        self.max_steps = max(1, int(max_steps))
        self.obs_chars = obs_chars
        self.max_obs = max_obs
        self.max_parse_retries = max_parse_retries
        self.max_repeat = max(1, int(max_repeat))
        self.read_max_lines = read_max_lines
        self.summary_max_lines = summary_max_lines
        self.heal_budget = max(1, int(heal_budget))
        self._approved_paths: set = set()
        self._approved_commands: set = set()

    def _emit_event(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        if self.on_event:
            try:
                self.on_event(event, data or {})
            except Exception:
                logger.exception("[coding-agent] on_event callback failed for event=%s", event)

    # ---- planning ----
    def _plan_prompt(self, task: str, corrective: Optional[str] = None) -> str:
        lines = [
            f"TASK: {task}", "",
            "Produce an ORDERED PLAN of the file actions needed to scaffold this, "
            "using ONLY these tools: " + ", ".join(AGENT_TOOLS) + ".",
            "Reply with ONLY a JSON array, each item {\"tool\":\"fs_...\",\"args\":{...},"
            "\"note\":\"why\"}. Use forward-slash relative paths. No prose, no fences.",
        ]
        if corrective:
            lines.append("NOTE: " + corrective)
        return "\n".join(lines)

    def _plan(self, task: str, trace: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        corrective = None
        for attempt in range(self.max_parse_retries + 1):
            raw = self.think_fn(self._plan_prompt(task, corrective))
            plan = _parse_plan(raw)
            if plan is not None:
                trace.append({"phase": "plan", "actions": len(plan)})
                return plan
            corrective = ('Your previous reply was not a valid JSON array. Reply with ONLY a '
                          'JSON array of {"tool":"fs_...","args":{...}} objects.')
            trace.append({"phase": "plan", "error": "parse_retry", "attempt": attempt + 1})
        return None

    def _scope_paths(self, plan: List[Dict[str, Any]]) -> set:
        """Workspace-relative paths the approved plan intends to write/delete."""
        sb = guarded.active_workspace()
        paths: set = set()
        for a in plan:
            if a["tool"] not in WRITE_TOOLS:
                continue
            p = a.get("args", {}).get("path")
            if not p:
                continue
            if sb is None:
                paths.add(str(p))
                continue
            try:
                paths.add(sb.relpath(sb.resolve(str(p))))
            except SandboxViolation:
                continue  # an escaping plan path is never in scope
        return paths

    def _scope_commands(self, plan: List[Dict[str, Any]]) -> set:
        """Normalized commands the approved plan intends to run (for auto-run of
        in-plan MEDIUM commands). Install/dep commands only auto-run if here."""
        cmds: set = set()
        for a in plan:
            if a["tool"] not in ("sh_run", "serve_start"):
                continue
            c = a.get("args", {}).get("command") or a.get("args", {}).get("cmd")
            if c:
                cmds.add(_norm_cmd(str(c)))
        return cmds

    def _session_approver(self) -> Callable[[Any], bool]:
        """Approval policy during the approved plan's execution.

        Shell (ShellProposal): CRITICAL is already hard-blocked in the gate; HIGH
        always goes to the individual shell approver; MEDIUM auto-runs ONLY if the
        command is in the approved plan, otherwise it is individually confirmed.
        Writes (WriteProposal): in-scope MEDIUM auto-approve (no per-file spam);
        HIGH deletes use the individual delete approver; out-of-scope denies."""
        def _appr(proposal) -> bool:
            if isinstance(proposal, hitl.ShellProposal):
                if proposal.tier == "HIGH":
                    return bool(self.shell_approver(proposal))
                if _norm_cmd(proposal.command) in self._approved_commands:
                    return True
                logger.info("[coding-agent] out-of-plan MEDIUM command -> confirm: %s",
                            proposal.command)
                return bool(self.shell_approver(proposal))
            # write proposal
            if proposal.path not in self._approved_paths:
                logger.info("[coding-agent] out-of-scope write denied: %s", proposal.path)
                return False
            if proposal.tier == "HIGH":
                return bool(self.delete_approver(proposal))
            return True
        return _appr

    # ---- stepping ----
    def _step_prompt(self, task: str, plan: List[Dict[str, Any]],
                     history: List[Tuple[Dict, str]], running_summary: List[str],
                     corrective: Optional[str] = None) -> str:
        lines = [f"TASK: {task}", "", "APPROVED PLAN:"]
        for i, a in enumerate(plan, 1):
            lines.append(f"  {i}. {a['tool']} {json.dumps(a.get('args', {}))[:120]}")
        lines.append("")
        if running_summary:
            lines.append("EARLIER (summary): " + " | ".join(running_summary[-self.summary_max_lines:]))
        if history:
            lines.append("RECENT OBSERVATIONS:")
            for i, (act, obs) in enumerate(history[-self.max_obs:], 1):
                lines.append(f"[{i}] {act['tool']} {_arg_label(act['args'])}")
                lines.append(f"    -> {obs}")
        if corrective:
            lines.append("NOTE: " + corrective)
        lines.append("")
        lines.append('Choose the NEXT single action to execute the plan. Reply with ONE JSON '
                     'object only: {"tool":"fs_...","args":{...}} or {"finish":"<summary>"}.')
        return "\n".join(lines)

    def _fold(self, running_summary: List[str], line: str) -> None:
        running_summary.append(line)
        if len(running_summary) > self.summary_max_lines:
            del running_summary[0]

    def _nudge_hint(self, history) -> str:
        """Pick a targeted corrective hint from the most recent observation."""
        last = history[-1][1] if history else ""
        low = last.lower()
        if "sandbox_violation" in low or "critical_blocked" in low or "absolute" in low:
            return ("The previous path/command was rejected as absolute. Retry using a path "
                    "RELATIVE to the workspace root — never start a path with '/'.")
        return ('The previous action already succeeded. If the task is complete, respond with '
                '{"finish":"<summary>"}. Otherwise take a DIFFERENT next action.')

    def _maybe_nudge(self, key, history, trace, step, nudged: set) -> bool:
        """Inject ONE corrective observation for a stuck point. Returns True (caller
        gives the model one more call) the first time; False (break) if already done."""
        if key in nudged:
            return False
        nudged.add(key)
        hint = self._nudge_hint(history)
        history.append(({"tool": "(nudge)", "args": {}}, "NUDGE: " + hint))
        trace.append({"step": step, "nudge": hint[:100]})
        logger.info("[coding-agent] nudge step=%d: %s", step, hint[:80])
        return True

    def run(self, task: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        trace: List[Dict[str, Any]] = []
        self._emit_event("planning", {"task": task})

        # 1) PLAN
        plan = self._plan(task, trace)
        if plan is None:
            self._emit_event("plan_failed", {"task": task, "error": "plan_parse_error"})
            return self._result(task, "Could not produce a valid build plan.",
                                 trace, 0, "plan_parse_error", t0, None, [])
        self._emit_event("plan", {"task": task, "plan": plan, "actions": len(plan)})

        # 2) APPROVAL (once)
        try:
            approved = bool(self.plan_approver(plan))
        except Exception as exc:  # any approver error -> reject (fail safe)
            logger.info("[coding-agent] plan approver error -> reject: %s", exc)
            approved = False
        if not approved:
            logger.info("[coding-agent] plan rejected; nothing written")
            self._emit_event("plan_rejected", {"task": task, "plan": plan})
            return self._result(task, "Plan rejected; nothing was written.",
                                 trace, 0, "rejected", t0, plan, [])
        self._emit_event("plan_approved", {"task": task, "plan": plan})

        # 3) EXECUTE under the session approver (batched in-scope MEDIUM writes /
        #    in-plan MEDIUM commands; HIGH + out-of-scope still confirm/deny).
        self._approved_paths = self._scope_paths(plan)
        self._approved_commands = self._scope_commands(plan)
        self._run_deploys: List[Dict[str, Any]] = []
        history: List[Tuple[Dict, str]] = []
        running_summary: List[str] = []
        executed: List[Dict[str, Any]] = []
        # The session approver handles in-scope writes / in-plan shell + servers.
        # Deploy is installed on a SEPARATE channel (individual, never approve_all).
        with hitl.use_approver(self._session_approver()), \
                hitl.use_deploy_approver(self.deploy_approver):
            return self._react(task, plan, history, running_summary, trace, executed, t0)

    def _react(self, task, plan, history, running_summary, trace, executed, t0) -> Dict[str, Any]:
        sig_counts: Dict[str, int] = {}
        # Self-heal bookkeeping: total attempts per command. sh_run is EXEMPT from
        # the generic no-progress guard (re-running a test after a fix is valid);
        # instead a command may be attempted at most `heal_budget` times.
        cmd_attempts: Dict[str, int] = {}
        commands: List[Dict[str, Any]] = []
        # Stuck points already nudged once: a no-progress/heal break is delayed by
        # EXACTLY ONE corrective model call, then it fires. Never an infinite loop.
        nudged: set = set()
        parse_retries = 0
        # Implicit-finish tracking: which action was nudged and at which step.
        _nudged_action_sig: Optional[str] = None
        _nudged_step: Optional[int] = None

        for step in range(1, self.max_steps + 1):
            self._emit_event("step_start", {"step": step, "max_steps": self.max_steps})
            action = None
            corrective = None
            for _attempt in range(2):  # initial + one corrective nudge
                raw = self.think_fn(self._step_prompt(task, plan, history,
                                                      running_summary, corrective))
                action = _parse_action(raw)
                if action is not None:
                    break
                parse_retries += 1
                corrective = ('Your previous reply was not valid JSON. Reply with ONLY one JSON '
                              'object: {"tool":"fs_...","args":{...}} or {"finish":"<summary>"}.')
                if parse_retries > self.max_parse_retries:
                    break

            if action is None:
                if parse_retries > self.max_parse_retries:
                    trace.append({"step": step, "error": "parse_failed"})
                    return self._result(task, "Could not parse a valid action after repeated "
                                        "retries.", trace, step, "parse_error", t0, plan, executed, commands)
                trace.append({"step": step, "error": "parse_failed_step"})
                self._fold(running_summary, "a step produced no valid action")
                continue

            tool, args = action["tool"], action["args"]
            self._emit_event("action_start", {"step": step, "tool": tool, "args": args})

            if tool == "finish":
                summary = str(args.get("summary", args.get("answer", ""))).strip() or "(done)"
                self._emit_event("finish", {"step": step, "summary": summary})
                trace.append({"step": step, "action": "finish"})
                return self._result(task, summary, trace, step, "finish", t0, plan, executed, commands)

            if tool == "sh_run":
                # Heal budget bounds re-runs of one command (diagnose→fix→rerun).
                ncmd = _norm_cmd(args.get("command", args.get("cmd", "")))
                cmd_attempts[ncmd] = cmd_attempts.get(ncmd, 0) + 1
                if cmd_attempts[ncmd] > self.heal_budget:
                    if self._maybe_nudge(("cmd", ncmd), history, trace, step, nudged):
                        _nudged_action_sig = ncmd
                        _nudged_step = step
                        continue  # one corrective call before the break fires
                    trace.append({"step": step, "error": "heal_budget", "command": ncmd[:160]})
                    logger.info("[coding-agent] heal-budget break step=%d cmd=%r", step, ncmd)
                    return self._result(task, f"Stopped: heal budget exhausted for `{ncmd}` "
                                        f"(attempted {self.heal_budget} times without success).",
                                        trace, step, "heal_budget", t0, plan, executed, commands)
            else:
                # No-progress guard: identical (tool,args) repeating -> break. This
                # also catches a repeated identical FIX (fs_edit_file) — attempt memory.
                sig = f"{tool}:{json.dumps(args, sort_keys=True, default=str)}"
                sig_counts[sig] = sig_counts.get(sig, 0) + 1

            result = _dispatch(tool, args)
            marker = result.get("marker") if isinstance(result, dict) else None
            gate = ("DENY:" + marker) if marker in _DENY_MARKERS else "ALLOW"
            obs = _summarize(tool, args, result, self.obs_chars, self.read_max_lines)
            # A path/command rejected as absolute -> tell the model to go relative.
            if marker in ("SANDBOX_VIOLATION", "CRITICAL_BLOCKED"):
                obs += " | HINT: use a path RELATIVE to the workspace root (no leading '/')."
            logger.info("[coding-agent] step=%d tool=%s gate=%s arg=%s",
                        step, tool, gate, _arg_label(args))
            history.append((action, obs))
            diff = result.get("diff") if isinstance(result, dict) else None
            self._emit_event("action_complete", {
                "step": step,
                "tool": tool,
                "args": args,
                "gate": gate,
                "observation": obs,
                "diff": diff,
                "status": result.get("status") if isinstance(result, dict) else None,
            })
            if diff:
                self._emit_event("diff", {
                    "step": step,
                    "tool": tool,
                    "path": args.get("path") or (result.get("path") if isinstance(result, dict) else None),
                    "diff": diff,
                })
            if isinstance(result, dict) and result.get("status") == "success" and tool in WRITE_TOOLS:
                executed.append({"tool": tool, "path": result.get("path")})
            if tool == "sh_run" and isinstance(result, dict):
                commands.append({"command": result.get("command"),
                                 "exit_code": result.get("exit_code"), "gate": gate})
                # TRIGGER A: implicit verify — sh_run of a verify command exits 0
                # => task likely done; break without calling the model again.
                if (gate == "ALLOW"
                        and result.get("exit_code") == 0
                        and _is_verify_command(args.get("command", args.get("cmd", "")).split())):
                    trace.append({"step": step, "action": "implicit_verify",
                                  "command": result.get("command", "")})
                    logger.info("[coding-agent] TRIGGER implicit_verify step=%d cmd=%r",
                                step, result.get("command", ""))
                    return self._result(
                        task, obs, trace, step, "implicit_verify",
                        t0, plan, executed, commands)
            if tool == "deploy_run" and isinstance(result, dict) and result.get("status") == "success":
                self._run_deploys.append({"platform": result.get("platform"),
                                          "prod": result.get("prod"), "url": result.get("url"),
                                          "ok": result.get("ok")})
            # TRIGGER B: implicit repeat — after a nudge, if the model repeats the
            # same action (success or failure), it is stuck. Fire implicit_repeat to stop cleanly.
            # Terminate cleanly rather than looping or breaking with no_progress.
            if (_nudged_step is not None
                    and step > _nudged_step
                    and gate == "ALLOW"
                    and isinstance(result, dict)
                    and marker not in _DENY_MARKERS):
                cur_sig = f"{tool}:{json.dumps(args, sort_keys=True, default=str)}"
                if cur_sig == _nudged_action_sig:
                    trace.append({"step": step, "action": "implicit_repeat"})
                    logger.info("[coding-agent] TRIGGER implicit_repeat step=%d tool=%s",
                                step, tool)
                    return self._result(
                        task, obs, trace, step, "implicit_repeat",
                        t0, plan, executed, commands)
            # Deferred no-progress break: only fire AFTER dispatch (so TRIGGER B
            # can override it for successful repeats).  Only for non-sh_run tools.
            if tool != "sh_run" and sig_counts.get(sig, 0) > self.max_repeat:
                if self._maybe_nudge(("sig", sig), history, trace, step, nudged):
                    _nudged_action_sig = sig
                    _nudged_step = step
                    # Do NOT break here - continue to dispatch + TRIGGER B check.
                else:
                    trace.append({"step": step, "error": "no_progress", "signature": sig[:160]})
                    logger.info("[coding-agent] no-progress break step=%d tool=%s", step, tool)
                    return self._result(task, f"Stopped: repeated the same action with no progress "
                                        f"({tool} {_arg_label(args)}).", trace, step,
                                        "no_progress", t0, plan, executed, commands)
            trace.append({"step": step, "action": tool, "args": args,
                          "gate": gate, "observation": obs[:300]})

            # Context budget: fold observations that fell out of the window.
            while len(history) > self.max_obs:
                old_act, _old_obs = history.pop(0)
                self._fold(running_summary, f"{old_act['tool']} {_arg_label(old_act['args'])}")

        trace.append({"step": self.max_steps, "stopped": "max_steps"})
        logger.info("[coding-agent] max_steps=%d reached", self.max_steps)
        return self._result(task, "Reached the step limit before finishing.",
                            trace, self.max_steps, "max_steps", t0, plan, executed, commands)

    def _result(self, task, summary, trace, steps, stopped, t0, plan, executed,
                commands=None) -> Dict[str, Any]:
        status = {"finish": "success", "rejected": "rejected"}.get(stopped, "incomplete")
        # Report any LOCAL servers still running so nothing is silently orphaned —
        # each with its serve_stop handle. We deliberately do NOT stop them here
        # (the user wants to view their app); atexit stop_all is the final backstop.
        servers = [{"id": s["id"], "command": s["command"],
                    "url": s.get("detected_url"), "stop_with": f"serve_stop id={s['id']}"}
                   for s in server.list_running()]
        res = {
            "status": status,
            "task": task,
            "summary": summary,
            "stopped": stopped,
            "steps": steps,
            "plan": plan or [],
            "executed": executed,
            "commands": commands or [],
            "servers": servers,
            "deploys": getattr(self, "_run_deploys", []),
            "trace": trace,
            "total_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        self._emit_event("done", {"result": res, "status": status, "stopped": stopped, "summary": summary})
        return res


def run_build(task: str, think_fn: Callable[[str], str],
              plan_approver: Optional[Callable[[List[Dict[str, Any]]], bool]] = None,
              workspace: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Convenience entry: optionally grant a workspace, then plan+build one task."""
    if workspace is not None:
        grant = guarded.grant_workspace(workspace)
        if grant.get("status") != "success":
            return {"status": "error", "marker": grant.get("marker", "INVALID_WORKSPACE"),
                    "message": grant.get("message", "workspace not granted"), "task": task}
    return CodingAgent(think_fn, plan_approver=plan_approver, **kw).run(task)


# ── opt-in trigger (mirrors browser.routing) ──────────────────────────────────
# Explicit "scaffold/build a project" phrasings (English + Hinglish). Deliberately
# narrow so ordinary chat / coding Q&A / RAG never routes into the builder.
_BUILD_TRIGGERS = (
    "scaffold", "boilerplate",
    "build me a", "build a project", "build the project", "build an app",
    "build a website", "build a web app", "build a python", "build a react",
    "create a project", "create a new project", "create the project",
    "set up a project", "setup a project", "generate a project", "generate the project",
    "bootstrap a project", "bootstrap the project",
    "create the files for", "generate the files for", "scaffold a", "scaffold the",
    "project banao", "app banao", "website banao", "project bana do", "app bana do",
    "code files banao", "file structure banao", "folder structure banao",
)
# Question / discussion framing -> NOT a request to actually build (suppress).
_QUESTION_MARKERS = (
    "how to", "how do", "how can i", "how does", "how would", "what is", "what are",
    "why ", "explain", "difference between", "should i use", "which is better",
    "tutorial", "example of", "what's the best way",
)


def is_build_request(text: str) -> bool:
    """True only when the user EXPLICITLY asks the agent to scaffold/build a
    project into files. Opt-in and narrow: ordinary chat, coding questions, and
    RAG messages never match, so default paths are unchanged. Discussion/how-to
    framing is suppressed even if it contains a build word."""
    t = (text or "").lower().strip()
    if not t:
        return False
    if any(q in t for q in _QUESTION_MARKERS):
        return False
    return any(p in t for p in _BUILD_TRIGGERS)
