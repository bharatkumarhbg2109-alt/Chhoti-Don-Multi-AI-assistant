"""Mic + STT self-diagnostic.  Run:  python -m voice.diagnose

Records a few seconds from the mic, shows a live level meter so you can SEE your
voice register, checks voice-activity detection, then does one real
record-utterance + transcription. Use this to confirm the mic works before
starting `python -m voice`.
"""

from __future__ import annotations

import sys
import time

import numpy as np

from .config import VoiceConfig


def _meter(rms: float, width: int = 40) -> str:
    # ~RMS 0..1500 mapped to a bar; speech usually pushes well past half.
    level = min(1.0, rms / 1500.0)
    filled = int(level * width)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {int(rms):5d}"


def run(seconds: float = 5.0) -> None:
    cfg = VoiceConfig()
    import sounddevice as sd
    import webrtcvad

    print("Default devices (input, output):", sd.default.device)
    try:
        di = sd.query_devices(kind="input")
        print(f"Mic: {di['name']}  native_sr={di['default_samplerate']}")
    except Exception as exc:
        print("Could not query mic:", exc)

    cr = cfg.capture_sample_rate
    fs = cfg.vad_frame_samples
    vad = webrtcvad.Vad(cfg.vad_aggressiveness)
    print(f"\nCapturing at {cr} Hz for {seconds:.0f}s — SPEAK NOW (say a Hinglish sentence)…\n")

    frames, rmss, voiced = [], [], 0
    n = int(seconds * 1000 / cfg.vad_frame_ms)
    peak = 0.0
    with sd.InputStream(samplerate=cr, channels=1, dtype="int16",
                        blocksize=fs, device=cfg.input_device) as stream:
        for i in range(n):
            data, _ = stream.read(fs)
            fr = np.asarray(data, dtype=np.int16).reshape(-1)
            if fr.shape[0] < fs:
                fr = np.pad(fr, (0, fs - fr.shape[0]))
            frames.append(fr)
            rms = float(np.sqrt(np.mean(fr.astype(np.float32) ** 2)))
            rmss.append(rms)
            peak = max(peak, rms)
            if vad.is_speech(fr.tobytes(), cr):
                voiced += 1
            if i % 3 == 0:  # ~10 updates/sec
                sys.stdout.write("\r" + _meter(rms))
                sys.stdout.flush()
    print("\n")
    print(f"mean RMS={np.mean(rmss):.1f}  peak RMS={peak:.1f}  voiced frames={voiced}/{n}")

    if peak < 30:
        print("\n⚠️  Mic level is almost silent. Check: Windows Settings > Privacy > "
              "Microphone (allow desktop apps), the mic isn't muted, and input volume is up.")
        return
    if voiced == 0:
        print("\n⚠️  Audio captured but VAD saw no speech. Try speaking louder/closer, or "
              "lower aggressiveness: set CHHOTI_DON_VOICE_VAD_AGGR=1")

    # One real transcription through the actual pipeline.
    print("\nTranscribing what you just said…")
    from .stt import SpeechToText
    from scipy.signal import resample_poly
    audio_i16 = np.concatenate(frames)
    audio16 = resample_poly(audio_i16.astype(np.float32) / 32768.0,
                            cfg.sample_rate, cr).astype(np.float32)
    stt = SpeechToText(cfg).load()
    t = time.time()
    text, lang, logprob = stt.transcribe(audio16)
    print(f"device={stt.device}  time={time.time() - t:.2f}s")
    print(f"TRANSCRIPT ({lang}, conf={logprob:.2f}): {text!r}")
    if text.strip():
        print("\n✅ Mic + STT working. Start voice mode: python -m voice")
    else:
        print("\n⚠️  Empty transcript. If the meter showed movement, try a bigger model: "
              "python -m voice --stt-model large-v3")


if __name__ == "__main__":
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    run(secs)
