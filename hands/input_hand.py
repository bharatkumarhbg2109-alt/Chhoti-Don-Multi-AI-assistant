"""
Chhoti Don - Hands Layer :: Keyboard & Mouse Hand

Mouse and keyboard automation via pyautogui (primary) or pynput (fallback).

Safe Automation Mode (default ON) makes every action a no-op "simulation" that
is logged but not performed — so nothing moves the cursor or types unexpectedly.
Turn it off explicitly (set_safe_mode(enabled=False)) to perform real input.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission


def _has(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


class InputHand(BaseHand):
    name = "input"
    description = "Mouse & keyboard automation (safe mode on by default)."

    def __init__(self) -> None:
        super().__init__()
        # Safe mode default from env; can be toggled at runtime.
        self.safe_mode = os.environ.get("CHHOTI_DON_HANDS_SAFE_MODE", "1") not in ("0", "false", "False")

        E = Permission.EXECUTE
        self.register("set_safe_mode", self.set_safe_mode, permission=Permission.WRITE, doc="Enable/disable Safe Automation Mode.")
        self.register("mouse_click", lambda **k: self._mouse("click", **k), permission=E, doc="Left click (optionally at x,y).")
        self.register("double_click", lambda **k: self._mouse("doubleClick", **k), permission=E, doc="Double click.")
        self.register("right_click", lambda **k: self._mouse("rightClick", **k), permission=E, doc="Right click.")
        self.register("move_mouse", self.move_mouse, permission=E, doc="Move the cursor to x,y.")
        self.register("drag_mouse", self.drag_mouse, permission=E, doc="Drag from current position to x,y.")
        self.register("scroll", self.scroll, permission=E, doc="Scroll vertically by amount.")
        self.register("type_text", self.type_text, permission=E, doc="Type a string.")
        self.register("hotkey", self.hotkey, permission=E, doc="Press a key combination, e.g. ['ctrl','c'].")
        self.register("copy", lambda **k: self.hotkey(keys=["ctrl", "c"]), permission=E, doc="Copy (Ctrl+C).")
        self.register("paste", lambda **k: self.hotkey(keys=["ctrl", "v"]), permission=E, doc="Paste (Ctrl+V).")
        self.register("select_all", lambda **k: self.hotkey(keys=["ctrl", "a"]), permission=E, doc="Select all (Ctrl+A).")
        self.register("press_enter", lambda **k: self.press(key="enter"), permission=E, doc="Press Enter.")
        self.register("press_escape", lambda **k: self.press(key="esc"), permission=E, doc="Press Escape.")
        self.register("press_tab", lambda **k: self.press(key="tab"), permission=E, doc="Press Tab.")
        self.register("press_arrow", self.press_arrow, permission=E, doc="Press an arrow key (up/down/left/right).")
        self.register("press", self.press, permission=E, doc="Press a named key.")

    def _check_available(self) -> bool:
        return _has("pyautogui") or _has("pynput")

    def missing_dependencies(self) -> List[str]:
        return [] if self._check_available() else ["pyautogui"]

    def _pg(self):
        import pyautogui
        pyautogui.FAILSAFE = True
        return pyautogui

    def _guard(self, action: str, params: Dict) -> Optional[Dict[str, Any]]:
        """Return a simulation envelope when in safe mode, else None to proceed."""
        if self.safe_mode:
            return {"simulated": True, "safe_mode": True, "action": action, "params": params,
                    "note": "Safe Automation Mode is ON — action logged but not performed."}
        return None

    # ── Config ───────────────────────────────────────────────
    def set_safe_mode(self, enabled: bool = True) -> Dict[str, Any]:
        self.safe_mode = bool(enabled)
        return {"safe_mode": self.safe_mode}

    # ── Mouse ────────────────────────────────────────────────
    def _mouse(self, kind: str, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        sim = self._guard(kind, {"x": x, "y": y})
        if sim:
            return sim
        pg = self._pg()
        getattr(pg, kind)(x=x, y=y) if x is not None and y is not None else getattr(pg, kind)()
        return {"performed": kind, "x": x, "y": y}

    def move_mouse(self, x: int, y: int, duration: float = 0.2) -> Dict[str, Any]:
        sim = self._guard("move", {"x": x, "y": y})
        if sim:
            return sim
        self._pg().moveTo(x, y, duration=duration)
        return {"moved_to": [x, y]}

    def drag_mouse(self, x: int, y: int, duration: float = 0.3, button: str = "left") -> Dict[str, Any]:
        sim = self._guard("drag", {"x": x, "y": y})
        if sim:
            return sim
        self._pg().dragTo(x, y, duration=duration, button=button)
        return {"dragged_to": [x, y]}

    def scroll(self, amount: int = -300, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        sim = self._guard("scroll", {"amount": amount})
        if sim:
            return sim
        self._pg().scroll(amount, x=x, y=y)
        return {"scrolled": amount}

    # ── Keyboard ─────────────────────────────────────────────
    def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        sim = self._guard("type", {"text": text})
        if sim:
            return sim
        self._pg().typewrite(text, interval=interval)
        return {"typed": len(text)}

    def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        if not keys:
            raise ValueError("keys list is required, e.g. ['ctrl','c'].")
        sim = self._guard("hotkey", {"keys": keys})
        if sim:
            return sim
        self._pg().hotkey(*keys)
        return {"hotkey": keys}

    def press(self, key: str) -> Dict[str, Any]:
        sim = self._guard("press", {"key": key})
        if sim:
            return sim
        self._pg().press(key)
        return {"pressed": key}

    def press_arrow(self, direction: str = "down") -> Dict[str, Any]:
        mapping = {"up": "up", "down": "down", "left": "left", "right": "right"}
        key = mapping.get(direction.lower())
        if not key:
            raise ValueError("direction must be up/down/left/right")
        return self.press(key=key)
