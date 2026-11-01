"""Coding-agent policy values (Phase 1: read-only workspace tools).

Self-contained, env-overridable caps so the coding_agent/ package stays
independent of the rest of the app — mirroring browser/config.py. Every bound
here exists to stop a single tool call from ever returning an unbounded amount
of data (protects latency + the model's context window).
"""

import os

# Heavy / noisy directories that are always skipped when walking a workspace.
# Kept as a frozenset for cheap membership tests inside os.walk pruning.
IGNORED_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".idea", ".vscode",
    "dist", "build", ".next", ".turbo",
})


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ── list_dir ──────────────────────────────────────────────────────────────────
# Max directory depth walked (root itself is depth 0) and the hard ceiling on the
# number of entries returned so a giant tree can never flood the caller.
LIST_MAX_DEPTH = _env_int("CHHOTI_DON_FS_LIST_MAX_DEPTH", 4)
LIST_MAX_ENTRIES = _env_int("CHHOTI_DON_FS_LIST_MAX_ENTRIES", 2000)

# ── read_file ─────────────────────────────────────────────────────────────────
# Max bytes read from a single file (1 MB default). Larger files are truncated
# and flagged, never read whole.
READ_MAX_BYTES = _env_int("CHHOTI_DON_FS_READ_MAX_BYTES", 1_000_000)

# ── search ────────────────────────────────────────────────────────────────────
# Max match lines returned, and the per-file byte ceiling for the pure-Python
# fallback so scanning a huge binary/log can't stall the search.
SEARCH_MAX_RESULTS = _env_int("CHHOTI_DON_FS_SEARCH_MAX_RESULTS", 200)
SEARCH_MAX_FILE_BYTES = _env_int("CHHOTI_DON_FS_SEARCH_MAX_FILE_BYTES", 2_000_000)
# Longest slice of a matching line echoed back (keeps result rows compact).
SEARCH_MAX_LINE_CHARS = _env_int("CHHOTI_DON_FS_SEARCH_MAX_LINE_CHARS", 400)


# ── agent loop (Phase 3: autonomous builder) ──────────────────────────────────
# HARD step cap so the plan->act->observe loop can never run away. Kept modest —
# scaffolding a project is a handful of writes, not dozens.
AGENT_MAX_STEPS = _env_int("CHHOTI_DON_CODE_AGENT_MAX_STEPS", 16)
# Per-step observation char budget and how many recent observations stay verbatim
# in the prompt; older ones fold into a terse running summary (protects the local
# model's context window / 8GB VRAM — file contents never accumulate).
AGENT_OBS_CHARS = _env_int("CHHOTI_DON_CODE_AGENT_OBS_CHARS", 800)
AGENT_MAX_OBS = _env_int("CHHOTI_DON_CODE_AGENT_MAX_OBS", 6)
AGENT_SUMMARY_MAX_LINES = _env_int("CHHOTI_DON_CODE_AGENT_SUMMARY_LINES", 24)
# read_file observations are truncated to this many leading lines (+ "…truncated").
AGENT_READ_MAX_LINES = _env_int("CHHOTI_DON_CODE_AGENT_READ_LINES", 40)
# Corrective re-prompts allowed when the model emits unparseable JSON.
AGENT_MAX_PARSE_RETRIES = _env_int("CHHOTI_DON_CODE_AGENT_PARSE_RETRIES", 2)
# No-progress guard: how many times the SAME (tool,args) may occur before the loop
# breaks with a diagnostic. 1 => a second identical action stops the loop.
AGENT_MAX_REPEAT = _env_int("CHHOTI_DON_CODE_AGENT_MAX_REPEAT", 1)


# ── gated shell (Phase 4: run-to-completion dev commands + self-heal) ─────────
# HARD wall-clock timeout (seconds) for a single command; the child is KILLED on
# timeout so a hung test/build can never wedge the loop.
SHELL_TIMEOUT_S = _env_int("CHHOTI_DON_CODE_SHELL_TIMEOUT_S", 120)
# Max bytes kept from stdout and (separately) stderr; the middle is truncated,
# head+tail retained, so a chatty build can't blow the context window.
SHELL_OUTPUT_CAP = _env_int("CHHOTI_DON_CODE_SHELL_OUTPUT_CAP", 16_000)
# Self-heal budget: how many times a SINGLE failing command may be retried (after
# an edit) before the loop gives up on it. Small on purpose (diagnose→fix→rerun).
AGENT_HEAL_BUDGET = _env_int("CHHOTI_DON_CODE_AGENT_HEAL_BUDGET", 3)


# ── background servers (Phase 5: local host, long-lived dev servers) ──────────
# Max number of concurrently-tracked live servers so a mis-planning loop cannot
# spawn an unbounded fleet of processes.
SERVER_MAX_CONCURRENT = _env_int("CHHOTI_DON_CODE_SERVER_MAX", 3)
# How many recent stdout/stderr lines are retained per server (bounded ring).
SERVER_LOG_CAP_LINES = _env_int("CHHOTI_DON_CODE_SERVER_LOG_LINES", 500)
# How long serve_start waits for a URL/"listening" line before returning "started,
# no URL detected" (the server keeps running regardless).
SERVER_URL_DETECT_TIMEOUT_S = _env_int("CHHOTI_DON_CODE_SERVER_URL_TIMEOUT_S", 8)
# Grace period for a graceful terminate before we hard-kill on serve_stop.
SERVER_STOP_GRACE_S = _env_int("CHHOTI_DON_CODE_SERVER_STOP_GRACE_S", 5)
# Timeout (seconds) for the localhost socket health probe.
HEALTH_CHECK_TIMEOUT_S = _env_int("CHHOTI_DON_CODE_HEALTH_TIMEOUT_S", 2)


# ── public deploy (Phase 6: FINAL capability — highest risk) ──────────────────
# Deploys can be slow (build + upload); give the CLI a generous wall-clock cap.
DEPLOY_TIMEOUT_S = _env_int("CHHOTI_DON_CODE_DEPLOY_TIMEOUT_S", 600)
# Bytes kept from the deploy CLI's stdout/stderr (head+tail, middle truncated).
DEPLOY_OUTPUT_CAP = _env_int("CHHOTI_DON_CODE_DEPLOY_OUTPUT_CAP", 16_000)
# Per-file byte ceiling for the pre-deploy secret scan (skip large/binary files).
SECRET_SCAN_MAX_FILE_BYTES = _env_int("CHHOTI_DON_CODE_SECRET_SCAN_BYTES", 1_000_000)

# Human-in-the-loop (HITL) confirmation timeout (seconds)
HITL_CONFIRM_TIMEOUT_S = _env_int("CHHOTI_DON_CODE_CONFIRM_TIMEOUT_S", 60)
