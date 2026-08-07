"""The single policy choke point for all browser operations."""

from collections import defaultdict, deque
from time import monotonic
from typing import Any, Dict
from urllib.parse import urlparse

from cyber_engine.guardian.operator_guard import OperatorGuard

from .config import BLOCKED_DOMAINS, RATE_LIMIT_PER_MIN, REQUIRE_CONFIRMATION
from . import search as _raw_search

_calls_by_domain = defaultdict(deque)
_guardian = OperatorGuard()
_SEARCH_DOMAIN = "ddgs-search"


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
