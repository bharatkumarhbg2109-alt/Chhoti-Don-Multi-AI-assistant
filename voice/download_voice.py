"""Download a Piper ONNX voice (model + config) into voice/models/.

Zero API keys — fetches from the public HuggingFace rhasspy/piper-voices repo.

    python -m voice.download_voice                      # default en_US-lessac-medium
    python -m voice.download_voice en_US-amy-low        # smaller/faster
    python -m voice.download_voice hi_IN-<voice>-medium # if a Hindi voice exists

Voice-name format: <lang>_<REGION>-<name>-<quality>, e.g. en_US-lessac-medium.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .config import MODELS_DIR, DEFAULT_VOICE_NAME

_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
_NAME_RE = re.compile(r"^([a-z]{2,3})_([A-Z]{2})-(.+)-(x_low|low|medium|high)$")


def _paths_for(voice_name: str):
    m = _NAME_RE.match(voice_name)
    if not m:
        raise ValueError(
            f"Bad voice name '{voice_name}'. Expected <lang>_<REGION>-<name>-<quality>, "
            f"e.g. en_US-lessac-medium.")
    lang, region, name, quality = m.groups()
    subdir = f"{lang}/{lang}_{region}/{name}/{quality}"
    onnx_url = f"{_HF_BASE}/{subdir}/{voice_name}.onnx"
    json_url = f"{_HF_BASE}/{subdir}/{voice_name}.onnx.json"
    return onnx_url, json_url


def _download(url: str, dest: Path) -> None:
    import requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        got = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
                got += len(chunk)
        print(f"  saved {dest.name} ({got} bytes"
              + (f" / {total}" if total else "") + ")")


def download_voice(voice_name: str = DEFAULT_VOICE_NAME) -> Path:
    onnx_url, json_url = _paths_for(voice_name)
    onnx_dest = MODELS_DIR / f"{voice_name}.onnx"
    json_dest = MODELS_DIR / f"{voice_name}.onnx.json"
    if onnx_dest.exists() and json_dest.exists():
        print(f"[voice] '{voice_name}' already present at {onnx_dest}")
        return onnx_dest
    print(f"[voice] downloading Piper voice '{voice_name}' …")
    _download(onnx_url, onnx_dest)
    _download(json_url, json_dest)
    print(f"[voice] done -> {onnx_dest}")
    return onnx_dest


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VOICE_NAME
    try:
        download_voice(name)
    except Exception as exc:
        print(f"[voice] download failed: {type(exc).__name__}: {exc}")
        sys.exit(1)
