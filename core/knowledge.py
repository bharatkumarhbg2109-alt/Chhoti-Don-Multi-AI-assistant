"""
core/knowledge.py — RAG bridge into the main conversation.

Retrieves relevant chunks from the SHARED ai_knowledge ChromaDB collection (the
one the knowledge_pipeline ingests into) and turns them into grounding context
for the conversation brain. This is the "answering half" of the pipeline merged
into the main /api/chat path — the standalone /ingest endpoint + scheduler keep
populating the same collection.

Design guarantees:
  * FAIL-OPEN: any error (Ollama down, embed model missing, empty/locked DB) or
    no sufficiently-relevant hit returns ("", []), so the conversation falls
    back to its normal, un-grounded behavior and never breaks.
  * NON-INTRUSIVE: only chunks closer than RAG_MAX_DISTANCE are injected, so an
    unrelated (non-AI) question retrieves nothing and behaves exactly as before.
"""

from __future__ import annotations

import os
import sys
import logging

logger = logging.getLogger("chhoti_don.knowledge")

# Make the sibling knowledge_pipeline package importable (flat sibling imports:
# it does `import config` / `import store`). Anchored to the repo root so CWD
# doesn't matter.
#
# APPEND (not insert-at-0): these flat names (config/store/retriever/novelty)
# exist ONLY inside knowledge_pipeline, so appending resolves them fine while
# NOT shadowing root-level modules that share a name — notably the root Flask
# `app.py` vs knowledge_pipeline's FastAPI `app.py`. Inserting at position 0
# made a later `import app` resolve to the wrong module once this ran.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KP_DIR = os.path.join(_REPO_ROOT, "knowledge_pipeline")
if os.path.isdir(_KP_DIR) and _KP_DIR not in sys.path:
    sys.path.append(_KP_DIR)

# How many chunks to pull, and the cosine-distance ceiling for "relevant enough".
# cosine distance is in [0, 2]; smaller = closer. Calibrated against the arXiv
# corpus: on-topic AI questions retrieve at ~0.28-0.40 while unrelated questions
# sit at ~0.54+, so 0.45 injects for real AI questions and stays silent
# otherwise. Each chunk is truncated so the grounded prompt stays lean/fast.
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "3"))
RAG_MAX_DISTANCE = float(os.environ.get("RAG_MAX_DISTANCE", "0.45"))
RAG_CHUNK_CHARS = int(os.environ.get("RAG_CHUNK_CHARS", "900"))


def retrieve_context(query: str, top_k: int | None = None,
                     max_distance: float | None = None):
    """
    Return (context_text, sources) from the shared ai_knowledge collection.

    ``sources`` is a list of {title, url, source_type} for the chunks actually
    used. Returns ("", []) on any failure or when nothing clears the distance
    gate — the caller then answers without grounding.
    """
    top_k = RAG_TOP_K if top_k is None else top_k
    max_distance = RAG_MAX_DISTANCE if max_distance is None else max_distance

    try:
        import store          # knowledge_pipeline/store.py
        import retriever      # knowledge_pipeline/retriever.py

        collection = store.get_collection()
        if collection.count() == 0:
            return "", []
        query_embedding = store.embed_text(query)          # live nomic-embed-text
        docs = retriever.retrieve(collection, query_embedding, top_k)
    except Exception as exc:  # fail-open: never break the conversation
        logger.warning("RAG retrieval skipped (%s: %s)", type(exc).__name__, exc)
        return "", []

    relevant = [d for d in docs if d.get("distance", 9.0) <= max_distance]
    if not relevant:
        return "", []

    blocks: list[str] = []
    sources: list[dict] = []
    for i, d in enumerate(relevant, start=1):
        meta = d.get("metadata") or {}
        title = meta.get("title", "untitled")
        url = meta.get("url", "")
        text = d.get("text", "") or ""
        if len(text) > RAG_CHUNK_CHARS:  # keep the grounded prompt lean/fast
            text = text[:RAG_CHUNK_CHARS].rsplit(" ", 1)[0] + " …"
        blocks.append(f"[{i}] {title}\n{text}")
        sources.append({
            "title": title,
            "url": url,
            "source_type": meta.get("source_type", "ai_knowledge"),
        })
    return "\n\n".join(blocks), sources


def build_grounded_system(base_system: str, context: str) -> str:
    """
    Append retrieved context to the brain's normal system prompt (so the base
    persona is preserved) with instructions to ground the answer and cite by
    [number]. Injected as a SYSTEM prompt so it never pollutes conversation
    memory as if the user had typed it.
    """
    prefix = (base_system + "\n\n") if base_system else ""
    return (
        prefix
        + "The CONTEXT below is freshly-retrieved AI-research knowledge. Use it to "
          "ground your answer and cite sources by their [number] where relevant. "
          "If it does not cover the question, say so briefly and answer from your "
          "own knowledge.\n\n"
          f"CONTEXT:\n{context}"
    )
