"""
app.py — FastAPI wiring, startup, and the /ingest + /ask endpoints.

This is where Modules 1–7 come together:
    fetch (fetcher)  ->  clean+chunk (processor)  ->  embed+store (store)
    ...and at query time: retrieve+generate (retriever)
    ...on a schedule: scheduler.

Run:
    cd knowledge_pipeline
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
import fetcher
import processor
import retriever
import store
from scheduler import create_scheduler
from store import OllamaError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("knowledge_pipeline")


# --------------------------------------------------------------------------- #
# Shared ChromaDB collection (one client/collection per process)
# --------------------------------------------------------------------------- #
_collection = None


def get_shared_collection():
    """Lazily create and cache the single shared collection for this process."""
    global _collection
    if _collection is None:
        _collection = store.get_collection()
    return _collection


# --------------------------------------------------------------------------- #
# The ingest pipeline: fetch -> process -> store
# --------------------------------------------------------------------------- #
def run_ingest() -> dict:
    """
    One full ingest cycle. Each stage is guarded so a failure is logged and
    reported rather than raised — the scheduler and server stay alive.
    """
    summary = {"fetched": 0, "chunks": 0, "stored": 0}

    # Stage 1: fetch (network). fetch_new_items already swallows its own errors.
    try:
        items = fetcher.fetch_new_items()
    except Exception as exc:  # last-resort guard
        logger.exception("Ingest fetch stage failed: %s", exc)
        summary["error"] = f"fetch: {exc}"
        return summary
    summary["fetched"] = len(items)
    if not items:
        logger.info("No new items to ingest.")
        return summary

    # Stage 2: clean + chunk (pure, local).
    chunks = processor.process_items(items)
    summary["chunks"] = len(chunks)

    # Stage 3: embed + store (network via Ollama). store_chunks catches
    # OllamaError internally and returns however many it managed to store.
    try:
        collection = get_shared_collection()
        summary["stored"] = store.store_chunks(collection, chunks)
    except OllamaError as exc:
        logger.error("Ingest store stage failed (Ollama): %s", exc)
        summary["error"] = f"store: {exc}"
    except Exception as exc:  # e.g. ChromaDB issue
        logger.exception("Ingest store stage failed: %s", exc)
        summary["error"] = f"store: {exc}"

    logger.info("Ingest summary: %s", summary)
    return summary


# --------------------------------------------------------------------------- #
# App lifespan: start/stop the background scheduler
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the DB/collection exists on boot (also proves the path is writable).
    try:
        get_shared_collection()
    except Exception as exc:  # don't prevent the server from starting
        logger.exception("Could not initialise ChromaDB collection at startup: %s", exc)

    scheduler = create_scheduler(run_ingest, config.INGEST_INTERVAL_HOURS)
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Startup complete; ingest scheduled every %s h.", config.INGEST_INTERVAL_HOURS)

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped; shutting down.")


app = FastAPI(
    title="Auto-Updating AI Knowledge Pipeline",
    description="Local, zero-cost RAG that keeps a local LLM's knowledge fresh.",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Request/response models
# --------------------------------------------------------------------------- #
class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    num_context: int


class IngestResponse(BaseModel):
    fetched: int
    chunks: int
    stored: int
    error: str | None = None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/")
def root() -> dict:
    """Health/status check."""
    try:
        count = get_shared_collection().count()
    except Exception:
        count = None
    return {
        "status": "ok",
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
        "stored_chunks": count,
        "ingest_interval_hours": config.INGEST_INTERVAL_HOURS,
    }


@app.post("/ingest", response_model=IngestResponse)
def ingest() -> dict:
    """Manually trigger one ingest cycle (fetch -> process -> store)."""
    return run_ingest()


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> dict:
    """Answer a question with retrieval-augmented context."""
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    try:
        result = retriever.answer_query(query, collection=get_shared_collection())
    except OllamaError as exc:
        # Ollama unreachable at query time -> clear 503, don't crash the server.
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "num_context": result["num_context"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
