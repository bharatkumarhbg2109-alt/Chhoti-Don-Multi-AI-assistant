"""Microphone capture with webrtcvad. Records ONE utterance: start on speech,
stop after a configurable silence gap. Also provides a barge-in listener used
while the assistant is speaking.

The mic is opened at cfg.capture_sample_rate (48 kHz — Windows MME delivers
near-silence at 16 kHz and WASAPI refuses it). VAD runs at that rate (48 kHz is
webrtcvad-valid); the captured utterance is resampled to cfg.sample_rate
(16 kHz) before it is handed to faster-whisper.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Optional

import numpy as np

from .config import VoiceConfig


class MicCapture:
    def __init__(self, cfg: VoiceConfig):
        self.cfg = cfg
        import webrtcvad
        self._vad = webrtcvad.Vad(cfg.vad_aggressiveness)
        self._cr = cfg.capture_sample_rate                 # mic + VAD rate
        self._frame_samples = cfg.vad_frame_samples        # at capture rate
        self._silence_frames = max(1, int(cfg.silence_timeout_ms / cfg.vad_frame_ms))
        self._preroll_frames = max(0, int(cfg.preroll_ms / cfg.vad_frame_ms))
        self._max_frames = int(cfg.max_utterance_sec * (1000.0 / cfg.vad_frame_ms))

    def _is_speech(self, frame_i16: np.ndarray) -> bool:
        # webrtcvad wants raw little-endian 16-bit bytes for one frame, at the
        # SAME sample rate the audio was captured at.
        return self._vad.is_speech(frame_i16.tobytes(), self._cr)

    def _to_stt(self, audio_i16: np.ndarray) -> np.ndarray:
        """Resample captured int16 @ capture_rate -> float32 [-1,1] @ 16 kHz."""
        f = audio_i16.astype(np.float32) / 32768.0
        if self._cr != self.cfg.sample_rate:
            from scipy.signal import resample_poly
            f = resample_poly(f, self.cfg.sample_rate, self._cr).astype(np.float32)
        return f

    # ── record a single utterance ────────────────────────────────
    def record_utterance(self) -> np.ndarray:
        """Block until an utterance is captured; return float32 [-1,1] @ 16 kHz.

        Returns an empty array if the max duration elapses with no speech.
        """
        import sounddevice as sd

        preroll = deque(maxlen=self._preroll_frames or 1)
        collected = []
        started = False
        silence_run = 0
        total = 0

        with sd.InputStream(
            samplerate=self._cr, channels=1, dtype="int16",
            blocksize=self._frame_samples, device=self.cfg.input_device,
        ) as stream:
            while True:
                data, _ = stream.read(self._frame_samples)
                frame = np.asarray(data, dtype=np.int16).reshape(-1)
                if frame.shape[0] < self._frame_samples:
                    frame = np.pad(frame, (0, self._frame_samples - frame.shape[0]))
                total += 1
                voiced = self._is_speech(frame)

                if not started:
                    preroll.append(frame)
                    if voiced:
                        collected.extend(preroll)  # include a little pre-speech
                        collected.append(frame)
                        started = True
                        silence_run = 0
                    elif total >= self._max_frames:
                        return np.zeros(0, dtype=np.float32)  # nothing was said
                else:
                    collected.append(frame)
                    silence_run = 0 if voiced else silence_run + 1
                    if silence_run >= self._silence_frames:
                        break
                    if len(collected) >= self._max_frames:
                        break

        if not collected:
            return np.zeros(0, dtype=np.float32)
        return self._to_stt(np.concatenate(collected))

    # ── barge-in listener (used during TTS playback) ─────────────
    def listen_for_barge_in(self, stop_event: threading.Event,
                            on_speech: threading.Event) -> None:
        """Set `on_speech` as soon as the user clearly starts talking.

        Requires several consecutive voiced frames to avoid triggering on the
        assistant's own speaker output (no echo cancellation here).
        """
        import sounddevice as sd

        needed = max(self.cfg.speech_start_frames + 2, 5)
        run = 0
        try:
            with sd.InputStream(
                samplerate=self._cr, channels=1, dtype="int16",
                blocksize=self._frame_samples, device=self.cfg.input_device,
            ) as stream:
                while not stop_event.is_set():
                    data, _ = stream.read(self._frame_samples)
                    frame = np.asarray(data, dtype=np.int16).reshape(-1)
                    if frame.shape[0] < self._frame_samples:
                        continue
                    run = run + 1 if self._is_speech(frame) else 0
                    if run >= needed:
                        on_speech.set()
                        return
        except Exception:
            # If the mic can't be opened during playback, just skip barge-in.
            return
