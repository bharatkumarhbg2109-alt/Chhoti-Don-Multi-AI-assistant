"""CLI entry point for Chhoti Don VOICE mode (opt-in; text mode is untouched).

    python -m voice                         # push-to-talk, default settings
    python -m voice --continuous            # always-listening VAD mode
    python -m voice --stt-model large-v3    # better Hinglish accuracy
    python -m voice --brain-mode inprocess  # no server; import the brain directly
    python -m voice --list-devices          # show mics/speakers and exit
"""

from __future__ import annotations

import argparse
import dataclasses

from .config import VoiceConfig
from .orchestrator import VoiceAssistant


def _list_devices() -> None:
    import sounddevice as sd
    print(sd.query_devices())


def build_config(args) -> VoiceConfig:
    cfg = VoiceConfig()
    overrides = {}
    if args.mode:
        overrides["mode"] = args.mode
    if args.continuous:
        overrides["mode"] = "continuous_vad"
    if args.stt_model:
        overrides["stt_model_size"] = args.stt_model
    if args.device:
        overrides["stt_device"] = args.device
    if args.compute:
        overrides["stt_compute_type"] = args.compute
    if args.language:
        overrides["stt_language"] = args.language
    if args.tts_model:
        overrides["tts_voice_model"] = args.tts_model
    if args.brain_mode:
        overrides["brain_mode"] = args.brain_mode
    if args.brain_api:
        overrides["brain_api_base"] = args.brain_api.rstrip("/")
    if args.no_barge_in:
        overrides["barge_in"] = False
    return dataclasses.replace(cfg, **overrides) if overrides else cfg


def main() -> None:
    p = argparse.ArgumentParser(prog="voice", description="Chhoti Don voice mode")
    p.add_argument("--mode", choices=["push_to_talk", "continuous_vad"])
    p.add_argument("--continuous", action="store_true", help="shortcut for continuous_vad")
    p.add_argument("--stt-model", help="faster-whisper size: small (default) / large-v3 / …")
    p.add_argument("--device", help="STT device: cuda (default) / cpu")
    p.add_argument("--compute", help="STT compute_type: float16 / int8 / …")
    p.add_argument("--language", help="STT language: auto (default) / hi / en")
    p.add_argument("--tts-model", help="path to a Piper .onnx voice")
    p.add_argument("--brain-mode", choices=["http", "inprocess"])
    p.add_argument("--brain-api", help="base URL for http brain mode")
    p.add_argument("--no-barge-in", action="store_true")
    p.add_argument("--list-devices", action="store_true")
    args = p.parse_args()

    if args.list_devices:
        _list_devices()
        return

    cfg = build_config(args)
    VoiceAssistant(cfg).run()


if __name__ == "__main__":
    main()
