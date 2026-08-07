"""
fetcher.py — Modules 1 & 2: Sources + Incremental fetch.

Pulls the newest papers from the arXiv Atom API for the configured categories
and returns ONLY items that are newer than the last successful run. State is
persisted to a small JSON file so restarts don't re-ingest the same papers.

Network / feed errors are caught and logged; the caller gets an empty list and
the next cycle simply tries again.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

import feedparser

import config

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Query construction
# --------------------------------------------------------------------------- #
def build_query_url(
    categories: list[str] | None = None,
    max_results: int | None = None,
) -> str:
    """Build the arXiv API URL for the configured categories, newest first."""
    categories = categories if categories is not None else config.ARXIV_CATEGORIES
    max_results = max_results if max_results is not None else config.FETCH_MAX

    # e.g. "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"
    search_query = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }
    return f"{config.ARXIV_API_URL}?{urlencode(params)}"


def _download_feed(url: str):
    """
    Download and parse the arXiv Atom feed for ``url``.

    Uses ``requests`` (which ships certifi's CA bundle) instead of letting
    feedparser fall back to urllib's default SSL context. urllib's default CA
    store is unreliable on some platforms — notably Windows/conda, where the
    default cafile path is empty/missing and every https handshake fails with
    CERTIFICATE_VERIFY_FAILED. This also keeps arXiv HTTP consistent with how
    the rest of the codebase talks to services (store/retriever). Kept as its
    own function so it is a single, clean seam to monkeypatch in offline tests.
    """
    import requests  # lazy import (matches store/retriever idiom)

    resp = requests.get(url, timeout=config.ARXIV_TIMEOUT)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


# --------------------------------------------------------------------------- #
# Incremental-fetch state
# --------------------------------------------------------------------------- #
def load_state(state_path: str | None = None) -> dict:
    """Load persisted fetch state. Returns an empty-ish dict when absent."""
    state_path = state_path or config.LAST_RUN_FILE
    if not os.path.exists(state_path):
        return {"last_published": None, "seen_ids": []}
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data.setdefault("last_published", None)
        data.setdefault("seen_ids", [])
        return data
    except (json.JSONDecodeError, OSError) as exc:
        # Corrupt/unreadable state must not crash the pipeline — start fresh.
        logger.warning("Could not read state file %s (%s); starting fresh.", state_path, exc)
        return {"last_published": None, "seen_ids": []}


def save_state(state: dict, state_path: str | None = None) -> None:
    """Persist fetch state atomically-ish (write temp, then replace)."""
    state_path = state_path or config.LAST_RUN_FILE
    tmp = f"{state_path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        os.replace(tmp, state_path)
    except OSError as exc:
        logger.error("Failed to persist state file %s: %s", state_path, exc)


# --------------------------------------------------------------------------- #
# Entry normalisation
# --------------------------------------------------------------------------- #
def _parse_published(entry) -> datetime | None:
    """Extract a timezone-aware UTC datetime from a feed entry, or None."""
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if not st:
        return None
    # feedparser returns *_parsed as a UTC time.struct_time.
    return datetime(*st[:6], tzinfo=timezone.utc)


def _normalize_entry(entry) -> dict | None:
    """Turn a raw feed entry into our internal item dict, or None if unusable."""
    arxiv_id = entry.get("id")
    if not arxiv_id:
        return None
    published = _parse_published(entry)
    return {
        "id": arxiv_id,
        "title": (entry.get("title") or "").strip(),
        "summary": (entry.get("summary") or "").strip(),
        "url": entry.get("link") or arxiv_id,
        "published": published,  # datetime | None
        "published_iso": published.isoformat() if published else "",
        "source": "arxiv",
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def fetch_new_items(state_path: str | None = None) -> list[dict]:
    """
    Fetch newest arXiv items and return only those newer than the last run.

    Semantics:
      * Only items with publish time strictly newer than the stored
        ``last_published`` are returned (incremental fetch).
      * Items already seen (by arXiv id) are skipped, which also handles
        ties on identical publish timestamps.
      * Duplicate ids *within a single batch* are collapsed.
      * State is updated so a second run over identical data returns 0 items.

    Never raises on network/feed failure — logs and returns [] instead.
    """
    state_path = state_path or config.LAST_RUN_FILE
    state = load_state(state_path)

    last_published: datetime | None = None
    if state.get("last_published"):
        try:
            last_published = datetime.fromisoformat(state["last_published"])
        except ValueError:
            last_published = None
    seen_ids: set[str] = set(state.get("seen_ids", []))

    url = build_query_url()

    try:
        feed = _download_feed(url)
    except Exception as exc:  # network/HTTP/parse trouble -> retry next cycle
        logger.error("arXiv fetch failed (%s); will retry next cycle.", exc)
        return []

    # feedparser signals fetch/parse trouble via `bozo` rather than raising.
    if getattr(feed, "bozo", 0) and not getattr(feed, "entries", None):
        logger.error(
            "arXiv fetch problem: %s; will retry next cycle.",
            getattr(feed, "bozo_exception", "unknown error"),
        )
        return []

    entries = getattr(feed, "entries", []) or []

    new_items: list[dict] = []
    batch_ids: set[str] = set()
    newest = last_published

    for entry in entries:
        item = _normalize_entry(entry)
        if item is None:
            continue

        # Collapse duplicate ids within this batch.
        if item["id"] in batch_ids:
            continue
        batch_ids.add(item["id"])

        pub = item["published"]

        # Track the newest publish time we've seen this batch.
        if pub is not None and (newest is None or pub > newest):
            newest = pub

        # Already ingested in a previous run?
        if item["id"] in seen_ids:
            continue
        # Not strictly newer than last run?
        if last_published is not None and pub is not None and pub <= last_published:
            continue

        new_items.append(item)

    # Persist updated state. Remember ids we just accepted, capped in size.
    updated_seen = list(seen_ids | {i["id"] for i in new_items})
    if len(updated_seen) > config.SEEN_IDS_CAP:
        updated_seen = updated_seen[-config.SEEN_IDS_CAP:]
    save_state(
        {
            "last_published": newest.isoformat() if newest else state.get("last_published"),
            "seen_ids": updated_seen,
        },
        state_path,
    )

    logger.info("Fetched %d new item(s) from arXiv.", len(new_items))
    return new_items
