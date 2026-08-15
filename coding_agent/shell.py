"""Gated, run-to-completion shell for the coding agent (Phase 4).

Two parts:

  * ``classify(command)`` — THE SAFETY CORE. Parses a command with ``shlex`` and
    assigns a risk tier by *classification*, never a blanket prefix:
        MEDIUM   — allowlisted dev commands (pytest/npm/pip/node/python/ruff/
                   eslint/tsc/git status|diff|log|add|commit/ls/cat/pwd).
        HIGH     — destructive-but-legit (rm non-recursive, git reset --hard,
                   git clean, git push, mv, and any unknown/unlisted program).
        CRITICAL — hard-blocked, NEVER runs and is never even offered for
                   confirmation (rm -rf, sudo, dd, mkfs, chmod/chown of system
                   paths, curl|sh, shutdown/reboot, del /f, rmdir /s, format,
                   reg, any absolute/system path outside the workspace, and any
                   command containing shell metacharacters).

  * an INJECTABLE executor — ``run(argv, cwd, timeout, output_cap)`` — that runs
    the argv list with ``shell=False`` (no shell interpretation), pins ``cwd`` to
    the workspace root, hard-kills on timeout, and bounds output.

SHELL JAIL IS BEST-EFFORT. Pinning ``cwd`` and refusing absolute/system path args
does NOT sandbox a child process — a program we launch can still read outside the
workspace. The REAL defenses are, in order: the classifier + the CRITICAL
hard-block (metacharacters / dangerous programs never run), the per-command HIGH
confirmation, ``shell=False`` (so ``;`` ``&&`` ``|`` `` ` `` ``$()`` cannot
chain-escape), and the hard timeout. Treat this as a guardrail, not a sandbox.
"""

from __future__ import annotations

import contextvars
import logging
import os
import shlex
import subprocess
from typing import Any, Callable, Dict, List, Optional

from .sandbox import strip_bare_root

logger = logging.getLogger("chhoti.coding_agent.shell")

# Shell metacharacters that imply chaining / substitution / redirection / pipes.
# ANY of these -> the command "needs a shell" -> CRITICAL (we never run it). Bare
# parens are intentionally NOT here: they appear inside quoted args like
# python -c "print(1)"; real substitution ("$(", backtick) is still caught.
_SHELL_METACHARS = (";", "|", "&", "`", "$(", "${", ">", "<", "\n", "\r")

# Programs that are never acceptable in a build/dev flow -> CRITICAL.
_CRITICAL_PROGRAMS = {
    "sudo", "doas", "su", "dd", "mkfs", "shutdown", "reboot", "halt", "poweroff",
    "init", "telinit", "format", "reg", "del", "rmdir", "diskpart", "fdisk",
    "mkswap", "parted", "chpasswd", "passwd", "useradd", "userdel", "mount",
    "umount", "systemctl", "rundll32", "regsvr32", "bcdedit",
}
# mkfs.ext4 etc. — any mkfs.* is CRITICAL (handled by prefix check too).

# Destructive-but-legitimate programs -> HIGH (individual confirm every time).
_HIGH_PROGRAMS = {"rm", "mv", "chmod", "chown", "chgrp", "kill", "pkill", "taskkill"}

# Allowlisted dev programs -> MEDIUM (may auto-run only when in an approved plan).
_MEDIUM_PROGRAMS = {
    "python", "python3", "py", "node", "pytest", "pip", "pip3",
    "ruff", "eslint", "tsc", "prettier", "mypy", "black", "flake8",
    "ls", "cat", "pwd", "echo", "which", "where",
}
# npm/yarn/pnpm are MEDIUM only for a safe subcommand allowlist (below).
_NODE_PKG_MANAGERS = {"npm", "yarn", "pnpm"}
_NODE_PKG_SAFE_SUBCMDS = {"test", "run", "install", "ci", "i", "build", "lint",
                          "exec", "audit", "ls", "list"}

# System path prefixes that must never be touched (absolute-outside -> CRITICAL).
_SYSTEM_PATH_PREFIXES = (
    "/etc", "/bin", "/sbin", "/usr", "/lib", "/boot", "/dev", "/proc", "/sys",
    "/root", "/var", "/opt", "c:\\windows", "c:/windows", "c:\\program files",
    "c:/program files", "\\windows", "/system", "%windir%", "%systemroot%",
)


def _basename(prog: str) -> str:
    return os.path.basename(prog.replace("\\", "/")).lower()


def _has_shell_meta(raw: str) -> bool:
    return any(m in raw for m in _SHELL_METACHARS)


def _looks_absolute(arg: str) -> bool:
    if not arg:
        return False
    if arg.startswith("/") or arg.startswith("\\\\") or arg.startswith("~"):
        return True
    # Windows drive-letter path: X:\ or X:/
    return len(arg) >= 3 and arg[1] == ":" and arg[2] in ("\\", "/")


def _is_system_path(arg: str) -> bool:
    low = arg.lower().replace("\\", "\\")  # keep as-is; compare both sep forms
    low2 = arg.lower()
    return any(low2.startswith(p) or low.startswith(p) for p in _SYSTEM_PATH_PREFIXES)


def _arg_escapes_workspace(arg: str, workspace_root: Optional[str]) -> bool:
    """True if an absolute path arg points at a system path, or (when the root is
    known) resolves outside the workspace. Relative args are treated as in-cwd."""
    # Strip a leading =value (e.g. --out=/etc/x) and quotes.
    candidate = arg.split("=", 1)[1] if arg.startswith("--") and "=" in arg else arg
    # A bare POSIX-root path (/x) is workspace-relative, not an escape; only a
    # genuine drive-letter/UNC absolute survives normalization and is checked.
    candidate = strip_bare_root(candidate)
    if not _looks_absolute(candidate):
        return False
    if _is_system_path(candidate):
        return True
    if workspace_root is None:
        return True  # unknown workspace -> any absolute path is treated as outside
    try:
        real = os.path.realpath(candidate)
        root = os.path.realpath(workspace_root)
        cmp = os.path.normcase(real)
        return not (cmp == os.path.normcase(root) or cmp.startswith(os.path.normcase(root) + os.sep))
    except OSError:
        return True


def _mk(tier: str, reason: str, program: str, argv: List[str]) -> Dict[str, Any]:
    return {"tier": tier, "reason": reason, "program": program,
            "argv": argv, "critical": tier == "CRITICAL"}


def _has_flag(args: List[str], *flags: str) -> bool:
    return any(a in flags for a in args)


def classify(command: str, workspace_root: Optional[str] = None) -> Dict[str, Any]:
    """Classify a command into MEDIUM / HIGH / CRITICAL WITHOUT running it."""
    raw = (command or "").strip()
    if not raw:
        return _mk("CRITICAL", "empty command", "", [])

    # 1) shell metacharacters -> needs a shell -> CRITICAL (pipe-to-shell, chaining…)
    if _has_shell_meta(raw):
        return _mk("CRITICAL", "shell metacharacters / pipe-to-shell not allowed", "", [])

    # 2) must be parseable as a plain argv list
    try:
        argv = shlex.split(raw, posix=(os.name != "nt"))
    except ValueError:
        return _mk("CRITICAL", "unparseable command (unbalanced quotes)", "", [])
    if not argv:
        return _mk("CRITICAL", "empty command", "", [])

    program = _basename(argv[0])
    # Normalize bare-root path ARGS (/add.py -> add.py) so the command both
    # classifies AND RUNS relative to the workspace. Drive-letter/UNC absolutes
    # are left intact and still blocked below. argv[0] (the program) is untouched.
    args = [strip_bare_root(a) for a in argv[1:]]
    argv = [argv[0]] + args  # what the executor will run

    # 3) any absolute/system path argument outside the workspace -> CRITICAL
    for a in args:
        if _arg_escapes_workspace(a, workspace_root):
            return _mk("CRITICAL", f"absolute/system path argument not allowed: {a}", program, argv)

    # 4) hard-blocked programs / forms
    if program.startswith("mkfs"):
        return _mk("CRITICAL", "filesystem-format command", program, argv)
    if program in _CRITICAL_PROGRAMS:
        return _mk("CRITICAL", f"dangerous program '{program}'", program, argv)
    if program == "rm" and _has_flag(args, "-r", "-rf", "-fr", "-R", "-Rf", "--recursive"):
        return _mk("CRITICAL", "recursive rm (rm -rf) is hard-blocked", program, argv)
    if program in ("chmod", "chown", "chgrp") and any(_looks_absolute(a) for a in args):
        return _mk("CRITICAL", f"{program} on an absolute path", program, argv)

    # 5) HIGH: destructive-but-legit (individual confirm every time)
    if program in _HIGH_PROGRAMS:
        return _mk("HIGH", f"destructive command '{program}'", program, argv)
    if program == "git" and args:
        sub = args[0].lower()
        if sub == "reset" and _has_flag(args, "--hard"):
            return _mk("HIGH", "git reset --hard discards changes", program, argv)
        if sub in ("clean", "push"):
            return _mk("HIGH", f"git {sub}", program, argv)
        if sub in ("status", "diff", "log", "add", "commit", "show", "branch", "fetch"):
            return _mk("MEDIUM", f"git {sub}", program, argv)
        return _mk("HIGH", f"unlisted git subcommand '{sub}'", program, argv)

    # 6) MEDIUM: allowlisted dev programs
    if program in _NODE_PKG_MANAGERS:
        sub = args[0].lower() if args else ""
        if sub in _NODE_PKG_SAFE_SUBCMDS:
            return _mk("MEDIUM", f"{program} {sub}", program, argv)
        return _mk("HIGH", f"unlisted {program} subcommand '{sub or '(none)'}'", program, argv)
    if program in _MEDIUM_PROGRAMS:
        return _mk("MEDIUM", f"dev command '{program}'", program, argv)

    # 7) default: unknown / unlisted program -> HIGH (never silently MEDIUM)
    return _mk("HIGH", f"unknown/unlisted program '{program}'", program, argv)


# ── executor (injectable; default runs the argv list with shell=False) ─────────
def _truncate_middle(text: str, cap: int) -> str:
    if cap <= 0 or len(text) <= cap:
        return text
    half = cap // 2
    omitted = len(text) - 2 * half
    return f"{text[:half]}\n…[truncated {omitted} chars]…\n{text[-half:]}"


def default_run(argv: List[str], cwd: str, timeout: float, output_cap: int) -> Dict[str, Any]:
    """Run ``argv`` to completion with ``shell=False``, cwd pinned, hard timeout
    (child killed), and bounded output. NEVER uses a shell."""
    try:
        proc = subprocess.run(
            argv, cwd=cwd, shell=False, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        stdout, stderr, code, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:  # subprocess.run kills the child here
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        stderr = (exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes)
                  else (exc.stderr or ""))
        stderr = (stderr + f"\n[killed: exceeded {timeout}s timeout]").strip()
        code, timed_out = -1, True
    except FileNotFoundError:
        return {"exit_code": 127, "stdout": "", "stderr": f"command not found: {argv[0]}",
                "timed_out": False}
    return {
        "exit_code": code,
        "stdout": _truncate_middle(stdout, output_cap),
        "stderr": _truncate_middle(stderr, output_cap),
        "timed_out": timed_out,
    }


# Context-local executor override (mirrors hitl.use_approver) so tests never run
# real dangerous commands.
_executor: "contextvars.ContextVar[Optional[Callable[..., Dict[str, Any]]]]" = \
    contextvars.ContextVar("shell_executor", default=None)


class use_executor:
    """Context manager to install a mock executor for the current context."""

    def __init__(self, fn: Callable[..., Dict[str, Any]]):
        self._fn = fn

    def __enter__(self):
        self._token = _executor.set(self._fn)
        return self

    def __exit__(self, *exc):
        _executor.reset(self._token)
        return False


def run(argv: List[str], cwd: str, timeout: float, output_cap: int) -> Dict[str, Any]:
    """Execute via the active executor (mock in tests, else default_run)."""
    fn = _executor.get() or default_run
    return fn(argv, cwd=cwd, timeout=timeout, output_cap=output_cap)
