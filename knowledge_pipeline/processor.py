"""
processor.py — Module 3: Clean + chunk.

Turns a fetched item into one or more retrieval-ready chunks. arXiv abstracts
arrive as clean text and are typically short enough to be a single chunk. Raw
HTML sources (future work) are cleaned with trafilatura first.

Chunk sizing follows config: CHUNK_MAX_WORDS with CHUNK_OVERLAP_WORDS of overlap
between consecutive chunks, and a CHUNK_MIN_WORDS floor so we don't emit tiny
trailing fragments.
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)


def clean_html(raw_html: str) -> str:
    """
    Extract clean main text from raw HTML using trafilatura.

    Imported lazily so the rest of the pipeline (and the smoke test) does not
    hard-depend on trafilatura being importable. Falls back to the raw string
    if extraction yields nothing.
    """
    if not raw_html:
        return ""
    try:
        import trafilatura  # lazy import
    except ImportError:
        logger.warning("trafilatura not installed; returning raw text unchanged.")
        return raw_html
    extracted = trafilatura.extract(raw_html)
    return extracted if extracted else raw_html


def chunk_text(
    text: str,
    max_words: int | None = None,
    overlap: int | None = None,
    min_words: int | None = None,
) -> list[str]:
    """
    Split ``text`` into overlapping word-windows.

    * Windows are at most ``max_words`` words long.
    * Consecutive windows share ``overlap`` words.
    * Text shorter than ``max_words`` is returned as a single chunk.
    * A final window shorter than ``min_words`` is merged into the previous
      window so we never emit a tiny fragment.
    """
    max_words = max_words if max_words is not None else config.CHUNK_MAX_WORDS
    overlap = overlap if overlap is not None else config.CHUNK_OVERLAP_WORDS
    min_words = min_words if min_words is not None else config.CHUNK_MIN_WORDS

    # Defensive: overlap must be smaller than the window or we can't advance.
    if overlap >= max_words:
        overlap = max_words // 4

    words = (text or "").split()
    if not words:
        return []
    if len(words) <= max_words:
        return [" ".join(words)]

    step = max_words - overlap
    chunks: list[str] = []
    start = 0
    while start < len(words):
        window = words[start : start + max_words]
        chunks.append(" ".join(window))
        if start + max_words >= len(words):
            break
        start += step

    # Merge a too-small tail chunk into its predecessor.
    if len(chunks) >= 2:
        tail_words = chunks[-1].split()
        if len(tail_words) < min_words:
            merged = f"{chunks[-2]} {chunks[-1]}"
            chunks = chunks[:-2] + [merged]

    return chunks


def process_item(item: dict) -> list[dict]:
    """
    Convert a fetched item into a list of chunk dicts ready for storage.

    Each chunk dict has:
        id       -> stable, unique per (item, chunk index)
        text     -> the chunk text
        metadata -> {title, date, source, url}

    The chunk id embeds the source item id so duplicate items can never be
    double-inserted (see store.store_chunks).
    """
    title = item.get("title", "")
    summary = item.get("summary", "")

    # arXiv abstracts are already clean. Prepend the title so it's embedded and
    # retrievable alongside the abstract body.
    body = f"{title}\n\n{summary}".strip() if title else summary
    chunks = chunk_text(body)

    metadata = {
        "title": title,
        "date": item.get("published_iso", ""),
        "source": item.get("source", "unknown"),
        "url": item.get("url", ""),
        # Tags this document's origin so the shared conversation collection can
        # still be filtered back to just the auto-ingested AI-research corpus.
        "source_type": "ai_knowledge",
    }

    item_id = item.get("id", "unknown")
    processed: list[dict] = []
    for idx, chunk in enumerate(chunks):
        processed.append(
            {
                "id": f"{item_id}::chunk{idx}",
                "text": chunk,
                "metadata": dict(metadata),  # copy per chunk
            }
        )
    return processed


def process_items(items: list[dict]) -> list[dict]:
    """Flatten process_item over a list of items."""
    out: list[dict] = []
    for item in items:
        out.extend(process_item(item))
    return out
