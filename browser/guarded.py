"""The single policy choke point for all browser operations."""

import logging
import threading
from collections import defaultdict, deque
from time import monotonic
from typing import Any, Callable, Dict
from urllib.parse import urlparse

from cyber_engine.guardian.operator_guard import OperatorGuard

from .config import BLOCKED_DOMAINS, RATE_LIMIT_PER_MIN, REQUIRE_CONFIRMATION
from . import search as _raw_search
from . import session as _raw_session

logger = logging.getLogger("chhoti.browser")

_calls_by_domain = defaultdict(deque)
_guardian = OperatorGuard()
_SEARCH_DOMAIN = "ddgs-search"

# Serialize live Playwright operations: the persistent profile dir is single-use
# and the product opens ONE visible window at a time.
_browser_lock = threading.Lock()


def _domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"//{value}")
    return (parsed.hostname or "").lower().rstrip(".")


def _is_blocked(domain: str) -> bool:
    return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in BLOCKED_DOMAINS)


def _gate(action: str, target: str) -> Dict[str, Any] | None:
    """Apply blocklist, rate limit, then Guardian assessment in that order."""
    domain = _domain(target) or _SEARCH_DOMAIN
    if _is_blocked(domain):
        return {"status": "error", "marker": "BLOCKED_DOMAIN", "domain": domain}

    now = monotonic()
    calls = _calls_by_domain[domain]
    while calls and now - calls[0] >= 60:
        calls.popleft()
    if len(calls) >= RATE_LIMIT_PER_MIN:
        return {"status": "error", "marker": "RATE_LIMITED", "domain": domain}
    calls.append(now)

    assessment = _guardian.assess_action(action, target)
    if (assessment["requires_confirmation"] or REQUIRE_CONFIRMATION) and not _guardian.request_permission(action):
        return {"status": "error", "marker": "GUARDIAN_DENIED", "guardian": assessment}
    return None


def web_search(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded search: returns links and snippets only."""
    data = input_data if isinstance(input_data, dict) else {"query": str(input_data)}
    query = str(data.get("query") or data.get("q") or "").strip()
    # A query normally has no target domain; the DDGS metasearch endpoint is gated.
    blocked = _gate("web_search", _SEARCH_DOMAIN)
    if blocked:
        return blocked
    return _raw_search.web_search(query, data.get("max_results", 5))


def open_page(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded page read; fetched content is returned as untrusted data."""
    data = input_data if isinstance(input_data, dict) else {"url": str(input_data)}
    url = str(data.get("url") or "").strip()
    if not urlparse(url).scheme in {"http", "https"} or not _domain(url):
        return {"status": "error", "marker": "INVALID_URL", "url": url}
    blocked = _gate("open_page", url)
    if blocked:
        return blocked
    return _raw_search.open_page(url)


# ── Playwright browser automation (Phase 1: READ-ONLY) ────────────────────────
# These wrappers are the ONLY sanctioned entry to browser.session. Every call is
# routed through the SAME Guardian gate as the trafilatura reads above, then
# logged with its risk decision. The action names use the "web_" prefix so the
# Guardian assigns them the LOW risk tier (auto-allow, no confirmation) — see
# OperatorGuard.assess_action. HIGH-RISK FUTURE ACTIONS (click/type/buy) will use
# non-"web_" action names and/or set requires_confirmation=True, which makes _gate
# invoke _guardian.request_permission(...) — that is the human-in-the-loop hook.
def _guarded_browser(action: str, url: str,
                     raw_fn: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
    if urlparse(url).scheme not in {"http", "https"} or not _domain(url):
        return {"status": "error", "marker": "INVALID_URL", "url": url}

    domain = _domain(url)
    # assess_action is explicitly non-mutating; used here purely to log the tier.
    assessment = _guardian.assess_action(action, url)
    blocked = _gate(action, url)
    decision = "ALLOW" if blocked is None else blocked.get("marker", "DENY")
    logger.info(
        "[browser-guardian] action=%s domain=%s risk=%s score=%s "
        "requires_confirmation=%s decision=%s",
        action, domain, assessment["risk_level"], assessment["risk_score"],
        assessment["requires_confirmation"], decision,
    )
    if blocked:
        return blocked
    # One live browser at a time (single visible window / single-use profile).
    with _browser_lock:
        return raw_fn(url)


def browser_navigate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded headed navigate: open the browser, go to URL, return title + final URL."""
    data = input_data if isinstance(input_data, dict) else {"url": str(input_data)}
    url = str(data.get("url") or "").strip()
    return _guarded_browser("web_navigate", url, _raw_session.navigate)


def browser_read(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded research read: open the browser, render the (JS-heavy) page, and
    return clean readable text as untrusted data for the assistant to summarize."""
    data = input_data if isinstance(input_data, dict) else {"url": str(input_data)}
    url = str(data.get("url") or "").strip()
    return _guarded_browser("web_read", url, _raw_session.read_page)


def browser_get_content(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarded accessibility-tree read: render the page and return a compact
    markdown outline of its accessibility tree (token-efficient, untrusted)."""
    data = input_data if isinstance(input_data, dict) else {"url": str(input_data)}
    url = str(data.get("url") or "").strip()
    return _guarded_browser("web_get_content", url, _raw_session.get_content)
