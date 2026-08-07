"""Speech-to-text via faster-whisper. Model loads ONCE and is reused.

Hinglish note: language defaults to auto-detect so code-switched Hindi+English
transcribes without being forced to English. Raise accuracy by setting a bigger
model (CHHOTI_DON_VOICE_STT_MODEL=large-v3) if "small" mis-hears Hindi.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import numpy as np

from .config import VoiceConfig


class SpeechToText:
    """Thin, load-once wrapper around faster-whisper's WhisperModel."""

    def __init__(self, cfg: VoiceConfig):
        self.cfg = cfg
        self._model = None
        self.device = cfg.stt_device
        self.compute_type = cfg.stt_compute_type

    # ── load once ────────────────────────────────────────────────
    def load(self) -> "SpeechToText":
        if self._model is not None:
            return self
        from faster_whisper import WhisperModel

        t0 = time.time()
        try:
            self._model = WhisperModel(
                self.cfg.stt_model_size,
                device=self.cfg.stt_device,
                compute_type=self.cfg.stt_compute_type,
            )
            self.device = self.cfg.stt_device
            self.compute_type = self.cfg.stt_compute_type
        except Exception as exc:
            # Blackwell / CUDA / cuDNN can fail to init — fall back to CPU so the
            # assistant still works (slower) instead of crashing.
            print(f"[voice.stt] CUDA init failed ({type(exc).__name__}: {str(exc)[:120]}). "
                  f"Falling back to CPU/{self.cfg.stt_cpu_compute_type}.")
            self._model = WhisperModel(
                self.cfg.stt_model_size,
                device="cpu",
                compute_type=self.cfg.stt_cpu_compute_type,
            )
            self.device = "cpu"
            self.compute_type = self.cfg.stt_cpu_compute_type
        print(f"[voice.stt] loaded '{self.cfg.stt_model_size}' on {self.device} "
              f"({self.compute_type}) in {time.time() - t0:.1f}s")
        return self

    # ── transcribe ───────────────────────────────────────────────
    def transcribe(self, audio: np.ndarray) -> Tuple[str, Optional[str], float]:
        """Transcribe a mono float32 [-1,1] @ sample_rate array.

        Returns (text, detected_language, avg_logprob). Never raises on empty
        audio — returns ("", None, 0.0) so the caller can ask the user to repeat.
        If a CUDA runtime lib (cuBLAS/cuDNN) is missing, transparently falls back
        to CPU and retries, so the GPU default never hard-crashes a turn.
        """
        if self._model is None:
            self.load()
        if audio is None or len(audio) == 0:
            return "", None, 0.0
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        try:
            return self._run(audio)
        except RuntimeError as exc:
            if self.device == "cuda" and self._is_cuda_lib_error(exc):
                print(f"[voice.stt] CUDA runtime lib missing "
                      f"({str(exc)[:90]}). Reloading on CPU. "
                      f"For GPU speed: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
                self._reload_cpu()
                return self._run(audio)
            raise

    def transcribe_file(self, path: str) -> Tuple[str, Optional[str], float]:
        """Transcribe an audio FILE (wav/webm/ogg/mp3…). faster-whisper decodes and
        resamples via PyAV, so browser MediaRecorder blobs work directly. Same
        CUDA->CPU fallback as transcribe()."""
        if self._model is None:
            self.load()
        try:
            return self._run(path)
        except RuntimeError as exc:
            if self.device == "cuda" and self._is_cuda_lib_error(exc):
                print(f"[voice.stt] CUDA runtime lib missing "
                      f"({str(exc)[:90]}). Reloading on CPU.")
                self._reload_cpu()
                return self._run(path)
            raise

    def _run(self, audio) -> Tuple[str, Optional[str], float]:
        segments, info = self._model.transcribe(
            audio,
            language=self.cfg.language,          # None -> auto-detect (Hinglish)
            beam_size=self.cfg.stt_beam_size,
            vad_filter=True,                     # drop leading/trailing silence
            condition_on_previous_text=False,    # avoid runaway hallucination
        )
        parts, logprobs = [], []
        for seg in segments:
            parts.append(seg.text)
            if getattr(seg, "avg_logprob", None) is not None:
                logprobs.append(seg.avg_logprob)
        text = " ".join(p.strip() for p in parts).strip()
        avg = float(np.mean(logprobs)) if logprobs else 0.0
        lang = getattr(info, "language", None)
        return text, lang, avg

    @staticmethod
    def _is_cuda_lib_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(k in msg for k in ("cublas", "cudnn", "cuda", ".dll", "library"))

    def _reload_cpu(self) -> None:
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self.cfg.stt_model_size, device="cpu",
            compute_type=self.cfg.stt_cpu_compute_type,
        )
        self.device = "cpu"
        self.compute_type = self.cfg.stt_cpu_compute_type
