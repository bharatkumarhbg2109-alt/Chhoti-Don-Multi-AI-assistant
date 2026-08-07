"""
Chhoti Don - Hands Layer :: Terminal Hand

Run shell commands via subprocess with captured stdout/stderr, working
directory and environment support, timeouts, and background (streaming)
execution that can be cancelled.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission


class _BackgroundRun:
    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self.stdout: List[str] = []
        self.stderr: List[str] = []
        self._lock = threading.Lock()
        self._start = time.time()
        threading.Thread(target=self._pump, args=(proc.stdout, self.stdout), daemon=True).start()
        threading.Thread(target=self._pump, args=(proc.stderr, self.stderr), daemon=True).start()

    def _pump(self, stream, sink: List[str]) -> None:
        if stream is None:
            return
        try:
            for line in iter(stream.readline, ""):
                with self._lock:
                    sink.append(line)
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.proc.poll() is None,
                "returncode": self.proc.returncode,
                "stdout": "".join(self.stdout),
                "stderr": "".join(self.stderr),
                "elapsed_sec": round(time.time() - self._start, 2),
            }


class TerminalHand(BaseHand):
    name = "terminal"
    description = "Execute shell commands with captured output, timeouts and cancellation."

    def __init__(self) -> None:
        super().__init__()
        E = Permission.EXECUTE
        self.register("execute", self.execute_command, permission=E, doc="Run a command and capture output.")
        self.register("start", self.start, permission=E, doc="Start a background command (streaming).")
        self.register("read", self.read, permission=Permission.READ_ONLY, doc="Read a background command's output so far.")
        self.register("cancel", self.cancel, permission=E, doc="Cancel a running background command.")
        self.register("list_running", self.list_running, permission=Permission.READ_ONLY, doc="List background commands.")
        self._runs: Dict[str, _BackgroundRun] = {}

    def _env(self, env: Optional[Dict[str, str]]) -> Dict[str, str]:
        merged = dict(os.environ)
        if env:
            merged.update({str(k): str(v) for k, v in env.items()})
        return merged

    # ── Synchronous ──────────────────────────────────────────
    def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
        shell: bool = True,
    ) -> Dict[str, Any]:
        if not command or not str(command).strip():
            raise ValueError("command is required")
        try:
            proc = subprocess.run(
                command if shell else command.split(),
                cwd=os.path.expanduser(cwd) if cwd else None,
                env=self._env(env),
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "command": command,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": command,
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": (exc.stderr or "") + f"\n[timeout after {timeout}s]",
                "timed_out": True,
            }

    # ── Background / streaming ───────────────────────────────
    def start(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = True,
    ) -> Dict[str, Any]:
        if not command or not str(command).strip():
            raise ValueError("command is required")
        proc = subprocess.Popen(
            command if shell else command.split(),
            cwd=os.path.expanduser(cwd) if cwd else None,
            env=self._env(env),
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        run_id = uuid.uuid4().hex[:12]
        self._runs[run_id] = _BackgroundRun(proc)
        return {"run_id": run_id, "pid": proc.pid, "command": command}

    def read(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Unknown run_id '{run_id}'")
        snap = run.snapshot()
        snap["run_id"] = run_id
        return snap

    def cancel(self, run_id: str) -> Dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Unknown run_id '{run_id}'")
        if run.proc.poll() is None:
            try:
                run.proc.terminate()
                try:
                    run.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    run.proc.kill()
            except Exception:
                pass
        return {"run_id": run_id, "cancelled": True, "returncode": run.proc.returncode}

    def list_running(self) -> Dict[str, Any]:
        return {
            "runs": [
                {"run_id": rid, "running": r.proc.poll() is None, "pid": r.proc.pid}
                for rid, r in self._runs.items()
            ]
        }
