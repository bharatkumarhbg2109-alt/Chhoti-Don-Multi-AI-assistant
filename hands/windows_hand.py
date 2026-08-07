"""
Chhoti Don - Hands Layer :: Windows Hand

Launch/close apps, control windows, inspect processes and read system metrics
using subprocess, psutil and pywin32. Killing processes / closing apps is
destructive and requires confirmation.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission

# Friendly aliases → launch spec. GUI apps prefer os.startfile / shell resolution.
_APP_ALIASES = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file_explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "chrome": "chrome",
    "vscode": "code",
    "vs_code": "code",
    "code": "code",
}


class WindowsHand(BaseHand):
    name = "windows"
    description = "Launch/close apps, control windows, inspect processes and read system metrics."
    dependencies = ["psutil"]

    def __init__(self) -> None:
        super().__init__()
        R, E, D = Permission.READ_ONLY, Permission.EXECUTE, Permission.DANGEROUS
        self.register("open_application", self.open_application, permission=E, doc="Launch an application by name/alias/path.")
        self.register("close_application", self.close_application, permission=D, destructive=True, doc="Close all processes of an app by name.")
        self.register("restart_application", self.restart_application, permission=D, destructive=True, doc="Close then relaunch an app.")
        self.register("open_chrome", lambda **k: self.open_application(name="chrome", **k), permission=E, doc="Open Chrome.")
        self.register("open_vscode", lambda **k: self.open_application(name="code", **k), permission=E, doc="Open VS Code.")
        self.register("open_file_explorer", lambda **k: self.open_application(name="explorer", **k), permission=E, doc="Open File Explorer.")
        self.register("open_calculator", lambda **k: self.open_application(name="calc", **k), permission=E, doc="Open Calculator.")
        self.register("open_notepad", lambda **k: self.open_application(name="notepad", **k), permission=E, doc="Open Notepad.")
        self.register("window_maximize", lambda **k: self._window(k.get("title"), "max"), permission=E, doc="Maximize a window by title.")
        self.register("window_minimize", lambda **k: self._window(k.get("title"), "min"), permission=E, doc="Minimize a window by title.")
        self.register("bring_window_to_front", lambda **k: self._window(k.get("title"), "front"), permission=E, doc="Bring a window to the foreground.")
        self.register("list_processes", self.list_processes, permission=R, doc="List running processes.")
        self.register("kill_process", self.kill_process, permission=D, destructive=True, doc="Kill a process by pid or name.")
        self.register("system_info", self.system_info, permission=R, doc="OS / machine information.")
        self.register("battery_status", self.battery_status, permission=R, doc="Battery percentage & plugged state.")
        self.register("cpu_usage", self.cpu_usage, permission=R, doc="CPU utilisation.")
        self.register("ram_usage", self.ram_usage, permission=R, doc="Memory utilisation.")
        self.register("disk_usage", self.disk_usage, permission=R, doc="Disk utilisation.")

    def _check_available(self) -> bool:
        # The hand is meaningful on Windows; process/system metrics need psutil.
        if not self.missing_dependencies() == []:
            return False
        return sys.platform.startswith("win")

    # ── Applications ─────────────────────────────────────────
    def open_application(self, name: str = "", path: str = "", args: Optional[List[str]] = None) -> Dict[str, Any]:
        target = path or _APP_ALIASES.get((name or "").lower(), name)
        if not target:
            raise ValueError("Provide an application 'name' or 'path'.")
        args = args or []
        try:
            # Resolve on PATH when possible (chrome/code), else launch directly.
            resolved = shutil.which(target) or target
            proc = subprocess.Popen([resolved, *args])
            return {"launched": target, "resolved": resolved, "pid": proc.pid}
        except FileNotFoundError:
            # Fall back to the shell/OS association (handles GUI apps & URLs).
            try:
                if sys.platform.startswith("win"):
                    os.startfile(target)  # type: ignore[attr-defined]
                    return {"launched": target, "pid": None, "via": "os.startfile"}
            except Exception:
                pass
            raise FileNotFoundError(f"Application not found: {target}")

    def _find_procs_by_name(self, name: str):
        import psutil
        name_l = name.lower()
        out = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pname = (p.info.get("name") or "").lower()
                if name_l == pname or name_l == os.path.splitext(pname)[0] or name_l in pname:
                    out.append(p)
            except Exception:
                continue
        return out

    def close_application(self, name: str) -> Dict[str, Any]:
        procs = self._find_procs_by_name(name)
        killed = []
        for p in procs:
            try:
                p.terminate()
                killed.append(p.pid)
            except Exception:
                continue
        return {"application": name, "terminated_pids": killed, "count": len(killed)}

    def restart_application(self, name: str = "", path: str = "", args: Optional[List[str]] = None) -> Dict[str, Any]:
        closed = self.close_application(name or path)
        time.sleep(1.0)
        launched = self.open_application(name=name, path=path, args=args)
        return {"restarted": name or path, "closed": closed, "launched": launched}

    # ── Windows (via pywin32) ────────────────────────────────
    def _window(self, title: Optional[str], mode: str) -> Dict[str, Any]:
        if not title:
            raise ValueError("A window 'title' (substring) is required.")
        try:
            import win32con
            import win32gui
        except Exception:
            return {"__envelope__": True, "status": "unavailable", "hand": self.name,
                    "action": f"window_{mode}", "error": "pywin32 (win32gui) not available.",
                    "result": None}

        matches: List[int] = []

        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t and title.lower() in t.lower():
                    matches.append(hwnd)

        win32gui.EnumWindows(_cb, None)
        if not matches:
            raise LookupError(f"No visible window matching '{title}'.")
        hwnd = matches[0]
        if mode == "max":
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        elif mode == "min":
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        elif mode == "front":
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        return {"window": win32gui.GetWindowText(hwnd), "hwnd": hwnd, "mode": mode}

    # ── Processes ────────────────────────────────────────────
    def list_processes(self, limit: int = 50, sort_by: str = "memory") -> Dict[str, Any]:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "username"]):
            try:
                info = p.info
                info["memory_mb"] = round(p.memory_info().rss / (1024 * 1024), 1)
                procs.append(info)
            except Exception:
                continue
        key = "memory_mb" if sort_by == "memory" else "pid"
        procs.sort(key=lambda x: x.get(key, 0), reverse=(sort_by == "memory"))
        return {"count": len(procs), "processes": procs[:limit]}

    def kill_process(self, pid: Optional[int] = None, name: str = "") -> Dict[str, Any]:
        import psutil
        if pid is not None:
            p = psutil.Process(int(pid))
            p.terminate()
            return {"killed_pid": int(pid), "name": p.name()}
        if name:
            procs = self._find_procs_by_name(name)
            killed = []
            for p in procs:
                try:
                    p.terminate()
                    killed.append(p.pid)
                except Exception:
                    continue
            return {"killed_by_name": name, "pids": killed}
        raise ValueError("Provide a 'pid' or a process 'name'.")

    # ── System metrics ───────────────────────────────────────
    def system_info(self) -> Dict[str, Any]:
        uname = platform.uname()
        return {
            "system": uname.system,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "node": uname.node,
            "python": platform.python_version(),
        }

    def battery_status(self) -> Dict[str, Any]:
        import psutil
        batt = getattr(psutil, "sensors_battery", lambda: None)()
        if batt is None:
            return {"present": False, "message": "No battery detected (desktop or unsupported)."}
        return {"present": True, "percent": batt.percent, "plugged": batt.power_plugged,
                "secs_left": None if batt.secsleft in (-1, -2) else batt.secsleft}

    def cpu_usage(self, interval: float = 0.5) -> Dict[str, Any]:
        import psutil
        return {"percent": psutil.cpu_percent(interval=interval), "cores": psutil.cpu_count(logical=True)}

    def ram_usage(self) -> Dict[str, Any]:
        import psutil
        vm = psutil.virtual_memory()
        return {"percent": vm.percent, "total_gb": round(vm.total / 1e9, 2),
                "used_gb": round(vm.used / 1e9, 2), "available_gb": round(vm.available / 1e9, 2)}

    def disk_usage(self, path: str = "C:\\" if sys.platform.startswith("win") else "/") -> Dict[str, Any]:
        # shutil.disk_usage (stdlib) is more portable than psutil on some Windows builds.
        du = shutil.disk_usage(path)
        percent = round(du.used / du.total * 100, 1) if du.total else 0.0
        return {"path": path, "percent": percent, "total_gb": round(du.total / 1e9, 2),
                "used_gb": round(du.used / 1e9, 2), "free_gb": round(du.free / 1e9, 2)}
