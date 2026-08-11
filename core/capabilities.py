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
    vision_ok = _importable("tools.image_analyzer", "analyze_image")
    web_ok = _importable("browser.guarded", "web_search")
    # Playwright headed browser (read-only research). Available only when both the
    # guarded wrappers import AND the optional playwright package is present.
    browser_ok = (_importable("browser.guarded", "browser_read")
                  and _importable("playwright"))
    cyber_ok = _importable("cyber_engine.cyber_controller", "CyberController")
    heal_ok = _importable("cyber_engine.code_intelligence.code_controller", "run_code_intelligence")
    # New local voice package (faster-whisper STT + Piper TTS), wired to the UI
    # via /api/voice/transcribe and /api/voice/speak.
    voice_ok = _importable("voice", "VoiceAssistant")

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
            "id": "vision",
            "name": "Vision",
            "available": vision_ok,
            "category": "Vision",
            "description": "Understand images locally (qwen3.5 vision). Attach an image or send a file path in chat.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "assistant",
        },
        {
            "id": "web_search",
            "name": "Web Search",
            "available": web_ok,
            "category": "Web",
            "description": "Keyless web search + page reading (guarded). Ask to 'web search ...' or 'open page <url>'.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "assistant",
        },
        {
            "id": "browser_automation",
            "name": "Browser (read-only)",
            "available": browser_ok,
            "category": "Web",
            "description": ("Headed Playwright browser for JS-heavy pages: the assistant opens a "
                            "real Chromium window, navigates and extracts readable content. "
                            "Phase 1 is READ-ONLY (no clicking/typing/logins). Complements the "
                            "keyless static web search."),
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
            "name": "Voice I/O",
            "available": voice_ok,
            "category": "Voice",
            "description": "Local speech-in / speech-out (faster-whisper + Piper). Use the mic button, or run `python -m voice`.",
            "risk_level": "low",
            "requires_confirmation": False,
            "view": "assistant",
            "note": "Wired to /api/voice/transcribe and /api/voice/speak.",
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
