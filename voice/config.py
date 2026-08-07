"""Chhoti Don - Voice layer configuration (single source of truth).

Every tunable for the voice I/O layer lives here. Values may be overridden with
CHHOTI_DON_VOICE_* environment variables so nothing needs code edits to retune.

The voice layer is a THIN ADAPTER around the existing text pipeline: it only
converts audio <-> text at the edges and calls the same `/api/chat` brain
entry point the web UI uses. None of the brain/tool/risk logic lives here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# Anaconda links several OpenMP runtimes (numpy-MKL, ctranslate2, onnxruntime).
# Without this, faster-whisper aborts at transcribe time with "OMP Error #15:
# libiomp5md.dll already initialized". Must be set before those libs load, and
# config is imported first by every voice module, so this is the right place.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")

# Package-local default location for downloaded Piper ONNX voices.
_PKG_DIR = Path(__file__).resolve().parent
_MODELS_DIR = _PKG_DIR / "models"

# Default Piper voice. English is a deliberate, reliable default: pure Hinglish
# (mixed Devanagari + Latin) has no strong single Piper voice, and the spec asks
# for a sensible default that is swappable. Override with a Hindi/other .onnx via
# CHHOTI_DON_VOICE_TTS_MODEL once you have one downloaded.
_DEFAULT_VOICE = "en_US-lessac-medium"


def _env(name: str, default: str) -> str:
    return os.getenv(f"CHHOTI_DON_VOICE_{name}", default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(f"CHHOTI_DON_VOICE_{name}", str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(f"CHHOTI_DON_VOICE_{name}")
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class VoiceConfig:
    # ── Speech-to-text (faster-whisper) ───────────────────────────
    stt_model_size: str = field(default_factory=lambda: _env("STT_MODEL", "small"))
    stt_device: str = field(default_factory=lambda: _env("STT_DEVICE", "cuda"))
    stt_compute_type: str = field(default_factory=lambda: _env("STT_COMPUTE", "float16"))
    # language=None -> Whisper auto-detects (best for code-switched Hinglish).
    # Set to "hi" to bias toward Hindi, or "en" to force English.
    stt_language: Optional[str] = field(
        default_factory=lambda: (_env("STT_LANG", "auto") or "auto"))
    stt_beam_size: int = field(default_factory=lambda: _env_int("STT_BEAM", 1))
    # Fallback used automatically if CUDA init fails (Blackwell/driver issues).
    stt_cpu_compute_type: str = field(default_factory=lambda: _env("STT_CPU_COMPUTE", "int8"))

    # ── Text-to-speech (Piper, CPU) ───────────────────────────────
    tts_voice_model: str = field(
        default_factory=lambda: _env("TTS_MODEL", str(_MODELS_DIR / f"{_DEFAULT_VOICE}.onnx")))
    tts_speaker_id: Optional[int] = None
    tts_length_scale: float = field(
        default_factory=lambda: float(_env("TTS_LENGTH_SCALE", "1.0")))

    # ── Audio / microphone ────────────────────────────────────────
    # sample_rate is the STT rate faster-whisper needs (16 kHz).
    sample_rate: int = field(default_factory=lambda: _env_int("SAMPLE_RATE", 16000))
    # capture_sample_rate is what the MIC is actually opened at. Windows MME
    # commonly delivers near-silence when forced to 16 kHz, and WASAPI refuses
    # 16 kHz outright — so we capture at 48 kHz (a webrtcvad-valid rate that
    # every backend supports) and resample down to 16 kHz for Whisper.
    capture_sample_rate: int = field(default_factory=lambda: _env_int("CAPTURE_RATE", 48000))
    input_device: Optional[int] = None   # None = system default mic
    output_device: Optional[int] = None  # None = system default speaker

    # ── Voice activity detection (webrtcvad) ──────────────────────
    vad_aggressiveness: int = field(default_factory=lambda: _env_int("VAD_AGGR", 2))  # 0-3
    vad_frame_ms: int = 30                      # webrtcvad supports 10/20/30 ms
    speech_start_frames: int = 3                # consecutive voiced frames to trigger
    silence_timeout_ms: int = field(default_factory=lambda: _env_int("SILENCE_MS", 800))
    preroll_ms: int = 300                       # audio kept before speech trigger
    max_utterance_sec: int = field(default_factory=lambda: _env_int("MAX_UTTER_SEC", 15))

    # ── Interaction ───────────────────────────────────────────────
    # push_to_talk (default, reliable) | continuous_vad | wake_word (not impl)
    mode: str = field(default_factory=lambda: _env("MODE", "push_to_talk"))
    barge_in: bool = field(default_factory=lambda: _env_bool("BARGE_IN", True))

    # ── Brain entry point (thin adapter -> existing text pipeline) ─
    # "http"  -> POST to the running Flask server's /api/chat (same as the UI)
    # "inprocess" -> import app._route_to_tool/_extract_response (no server)
    brain_mode: str = field(default_factory=lambda: _env("BRAIN_MODE", "http"))
    brain_api_base: str = field(
        default_factory=lambda: _env("BRAIN_API", "http://127.0.0.1:8000").rstrip("/"))
    brain_tool: str = field(default_factory=lambda: _env("BRAIN_TOOL", "chat"))
    brain_timeout: int = field(default_factory=lambda: _env_int("BRAIN_TIMEOUT", 120))

    # ── Misc ──────────────────────────────────────────────────────
    log_timings: bool = field(default_factory=lambda: _env_bool("LOG_TIMINGS", True))

    # Derived helpers -------------------------------------------------
    @property
    def language(self) -> Optional[str]:
        """Whisper language arg: None means auto-detect."""
        return None if (self.stt_language or "auto").lower() == "auto" else self.stt_language

    @property
    def vad_frame_bytes(self) -> int:
        """Bytes per VAD frame for 16-bit mono PCM (at the CAPTURE rate)."""
        return int(self.capture_sample_rate * (self.vad_frame_ms / 1000.0)) * 2

    @property
    def vad_frame_samples(self) -> int:
        """Samples per VAD frame at the CAPTURE rate (webrtcvad needs this)."""
        return int(self.capture_sample_rate * (self.vad_frame_ms / 1000.0))

    @property
    def models_dir(self) -> Path:
        return _MODELS_DIR

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_VOICE_NAME = _DEFAULT_VOICE
MODELS_DIR = _MODELS_DIR
