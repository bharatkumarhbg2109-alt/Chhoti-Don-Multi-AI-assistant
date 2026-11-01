"""
Cross-Session Semantic Memory Bridge
Indexes important conversation turns into ChromaDB for 
persistent recall across sessions.
"""
import hashlib
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_long_term_memory"
IMPORTANCE_KEYWORDS = [
    "my name is", "i am a", "i work at", "i prefer", "remember that",
    "always", "never", "my project", "i built", "i study", "i live",
    "important:", "note:", "my goal", "i want to", "i need to",
    "deadline", "my team", "my boss", "my stack"
]


def _is_important(text: str) -> bool:
    """Heuristic: is this message worth remembering long-term?"""
    lower = text.lower()
    return any(kw in lower for kw in IMPORTANCE_KEYWORDS)


def _make_id(text: str, session_id: str) -> str:
    return hashlib.sha256(
        f"{session_id}:{text[:100]}".encode()
    ).hexdigest()[:16]


class SemanticMemory:
    def __init__(self, config):
        self.config = config
        self._client = None
        self._collection = None
        self._enabled = False
        self._init()

    def _init(self):
        try:
            import chromadb
            from chromadb.config import Settings
            chroma_path = getattr(self.config, "CHROMA_PATH", None)
            if not chroma_path:
                chroma_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "knowledge_pipeline", "chroma_db"
                )
            self._client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            self._enabled = True
            logger.info(
                f"SemanticMemory initialized. Stored memories: {self._collection.count()}"
            )
        except Exception as e:
            logger.warning(f"SemanticMemory disabled: {e}")
            self._enabled = False

    def store(self, user_message: str, assistant_response: str,
              session_id: str = "default") -> bool:
        """Store a conversation turn if it seems important."""
        if not self._enabled:
            return False
        if not _is_important(user_message):
            return False
        try:
            doc_text = f"User: {user_message}\nAssistant: {assistant_response}"
            doc_id = _make_id(doc_text, session_id)
            self._collection.upsert(
                ids=[doc_id],
                documents=[doc_text],
                metadatas=[{
                    "session_id": session_id,
                    "timestamp": int(time.time()),
                    "user_message": user_message[:500]
                }]
            )
            return True
        except Exception as e:
            logger.warning(f"SemanticMemory store failed: {e}")
            return False

    def recall(self, query: str, top_k: int = 3) -> str:
        """Retrieve relevant past context for current query."""
        if not self._enabled:
            return ""
        try:
            if self._collection.count() == 0:
                return ""
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, self._collection.count())
            )
            docs = results.get("documents", [[]])[0]
            if not docs:
                return ""
            context = "\n---\n".join(docs[:top_k])
            return (
                f"\n[Long-term memory -- relevant past context:]\n"
                f"{context}\n[End of memory context]\n"
            )
        except Exception as e:
            logger.warning(f"SemanticMemory recall failed: {e}")
            return ""

    def clear_session(self, session_id: str):
        """Clear all memories from a specific session."""
        if not self._enabled:
            return
        try:
            results = self._collection.get(
                where={"session_id": session_id}
            )
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
        except Exception as e:
            logger.warning(f"SemanticMemory clear failed: {e}")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def memory_count(self) -> int:
        if not self._enabled:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0
