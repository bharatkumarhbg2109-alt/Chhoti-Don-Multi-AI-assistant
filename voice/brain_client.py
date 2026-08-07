"""Thin adapter to the EXISTING text brain. Voice never forks reasoning/tools.

Two backends (config.brain_mode):
  http       -> POST the transcript to the running Flask server's /api/chat, the
                exact endpoint the web UI uses. Reuses routing + safety policy +
                tools + _extract_response with zero duplication. (default)
  inprocess  -> import app._route_to_tool/_extract_response and call them in the
                same process (no server needed). Still the same brain functions.
"""

from __future__ import annotations

from typing import Optional

from .config import VoiceConfig


class BrainClient:
    def __init__(self, cfg: VoiceConfig):
        self.cfg = cfg
        self._inproc = None  # lazily-imported (chhoti_don, _route_to_tool, _extract_response)

    def health(self) -> tuple[bool, str]:
        """Report whether the chosen brain backend is reachable."""
        if self.cfg.brain_mode == "inprocess":
            try:
                self._ensure_inproc()
                return True, "inprocess brain ready"
            except Exception as exc:
                return False, f"inprocess import failed: {exc}"
        try:
            import requests
            r = requests.get(f"{self.cfg.brain_api_base}/api/health", timeout=5)
            return (r.status_code == 200), f"/api/health -> {r.status_code}"
        except Exception as exc:
            return False, (f"cannot reach {self.cfg.brain_api_base} "
                           f"({type(exc).__name__}). Start it with: python app.py")

    def ask(self, text: str) -> str:
        """Send transcript to the brain, return the clean text answer."""
        if self.cfg.brain_mode == "inprocess":
            return self._ask_inprocess(text)
        return self._ask_http(text)

    # ── HTTP backend (same entry point as the UI) ────────────────
    def _ask_http(self, text: str) -> str:
        import requests
        resp = requests.post(
            f"{self.cfg.brain_api_base}/api/chat",
            json={"message": text, "tool": self.cfg.brain_tool,
                  "conversation_id": None, "private": True, "persist_user": True},
            timeout=self.cfg.brain_timeout,
        )
        try:
            data = resp.json()
        except Exception:
            data = {}
        answer = (data.get("response") or data.get("message") or "").strip()
        if not answer and resp.status_code != 200:
            return f"(brain error {resp.status_code})"
        return answer

    # ── In-process backend (reuses app.py's own functions) ───────
    def _ensure_inproc(self):
        if self._inproc is None:
            # Importing app.py builds the ManagerAgent but does NOT start Flask
            # (app.run is under __main__), so these are the same functions the
            # HTTP route calls.
            from app import _route_to_tool, _extract_response, chhoti_don
            self._inproc = (chhoti_don, _route_to_tool, _extract_response)
        return self._inproc

    def _ask_inprocess(self, text: str) -> str:
        _chhoti, route, extract = self._ensure_inproc()
        result = route(text, self.cfg.brain_tool)
        return (extract(result) or "").strip()
