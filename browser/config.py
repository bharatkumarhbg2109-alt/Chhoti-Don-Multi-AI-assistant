"""Browser policy values sourced from the existing Guardian configuration."""

from cyber_engine.config.config_manager import DEFAULT_CONFIG

_BROWSER_POLICY = DEFAULT_CONFIG["guardian"]["browser"]

BLOCKED_DOMAINS = frozenset(_BROWSER_POLICY["blocked_domains"])
RATE_LIMIT_PER_MIN = int(_BROWSER_POLICY["rate_limit_per_min"])
MAX_CONTENT_CHARS = int(_BROWSER_POLICY["max_content_chars"])
REQUIRE_CONFIRMATION = bool(_BROWSER_POLICY["require_confirmation"])
