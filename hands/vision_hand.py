"""
Chhoti Don - Hands Layer :: Vision Hand

Thin wrapper that exposes the EXISTING configured vision model (llava, via
core.model_router / Ollama) through the Tool Manager. It does not replace or
reconfigure the vision model — it only routes image/screenshot/UI questions to
it and reuses the project's Ollama settings.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission

from core.config import Config
from core import model_router


class VisionHand(BaseHand):
    name = "vision"
    description = "Analyze images, screenshots and UI using the existing vision model (llava)."
    dependencies = ["requests"]

    def __init__(self) -> None:
        super().__init__()
        R = Permission.READ_ONLY
        self.register("image_analysis", self.image_analysis, permission=R, doc="Describe/analyze an image file or base64.")
        self.register("screenshot_analysis", self.screenshot_analysis, permission=R, doc="Capture the screen and analyze it.")
        self.register("ui_analysis", self.ui_analysis, permission=R, doc="Analyze on-screen UI layout & elements.")
        self.register("popup_detection", self.popup_detection, permission=R, doc="Detect dialogs/popups on screen.")
        self.register("ocr", self.ocr, permission=R, doc="Extract text from an image (if OCR available).")
        self.register("vision_status", self.vision_status, permission=R, doc="Report vision model availability.")

    # ── Model plumbing (reuses model_router / Ollama) ────────
    def vision_status(self) -> Dict[str, Any]:
        return model_router.check_model(model_router.VISION_MODEL)

    def _b64_from(self, image_path: str = "", image_b64: str = "") -> str:
        if image_b64:
            return image_b64
        if image_path:
            p = Path(image_path).expanduser()
            if not p.is_file():
                raise FileNotFoundError(f"Image not found: {p}")
            return base64.b64encode(p.read_bytes()).decode("ascii")
        raise ValueError("Provide 'image_path' or 'image_b64'.")

    def _llava(self, prompt: str, b64: str) -> Dict[str, Any]:
        import requests
        status = model_router.check_model(model_router.VISION_MODEL)
        if not status["available"]:
            return {"__envelope__": True, "status": "unavailable", "hand": self.name,
                    "action": "vision", "error": status["message"], "result": None}
        resp = requests.post(
            Config.OLLAMA_URL,
            json={"model": model_router.VISION_MODEL, "prompt": prompt,
                  "images": [b64], "stream": False},
            timeout=Config.OLLAMA_TIMEOUT,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
        return {"model": model_router.VISION_MODEL, "analysis": resp.json().get("response", "").strip()}

    def _grab_screen_b64(self) -> str:
        try:
            from PIL import ImageGrab
            import io
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception as exc:
            raise RuntimeError(f"Screen capture unavailable: {exc}")

    # ── Capabilities ─────────────────────────────────────────
    def image_analysis(self, image_path: str = "", image_b64: str = "", prompt: str = "Describe this image in detail.") -> Dict[str, Any]:
        return self._llava(prompt, self._b64_from(image_path, image_b64))

    def screenshot_analysis(self, prompt: str = "Describe what is shown on this screen.") -> Dict[str, Any]:
        return self._llava(prompt, self._grab_screen_b64())

    def ui_analysis(self, image_path: str = "", image_b64: str = "") -> Dict[str, Any]:
        prompt = ("Analyze this user interface. List the main UI elements (buttons, inputs, "
                  "menus), their layout, and any visible state or errors.")
        b64 = self._b64_from(image_path, image_b64) if (image_path or image_b64) else self._grab_screen_b64()
        return self._llava(prompt, b64)

    def popup_detection(self, image_path: str = "", image_b64: str = "") -> Dict[str, Any]:
        prompt = ("Is there a dialog box, popup, alert or modal window visible? "
                  "If yes, describe it and its buttons. If no, say 'No popup detected'.")
        b64 = self._b64_from(image_path, image_b64) if (image_path or image_b64) else self._grab_screen_b64()
        return self._llava(prompt, b64)

    def ocr(self, image_path: str = "", image_b64: str = "") -> Dict[str, Any]:
        # Prefer a real OCR engine if the project/environment already has one.
        try:
            import pytesseract  # type: ignore
            from PIL import Image
            import io
            if image_b64:
                img = Image.open(io.BytesIO(base64.b64decode(image_b64)))
            else:
                img = Image.open(Path(image_path).expanduser())
            return {"engine": "pytesseract", "text": pytesseract.image_to_string(img)}
        except ImportError:
            # Fall back to the vision model for text extraction.
            b64 = self._b64_from(image_path, image_b64)
            out = self._llava("Extract and return only the text visible in this image.", b64)
            if isinstance(out, dict) and "analysis" in out:
                out = {"engine": "llava", "text": out["analysis"]}
            return out
