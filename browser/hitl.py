"""Human-in-the-loop (HITL) confirmation core for Phase 3 state-changing actions.

Responsibilities (all enforcement lives here + in browser.guarded, NEVER only in
the LLM prompt):
  * classify()  — risk-tier a browser action: LOW / MEDIUM / HIGH / CRITICAL.
  * confirm()   — the gate's single approval point. Consults a context-local
                  confirmation provider; if NONE is set, it FAILS SAFE (DENY).
  * providers   — approve_all / deny_all for tests, and an InteractiveRun whose
                  provider BLOCKS until the user answers over HTTP (or a timeout
                  elapses -> DENY), enabling a paused pending-action in Flask.
  * audit       — every proposal + decision + result is logged.

CRITICAL actions (submit / checkout / pay / place-order / purchase, and anything
uncertain) are HARD-BLOCKED this phase: they are never even offered for
confirmation. Fail-safe is the rule everywhere: no provider -> deny, timeout ->
deny, ambiguous target -> CRITICAL.
"""

from __future__ import annotations

import contextvars
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

from .config import HITL_CONFIRM_TIMEOUT_S

audit = logging.getLogger("chhoti.browser.audit")
logger = logging.getLogger("chhoti.browser.hitl")

# ── Risk tiers ────────────────────────────────────────────────────────────────
READ_ACTIONS = {"search", "navigate", "read_page", "get_content", "extract_text", "finish"}
MEDIUM_ACTIONS = {"type_text", "select_option"}
# add_to_cart (Phase 4) is a HIGH click: the cart is the permitted ceiling.
HIGH_ACTIONS = {"click", "press_key", "add_to_cart"}

# Text/URL that marks a payment/checkout/order action -> CRITICAL hard-block.
# Phase 4: "add to cart" is DELIBERATELY NOT here — the cart is the ceiling and
# add-to-cart is a HIGH (confirmable) action. Everything PAST the cart stays
# CRITICAL. Extended with shopping-specific labels (Flipkart/Amazon/generic).
CRITICAL_KEYWORDS = (
    "submit", "checkout", "check out", "go to checkout", "proceed to checkout",
    "continue to checkout", "pay", "payment", "pay now", "proceed to pay",
    "proceed to buy", "continue to payment", "make payment", "pay securely",
    "place order", "place-order", "placeorder", "place your order", "order now",
    "confirm order", "confirm purchase", "complete order", "complete purchase",
    "purchase", "buy now", "buy", "billing", "place bid", "submit order",
    "cash on delivery", "net banking",
)
COMMERCE_URL_HINTS = ("/checkout", "/cart", "/payment", "/billing", "/order",
                      "/pay", "/buy", "/purchase", "/wallet", "/addresses")

# Fields we must NEVER type into (credentials / payment / personal data). Typing
# into any of these is CRITICAL -> hard-blocked; login is a manual human handoff.
CREDENTIAL_FIELD_PATTERNS = (
    "password", "passwd", "pwd", "otp", "one-time", "one time", "cvv", "cvc",
    "security code", "card number", "cardnumber", "card no", "credit card",
    "debit card", "expiry", "expiration", "upi", "vpa", "pin", "account number",
    "aadhaar", "aadhar", "ssn", "passport", "netbanking", "net banking",
)


def _target_text(target: Any) -> str:
    if isinstance(target, dict):
        return " ".join(str(target.get(k, "")) for k in
                        ("name", "text", "label", "value", "selector", "placeholder")).lower()
    return str(target or "").lower()


def _has_identifier(target: Any) -> bool:
    if isinstance(target, dict):
        return any(str(target.get(k, "")).strip()
                   for k in ("name", "text", "label", "selector", "role", "placeholder"))
    return bool(str(target or "").strip())


def _is_credential_field(target: Any) -> bool:
    tgt = _target_text(target)
    return any(p in tgt for p in CREDENTIAL_FIELD_PATTERNS)


def _is_critical(action: str, target: Any, value: Any, url: str) -> bool:
    hay = f"{_target_text(target)} {str(value or '').lower()} {str(url or '').lower()}"
    if any(k in hay for k in CRITICAL_KEYWORDS):
        return True
    low_url = str(url or "").lower()
    if any(h in low_url for h in COMMERCE_URL_HINTS):
        return True
    if action in (MEDIUM_ACTIONS | HIGH_ACTIONS):
        # Never type into a credential/payment/personal field (fail-safe CRITICAL).
        if _is_credential_field(target):
            return True
        # AMBIGUOUS -> fail safe to CRITICAL: never act on a state-changing target
        # we cannot even identify.
        if not _has_identifier(target):
            return True
    return False


def classify(action: str, target: Any = None, value: Any = None, url: str = "") -> Dict[str, Any]:
    """Return {tier, requires_confirmation, critical} for a proposed action."""
    action = (action or "").lower()
    if action in (MEDIUM_ACTIONS | HIGH_ACTIONS) and _is_critical(action, target, value, url):
        return {"tier": "CRITICAL", "requires_confirmation": False, "critical": True}
    if action in MEDIUM_ACTIONS:
        return {"tier": "MEDIUM", "requires_confirmation": True, "critical": False}
    if action in HIGH_ACTIONS:
        return {"tier": "HIGH", "requires_confirmation": True, "critical": False}
    return {"tier": "LOW", "requires_confirmation": False, "critical": False}


# ── Proposal ──────────────────────────────────────────────────────────────────
@dataclass
class Proposal:
    action: str
    tier: str
    url: str
    domain: str
    target: str = ""
    value: str = ""

    def describe(self) -> str:
        val = f' value="{self.value}"' if self.value else ""
        tgt = f" on [{self.target}]" if self.target else ""
        return f"{self.tier} {self.action}{tgt}{val} @ {self.domain} ({self.url})"

    def as_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "tier": self.tier, "url": self.url,
                "domain": self.domain, "target": self.target, "value": self.value,
                "prompt": (f"Approve this {self.tier}-risk browser action?\n"
                           f"  action: {self.action}\n  target: {self.target}\n"
                           + (f"  value : {self.value}\n" if self.value else "")
                           + f"  page  : {self.url}\nReply approve / deny.")}


def make_proposal(action: str, target: Any, value: Any, url: str, tier: str) -> Proposal:
    dom = (urlparse(url).hostname or "").lower() if url else ""
    tgt = ""
    if isinstance(target, dict):
        tgt = (target.get("name") or target.get("text") or target.get("label")
               or target.get("selector") or target.get("role") or "").strip()
    else:
        tgt = str(target or "").strip()
    return Proposal(action=action, tier=tier, url=url, domain=dom,
                    target=tgt, value=str(value or ""))


# ── Confirmation provider (context-local; fail-safe DENY when unset) ──────────
_provider: "contextvars.ContextVar[Optional[Callable[[Proposal], bool]]]" = \
    contextvars.ContextVar("hitl_provider", default=None)


class use_provider:
    """Context manager to install a confirmation provider for the current context."""

    def __init__(self, fn: Callable[[Proposal], bool]):
        self._fn = fn

    def __enter__(self):
        self._token = _provider.set(self._fn)
        return self

    def __exit__(self, *exc):
        _provider.reset(self._token)
        return False


def confirm(proposal: Proposal) -> bool:
    """The gate's approval point. Returns True ONLY on explicit approval."""
    fn = _provider.get()
    audit.info("PROPOSE %s", proposal.describe())
    if fn is None:
        audit.info("DECISION DENY (no confirmation provider) %s", proposal.describe())
        return False
    try:
        decision = bool(fn(proposal))
    except Exception as exc:  # any provider error -> deny (fail safe)
        audit.info("DECISION DENY (provider error: %s) %s", exc, proposal.describe())
        return False
    audit.info("DECISION %s %s", "APPROVE" if decision else "DENY", proposal.describe())
    return decision


# Simple providers for tests / demos (simulate the user's click).
def approve_all(_proposal: Proposal) -> bool:
    return True


def deny_all(_proposal: Proposal) -> bool:
    return False


# ── Flask pause/resume: a paused pending-action resumed on the user's reply ───
class InteractiveRun:
    """Runs an agent goal in a background thread; each risky action PAUSES here
    until the user approves/denies over HTTP (or a timeout -> DENY)."""

    def __init__(self, confirm_timeout: float = None):
        self.cond = threading.Condition()
        self.state = "running"        # running | pending | done | error
        self.pending: Optional[Proposal] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._decision: Optional[bool] = None
        self._timeout = confirm_timeout if confirm_timeout is not None else HITL_CONFIRM_TIMEOUT_S
        self.thread: Optional[threading.Thread] = None

    def provider(self) -> Callable[[Proposal], bool]:
        def _p(proposal: Proposal) -> bool:
            with self.cond:
                self.pending = proposal
                self.state = "pending"
                self._decision = None
                self.cond.notify_all()
                got = self.cond.wait_for(lambda: self._decision is not None, timeout=self._timeout)
                decision = self._decision if got else False   # timeout/no-answer -> DENY
                if not got:
                    audit.info("DECISION DENY (timeout %.0fs) %s", self._timeout, proposal.describe())
                self.pending = None
                self.state = "running"
                self._decision = None
                self.cond.notify_all()
                return bool(decision)
        return _p

    def respond(self, approve: bool) -> None:
        with self.cond:
            self._decision = bool(approve)
            self.cond.notify_all()
            # Block until the worker actually CONSUMES this decision (it resets
            # _decision to None as it leaves the 'pending' wait). Without this, a
            # following wait_checkpoint() could observe the just-resolved 'pending'
            # state and wrongly re-return the same proposal instead of advancing.
            self.cond.wait_for(lambda: self._decision is None, timeout=10)

    def finish(self, result=None, error=None) -> None:
        with self.cond:
            self.result = result
            self.error = error
            self.state = "error" if error else "done"
            self.cond.notify_all()

    def wait_checkpoint(self, timeout: float = 30.0) -> Dict[str, Any]:
        with self.cond:
            self.cond.wait_for(lambda: self.state in ("pending", "done", "error"),
                               timeout=timeout)
            if self.state == "pending" and self.pending is not None:
                return {"status": "pending_confirmation", "proposal": self.pending.as_dict()}
            if self.state == "error":
                return {"status": "error", "error": self.error}
            if self.state == "done":
                return {"status": "done", "result": self.result}
            return {"status": "running"}


_runs: Dict[str, InteractiveRun] = {}
_runs_lock = threading.Lock()


def start_run(session_id: str, goal: str, think_fn, synth_fn=None,
              max_steps: int = None, confirm_timeout: float = None) -> InteractiveRun:
    """Start an interactive agent run in a background thread, returning its handle.
    The confirmation provider is installed INSIDE the worker thread's context."""
    run = InteractiveRun(confirm_timeout=confirm_timeout)

    def _worker():
        try:
            from .agent import run_research
            with use_provider(run.provider()):
                result = run_research(goal, think_fn=think_fn, synth_fn=synth_fn,
                                      max_steps=max_steps) if max_steps is not None else \
                    run_research(goal, think_fn=think_fn, synth_fn=synth_fn)
            run.finish(result=result)
        except Exception as exc:  # pragma: no cover - defensive
            run.finish(error=str(exc))

    run.thread = threading.Thread(target=_worker, name=f"hitl-{session_id}", daemon=True)
    with _runs_lock:
        _runs[session_id] = run
    run.thread.start()
    return run


def poll(session_id: str, wait: float = 30.0) -> Dict[str, Any]:
    run = _runs.get(session_id)
    if not run:
        return {"status": "unknown"}
    return run.wait_checkpoint(wait)


def respond(session_id: str, approve: bool, wait: float = 30.0) -> Dict[str, Any]:
    run = _runs.get(session_id)
    if not run:
        return {"status": "unknown"}
    run.respond(approve)
    return run.wait_checkpoint(wait)
