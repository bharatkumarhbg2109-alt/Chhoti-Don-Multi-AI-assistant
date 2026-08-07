"""Text-to-speech via Piper (CPU, so the GPU stays free for the LLM).

Model loads ONCE. Playback supports barge-in: pass a threading.Event and it is
checked between audio blocks, so speaking over the assistant stops it instantly.
On any failure the caller falls back to printing the text.
"""

from __future__ import annotations

import os
import time
import wave
import threading
from typing import Optional

import numpy as np

from .config import VoiceConfig


class TextToSpeech:
    """Load-once Piper voice with interruptible playback."""

    def __init__(self, cfg: VoiceConfig):
        self.cfg = cfg
        self._voice = None
        self._syn_config = None
        self.sample_rate = 22050  # refined after load from the voice config

    # ── load once ────────────────────────────────────────────────
    def load(self) -> "TextToSpeech":
        if self._voice is not None:
            return self
        from piper import PiperVoice, SynthesisConfig

        model_path = self.cfg.tts_voice_model
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Piper voice model not found: {model_path}\n"
                f"Download one with:  python -m voice.download_voice\n"
                f"or set CHHOTI_DON_VOICE_TTS_MODEL to an existing .onnx file."
            )
        t0 = time.time()
        # use_cuda=False on purpose: keep the GPU free for the LLM.
        self._voice = PiperVoice.load(model_path, use_cuda=False)
        self.sample_rate = int(getattr(self._voice.config, "sample_rate", 22050))
        syn_kwargs = {"length_scale": self.cfg.tts_length_scale}
        if self.cfg.tts_speaker_id is not None:
            syn_kwargs["speaker_id"] = self.cfg.tts_speaker_id
        self._syn_config = SynthesisConfig(**syn_kwargs)
        print(f"[voice.tts] loaded Piper '{os.path.basename(model_path)}' "
              f"@ {self.sample_rate} Hz in {time.time() - t0:.1f}s")
        return self

    # ── synthesize to a numpy int16 array ────────────────────────
    def synthesize(self, text: str) -> np.ndarray:
        if self._voice is None:
            self.load()
        chunks = []
        for chunk in self._voice.synthesize(text, syn_config=self._syn_config):
            arr = getattr(chunk, "audio_int16_array", None)
            if arr is None:
                arr = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
            chunks.append(np.asarray(arr, dtype=np.int16))
        if not chunks:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(chunks)

    # ── synthesize straight to a WAV file (used by verification) ──
    def synth_to_wav(self, text: str, path: str) -> str:
        if self._voice is None:
            self.load()
        with wave.open(path, "wb") as wav_file:
            self._voice.synthesize_wav(text, wav_file, syn_config=self._syn_config)
        return path

    # ── speak (interruptible playback) ───────────────────────────
    def speak(self, text: str, interrupt: Optional[threading.Event] = None) -> bool:
        """Synthesize and play `text`. Returns True if it finished, False if
        interrupted (barge-in) or on failure (caller then prints the text)."""
        try:
            audio = self.synthesize(text)
        except Exception as exc:
            print(f"[voice.tts] synth failed ({type(exc).__name__}: {str(exc)[:120]}).")
            return False
        if audio.size == 0:
            return False
        try:
            return self._play(audio, interrupt)
        except Exception as exc:
            print(f"[voice.tts] playback failed ({type(exc).__name__}: {str(exc)[:120]}).")
            return False

    def _play(self, audio: np.ndarray, interrupt: Optional[threading.Event]) -> bool:
        """Block-by-block playback so a barge-in Event can stop it immediately."""
        import sounddevice as sd

        block = max(1, int(self.sample_rate * 0.1))  # 100 ms blocks
        finished = True
        stream = sd.OutputStream(
            samplerate=self.sample_rate, channels=1, dtype="int16",
            device=self.cfg.output_device,
        )
        stream.start()
        try:
            for start in range(0, len(audio), block):
                if interrupt is not None and interrupt.is_set():
                    finished = False
                    break
                stream.write(audio[start:start + block])
        finally:
            stream.stop()
            stream.close()
        return finished
