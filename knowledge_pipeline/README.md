# Auto-Updating AI Knowledge Pipeline

A **local, zero-cost** system that keeps a frozen local LLM's answers up to date
**without ever retraining it**. New AI research is automatically fetched from
arXiv, deduplicated, embedded, stored in a vector database, and injected into the
model's context at query time (RAG). As the database grows, answers stay fresh.

```
arXiv ──► fetch (incremental) ──► clean + chunk ──► novelty filter ──► embed + store (ChromaDB)
                                                                              │
   user question ──► embed ──► retrieve top-K ──► build prompt (+context) ──► llama3.1 ──► answer
```

Everything runs on your machine. No API keys, no paid services.

---

## 1. Prerequisites

* **Python 3.11+** (tested on 3.13)
* **[Ollama](https://ollama.com)** installed and running locally

Pull the two models the pipeline uses:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

Make sure the Ollama server is running (it usually starts automatically; if not,
run `ollama serve`). It listens on `http://localhost:11434` by default.

---

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Windows without Visual C++ build tools?** ChromaDB's native dependency
> (`chroma-hnswlib`) needs a prebuilt wheel. Force wheels only:
>
> ```bash
> pip install --only-binary=:all: -r requirements.txt
> ```

---

## 3. Start the server

Run from **inside** the `knowledge_pipeline/` directory (the modules use flat
imports):

```bash
cd knowledge_pipeline
uvicorn app:app --host 0.0.0.0 --port 8000
```

(or simply `python app.py`)

On startup the pipeline:
* opens/creates the ChromaDB store at `./chroma_db`,
* starts a background scheduler that ingests fresh papers every
  `INGEST_INTERVAL_HOURS` (default **6h**).

Open **http://localhost:8000/** for a status check, or
**http://localhost:8000/docs** for interactive API docs.

---

## 4. Trigger an ingest manually

Don't want to wait 6 hours for the first cycle? Trigger one now:

```bash
curl -X POST http://localhost:8000/ingest
```

Example response:

```json
{ "fetched": 42, "chunks": 42, "stored": 40, "error": null }
```

*(`fetched` = new arXiv items, `chunks` = text chunks produced, `stored` = chunks
that passed the novelty filter and were embedded + saved.)*

---

## 5. Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest ideas in mixture-of-experts routing?"}'
```

> **Windows PowerShell** users:
> ```powershell
> Invoke-RestMethod -Method Post -Uri http://localhost:8000/ask `
>   -ContentType 'application/json' `
>   -Body '{"query":"What are the latest ideas in mixture-of-experts routing?"}'
> ```

Example response:

```json
{
  "answer": "Recent work proposes sparse routing that activates only a few experts per token ... [1]",
  "sources": [
    { "title": "Sparse Mixture-of-Experts Routing ...", "date": "2026-08-01T12:00:00+00:00",
      "source": "arxiv", "url": "http://arxiv.org/abs/2601.00003v1" }
  ],
  "num_context": 5
}
```

If the database is still empty, `/ask` answers from the model's own knowledge and
returns `num_context: 0` — it never crashes.

---

## 6. Run the smoke test (no Ollama needed)

The smoke test exercises the full chain with **mocked embeddings** and **no
network**, so it runs anywhere in seconds:

```bash
python knowledge_pipeline/smoke_test.py
```

It prints a `PASS`/`FAIL` line per check and exits `0` only if everything passes.

---

## Configuration

Every tunable lives in [`config.py`](config.py) and can be overridden via
environment variables:

| Setting                 | Default            | Meaning                                             |
|-------------------------|--------------------|-----------------------------------------------------|
| `CHAT_MODEL`            | `llama3.1`         | Ollama chat model for answers                       |
| `EMBED_MODEL`           | `nomic-embed-text` | Ollama embedding model                              |
| `DB_PATH`               | `./chroma_db`      | ChromaDB on-disk location                           |
| `COLLECTION_NAME`       | `ai_knowledge`     | Collection name                                     |
| `ARXIV_CATEGORIES`      | `cs.AI, cs.LG, cs.CL` | arXiv categories tracked                          |
| `FETCH_MAX`             | `50`               | Max items requested per fetch                       |
| `NOVELTY_THRESHOLD`     | `0.12`             | Cosine distance ≤ this ⇒ treated as duplicate       |
| `INGEST_INTERVAL_HOURS` | `6`                | Background ingest cadence                           |
| `TOP_K`                 | `5`                | Chunks injected into the prompt at query time       |

---

## Module map

| File            | Module | Responsibility                                        |
|-----------------|--------|-------------------------------------------------------|
| `config.py`     | 0      | All tunable values in one place                       |
| `fetcher.py`    | 1 + 2  | arXiv source + incremental (state-persisted) fetch    |
| `processor.py`  | 3      | Clean (trafilatura for HTML) + chunk                  |
| `novelty.py`    | 4      | Embedding-distance dedup                              |
| `store.py`      | 5      | Embed via Ollama + add to ChromaDB (id + novelty safe)|
| `retriever.py`  | 6      | Query-time RAG (retrieve → prompt → generate)         |
| `scheduler.py`  | 7      | APScheduler background ingest (failure-isolated)      |
| `app.py`        | —      | FastAPI wiring, startup, `/ingest`, `/ask`            |
| `smoke_test.py` | —      | End-to-end test with mocked embeddings                |

---

## Robustness

* **Ollama down** → embedding/chat errors are caught and logged; the scheduler
  keeps running and retries next cycle. `/ask` returns HTTP 503 with a clear
  message instead of crashing.
* **Network failure during fetch** → logged and skipped; next cycle retries.
* **Empty DB on first query** → still returns an answer (no context).
* **Duplicate arXiv ids** → never double-inserted (id check + novelty filter).
* **Restart-safe** → ChromaDB persists to `DB_PATH`; fetch state persists to
  `last_run.json`.
