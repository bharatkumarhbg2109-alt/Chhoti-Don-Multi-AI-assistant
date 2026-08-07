"""Chhoti Don - local, zero-cost VOICE I/O layer.

A thin adapter around the existing text pipeline:
    mic -> VAD -> faster-whisper (STT) -> [EXISTING BRAIN] -> Piper (TTS) -> speaker

The brain, tools, and risk engine are untouched; voice only converts audio <->
text at the edges and calls the same /api/chat entry point the web UI uses.
Text mode keeps working exactly as before — voice is opt-in via `python -m voice`.
"""

from .config import VoiceConfig
from .orchestrator import VoiceAssistant

__all__ = ["VoiceConfig", "VoiceAssistant"]
