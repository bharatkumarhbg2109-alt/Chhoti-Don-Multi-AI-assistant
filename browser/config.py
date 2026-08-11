"""Browser policy values sourced from the existing Guardian configuration.

The Guardian/blocklist/rate-limit policy is shared with the keyless ddgs+
trafilatura layer (search.py). The Playwright automation settings below are new
in Phase 1 (headed read-only research) and are self-contained here — env-
overridable — so the browser/ package stays independent of the rest of the app.
"""

import os

from cyber_engine.config.config_manager import DEFAULT_CONFIG

_BROWSER_POLICY = DEFAULT_CONFIG["guardian"]["browser"]

BLOCKED_DOMAINS = frozenset(_BROWSER_POLICY["blocked_domains"])
RATE_LIMIT_PER_MIN = int(_BROWSER_POLICY["rate_limit_per_min"])
MAX_CONTENT_CHARS = int(_BROWSER_POLICY["max_content_chars"])
REQUIRE_CONFIRMATION = bool(_BROWSER_POLICY["require_confirmation"])


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# ── Playwright automation (Phase 1: read-only research) ───────────────────────
# Headed by default: the product intent is "assistant khud browser khole" — the
# user should SEE the window open. Flip to headless with CHHOTI_DON_BROWSER_HEADLESS=1
# (used by CI / the test suite so it never pops a window on the runner).
BROWSER_HEADLESS = _env_bool("CHHOTI_DON_BROWSER_HEADLESS", False)

# Persistent profile dir under browser/ so later phases can reuse a session.
# NOTE: no login/credential handling exists in Phase 1 — this only reserves the
# location. Kept out of version control via browser/.gitignore.
USER_DATA_DIR = os.environ.get(
    "CHHOTI_DON_BROWSER_USERDATA",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".userdata"),
)

# Bounded timeouts (ms) so a hung page can never block the assistant forever.
NAV_TIMEOUT_MS = int(os.environ.get("CHHOTI_DON_BROWSER_NAV_TIMEOUT_MS", "20000"))
NETWORK_IDLE_TIMEOUT_MS = int(os.environ.get("CHHOTI_DON_BROWSER_IDLE_TIMEOUT_MS", "6000"))
# Hard ceiling for one whole navigate→read→close operation.
OPERATION_TIMEOUT_MS = int(os.environ.get("CHHOTI_DON_BROWSER_OP_TIMEOUT_MS", "35000"))


# ── Research agent loop (Phase 2: read-only plan→act→observe) ─────────────────
# HARD step cap so the loop can never run away. Observations are truncated to a
# small char budget and only the last AGENT_MAX_OBS are kept, so each step's
# context stays ~<=2k tokens (protects 8GB VRAM + latency). See browser/agent.py.
AGENT_MAX_STEPS = int(os.environ.get("CHHOTI_DON_AGENT_MAX_STEPS", "8"))
AGENT_OBS_CHARS = int(os.environ.get("CHHOTI_DON_AGENT_OBS_CHARS", "1200"))
AGENT_MAX_OBS = int(os.environ.get("CHHOTI_DON_AGENT_MAX_OBS", "6"))
AGENT_NUM_PREDICT = int(os.environ.get("CHHOTI_DON_AGENT_NUM_PREDICT", "256"))
AGENT_MAX_PARSE_RETRIES = int(os.environ.get("CHHOTI_DON_AGENT_MAX_PARSE_RETRIES", "3"))


# ── HITL confirmation (Phase 3: state-changing actions behind approval) ───────
# How long a paused pending-action waits for the user's approve/deny before it
# FAILS SAFE to DENY. Kept short-ish so a forgotten confirmation can't wedge a
# background worker forever.
HITL_CONFIRM_TIMEOUT_S = float(os.environ.get("CHHOTI_DON_HITL_TIMEOUT_S", "120"))


# ── Shopping assist (Phase 4) ─────────────────────────────────────────────────
# Cap on add-to-cart actions per shopping task so a mis-planning loop can't
# runaway-cart. Payment/checkout is ALWAYS hard-blocked regardless.
MAX_CART_ADDITIONS = int(os.environ.get("CHHOTI_DON_MAX_CART_ADDS", "5"))
