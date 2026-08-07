"""Voice loop: mic -> VAD -> STT -> [EXISTING BRAIN] -> TTS -> speaker.

This is the only place the pieces meet. It calls the existing text brain through
BrainClient (same /api/chat entry point as the UI) and never touches reasoning,
tools, or the risk engine. Text mode is unaffected — this runs only when a user
explicitly starts voice mode.
"""

from __future__ import annotations

import threading
import time

from .config import VoiceConfig
from .capture import MicCapture
from .stt import SpeechToText
from .tts import TextToSpeech
from .brain_client import BrainClient

# Whisper on silence/noise tends to emit very short, low-probability hallucinations.
_LOW_CONFIDENCE_LOGPROB = -1.1
_MIN_CHARS = 2


class VoiceAssistant:
    def __init__(self, cfg: VoiceConfig | None = None):
        self.cfg = cfg or VoiceConfig()
        self.stt = SpeechToText(self.cfg)
        self.tts = TextToSpeech(self.cfg)
        self.mic = MicCapture(self.cfg)
        self.brain = BrainClient(self.cfg)
        self._loaded = False

    # ── startup ──────────────────────────────────────────────────
    def warmup(self) -> None:
        """Load STT + TTS once and verify the brain backend is reachable."""
        if self._loaded:
            return
        print("[voice] loading models (once)…")
        self.stt.load()
        self.tts.load()
        ok, msg = self.brain.health()
        print(f"[voice] brain ({self.cfg.brain_mode}): {'OK' if ok else 'UNAVAILABLE'} — {msg}")
        if not ok and self.cfg.brain_mode == "http":
            print("[voice] Voice needs the backend running. Start it: python app.py")
        self._loaded = True

    # ── a single turn: audio -> answer -> speech ─────────────────
    def handle_turn(self, audio) -> bool:
        """Process one captured utterance. Returns True if a turn completed,
        False if it was rejected (empty/garbled) and the user should retry."""
        if audio is None or len(audio) == 0:
            self._say("Mujhe kuch sunai nahi diya. Dobara boliye.")
            return False

        t_stt = time.time()
        text, lang, logprob = self.stt.transcribe(audio)
        stt_s = time.time() - t_stt

        # Graceful failure: don't forward silence/garbage to the brain.
        if len(text.strip()) < _MIN_CHARS or logprob < _LOW_CONFIDENCE_LOGPROB:
            print(f"[voice] rejected transcript (text={text!r}, logprob={logprob:.2f})")
            self._say("Samajh nahi aaya, thoda saaf se dobara boliye.")
            return False

        print(f"\n🗣️  You ({lang}): {text}")

        t_brain = time.time()
        try:
            answer = self.brain.ask(text)
        except Exception as exc:
            print(f"[voice] brain call failed: {type(exc).__name__}: {str(exc)[:140]}")
            self._say("Backend se jawab nahi mila. Server chaalu hai kya?")
            return False
        brain_s = time.time() - t_brain

        if not answer.strip():
            answer = "Mujhe iska jawab nahi mila."
        print(f"🤖 Chhoti Don: {answer[:400]}")

        t_tts = time.time()
        spoke = self._say(answer)
        tts_s = time.time() - t_tts

        if self.cfg.log_timings:
            print(f"⏱  stt={stt_s:.2f}s  brain={brain_s:.2f}s  tts={tts_s:.2f}s"
                  f"  (spoken={spoke})")
        return True

    # ── speak, with optional barge-in (continuous mode) ──────────
    def _say(self, text: str) -> bool:
        """Speak text. In continuous mode, listen for barge-in and stop early.
        Falls back to printing if TTS is unavailable."""
        use_barge = self.cfg.barge_in and self.cfg.mode == "continuous_vad"
        on_speech = threading.Event()
        stop = threading.Event()
        listener = None
        if use_barge:
            listener = threading.Thread(
                target=self.mic.listen_for_barge_in, args=(stop, on_speech), daemon=True)
            listener.start()

        finished = self.tts.speak(text, interrupt=on_speech if use_barge else None)

        if listener is not None:
            stop.set()
            listener.join(timeout=0.5)
        if not finished and not on_speech.is_set():
            # TTS failed entirely -> ensure the user still gets the answer.
            print(f"[voice] (spoken output unavailable) {text}")
        if on_speech.is_set():
            print("[voice] barge-in: stopped speaking, listening…")
        return finished

    # ── interaction modes ────────────────────────────────────────
    def run(self) -> None:
        self.warmup()
        mode = self.cfg.mode
        print(f"\n=== Chhoti Don VOICE — mode: {mode} ===")
        try:
            if mode == "continuous_vad":
                self._run_continuous()
            else:
                self._run_push_to_talk()
        except KeyboardInterrupt:
            print("\n[voice] stopped.")

    def _run_push_to_talk(self) -> None:
        print("Press ENTER to talk (auto-stops on silence). Type 'q' + ENTER to quit.\n")
        while True:
            cmd = input("🎙️  [ENTER]=talk  q=quit > ").strip().lower()
            if cmd in {"q", "quit", "exit"}:
                break
            print("listening… (speak now)")
            audio = self.mic.record_utterance()
            self.handle_turn(audio)

    def _run_continuous(self) -> None:
        print("Listening continuously. Speak anytime. Ctrl-C to quit.\n")
        while True:
            audio = self.mic.record_utterance()
            self.handle_turn(audio)
