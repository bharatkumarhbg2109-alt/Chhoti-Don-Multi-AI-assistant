"""
retriever.py — Module 6: Query-time RAG.

Embeds the user's question, pulls the TOP_K nearest chunks from ChromaDB, builds
a prompt that injects the retrieved text, and asks the local chat model. Handles
an empty database gracefully by answering without context instead of crashing.
"""

from __future__ import annotations

import logging

import config
import store
from store import OllamaError

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
def retrieve(collection, query_embedding: list[float], top_k: int | None = None) -> list[dict]:
    """
    Return up to ``top_k`` nearest chunks as dicts {text, metadata, distance}.

    An empty collection yields an empty list (no crash).
    """
    top_k = top_k if top_k is not None else config.TOP_K

    try:
        count = collection.count()
    except Exception as exc:
        logger.warning("collection.count() failed (%s); returning no context.", exc)
        return []
    if count == 0:
        return []

    n_results = min(top_k, count)
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    docs: list[dict] = []
    for text, meta, dist in zip(documents, metadatas, distances):
        docs.append({"text": text, "metadata": meta or {}, "distance": dist})
    return docs


# --------------------------------------------------------------------------- #
# Prompt building
# --------------------------------------------------------------------------- #
def build_prompt(query: str, docs: list[dict]) -> str:
    """
    Build the RAG prompt. When ``docs`` is non-empty the retrieved text is
    injected as numbered CONTEXT; when empty the model answers unaided.
    """
    if docs:
        blocks = []
        for i, d in enumerate(docs, start=1):
            meta = d.get("metadata") or {}
            title = meta.get("title", "untitled")
            url = meta.get("url", "")
            header = f"[{i}] {title}".strip()
            if url:
                header += f" ({url})"
            blocks.append(f"{header}\n{d['text']}")
        context = "\n\n".join(blocks)
        return (
            "You are a helpful AI research assistant. Use the CONTEXT below, "
            "which contains the latest retrieved AI research, to answer the "
            "QUESTION. Ground your answer in the context where relevant and cite "
            "sources by their [number]. If the context does not cover the "
            "question, answer from your own knowledge and say so.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            "ANSWER:"
        )
    return (
        "You are a helpful AI research assistant. No retrieved context is "
        "available yet, so answer the QUESTION from your own knowledge.\n\n"
        f"QUESTION: {query}\n\n"
        "ANSWER:"
    )


# --------------------------------------------------------------------------- #
# Chat via Ollama
# --------------------------------------------------------------------------- #
def chat(prompt: str) -> str:
    """Send ``prompt`` to the local Ollama chat model and return the reply text."""
    import requests  # lazy import

    url = f"{config.OLLAMA_HOST}/api/chat"
    try:
        resp = requests.post(
            url,
            json={
                "model": config.CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                # Disable slow hidden "thinking" for direct RAG answers (see
                # config.CHAT_THINK). No-op for non-thinking models.
                "think": config.CHAT_THINK,
            },
            timeout=config.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Ollama chat request failed: {exc}") from exc
    except ValueError as exc:
        raise OllamaError(f"Ollama chat returned invalid JSON: {exc}") from exc

    content = (data.get("message") or {}).get("content")
    if content is None:
        raise OllamaError(f"Ollama chat response had no message content: {data}")
    return content


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def answer_query(
    query: str,
    collection=None,
    embed_fn=None,
    chat_fn=None,
    top_k: int | None = None,
) -> dict:
    """
    Full RAG answer for ``query``.

    Returns {answer, sources, num_context, prompt}. ``embed_fn`` and ``chat_fn``
    default to the real Ollama calls but can be injected for testing.
    """
    embed_fn = embed_fn or store.embed_text
    chat_fn = chat_fn or chat
    if collection is None:
        collection = store.get_collection()

    query_embedding = embed_fn(query)
    docs = retrieve(collection, query_embedding, top_k)
    prompt = build_prompt(query, docs)
    answer = chat_fn(prompt)

    return {
        "answer": answer,
        "sources": [d.get("metadata", {}) for d in docs],
        "num_context": len(docs),
        "prompt": prompt,  # retained for transparency / debugging
    }
