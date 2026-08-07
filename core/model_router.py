"""
Chhoti Don - Local Model Router

Single decision point that maps a task/brain type to the correct LOCAL Ollama
model. Model names come from one configuration location (core.config.Config):

    MAIN_MODEL   -> chat, planning, reasoning, conversation, tool calling
    CODING_MODEL -> code generation, code review, debugging, refactoring
    VISION_MODEL -> image understanding, screenshots, PDF image pages, UI analysis

This module only decides WHICH local model to use. Execution still goes through
the existing Ollama client (core.local_model_engine); nothing else changes.
"""

from typing import Dict

from core.config import Config

# ── Model constants (re-exported from the single config location) ──
MAIN_MODEL = Config.MAIN_MODEL
CODING_MODEL = Config.CODING_MODEL
VISION_MODEL = Config.VISION_MODEL

# ── Task / brain-type -> category mapping ─────────────────────
# Coding-oriented tasks and brain types.
_CODING_TASKS = {
    "coding", "code", "coder",
    "debug", "debugging", "bugfix", "fix",
    "code_generation", "code_review", "review_code",
    "refactor", "refactoring",
    "generate_code", "debug_code", "explain_code", "execute_code", "refactor_code",
}

# Vision-oriented tasks and brain types.
_VISION_TASKS = {
    "vision", "image", "image_understanding",
    "screenshot", "screenshot_analysis",
    "pdf_image", "pdf_image_pages",
    "ui_analysis", "ui",
}

# Everything else (chat, planning, reasoning, conversation, tool calling,
# research, analytics, security analysis, review, default, ...) uses MAIN_MODEL.


def resolve_model(task_type: str = "default") -> str:
    """Return the local model to use for a given task/brain type.

    Unknown types fall back to the main model, so this never raises.
    """
    key = (task_type or "default").strip().lower()
    if key in _CODING_TASKS:
        return CODING_MODEL
    if key in _VISION_TASKS:
        return VISION_MODEL
    return MAIN_MODEL


def get_models() -> Dict[str, str]:
    """The three configured local models, by role."""
    return {"main": MAIN_MODEL, "coding": CODING_MODEL, "vision": VISION_MODEL}


# ── Graceful availability / health checks ─────────────────────
def check_ollama() -> Dict:
    """Detect whether Ollama is reachable and list installed models.

    Never raises; returns a structured status usable by callers.
    """
    try:
        # Reuse the existing Ollama client instead of duplicating HTTP logic.
        from core.local_model_engine import list_available_models

        result = list_available_models()
        if result.get("status") == "success":
            return {"running": True, "models": result.get("models", []), "error": None}
        return {"running": False, "models": [], "error": "ollama_not_running"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"running": False, "models": [], "error": str(exc)}


def _is_installed(model: str, installed) -> bool:
    base = model.split(":")[0]
    return any(m == model or m.split(":")[0] == base for m in installed)


def check_model(model: str) -> Dict:
    """Gracefully report whether a specific local model can be used.

    Distinguishes: ollama not running, model not installed, or ready.
    """
    status = check_ollama()
    if not status["running"]:
        return {
            "model": model,
            "available": False,
            "reason": "ollama_not_running",
            "message": (
                "Ollama is not reachable. Start it with 'ollama serve'."
            ),
        }
    if not _is_installed(model, status["models"]):
        return {
            "model": model,
            "available": False,
            "reason": "model_not_installed",
            "message": f"Model '{model}' is not installed. Install it with: ollama pull {model}",
        }
    return {"model": model, "available": True, "reason": None, "message": "ready"}


def routing_report() -> Dict:
    """Snapshot of the routing configuration + availability (for diagnostics)."""
    return {
        "models": get_models(),
        "availability": {
            "main": check_model(MAIN_MODEL),
            "coding": check_model(CODING_MODEL),
            "vision": check_model(VISION_MODEL),
        },
    }
