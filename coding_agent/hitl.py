"""Human-in-the-loop confirmation for coding-agent WRITE actions (Phase 2).

Mirrors ``browser/hitl.py``: a context-local *approver* provider that tests can
install to auto-approve / auto-deny, and that fails safe when nothing can grant
approval. The difference from the browser layer is the payload — a
:class:`WriteProposal` carries a **unified diff** so the human (or the UI) sees
exactly what will change before they approve.

Confirmation resolution order in :func:`confirm`:
  1. an approver installed via :class:`use_approver` (tests / future HTTP HITL),
  2. else the ``fallback`` — in production the Guardian's blocking
     ``request_permission()`` (the real human prompt),
  3. else fail-safe DENY.

Every proposal + decision + result is written to the audit log. There is no
auto-allow path for writes: MEDIUM/HIGH fs actions can only proceed on an
explicit approval.
"""

from __future__ import annotations

import contextvars
import difflib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

audit = logging.getLogger("chhoti.coding_agent.audit")
logger = logging.getLogger("chhoti.coding_agent.hitl")


# ── Proposal ──────────────────────────────────────────────────────────────────
@dataclass
class WriteProposal:
    """A pending state-changing filesystem action awaiting human approval."""

    action: str          # fs_write_file / fs_create_file / fs_edit_file / …
    tier: str            # MEDIUM | HIGH
    path: str            # workspace-relative path
    summary: str         # one-line human summary of the change
    diff: str            # unified diff (old vs new)
    warning: str = ""    # extra caution text (HIGH/delete gets a stronger one)

    def describe(self) -> str:
        return f"{self.tier} {self.action} {self.path} :: {self.summary}"

    def as_dict(self) -> Dict[str, Any]:
        prompt = (f"Approve this {self.tier}-risk filesystem action?\n"
                  f"  action: {self.action}\n  path  : {self.path}\n"
                  f"  change: {self.summary}\n")
        if self.warning:
            prompt += f"  ⚠ {self.warning}\n"
        prompt += f"--- diff ---\n{self.diff}\nReply approve / deny."
        return {"action": self.action, "tier": self.tier, "path": self.path,
                "summary": self.summary, "diff": self.diff, "warning": self.warning,
                "prompt": prompt}


@dataclass
class ShellProposal:
    """A pending shell command awaiting approval (Phase 4). Same confirm flow as
    writes — carries the command text (shown to the human) instead of a diff."""

    command: str
    tier: str            # MEDIUM | HIGH  (CRITICAL is hard-blocked, never proposed)
    program: str = ""
    reason: str = ""
    warning: str = ""
    label: str = "sh_run"  # "sh_run" or "serve_start" — what kind of run this is

    def describe(self) -> str:
        return f"{self.tier} {self.label} `{self.command}` ({self.reason})"

    @property
    def diff(self) -> str:  # uniform render: show the command that will run
        return f"$ {self.command}"

    def as_dict(self) -> Dict[str, Any]:
        prompt = (f"Approve running this {self.tier}-risk command?\n"
                  f"  $ {self.command}\n  reason: {self.reason}\n")
        if self.warning:
            prompt += f"  ⚠ {self.warning}\n"
        prompt += "Reply approve / deny."
        return {"command": self.command, "tier": self.tier, "program": self.program,
                "reason": self.reason, "warning": self.warning, "prompt": prompt}


@dataclass
class DeployProposal:
    """A pending PUBLIC deploy awaiting an ALWAYS-individual human confirmation.

    Deploy is the highest-risk action, so it rides a SEPARATE approval channel
    (confirm_deploy / _deploy_approver) that the generic write/shell approver —
    including approve_all — can never satisfy. That is the structural guarantee
    that a deploy is never auto-approved."""

    platform: str
    command: str
    prod: bool = False
    secrets_found: bool = False
    secret_findings: list = field(default_factory=list)
    final: bool = False   # the extra confirmation required for a production deploy
    warning: str = ""

    @property
    def tier(self) -> str:
        return "DEPLOY"

    def describe(self) -> str:
        env = "PRODUCTION" if self.prod else "preview"
        extra = " [FINAL PRODUCTION CONFIRM]" if self.final else ""
        sec = f" ⚠ SECRETS×{len(self.secret_findings)}" if self.secrets_found else ""
        return f"DEPLOY[{env}] {self.platform}: {self.command}{extra}{sec}"

    @property
    def diff(self) -> str:  # uniform render surface
        lines = [f"$ {self.command}",
                 f"target: {'PRODUCTION (live)' if self.prod else 'preview'}"]
        if self.secrets_found:
            lines.append("SECRET PREFLIGHT — these would be uploaded:")
            lines += [f"  - {f.get('file')} ({f.get('pattern', f.get('type'))})"
                      for f in self.secret_findings]
        return "\n".join(lines)

    def as_dict(self) -> Dict[str, Any]:
        return {"platform": self.platform, "command": self.command, "prod": self.prod,
                "secrets_found": self.secrets_found, "secret_findings": self.secret_findings,
                "final": self.final, "warning": self.warning,
                "prompt": f"Approve this deploy?\n{self.diff}\nReply approve / deny."}


def unified_diff(old: str, new: str, path: str, *, context: int = 3) -> str:
    """Return a unified diff of ``old`` vs ``new`` for ``path`` (empty if equal)."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diff: List[str] = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{path}", tofile=f"b/{path}",
        lineterm="", n=context,
    ))
    return "\n".join(diff)


# ── Context-local approver (fail-safe DENY when unset & no fallback) ───────────
_approver: "contextvars.ContextVar[Optional[Callable[[WriteProposal], bool]]]" = \
    contextvars.ContextVar("fs_approver", default=None)


class use_approver:
    """Context manager to install a confirmation approver for the current context."""

    def __init__(self, fn: Callable[[WriteProposal], bool]):
        self._fn = fn

    def __enter__(self):
        self._token = _approver.set(self._fn)
        return self

    def __exit__(self, *exc):
        _approver.reset(self._token)
        return False


def approve_all(_proposal: WriteProposal) -> bool:
    return True


def deny_all(_proposal: WriteProposal) -> bool:
    return False


def _render(proposal: Any) -> None:
    """Surface the proposal (diff for writes, command for shell) so a human can see
    what will happen. Attribute-defensive so it works for any proposal type.

    Printed to stdout (the CLI confirm surface) and mirrored to the audit log.
    """
    lines = [f"\n[coding-agent] {getattr(proposal, 'tier', '?')}-risk action requires approval:",
             f"  {proposal.describe()}"]
    warning = getattr(proposal, "warning", "")
    if warning:
        lines.append(f"  ⚠ {warning}")
    diff = getattr(proposal, "diff", "")
    if diff:
        lines.append("--- change ---")
        lines.append(diff)
    print("\n".join(lines))


def confirm(proposal: Any,
            fallback: Optional[Callable[[Any], bool]] = None) -> bool:
    """The single approval point for a write. Returns True ONLY on explicit yes."""
    audit.info("PROPOSE %s", proposal.describe())
    _render(proposal)

    fn = _approver.get()
    if fn is not None:
        source = "approver"
    elif fallback is not None:
        fn = fallback
        source = "fallback"
    else:
        audit.info("DECISION DENY (no approver/fallback) %s", proposal.describe())
        return False

    try:
        decision = bool(fn(proposal))
    except Exception as exc:  # any approver/fallback error -> deny (fail safe)
        audit.info("DECISION DENY (%s error: %s) %s", source, exc, proposal.describe())
        return False

    audit.info("DECISION %s (%s) %s",
               "APPROVE" if decision else "DENY", source, proposal.describe())
    return decision


# ── deploy approval: a SEPARATE channel (never the generic _approver) ─────────
# Deploy MUST be individually confirmed every time — even under approve_all and
# even inside an approved build session. Using a distinct ContextVar makes it
# structurally impossible for the write/shell approver to auto-approve a deploy.
_deploy_approver: "contextvars.ContextVar[Optional[Callable[[DeployProposal], bool]]]" = \
    contextvars.ContextVar("deploy_approver", default=None)


class use_deploy_approver:
    """Install the (individual) deploy approver for the current context."""

    def __init__(self, fn: Callable[[DeployProposal], bool]):
        self._fn = fn

    def __enter__(self):
        self._token = _deploy_approver.set(self._fn)
        return self

    def __exit__(self, *exc):
        _deploy_approver.reset(self._token)
        return False


def confirm_deploy(proposal: DeployProposal,
                   fallback: Optional[Callable[[DeployProposal], bool]] = None) -> bool:
    """Approval point for a deploy. Consults ONLY the deploy channel (never the
    generic approver), then a fallback (the Guardian's human prompt), else denies."""
    audit.info("PROPOSE %s", proposal.describe())
    _render(proposal)

    fn = _deploy_approver.get()
    if fn is not None:
        source = "deploy_approver"
    elif fallback is not None:
        fn = fallback
        source = "fallback"
    else:
        audit.info("DECISION DENY (no deploy approver/fallback) %s", proposal.describe())
        return False

    try:
        decision = bool(fn(proposal))
    except Exception as exc:  # fail safe
        audit.info("DECISION DENY (%s error: %s) %s", source, exc, proposal.describe())
        return False

    audit.info("DECISION %s (%s) %s",
               "APPROVE" if decision else "DENY", source, proposal.describe())
    return decision
