"""
smoke_test.py — End-to-end test of the pipeline with MOCKED embeddings.

Runs the full chain fetch -> process -> novelty -> store -> retrieve WITHOUT a
live Ollama server (embeddings and chat are mocked) and WITHOUT network access
(feedparser.parse is monkeypatched). ChromaDB is real and writes to a temp dir.

Exit code 0 == all checks passed; non-zero == failure.

Run:
    python knowledge_pipeline/smoke_test.py
    #   ...or from inside the package:  python smoke_test.py
"""

from __future__ import annotations

import gc
import hashlib
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

# Make sibling modules importable no matter the invocation directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import fetcher
import processor
import retriever
import store

EMBED_DIM = 128


# --------------------------------------------------------------------------- #
# Mocks (no Ollama, no network)
# --------------------------------------------------------------------------- #
def mock_embed(text: str) -> list[float]:
    """
    Deterministic unit-norm embedding derived from the text.

    Identical text -> identical vector -> cosine distance 0 (a near-duplicate).
    Different text -> effectively orthogonal vector -> cosine distance ~1.
    """
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    vec = [rng.gauss(0.0, 1.0) for _ in range(EMBED_DIM)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def mock_chat(prompt: str) -> str:
    """Echo the prompt so tests can assert the retrieved context is present."""
    return f"MOCK_ANSWER::{prompt}"


class _MockFeed:
    """Stand-in for a feedparser result object."""

    def __init__(self, entries, bozo=0, bozo_exception=None):
        self.entries = entries
        self.bozo = bozo
        self.bozo_exception = bozo_exception


# Three arXiv-like entries, newest first (as arXiv returns them).
_ENTRIES = [
    {
        "id": "http://arxiv.org/abs/2601.00003v1",
        "title": "Sparse Mixture-of-Experts Routing for Efficient LLMs",
        "summary": "We introduce a routing scheme that activates a small subset "
                   "of experts per token, cutting inference cost while preserving "
                   "quality across reasoning and coding benchmarks.",
        "link": "http://arxiv.org/abs/2601.00003v1",
        "published_parsed": (2026, 8, 1, 12, 0, 0, 0, 0, 0),
    },
    {
        "id": "http://arxiv.org/abs/2601.00002v1",
        "title": "Retrieval-Augmented Generation with Freshness Guarantees",
        "summary": "A pipeline that continuously ingests new documents and injects "
                   "them at query time, keeping a frozen language model's answers "
                   "current without any retraining.",
        "link": "http://arxiv.org/abs/2601.00002v1",
        "published_parsed": (2026, 7, 31, 12, 0, 0, 0, 0, 0),
    },
    {
        "id": "http://arxiv.org/abs/2601.00001v1",
        "title": "Distilling Long-Context Attention into Linear State Spaces",
        "summary": "We distill a long-context transformer into a linear-time state "
                   "space model, matching accuracy on retrieval tasks at a fraction "
                   "of the memory footprint.",
        "link": "http://arxiv.org/abs/2601.00001v1",
        "published_parsed": (2026, 7, 30, 12, 0, 0, 0, 0, 0),
    },
]


# --------------------------------------------------------------------------- #
# Tiny test harness
# --------------------------------------------------------------------------- #
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    ok = bool(condition)
    _results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


# --------------------------------------------------------------------------- #
# The test
# --------------------------------------------------------------------------- #
def run() -> int:
    tmpdir = tempfile.mkdtemp(prefix="kp_smoke_")
    tmp_db = os.path.join(tmpdir, "chroma")
    state_path = os.path.join(tmpdir, "last_run.json")
    state_path2 = os.path.join(tmpdir, "last_run_netfail.json")

    print(f"Using temp dir: {tmpdir}\n")

    try:
        # -- 1. Incremental fetch (item 5) --------------------------------- #
        # Patch the single network seam so the test needs no network access.
        fetcher._download_feed = lambda url: _MockFeed(list(_ENTRIES))
        new1 = fetcher.fetch_new_items(state_path=state_path)
        check("fetch: first run returns all new items", len(new1) == 3,
              f"got {len(new1)} (expected 3)")

        new2 = fetcher.fetch_new_items(state_path=state_path)
        check("fetch: second run over same data returns 0 (incremental)",
              len(new2) == 0, f"got {len(new2)} (expected 0)")

        # -- 2. Network-failure path (item 10) ----------------------------- #
        fetcher._download_feed = lambda url: _MockFeed([], bozo=1,
                                                       bozo_exception=Exception("simulated network error"))
        net_fail = fetcher.fetch_new_items(state_path=state_path2)
        check("fetch: network failure is caught, returns [] (no crash)",
              net_fail == [], f"got {net_fail!r}")

        # -- 3. Clean + chunk ---------------------------------------------- #
        chunks = processor.process_items(new1)
        check("process: produced chunks with non-empty text",
              len(chunks) >= 3 and all(c["text"] for c in chunks),
              f"{len(chunks)} chunks")
        check("process: chunk metadata carries title/date/source/url",
              all({"title", "date", "source", "url"} <= set(c["metadata"]) for c in chunks))

        # -- 4. Store (embed + persist) ------------------------------------ #
        client = store.get_client(db_path=tmp_db)
        collection = store.get_collection(client=client, name="smoke")
        added1 = store.store_chunks(collection, chunks, embed_fn=mock_embed)
        check("store: all novel chunks are stored", added1 == len(chunks),
              f"added {added1} of {len(chunks)}")

        # -- 5. Duplicate id never double-inserts -------------------------- #
        added2 = store.store_chunks(collection, chunks, embed_fn=mock_embed)
        check("store: re-storing same ids adds nothing (id dedup)",
              added2 == 0, f"added {added2} (expected 0)")

        # -- 6. Novelty filter, isolated from id dedup (item 6) ------------ #
        # Same TEXT as an existing chunk but a DIFFERENT id -> the novelty
        # filter (not the id check) must reject it.
        near_dup = {
            "id": "NOVELTY-CHECK-DIFFERENT-ID",
            "text": chunks[0]["text"],
            "metadata": dict(chunks[0]["metadata"]),
        }
        added3 = store.store_chunks(collection, [near_dup], embed_fn=mock_embed)
        check("novelty: near-duplicate (new id, same text) is skipped",
              added3 == 0, f"added {added3} (expected 0)")

        stored_count = collection.count()
        check("store: collection count matches unique chunks",
              stored_count == len(chunks), f"count={stored_count}")

        # -- 7. Persistence across a FRESH process (item 7) ---------------- #
        gc.collect()
        subproc_code = (
            "import chromadb\n"
            f"c = chromadb.PersistentClient(path={tmp_db!r})\n"
            "col = c.get_collection('smoke')\n"
            "print(col.count())\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", subproc_code],
            capture_output=True, text=True,
        )
        fresh_count = -1
        if proc.returncode == 0 and proc.stdout.strip().isdigit():
            fresh_count = int(proc.stdout.strip())
        check("persistence: data survives a brand-new client in a fresh process",
              fresh_count == stored_count,
              f"fresh process saw {fresh_count} (expected {stored_count}); "
              f"stderr={proc.stderr.strip()[:200]}")

        # -- 8. Retrieval builds a prompt containing the retrieved text ---- #
        result = retriever.answer_query(
            "How can a frozen model stay up to date without retraining?",
            collection=collection, embed_fn=mock_embed, chat_fn=mock_chat, top_k=3,
        )
        check("retrieve: returned some context", result["num_context"] >= 1,
              f"num_context={result['num_context']}")
        check("retrieve: prompt injects the retrieved document text (RAG)",
              "CONTEXT:" in result["prompt"]
              and any(doc in result["prompt"]
                      for doc in collection.get(include=["documents"])["documents"]))
        check("retrieve: mocked answer reflects the built prompt",
              result["answer"].startswith("MOCK_ANSWER::"))

        # -- 9. Empty-DB query still answers (item 9) ---------------------- #
        empty_col = store.get_collection(client=client, name="empty_smoke")
        empty_res = retriever.answer_query(
            "What is attention?", collection=empty_col,
            embed_fn=mock_embed, chat_fn=mock_chat,
        )
        check("empty-DB: query returns an answer without crashing",
              empty_res["num_context"] == 0 and bool(empty_res["answer"]),
              f"num_context={empty_res['num_context']}")

        # -- 10. Ollama-down during store is caught (item 10) -------------- #
        def broken_embed(_text):
            raise store.OllamaError("simulated Ollama down")

        safe = store.store_chunks(
            empty_col,
            [{"id": "will-not-store::chunk0", "text": "brand new text", "metadata": {}}],
            embed_fn=broken_embed,
        )
        check("robustness: Ollama-down during embedding is caught, batch stops cleanly",
              safe == 0, f"added {safe} (expected 0)")

    except Exception as exc:  # any unexpected error is a hard failure
        import traceback
        traceback.print_exc()
        check(f"unexpected exception: {type(exc).__name__}", False, str(exc))
    finally:
        gc.collect()
        shutil.rmtree(tmpdir, ignore_errors=True)

    # -- Summary ----------------------------------------------------------- #
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print("\n" + "=" * 60)
    print(f"SMOKE TEST: {passed}/{total} checks passed")
    print("=" * 60)
    if passed == total and total > 0:
        print("RESULT: PASS ✅")
        return 0
    print("RESULT: FAIL ❌")
    return 1


if __name__ == "__main__":
    sys.exit(run())
