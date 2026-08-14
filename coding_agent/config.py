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
