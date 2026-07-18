"""
Chhoti Don - Memory
Advanced conversation memory with persistence,
context windowing, and semantic search.
Phase 2.2 - Full Upgrade
"""

import json
import os
import time
import datetime
from typing import Dict, List, Optional, Optional


MAX_MEMORY= 50
CONTEXT_WINDOW = 6
MEMORY_FILE = "core/memory_state.json"


class Memory:
    """
    Advanced Conversation Memory.
    Preserved + upgraded with persistence and search.
    """

    def __init__(self, max_size: int = MAX_MEMORY, persist: bool = False):
        self.history: List[Dict] = []
        self.max_size = max_size
        self.persist = persist
        self.session_id = f"session_{int(time.time())}"
        self._metadata: Dict = {}

        if persist:
            self._load()

    # ==================================================
    # 📝 Core Operations (PRESERVED + UPGRADED)
    # ==================================================
    def add(self, role: str, content: str, metadata: Dict = None) -> None:
        """Add message to memory. Preserved + upgraded."""
        entry = {
            "role": role,
            "content": str(content)[:5000],  # Limit size
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "session_id": self.session_id,
        }
        if metadata:
            entry["metadata"] = metadata

        self.history.append(entry)

        # Trim if over max
        if len(self.history) > self.max_size:
            self.history.pop(0)

        if self.persist:
            self._save()

    def get_context(self, limit: int = CONTEXT_WINDOW) -> List[Dict]:
        """
        Get recent context window.
        Preserved + upgraded — returns clean format for LLM.
        """
        recent = self.history[-limit:]
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def get_full_history(self) -> List[Dict]:
        """Full history return karo."""
        return list(self.history)

    def clear(self) -> None:
        """Memory clear karo."""
        self.history = []
        if self.persist:
            self._save()

    # ==================================================
    # 🔍 Search & Analysis (NEW)
    # ==================================================
    def search(self, query: str, top_n: int = 5) -> List[Dict]:
        """Memory mein keyword search karo."""
        query_lower = query.lower()
        matches = []

        for entry in reversed(self.history):
            if query_lower in entry.get("content", "").lower():
                matches.append(entry)
                if len(matches) >= top_n:
                    break

        return matches

    def get_last_user_message(self) -> Optional[str]:
        """Last user message lo."""
        for entry in reversed(self.history):
            if entry.get("role") == "user":
                return entry.get("content")
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Last assistant response lo."""
        for entry in reversed(self.history):
            if entry.get("role") == "assistant":
                return entry.get("content")
        return None

    def get_stats(self) -> Dict:
        """Memory statistics."""
        roles = {}
        for entry in self.history:
            role = entry.get("role", "unknown")
            roles[role] = roles.get(role, 0) + 1

        return {
            "total_messages": len(self.history),
            "by_role": roles,
            "session_id": self.session_id,
            "max_size": self.max_size,
        }

    def set_metadata(self, key: str, value) -> None:
        """Session metadata store karo."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default=None):
        return self._metadata.get(key, default)

    # ==================================================
    # 💾 Persistence (NEW)
    # ==================================================
    def _save(self) -> None:
        """Memory file mein save karo."""
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "history": self.history[-20:],  # Save last 20
                    "session_id": self.session_id,
                }, f, indent=2)
        except Exception:
            pass

    def _load(self) -> None:
        """File se memory load karo."""
        if not os.path.exists(MEMORY_FILE):
            return
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.history = data.get("history", [])
        except Exception:
            pass

    def export_conversation(self, format: str = "text") -> str:
        """Conversation export karo."""
        if format == "json":
            return json.dumps(self.history, indent=2)

        lines = []
        for entry in self.history:
            role = entry.get("role", "?").upper()
            content = entry.get("content", "")
            ts = entry.get("timestamp", "")[:19]
            lines.append(f"[{ts}] {role}: {content}")

        return "\n".join(lines)
