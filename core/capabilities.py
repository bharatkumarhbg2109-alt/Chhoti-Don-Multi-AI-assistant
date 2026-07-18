"""
Chhoti Don - Capability Registry

Reports the capabilities that genuinely exist in this project, with a
computed `available` flag based on whether the backing module actually
imports. This is intentionally conservative: a capability is only marked
available when its real implementation is importable. Offensive cyber
tooling is deliberately never advertised here.
"""

from __future__ import annotations

import importlib
from typing import Dict, List


def _importable(module: str, attr: str = None) -> bool:
    try:
        mod = importlib.import_module(module)
        if attr:
            return hasattr(mod, attr)
        return True
    except Exception:
        return False


def get_capabilities() -> List[Dict]:
    """Return the list of user-facing capabilities discovered in the project."""

    chat_ok = _importable("core.manager", "ManagerAgent")
    history_ok = _importable("core.history_store", "create_conversation")
    memory_ok = _importable("core.memory", "Memory")
    coding_ok = _importable("tools.registry", "ToolRegistry")
    cyber_ok = _importable("cyber_engine.cyber_controller", "CyberController")
    heal_ok = _importable("cyber_engine.code_intelligence.code_controller", "run_code_intelligence")
    voice_ok = _importable("voice_assistant")

    caps: List[Dict] = [
        {
            "id": "assistant",
            "name": "Assistant",
            "available": chat_ok,
            "category": "Assistant",
            "description": "Chat with the local AI (Ollama) with markdown, code blocks, retry and stop.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "assistant",
        },
        {
            "id": "conversations",
            "name": "Conversations",
            "available": history_ok,
            "category": "Conversations",
            "description": "Persistent conversation history stored locally in SQLite; survives restart.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "assistant",
        },
        {
            "id": "memory",
            "name": "Memory",
            "available": memory_ok,
            "category": "Memory",
            "description": "Short-term conversation memory the assistant uses for context.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "memory",
        },
        {
            "id": "coding",
            "name": "Coding Engine",
            "available": coding_ok,
            "category": "Coding",
            "description": "Generate, explain and debug code through the assistant (ask in chat).",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "assistant",
        },
        {
            "id": "system_health",
            "name": "System Status",
            "available": True,
            "category": "System health",
            "description": "Live status of the desktop shell, backend, Ollama, model and database.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "system",
        },
        {
            "id": "cyber_defense",
            "name": "Cyber Engine",
            "available": cyber_ok,
            "category": "Cyber defense",
            "description": "Read-only defensive posture: engine info, safety policy, private-lab allowlist and a confirmed loopback port check. Offensive tooling is not exposed.",
            "risk_level": "medium",
            "requires_confirmation": True,
            "view": "cyber",
        },
        {
            "id": "self_healing",
            "name": "Self-Healing",
            "available": heal_ok,
            "category": "Self-healing",
            "description": "Read-only code intelligence: static analysis and project health. Applying fixes requires explicit confirmation and is not automated from the UI.",
            "risk_level": "medium",
            "requires_confirmation": True,
            "view": "healing",
        },
        {
            "id": "voice",
            "name": "Voice Assistant",
            # Discovered in the repo (voice_assistant.py / chhoti_don_voice.py) but it is a
            # standalone microphone/CLI tool with no safe web API boundary — not exposed in the UI.
            "available": False,
            "category": "Voice",
            "description": "Voice interface exists as a standalone CLI tool; no desktop UI integration yet.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": None,
            "note": "CLI only — run voice_assistant.py directly.",
        },
    ]
    return caps


def get_registry() -> Dict:
    caps = get_capabilities()
    return {
        "capabilities": caps,
        "available_count": sum(1 for c in caps if c["available"]),
        "total_count": len(caps),
    }
