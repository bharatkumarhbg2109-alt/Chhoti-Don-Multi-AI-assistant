"""
Chhoti Don - Hands Layer :: Base

Foundations shared by every "Hand" (tool module) and the Tool Manager.

Design goals
------------
* Additive & self-contained — nothing here imports the Brain, agents, UI or
  existing tool registry; the Hands Layer is a separate, optional module.
* Never crash on a missing optional dependency. Each Hand lazily imports its
  libraries and reports availability through `health()`; unavailable actions
  return a structured error instead of raising.
* Consistent, JSON-friendly result envelopes and structured logging.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

# ── Runtime / logging location (honours the desktop relocation env) ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RUNTIME_DIR = os.environ.get("CHHOTI_DON_RUNTIME_DIR") or os.path.join(_PROJECT_ROOT, ".runtime")

logger = logging.getLogger("chhoti.hands")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    try:
        os.makedirs(_RUNTIME_DIR, exist_ok=True)
        _fh = logging.FileHandler(os.path.join(_RUNTIME_DIR, "hands.log"), encoding="utf-8")
        _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(_fh)
    except Exception:
        # Logging must never break tool execution.
        logger.addHandler(logging.NullHandler())


class Permission(IntEnum):
    """Escalating permission levels for actions."""
    READ_ONLY = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4
    DANGEROUS = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def tool_result(
    hand: str,
    action: str,
    *,
    status: str = "success",
    result: Any = None,
    error: Optional[str] = None,
    duration_ms: float = 0.0,
    permission: Optional[Permission] = None,
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build the standard, JSON-friendly result envelope for a tool execution."""
    payload: Dict[str, Any] = {
        "status": status,          # success | error | blocked | unavailable | confirmation_required | timeout
        "hand": hand,
        "action": action,
        "result": result,
        "error": error,
        "duration_ms": round(duration_ms, 2),
        "timestamp": _now_iso(),
    }
    if permission is not None:
        payload["permission"] = permission.name
    if extra:
        payload.update(extra)
    return payload


@dataclass
class Action:
    """Metadata + handler for one capability exposed by a Hand."""
    name: str
    fn: Callable[..., Any]
    permission: Permission = Permission.READ_ONLY
    destructive: bool = False
    doc: str = ""


class BaseHand:
    """Abstract base for every Hand.

    Subclasses:
      * set `name` and `description`
      * implement `_check_available()` (deps present?) — optional, defaults True
      * register capabilities in `__init__` via `self.register(...)`
    """

    name: str = "base"
    description: str = ""
    #: optional module names this hand needs (used by `missing_dependencies`)
    dependencies: List[str] = []

    def __init__(self) -> None:
        self._actions: Dict[str, Action] = {}

    # ── Registration ─────────────────────────────────────────
    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        *,
        permission: Permission = Permission.READ_ONLY,
        destructive: bool = False,
        doc: str = "",
    ) -> None:
        self._actions[name] = Action(name=name, fn=fn, permission=permission,
                                     destructive=destructive, doc=doc or (fn.__doc__ or "").strip())

    # ── Discovery ────────────────────────────────────────────
    def list_actions(self) -> List[str]:
        return list(self._actions.keys())

    def describe(self) -> Dict[str, Any]:
        return {
            "hand": self.name,
            "description": self.description,
            "available": self.is_available(),
            "missing_dependencies": self.missing_dependencies(),
            "actions": {
                a.name: {
                    "permission": a.permission.name,
                    "destructive": a.destructive,
                    "doc": a.doc,
                }
                for a in self._actions.values()
            },
        }

    # ── Availability ─────────────────────────────────────────
    def missing_dependencies(self) -> List[str]:
        missing = []
        for mod in self.dependencies:
            try:
                __import__(mod)
            except Exception:
                missing.append(mod)
        return missing

    def _check_available(self) -> bool:
        """Override for custom availability logic. Default: all deps importable."""
        return not self.missing_dependencies()

    def is_available(self) -> bool:
        try:
            return self._check_available()
        except Exception:
            return False

    def health(self) -> Dict[str, Any]:
        available = self.is_available()
        return {
            "hand": self.name,
            "available": available,
            "missing_dependencies": self.missing_dependencies(),
            "actions": len(self._actions),
            "status": "ready" if available else "unavailable",
        }

    # ── Execution ────────────────────────────────────────────
    def run(self, action: str, params: Optional[Dict] = None, *, confirm: bool = False) -> Dict[str, Any]:
        """Validate + execute one action, timing/logging it and never raising."""
        params = dict(params or {})
        started = time.time()

        act = self._actions.get(action)
        if act is None:
            return self._logged(tool_result(
                self.name, action, status="error",
                error=f"Unknown action '{action}'. Available: {self.list_actions()}",
                duration_ms=(time.time() - started) * 1000,
            ), params)

        if not self.is_available():
            return self._logged(tool_result(
                self.name, action, status="unavailable",
                error=f"{self.name} hand unavailable. Missing: {self.missing_dependencies()}",
                duration_ms=(time.time() - started) * 1000, permission=act.permission,
            ), params)

        # Destructive / dangerous actions require an explicit confirmation.
        if (act.destructive or act.permission >= Permission.DANGEROUS) and not confirm:
            return self._logged(tool_result(
                self.name, action, status="confirmation_required",
                error="This action is potentially destructive. Re-run with confirm=True.",
                duration_ms=(time.time() - started) * 1000, permission=act.permission,
                extra={"destructive": True},
            ), params)

        try:
            value = act.fn(**params)
            # Allow handlers to return a fully-formed envelope, or a raw value.
            if isinstance(value, dict) and value.get("__envelope__"):
                value.pop("__envelope__", None)
                return self._logged(value, params)
            return self._logged(tool_result(
                self.name, action, status="success", result=value,
                duration_ms=(time.time() - started) * 1000, permission=act.permission,
            ), params)
        except TypeError as exc:
            return self._logged(tool_result(
                self.name, action, status="error",
                error=f"Bad parameters for '{action}': {exc}",
                duration_ms=(time.time() - started) * 1000, permission=act.permission,
            ), params)
        except Exception as exc:  # never crash the caller
            return self._logged(tool_result(
                self.name, action, status="error", error=str(exc),
                duration_ms=(time.time() - started) * 1000, permission=act.permission,
            ), params)

    # ── Logging ──────────────────────────────────────────────
    def _logged(self, envelope: Dict[str, Any], params: Dict) -> Dict[str, Any]:
        try:
            safe = _sanitize_params(params)
            logger.info(
                "hand=%s action=%s status=%s duration_ms=%s params=%s error=%s",
                envelope.get("hand"), envelope.get("action"), envelope.get("status"),
                envelope.get("duration_ms"), safe, envelope.get("error"),
            )
        except Exception:
            pass
        return envelope


def _sanitize_params(params: Dict) -> Dict:
    """Truncate/redact params for logging (no secrets or huge blobs)."""
    out = {}
    for k, v in params.items():
        lk = str(k).lower()
        if any(s in lk for s in ("password", "token", "secret", "api_key", "apikey")):
            out[k] = "***"
        elif isinstance(v, (bytes, bytearray)):
            out[k] = f"<{len(v)} bytes>"
        else:
            s = str(v)
            out[k] = s if len(s) <= 200 else s[:200] + "…"
    return out
