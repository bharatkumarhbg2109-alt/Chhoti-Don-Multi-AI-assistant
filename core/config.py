"""
Chhoti Don - Config
Central configuration management for core module.
Phase 2.2 - Full Upgrade
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Central configuration class. Preserved + upgraded."""

    # AI Models — Chhoti Don is LOCAL-ONLY (no cloud LLM).
    # LOCAL_MODEL gates local vs. offline ("simulation") mode and is shown in
    # status. It must be an installed Ollama tag — kept in sync with MAIN_MODEL.
    LOCAL_MODEL = os.getenv("CHHOTI_DON_OLLAMA_MODEL", "qwen3.5:latest")

    # ── Local model routing (single source of truth) ──────────
    # These MUST match the exact tags installed in Ollama (`ollama list`).
    # Main brain: chat, planning, reasoning, conversation, tool calling.
    MAIN_MODEL = os.getenv("CHHOTI_DON_MAIN_MODEL", "qwen3.5:latest")
    # Coding: code generation, code review, debugging, refactoring, and the
    # autonomous coding-agent loop. deepseek-coder-v2:16b-lite-instruct-q4_K_M is
    # the SOLE coding model — it emits `finish`, self-heals, and fits 8GB VRAM.
    # Overridable at runtime via CHHOTI_DON_CODING_MODEL.
    CODING_MODEL = os.getenv("CHHOTI_DON_CODING_MODEL", "deepseek-coder-v2:16b-lite-instruct-q4_K_M")
    CODING_MODEL_FALLBACK = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
    # Vision: image understanding, screenshots, PDF image pages, UI analysis.
    # Uses the dedicated llava vision model (installed as `llava:latest`).
    # Override with CHHOTI_DON_VISION_MODEL if desired.
    VISION_MODEL = os.getenv("CHHOTI_DON_VISION_MODEL", "llava:latest")

    # Modes — LOCAL-ONLY. There is no cloud API key and no cloud mode. The
    # offline ("simulation") state is decided at RUNTIME by Brain probing Ollama,
    # not configured here; this flag is kept False for a backward-compatible
    # to_dict() export.
    SIMULATION_MODE = False
    DEBUG_MODE = os.getenv("CHHOTI_DON_DEBUG", "false").lower() == "true"

    # Memory
    MAX_MEMORY = 20
    MEMORY_FILE = "core/memory_state.json"
    LEARNING_FILE = "core/learning_state.json"

    # Ollama
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
    OLLAMA_TIMEOUT = int(os.getenv("CHHOTI_DON_OLLAMA_TIMEOUT", "120"))
    OLLAMA_GPU_LAYERS = int(os.getenv("OLLAMA_GPU_LAYERS", "99"))

    # Guardian
    GUARDIAN_ENABLED = True
    RATE_LIMIT_WINDOW = 60
    MAX_SCANS_PER_WINDOW = 5

    # Execution
    MAX_RETRIES = 2
    DEFAULT_TIMEOUT = 30
    MAX_PLAN_STEPS = 10

    # Logging
    LOG_LEVEL = os.getenv("CHHOTI_DON_LOG_LEVEL", "INFO")
    LOG_TO_FILE = False

    @classmethod
    def get(cls, key: str, default=None):
        """Config value get karo."""
        return getattr(cls, key.upper(), default)

    @classmethod
    def is_api_mode(cls) -> bool:
        # LOCAL-ONLY: the cloud LLM path was removed, so this is always False.
        return False

    @classmethod
    def is_local_mode(cls) -> bool:
        return not cls.is_api_mode()

    @classmethod
    def to_dict(cls) -> dict:
        """Safe config export — no secrets."""
        return {
            "model": cls.LOCAL_MODEL,
            "local_model": cls.LOCAL_MODEL,
            "simulation_mode": cls.SIMULATION_MODE,
            "debug_mode": cls.DEBUG_MODE,
            "max_memory": cls.MAX_MEMORY,
            "guardian_enabled": cls.GUARDIAN_ENABLED,
            "log_level": cls.LOG_LEVEL,
            "api_mode": cls.is_api_mode(),
        }
