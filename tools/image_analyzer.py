"""Chhoti Don - Local Vision Tool (image understanding via Ollama).

Zero-cost, no API keys: sends an image + prompt to a local vision-capable Ollama
model (default Config.VISION_MODEL = qwen3.5:latest, which has native vision) and
returns a text description. Accepts a local file path or a raw base64 string —
never fetches remote URLs (stays offline; avoids SSRF).

Returns a status dict with clear markers instead of raising, so callers/LLMs can
handle failures gracefully:
    {"status":"success","description":..., "model":..., "image":...}
    {"status":"error","marker":"IMAGE_NOT_FOUND"|"BAD_IMAGE"|"VISION_FAILED"|..., ...}
"""

from __future__ import annotations

import base64
import io
import os
from typing import Any, Dict, Optional, Tuple

import requests

from core.config import Config
from core.brain_registry import HINGLISH_STYLE

# Cap the longest side so large photos stay fast and fit 8 GB VRAM comfortably.
_MAX_DIM = 1280
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
_DEFAULT_PROMPT = (
    "Describe this image in detail. List the key objects, any visible text, "
    "and the main colors. Be concise and accurate."
)


def _downscale_to_b64(raw: bytes) -> str:
    """Validate/normalise image bytes -> resized JPEG base64 (uses Pillow if present)."""
    try:
        from PIL import Image
    except ImportError:
        # Pillow missing: send the original bytes as-is (Ollama still accepts them).
        return base64.b64encode(raw).decode("ascii")
    with Image.open(io.BytesIO(raw)) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > _MAX_DIM:
            scale = _MAX_DIM / float(max(w, h))
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=88)
        return base64.b64encode(out.getvalue()).decode("ascii")


def _resolve_image_b64(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict]]:
    """Return (base64, None) or (None, error_dict)."""
    # 1) explicit base64
    b64 = data.get("image_base64") or data.get("base64")
    if b64:
        try:
            return _downscale_to_b64(base64.b64decode(b64)), None
        except Exception as exc:
            return None, {"status": "error", "marker": "BAD_IMAGE", "message": str(exc)[:160]}
    # 2) local file path
    path = data.get("image_path") or data.get("image") or data.get("path")
    if not path or not isinstance(path, str):
        return None, {"status": "error", "marker": "NO_IMAGE",
                      "message": "Provide 'image_path' (local file) or 'image_base64'."}
    if path.lower().startswith(("http://", "https://")):
        return None, {"status": "error", "marker": "REMOTE_URL_UNSUPPORTED",
                      "message": "Only local files are supported. Download the image first."}
    if not os.path.isfile(path):
        return None, {"status": "error", "marker": "IMAGE_NOT_FOUND", "image": path}
    try:
        with open(path, "rb") as f:
            return _downscale_to_b64(f.read()), None
    except Exception as exc:
        return None, {"status": "error", "marker": "BAD_IMAGE", "image": path,
                      "message": str(exc)[:160]}


def analyze_image(input_data: Any) -> Dict[str, Any]:
    """Analyze an image with a local vision model and return a text description."""
    data = input_data if isinstance(input_data, dict) else {"image": str(input_data)}
    prompt = str(data.get("prompt") or _DEFAULT_PROMPT).strip()
    model = data.get("model") or Config.VISION_MODEL

    b64, err = _resolve_image_b64(data)
    if err:
        return err

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [b64],
        "system": HINGLISH_STYLE.strip(),  # describe the image in casual Hinglish
        "stream": False,
        "think": False,  # qwen3.x: keep the visible answer clean/fast
        "options": {"temperature": 0.2, "num_predict": 1024},
    }
    try:
        resp = requests.post(Config.OLLAMA_URL, json=payload, timeout=Config.OLLAMA_TIMEOUT)
    except requests.exceptions.ConnectionError:
        return {"status": "error", "marker": "OLLAMA_OFFLINE",
                "message": "Ollama not reachable. Run 'ollama serve'."}
    except requests.exceptions.Timeout:
        return {"status": "error", "marker": "VISION_TIMEOUT",
                "message": f"Vision model timed out after {Config.OLLAMA_TIMEOUT}s."}
    except Exception as exc:
        return {"status": "error", "marker": "VISION_FAILED", "message": str(exc)[:160]}

    if resp.status_code != 200:
        # Most common cause: the model isn't installed or lacks vision.
        return {"status": "error", "marker": "VISION_FAILED",
                "message": f"Ollama HTTP {resp.status_code}: {resp.text[:200]}",
                "hint": f"Is '{model}' installed and vision-capable? `ollama pull {model}`"}

    description = (resp.json().get("response") or "").strip()
    if not description:
        return {"status": "error", "marker": "NO_DESCRIPTION",
                "message": "Vision model returned no text."}
    return {
        "status": "success",
        "description": description,
        "model": model,
        "image": data.get("image_path") or data.get("image") or "base64",
    }
