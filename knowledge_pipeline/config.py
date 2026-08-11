"""
config.py — Module 0: Central configuration.

Every tunable value in the pipeline lives here and ONLY here. No other module
should hard-code a model name, path, threshold, or interval. This keeps the
system easy to reason about and re-tune without hunting through the codebase.
"""

from __future__ import annotations

import os

# Absolute path to this package directory. On-disk state (the ChromaDB store and
# the fetch-state file) is anchored here so it has a stable location regardless
# of the process CWD. This lets the standalone pipeline AND the main app (which
# imports these modules) read/write the SAME shared collection.
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- #
# Ollama (local LLM server)
# --------------------------------------------------------------------------- #
# Host of the local Ollama server. Override with the OLLAMA_HOST env var if
# Ollama listens somewhere other than the default.
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# Chat model used to generate answers at query time (RAG).
# Set to the locally-installed qwen model (the assistant's main conversation
# model) so RAG answers share the same voice; no extra model download required.
CHAT_MODEL: str = os.environ.get("CHAT_MODEL", "qwen3.5:latest")

# Embedding model used to turn text into vectors for storage and retrieval.
EMBED_MODEL: str = os.environ.get("EMBED_MODEL", "nomic-embed-text")

# How long (seconds) to wait on any single Ollama HTTP call before giving up.
OLLAMA_TIMEOUT: int = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

# Whether to enable "thinking" mode for thinking-capable chat models (e.g. qwen).
# Disabled by default: thinking mode can spend minutes on hidden reasoning before
# it answers, which blows past OLLAMA_TIMEOUT and isn't wanted for direct RAG
# answers. Ollama ignores this flag for models that don't support thinking.
CHAT_THINK: bool = os.environ.get("CHAT_THINK", "false").lower() in ("1", "true", "yes")

# --------------------------------------------------------------------------- #
# ChromaDB (on-disk vector store)
# --------------------------------------------------------------------------- #
# Directory where ChromaDB persists its data. Anchored to the package dir so the
# pipeline and the main app share one collection (override with DB_PATH env var).
DB_PATH: str = os.environ.get("DB_PATH", os.path.join(_PKG_DIR, "chroma_db"))

# Name of the collection that holds all knowledge chunks.
COLLECTION_NAME: str = os.environ.get("COLLECTION_NAME", "ai_knowledge")

# Distance metric for the collection. "cosine" gives distances in [0, 2] where
# 0 == identical, which is what NOVELTY_THRESHOLD is calibrated against.
DISTANCE_METRIC: str = os.environ.get("DISTANCE_METRIC", "cosine")

# --------------------------------------------------------------------------- #
# Source: arXiv
# --------------------------------------------------------------------------- #
# arXiv Atom API endpoint.
ARXIV_API_URL: str = "http://export.arxiv.org/api/query"

# Categories to track. cs.AI = Artificial Intelligence, cs.LG = Machine
# Learning, cs.CL = Computation and Language.
ARXIV_CATEGORIES: list[str] = ["cs.AI", "cs.LG", "cs.CL"]

# Maximum number of items to request from arXiv per fetch cycle.
FETCH_MAX: int = int(os.environ.get("FETCH_MAX", "50"))

# How long (seconds) to wait on the arXiv HTTP fetch before giving up.
ARXIV_TIMEOUT: int = int(os.environ.get("ARXIV_TIMEOUT", "30"))

# File that persists incremental-fetch state (last-seen publish time + ids).
# Anchored to the package dir for a stable, CWD-independent location.
LAST_RUN_FILE: str = os.environ.get("LAST_RUN_FILE", os.path.join(_PKG_DIR, "last_run.json"))

# Upper bound on how many recently-seen arXiv ids we remember for tie-breaking
# on identical publish timestamps. Keeps the state file from growing forever.
SEEN_IDS_CAP: int = int(os.environ.get("SEEN_IDS_CAP", "5000"))

# --------------------------------------------------------------------------- #
# Processing: clean + chunk
# --------------------------------------------------------------------------- #
# Target chunk size range (in words) and overlap between consecutive chunks.
CHUNK_MIN_WORDS: int = int(os.environ.get("CHUNK_MIN_WORDS", "500"))
CHUNK_MAX_WORDS: int = int(os.environ.get("CHUNK_MAX_WORDS", "800"))
CHUNK_OVERLAP_WORDS: int = int(os.environ.get("CHUNK_OVERLAP_WORDS", "75"))

# --------------------------------------------------------------------------- #
# Novelty filter
# --------------------------------------------------------------------------- #
# A candidate is considered a DUPLICATE (skipped) when the distance to its
# nearest existing neighbour is <= this value. Smaller = stricter dedup.
NOVELTY_THRESHOLD: float = float(os.environ.get("NOVELTY_THRESHOLD", "0.12"))

# --------------------------------------------------------------------------- #
# Retrieval (RAG)
# --------------------------------------------------------------------------- #
# Number of nearest chunks to inject into the prompt at query time.
TOP_K: int = int(os.environ.get("TOP_K", "5"))

# --------------------------------------------------------------------------- #
# Scheduler
# --------------------------------------------------------------------------- #
# How often (hours) the background ingest job runs.
INGEST_INTERVAL_HOURS: float = float(os.environ.get("INGEST_INTERVAL_HOURS", "6"))
