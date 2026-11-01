"""
EvolveX Guardian Layer
Controls high-risk autonomous actions.
"""

from __future__ import annotations

import contextvars
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Confirmation provider (ContextVar  -  fail-safe DENY when unset)
# ---------------------------------------------------------------------------
_approver: "contextvars.ContextVar[Optional[Callable[[str], bool]]]" =     contextvars.ContextVar("guardian_approver", default=None)


class use_approver:
    """Context manager to install an approval provider for the current context."""

    def __init__(self, fn: Callable[[str], bool]):
        self._fn = fn

    def __enter__(self):
        self._token = _approver.set(self._fn)
        return self

    def __exit__(self, *exc):
        _approver.reset(self._token)
        return False


def approve_all(_action_name: str) -> bool:
    """Test provider: approves everything."""
    return True


def deny_all(_action_name: str) -> bool:
    """Test provider: denies everything."""
    return False


def request_approval(action_name: str) -> bool:
    """Consult the context-local approver.  No provider -> DENY (fail-safe)."""
    fn = _approver.get()
    if fn is None:
        return False          # fail-safe: deny when nothing is configured
    try:
        return bool(fn(action_name))
    except Exception:
        return False          # any provider error -> deny (fail-safe)


class OperatorGuard:
    """Class Description"""

    def __init__(self):
        self.protected_actions = {
            "self_heal",
            "auto_fix",
            "patch_apply",
            "code_rewrite",
        }

        self.protected_files = {
            "main.py",
            "manager.py",
            "brain.py",
        }

        # Read-only coding-agent filesystem actions. Like the "web_" read tools,
        # these are LOW risk and auto-allow (no confirmation). Kept as an explicit
        # allowlist  -  NOT a broad "fs_" prefix  -  so state-changing actions stay OUT
        # of the low tier and must be granted a confirmation path of their own.
        self.readonly_fs_actions = {
            "fs_list_dir",
            "fs_read_file",
            "fs_search",
        }

        # State-changing coding-agent filesystem actions (Phase 2). These NEVER
        # auto-allow  -  assess_action forces requires_confirmation=True so the
        # guarded layer must obtain a human approval before committing.
        #   MEDIUM: create/overwrite/edit content, make a directory.
        #   HIGH  : delete a file (stronger warning in the confirm prompt).
        self.medium_fs_actions = {
            "fs_write_file",
            "fs_create_file",
            "fs_edit_file",
            "fs_make_dir",
        }
        self.high_fs_actions = {
            "fs_delete_file",
        }

    # -----------------------------------------
    # Check if action requires approval
    # -----------------------------------------
    def requires_approval(self, action_name):
        """Function Description"""
        return action_name in self.protected_actions

    # -----------------------------------------
    # Check if file is protected
    # -----------------------------------------
    def is_protected_file(self, file_path):
        """Function Description"""
        for protected in self.protected_files:
            if protected in file_path:
                return True
        return False

    # -----------------------------------------
    # Request permission from operator
    # -----------------------------------------
    def request_permission(self, action_name):
        """Consult the context-local approver (ContextVar).

        No provider set -> DENY (fail-safe).
        Never calls input() or any blocking I/O.
        """
        return request_approval(action_name)

    def assess_action(self, action_name, target=None):
        """Return a non-mutating Guardian assessment for a proposed action.

        Browser reads are deliberately low-risk, but still pass through the
        existing Guardian so all executable capabilities have a common audit
        and confirmation hook.
        """
        # State-changing fs actions always require confirmation; other actions
        # only if they are in the protected set.
        if action_name in self.high_fs_actions:
            risk_level, risk_score, requires_confirmation = "high", 80, True
        elif action_name in self.medium_fs_actions:
            risk_level, risk_score, requires_confirmation = "medium", 50, True
        elif action_name.startswith("web_") or action_name in self.readonly_fs_actions:
            risk_level, risk_score, requires_confirmation = "low", 10, self.requires_approval(action_name)
        else:
            risk_level, risk_score, requires_confirmation = "unknown", 0, self.requires_approval(action_name)
        return {
            "action": action_name,
            "target": target,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "requires_confirmation": requires_confirmation,
        }
