"""Background process supervisor for LOCAL dev servers (Phase 5).

The Phase 4 executor runs a command to COMPLETION; a dev server never returns, so
it needs its own path: launch with ``subprocess.Popen`` (no wait), capture output
non-blocking on a reader thread, detect the local URL from the startup logs, and
track the process in a module-level registry so it can be inspected and — above
all — never orphaned.

ORPHAN SAFETY
-------------
Every launched process is registered in ``_servers``; an ``atexit`` hook calls
``stop_all`` so a server can never silently outlive the Python session. A
concurrent-server CAP bounds how many can run at once.

LOCAL ONLY
----------
There is no tunnel, no external network, and no deploy here — only localhost
processes and a pure-Python localhost socket health probe (no outbound HTTP).

The process-starter and the socket prober are BOTH injectable (context-local,
mirroring ``shell.use_executor``) so tests never spawn a real server or open a
real socket.
"""

from __future__ import annotations

import atexit
import contextvars
import itertools
import logging
import re
import socket
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

from .config import (HEALTH_CHECK_TIMEOUT_S, SERVER_LOG_CAP_LINES,
                     SERVER_MAX_CONCURRENT, SERVER_STOP_GRACE_S,
                     SERVER_URL_DETECT_TIMEOUT_S)

logger = logging.getLogger("chhoti.coding_agent.server")

# Local URL / port hints emitted by common dev servers on startup.
_URL_RE = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::(\d{2,5}))?(?:/\S*)?", re.I)
_PORT_HINT_RE = re.compile(
    r"(?:running on|listening on|listening at|local:|on port|port)\D{0,8}(\d{2,5})", re.I)


def _detect_url(line: str) -> Optional[str]:
    """Return a normalized http://127.0.0.1:PORT URL if the line advertises one."""
    m = _URL_RE.search(line)
    if m:
        url = m.group(0).rstrip(".,)")
        # Normalize 0.0.0.0 -> 127.0.0.1 for a usable local URL.
        return url.replace("0.0.0.0", "127.0.0.1")
    m = _PORT_HINT_RE.search(line)
    if m:
        return f"http://127.0.0.1:{m.group(1)}"
    return None


def _port_of(url: Optional[str]) -> Optional[int]:
    if not url:
        return None
    m = re.search(r":(\d{2,5})", url)
    return int(m.group(1)) if m else None


@dataclass
class _Server:
    id: str
    command: str
    argv: List[str]
    cwd: str
    tier: str
    proc: Any
    log: Deque[str]
    lock: threading.Lock
    url_event: threading.Event
    reader: Optional[threading.Thread] = None
    detected_url: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    stopped: bool = False


_servers: Dict[str, _Server] = {}
_registry_lock = threading.Lock()
_id_counter = itertools.count(1)


# ── injectable starter + socket prober (context-local, mirrors shell) ─────────
_starter: "contextvars.ContextVar[Optional[Callable[..., Any]]]" = \
    contextvars.ContextVar("server_starter", default=None)
_prober: "contextvars.ContextVar[Optional[Callable[..., bool]]]" = \
    contextvars.ContextVar("server_prober", default=None)


class use_starter:
    """Install a fake process-starter for the current context (tests)."""

    def __init__(self, fn: Callable[..., Any]):
        self._fn = fn

    def __enter__(self):
        self._token = _starter.set(self._fn)
        return self

    def __exit__(self, *exc):
        _starter.reset(self._token)
        return False


class use_prober:
    """Install a fake socket prober for the current context (tests)."""

    def __init__(self, fn: Callable[..., bool]):
        self._fn = fn

    def __enter__(self):
        self._token = _prober.set(self._fn)
        return self

    def __exit__(self, *exc):
        _prober.reset(self._token)
        return False


def _default_starter(argv: List[str], cwd: str) -> Any:
    """Launch a long-lived process with shell=False, cwd pinned, merged output."""
    return subprocess.Popen(
        argv, cwd=cwd, shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )


def _default_probe(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def health_check(port: Optional[int], host: str = "127.0.0.1",
                 timeout: Optional[float] = None) -> bool:
    """Pure-Python localhost socket probe: is something accepting on host:port?"""
    if not port:
        return False
    fn = _prober.get() or _default_probe
    try:
        return bool(fn(host, int(port), timeout or HEALTH_CHECK_TIMEOUT_S))
    except Exception:
        return False


# ── reader thread ─────────────────────────────────────────────────────────────
def _reader(server: _Server) -> None:
    """Drain the process's merged output into the bounded log and detect the URL."""
    try:
        for line in iter(server.proc.stdout.readline, ""):
            if line == "":
                break
            with server.lock:
                server.log.append(line.rstrip("\n"))
            if server.detected_url is None:
                url = _detect_url(line)
                if url:
                    server.detected_url = url
                    server.url_event.set()
    except Exception as exc:  # pragma: no cover - defensive (stream closed on stop)
        logger.debug("[server] reader ended for %s: %s", server.id, exc)
    finally:
        # Stream ended (process exited / stopped) -> unblock any URL waiter.
        server.url_event.set()


def _alive(server: _Server) -> bool:
    if server.stopped:
        return False
    try:
        return server.proc.poll() is None
    except Exception:
        return False


# ── public API (raw; gating happens in coding_agent.guarded) ──────────────────
def start(command: str, argv: List[str], cwd: str, tier: str = "MEDIUM",
          url_timeout: Optional[float] = None) -> Dict[str, Any]:
    """Launch ``argv`` as a background server, register it, and wait briefly for a
    URL to appear in its logs. Never waits for the process to exit."""
    with _registry_lock:
        live = sum(1 for s in _servers.values() if not s.stopped)
        if live >= SERVER_MAX_CONCURRENT:
            return {"status": "error", "marker": "SERVER_CAP_REACHED",
                    "message": f"Concurrent server cap reached ({SERVER_MAX_CONCURRENT}). "
                               "Stop one with serve_stop first.",
                    "running": _running_locked()}

    starter = _starter.get() or _default_starter
    try:
        proc = starter(argv, cwd)
    except FileNotFoundError:
        return {"status": "error", "marker": "START_FAILED",
                "message": f"command not found: {argv[0] if argv else command}"}
    except Exception as exc:
        return {"status": "error", "marker": "START_FAILED", "message": str(exc)}

    sid = f"srv-{next(_id_counter)}"
    server = _Server(
        id=sid, command=command, argv=list(argv), cwd=cwd, tier=tier, proc=proc,
        log=deque(maxlen=SERVER_LOG_CAP_LINES), lock=threading.Lock(),
        url_event=threading.Event(),
    )
    server.reader = threading.Thread(target=_reader, args=(server,),
                                     name=f"srv-reader-{sid}", daemon=True)
    server.reader.start()
    with _registry_lock:
        _servers[sid] = server

    timeout = SERVER_URL_DETECT_TIMEOUT_S if url_timeout is None else url_timeout
    server.url_event.wait(timeout)

    alive = _alive(server)
    logger.info("[server] started id=%s pid=%s alive=%s url=%s cmd=%r",
                sid, getattr(proc, "pid", None), alive, server.detected_url, command)
    msg = ("Server started." if server.detected_url
           else "Server started, no URL detected yet (check serve_logs/serve_status).")
    if not alive:
        msg = "Process exited immediately after launch (check serve_logs)."
    return {"status": "success", "action": "serve_start", "id": sid,
            "pid": getattr(proc, "pid", None), "command": command, "tier": tier,
            "detected_url": server.detected_url, "alive": alive, "message": msg}


def _log_tail_locked(server: _Server, tail_n: int) -> List[str]:
    with server.lock:
        lines = list(server.log)
    return lines[-tail_n:] if tail_n and tail_n > 0 else lines


def status(server_id: str, probe: bool = True) -> Dict[str, Any]:
    server = _servers.get(server_id)
    if server is None:
        return {"status": "error", "marker": "SERVER_NOT_FOUND", "id": server_id}
    alive = _alive(server)
    port = _port_of(server.detected_url)
    healthy = health_check(port) if (probe and alive and port) else False
    return {"status": "success", "id": server_id, "command": server.command,
            "pid": getattr(server.proc, "pid", None), "alive": alive,
            "detected_url": server.detected_url, "port": port, "healthy": healthy,
            "log_tail": _log_tail_locked(server, 20)}


def logs(server_id: str, tail_n: int = 50) -> Dict[str, Any]:
    server = _servers.get(server_id)
    if server is None:
        return {"status": "error", "marker": "SERVER_NOT_FOUND", "id": server_id}
    return {"status": "success", "id": server_id,
            "lines": _log_tail_locked(server, tail_n)}


def stop(server_id: str) -> Dict[str, Any]:
    server = _servers.get(server_id)
    if server is None:
        return {"status": "error", "marker": "SERVER_NOT_FOUND", "id": server_id}
    _terminate(server)
    with _registry_lock:
        _servers.pop(server_id, None)
    logger.info("[server] stopped id=%s", server_id)
    return {"status": "success", "id": server_id, "stopped": True}


def _terminate(server: _Server) -> None:
    """Graceful terminate → wait → hard kill fallback → reap."""
    server.stopped = True
    proc = server.proc
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=SERVER_STOP_GRACE_S)
            except Exception:  # TimeoutExpired (or fake) -> force kill
                try:
                    proc.kill()
                    proc.wait(timeout=SERVER_STOP_GRACE_S)
                except Exception:
                    pass
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("[server] terminate error id=%s: %s", server.id, exc)
    # Close the pipe so the reader thread unblocks/ends.
    try:
        if getattr(proc, "stdout", None) is not None:
            proc.stdout.close()
    except Exception:
        pass
    if server.reader is not None:
        server.reader.join(timeout=2)


def _running_locked() -> List[Dict[str, Any]]:
    return [{"id": s.id, "command": s.command, "detected_url": s.detected_url,
             "pid": getattr(s.proc, "pid", None)}
            for s in _servers.values() if not s.stopped]


def list_running() -> List[Dict[str, Any]]:
    with _registry_lock:
        return _running_locked()


def stop_all() -> Dict[str, Any]:
    """Stop every tracked server (session cleanup / atexit)."""
    with _registry_lock:
        ids = list(_servers.keys())
    stopped = []
    for sid in ids:
        try:
            stop(sid)
            stopped.append(sid)
        except Exception:  # pragma: no cover - defensive
            pass
    return {"status": "success", "stopped": stopped, "count": len(stopped)}


# Orphan safety: never let a launched server outlive the Python session.
atexit.register(stop_all)
