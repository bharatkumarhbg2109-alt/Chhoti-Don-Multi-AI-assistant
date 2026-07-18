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

    # AI Models
    MODEL_NAME = os.getenv("CHHOTI_DON_OPENAI_MODEL", "gpt-4o-mini")
    LOCAL_MODEL = os.getenv("CHHOTI_DON_OLLAMA_MODEL", "mistral:latest")

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Modes
    SIMULATION_MODE = False if OPENAI_API_KEY else True
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
        return bool(cls.OPENAI_API_KEY)

    @classmethod
    def is_local_mode(cls) -> bool:
        return not cls.is_api_mode()

    @classmethod
    def to_dict(cls) -> dict:
        """Safe config export — no secrets."""
        return {
            "model": cls.MODEL_NAME,
            "local_model": cls.LOCAL_MODEL,
            "simulation_mode": cls.SIMULATION_MODE,
            "debug_mode": cls.DEBUG_MODE,
            "max_memory": cls.MAX_MEMORY,
            "guardian_enabled": cls.GUARDIAN_ENABLED,
            "log_level": cls.LOG_LEVEL,
            "api_mode": cls.is_api_mode(),
        }
