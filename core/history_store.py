"""
Chhoti Don - Conversation History Store (SQLite)

Durable, local conversation + message persistence for the desktop app.
Uses only the Python standard library (sqlite3) so it adds no dependencies.

Design notes
------------
* One database file lives under `<project>/.runtime/chhoti_don_history.db`
  (the `.runtime/` directory and `*.db` are already git-ignored).
* A fresh connection is opened per operation and guarded by a module lock,
  which is safe under Flask's threaded dev server without sharing a
  connection across threads.
* Schema creation is idempotent (`CREATE TABLE IF NOT EXISTS`) so an existing
  history database is never destroyed or overwritten on startup.
* All writes use parameterized queries.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

# ── Paths ─────────────────────────────────────────────────────
# The runtime directory (and therefore the history DB) can be relocated to a
# writable per-user directory via CHHOTI_DON_RUNTIME_DIR — used by the packaged
# desktop app so it never writes inside a read-only install location.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RUNTIME_DIR = os.environ.get("CHHOTI_DON_RUNTIME_DIR") or os.path.join(_PROJECT_ROOT, ".runtime")
_DB_PATH = os.environ.get(
    "CHHOTI_DON_HISTORY_DB", os.path.join(_RUNTIME_DIR, "chhoti_don_history.db")
)

_LOCK = threading.Lock()
_INITIALISED = False

DEFAULT_TITLE = "New conversation"


# ── Connection helpers ────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create tables if they do not already exist (idempotent, non-destructive)."""
    global _INITIALISED
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id          TEXT PRIMARY KEY,
                    title       TEXT NOT NULL DEFAULT 'New conversation',
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL,
                    is_private  INTEGER NOT NULL DEFAULT 0,
                    archived    INTEGER NOT NULL DEFAULT 0,
                    metadata    TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id               TEXT PRIMARY KEY,
                    conversation_id  TEXT NOT NULL,
                    role             TEXT NOT NULL,
                    content          TEXT NOT NULL,
                    created_at       REAL NOT NULL,
                    status           TEXT NOT NULL DEFAULT 'complete',
                    error_code       TEXT,
                    provider         TEXT,
                    model            TEXT,
                    metadata         TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages (conversation_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_conv_updated
                    ON conversations (updated_at DESC);
                """
            )
            conn.commit()
            _INITIALISED = True
        finally:
            conn.close()


def _ensure() -> None:
    if not _INITIALISED:
        init_db()


def _now() -> float:
    return time.time()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _loads(raw: Any) -> Dict:
    if not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except Exception:
        return {}


def _derive_title(text: str) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return DEFAULT_TITLE
    return clean[:60] + ("…" if len(clean) > 60 else "")


# ── Serialisers ───────────────────────────────────────────────
def _conv_row(row: sqlite3.Row, message_count: int = 0, preview: str = "") -> Dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "is_private": bool(row["is_private"]),
        "archived": bool(row["archived"]),
        "metadata": _loads(row["metadata"]),
        "message_count": message_count,
        "preview": preview,
    }


def _msg_row(row: sqlite3.Row) -> Dict:
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
        "status": row["status"],
        "error_code": row["error_code"],
        "provider": row["provider"],
        "model": row["model"],
        "metadata": _loads(row["metadata"]),
    }


# ── Conversations ─────────────────────────────────────────────
def create_conversation(
    title: Optional[str] = None,
    is_private: bool = False,
    metadata: Optional[Dict] = None,
    conv_id: Optional[str] = None,
) -> Dict:
    _ensure()
    now = _now()
    cid = conv_id or _uid("c")
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at, is_private, archived, metadata)"
                " VALUES (?, ?, ?, ?, ?, 0, ?)",
                (cid, title or DEFAULT_TITLE, now, now, 1 if is_private else 0,
                 json.dumps(metadata or {})),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
        finally:
            conn.close()
    return _conv_row(row)


def list_conversations(include_archived: bool = False, query: Optional[str] = None) -> List[Dict]:
    _ensure()
    with _LOCK:
        conn = _connect()
        try:
            sql = "SELECT * FROM conversations"
            clauses = []
            params: List[Any] = []
            if not include_archived:
                clauses.append("archived = 0")
            if query:
                # Match on title OR any message content in the conversation.
                clauses.append(
                    "(title LIKE ? OR id IN (SELECT conversation_id FROM messages WHERE content LIKE ?))"
                )
                like = f"%{query}%"
                params.extend([like, like])
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY updated_at DESC"
            rows = conn.execute(sql, params).fetchall()

            result = []
            for row in rows:
                counts = conn.execute(
                    "SELECT COUNT(*) AS n, "
                    "(SELECT content FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1) AS last "
                    "FROM messages WHERE conversation_id = ?",
                    (row["id"], row["id"]),
                ).fetchone()
                preview = (counts["last"] or "")[:120]
                result.append(_conv_row(row, counts["n"], preview))
            return result
        finally:
            conn.close()


def get_conversation(conv_id: str, with_messages: bool = True) -> Optional[Dict]:
    _ensure()
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if not row:
                return None
            msgs = []
            if with_messages:
                mrows = conn.execute(
                    "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                    (conv_id,),
                ).fetchall()
                msgs = [_msg_row(m) for m in mrows]
            data = _conv_row(row, len(msgs))
            data["messages"] = msgs
            return data
        finally:
            conn.close()


def rename_conversation(conv_id: str, title: str) -> Optional[Dict]:
    _ensure()
    title = (title or "").strip() or DEFAULT_TITLE
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title[:120], _now(), conv_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        finally:
            conn.close()
    return _conv_row(row)


def set_archived(conv_id: str, archived: bool) -> Optional[Dict]:
    _ensure()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE conversations SET archived = ?, updated_at = ? WHERE id = ?",
                (1 if archived else 0, _now(), conv_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        finally:
            conn.close()
    return _conv_row(row)


def delete_conversation(conv_id: str) -> bool:
    _ensure()
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# ── Messages ──────────────────────────────────────────────────
def add_message(
    conv_id: str,
    role: str,
    content: str,
    status: str = "complete",
    error_code: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    metadata: Optional[Dict] = None,
    auto_title: bool = True,
) -> Optional[Dict]:
    """Append a message and bump the conversation's updated_at.

    When the conversation still has the default title and this is the first
    user message, the title is derived from the message content.
    """
    _ensure()
    now = _now()
    mid = _uid("m")
    with _LOCK:
        conn = _connect()
        try:
            conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if not conv:
                return None
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at, status, error_code, provider, model, metadata)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (mid, conv_id, role, str(content), now, status, error_code, provider,
                 model, json.dumps(metadata or {})),
            )
            # Auto-title from the first user message.
            new_title = None
            if auto_title and role == "user" and (not conv["title"] or conv["title"] == DEFAULT_TITLE):
                new_title = _derive_title(content)
            if new_title:
                conn.execute(
                    "UPDATE conversations SET updated_at = ?, title = ? WHERE id = ?",
                    (now, new_title, conv_id),
                )
            else:
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id)
                )
            conn.commit()
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
        finally:
            conn.close()
    return _msg_row(row)


def get_messages(conv_id: str) -> List[Dict]:
    _ensure()
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conv_id,),
            ).fetchall()
            return [_msg_row(r) for r in rows]
        finally:
            conn.close()


# ── Migration + stats ─────────────────────────────────────────
def import_conversations(payload: List[Dict]) -> Dict:
    """One-time import of localStorage conversations.

    Each item: {id?, title?, messages: [{role, text|content, ...}], createdAt?, updatedAt?}
    Existing ids are skipped so re-running the import is safe.
    """
    _ensure()
    imported = 0
    skipped = 0
    with _LOCK:
        conn = _connect()
        try:
            for conv in payload or []:
                if not isinstance(conv, dict):
                    continue
                cid = conv.get("id") or _uid("c")
                exists = conn.execute(
                    "SELECT 1 FROM conversations WHERE id = ?", (cid,)
                ).fetchone()
                if exists:
                    skipped += 1
                    continue
                created = float(conv.get("createdAt") or _now() * 1000) / 1000.0 if conv.get("createdAt", 0) > 1e11 else float(conv.get("createdAt") or _now())
                updated = float(conv.get("updatedAt") or _now() * 1000) / 1000.0 if conv.get("updatedAt", 0) > 1e11 else float(conv.get("updatedAt") or _now())
                title = conv.get("title") or DEFAULT_TITLE
                conn.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at, is_private, archived, metadata)"
                    " VALUES (?, ?, ?, ?, 0, 0, ?)",
                    (cid, title, created, updated, json.dumps({"imported": True})),
                )
                for m in conv.get("messages", []) or []:
                    if not isinstance(m, dict):
                        continue
                    content = m.get("text", m.get("content", ""))
                    conn.execute(
                        "INSERT INTO messages (id, conversation_id, role, content, created_at, status, metadata)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (_uid("m"), cid, m.get("role", "user"), str(content), updated,
                         "error" if m.get("isError") else "complete",
                         json.dumps({"imported": True})),
                    )
                imported += 1
            conn.commit()
        finally:
            conn.close()
    return {"imported": imported, "skipped": skipped}


def stats() -> Dict:
    _ensure()
    with _LOCK:
        conn = _connect()
        try:
            conv_n = conn.execute("SELECT COUNT(*) AS n FROM conversations").fetchone()["n"]
            msg_n = conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
        finally:
            conn.close()
    return {
        "conversations": conv_n,
        "messages": msg_n,
        "db_path": _DB_PATH,
        "exists": os.path.exists(_DB_PATH),
    }


def db_path() -> str:
    return _DB_PATH
