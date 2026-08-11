"""
store.py — Module 5: Embed + persist to ChromaDB.

Provides the ChromaDB client/collection helpers, the Ollama embedding call, and
``store_chunks`` which embeds each candidate chunk, runs the novelty filter, and
adds only genuinely new content to the collection.

Guarantees:
  * A chunk whose id already exists is never re-inserted.
  * A chunk that fails the novelty filter is skipped.
  * If Ollama is unreachable, the error is logged and the batch stops cleanly
    (the scheduler / caller keeps running).
"""

from __future__ import annotations

import logging

import chromadb

import config
from novelty import is_novel

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Raised when the local Ollama server cannot be reached or errors out."""


# --------------------------------------------------------------------------- #
# ChromaDB helpers
# --------------------------------------------------------------------------- #
# Process-level singletons for the DEFAULT (no-override) client + collection.
# Constructing a PersistentClient and re-fetching the collection cost ~200ms on
# every retrieve_context() call; building them once and reusing removes that
# per-message overhead. Parameterized calls (custom client/db_path/name — used by
# the ingest pipeline and tests) bypass the cache and behave exactly as before.
_default_client = None
_default_collection = None


def get_client(db_path: str | None = None):
    """Create an on-disk (persistent) ChromaDB client.

    The default-path client is cached and reused; an explicit ``db_path`` always
    returns a fresh client (unchanged behavior for tests/ingest).
    """
    global _default_client
    if db_path is None:
        if _default_client is None:
            _default_client = chromadb.PersistentClient(path=config.DB_PATH)
        return _default_client
    return chromadb.PersistentClient(path=db_path)


def get_collection(client=None, db_path: str | None = None, name: str | None = None):
    """
    Get-or-create the knowledge collection using the configured distance metric.

    The cosine space keeps distances in [0, 2] where 0 == identical, which is
    what NOVELTY_THRESHOLD is calibrated against.

    The default collection (no client/db_path/name override) is built once and
    reused across calls; parameterized calls are not cached.
    """
    global _default_collection
    if client is None and db_path is None and name is None:
        if _default_collection is None:
            _default_collection = get_client().get_or_create_collection(
                name=config.COLLECTION_NAME,
                metadata={"hnsw:space": config.DISTANCE_METRIC},
            )
        return _default_collection
    client = client or get_client(db_path)
    name = name or config.COLLECTION_NAME
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": config.DISTANCE_METRIC},
    )


# --------------------------------------------------------------------------- #
# Embeddings via Ollama
# --------------------------------------------------------------------------- #
def embed_text(text: str) -> list[float]:
    """
    Embed a single string via the local Ollama embedding model.

    ``requests`` is imported lazily so modules that only need ChromaDB helpers
    don't pull it in. Raises OllamaError on any network/HTTP/parse failure.
    """
    import requests  # lazy import

    url = f"{config.OLLAMA_HOST}/api/embeddings"
    try:
        resp = requests.post(
            url,
            # keep_alive=-1 keeps nomic-embed resident so it doesn't cold-reload
            # each turn; it (~0.3GB) coexists with qwen3.5 (~5.5GB) in 8GB VRAM.
            json={"model": config.EMBED_MODEL, "prompt": text, "keep_alive": -1},
            timeout=config.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Ollama embedding request failed: {exc}") from exc
    except ValueError as exc:  # bad JSON
        raise OllamaError(f"Ollama embedding returned invalid JSON: {exc}") from exc

    embedding = data.get("embedding")
    if not embedding:
        raise OllamaError(f"Ollama embedding response had no 'embedding' field: {data}")
    return embedding


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def _already_stored(collection, chunk_id: str) -> bool:
    """True if a chunk with this id is already in the collection."""
    try:
        existing = collection.get(ids=[chunk_id])
    except Exception as exc:  # defensive; get() shouldn't normally fail
        logger.warning("collection.get(%s) failed (%s); assuming not stored.", chunk_id, exc)
        return False
    return bool(existing and existing.get("ids"))


def store_chunks(
    collection,
    chunks: list[dict],
    embed_fn=None,
    novelty_threshold: float | None = None,
) -> int:
    """
    Embed and store each novel, non-duplicate chunk. Returns the number added.

    ``embed_fn`` defaults to the real Ollama embedder but can be injected (e.g.
    a deterministic mock in tests). If the embedder raises OllamaError the batch
    stops gracefully and the count of already-added chunks is returned.
    """
    embed_fn = embed_fn or embed_text
    threshold = novelty_threshold if novelty_threshold is not None else config.NOVELTY_THRESHOLD

    added = 0
    for chunk in chunks:
        chunk_id = chunk["id"]

        # 1) Never double-insert the same id (handles duplicate source items).
        if _already_stored(collection, chunk_id):
            logger.debug("Chunk %s already stored; skipping.", chunk_id)
            continue

        # 2) Embed (may hit the network).
        try:
            embedding = embed_fn(chunk["text"])
        except OllamaError as exc:
            logger.error("Embedding failed (%s); stopping this ingest batch.", exc)
            break  # scheduler keeps running; we retry next cycle

        # 3) Novelty filter against existing neighbours.
        if not is_novel(collection, embedding, threshold):
            logger.debug("Chunk %s is a near-duplicate; skipping.", chunk_id)
            continue

        # 4) Persist. ChromaDB's PersistentClient writes to disk immediately.
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[chunk["metadata"]],
        )
        added += 1
        logger.debug("Stored chunk %s.", chunk_id)

    logger.info("Stored %d new chunk(s).", added)
    return added
