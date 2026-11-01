"""Chhoti Don - Coding Agent Interactive Session Manager

Enables asynchronous, non-blocking autonomous build runs over HTTP/SSE with
Human-in-the-Loop (HITL) checkpoints:
  - Plan Approval: Pauses after the plan is generated so the user can inspect
    and approve the list of intended file operations.
  - Action Confirmation: Pauses for dangerous actions (HIGH delete, out-of-plan
    commands, public deploys) presenting unified diffs / command details.
  - Fail-safe: Timeouts default to DENY/REJECT; sessions are bounded and reaped.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generator, List, Optional

from . import guarded, hitl
from .agent import CodingAgent, is_build_request
from .config import HITL_CONFIRM_TIMEOUT_S

logger = logging.getLogger("chhoti.coding_agent.interactive")

# Session storage
_sessions: Dict[str, "InteractiveBuildSession"] = {}
_sessions_lock = threading.Lock()
SESSION_TTL_S = 3600  # 1 hour


class InteractiveBuildSession:
    """Coordinates a background CodingAgent build run with HITL checkpoints."""

    def __init__(self, session_id: str, task: str, confirm_timeout: float = None):
        self.session_id = session_id
        self.task = task
        self.confirm_timeout = confirm_timeout if confirm_timeout is not None else HITL_CONFIRM_TIMEOUT_S
        self.cond = threading.Condition()
        self.state: str = "running"  # running | pending_plan | pending_confirmation | done | error | aborted
        self.plan: Optional[List[Dict[str, Any]]] = None
        self.pending_proposal: Optional[Any] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._decision: Optional[bool] = None
        self.thread: Optional[threading.Thread] = None
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.events: List[Dict[str, Any]] = []
        self._subscribers: List[queue.Queue] = []
        self._events_lock = threading.Lock()

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._events_lock:
            event_id = len(self.events) + 1
            event = {
                "id": event_id,
                "event": event_type,
                "timestamp": time.time(),
                "session_id": self.session_id,
                "state": self.state,
                **(data or {}),
            }
            self.events.append(event)
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass
                except Exception:
                    dead.append(q)
            for q in dead:
                if q in self._subscribers:
                    self._subscribers.remove(q)
            return event

    def subscribe(self) -> queue.Queue:
        with self._events_lock:
            q: queue.Queue = queue.Queue(maxsize=1000)
            self._subscribers.append(q)
            return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._events_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    @staticmethod
    def _format_sse(event: Dict[str, Any]) -> str:
        return f"id: {event['id']}\nevent: {event['event']}\ndata: {json.dumps(event)}\n\n"

    def stream_events(
        self,
        last_event_id: int = 0,
        heartbeat_interval: float = 15.0,
        max_heartbeats: Optional[int] = None,
    ) -> Generator[str, None, None]:
        q = self.subscribe()
        try:
            with self._events_lock:
                past = [e for e in self.events if e["id"] > last_event_id]
                last_sent_id = past[-1]["id"] if past else last_event_id

            for e in past:
                yield self._format_sse(e)
                if e.get("event") in ("done", "error", "aborted"):
                    return

            if self.state in ("done", "error", "aborted") and q.empty():
                return

            heartbeat_count = 0
            while True:
                if self.state in ("done", "error", "aborted") and q.empty():
                    break
                try:
                    event = q.get(timeout=heartbeat_interval)
                    if event["id"] > last_sent_id:
                        last_sent_id = event["id"]
                        yield self._format_sse(event)
                        if event.get("event") in ("done", "error", "aborted"):
                            break
                except queue.Empty:
                    if self.state in ("done", "error", "aborted"):
                        break
                    heartbeat_count += 1
                    if max_heartbeats is not None and heartbeat_count >= max_heartbeats:
                        break
                    yield ": heartbeat\n\n"
        finally:
            self.unsubscribe(q)

    def _plan_approver(self, plan: List[Dict[str, Any]]) -> bool:
        with self.cond:
            self.plan = plan
            self.state = "pending_plan"
            self.updated_at = time.time()
            self._decision = None
            self.emit("pending_plan", {
                "plan": plan,
                "prompt": f"Approve build plan with {len(plan)} step(s)?",
            })
            self.cond.notify_all()
            got = self.cond.wait_for(lambda: self._decision is not None, timeout=self.confirm_timeout)
            decision = self._decision if got else False
            if not got:
                logger.info("[interactive] plan approval timeout (%.0fs) -> REJECT", self.confirm_timeout)
            self._decision = None
            self.state = "running"
            self.updated_at = time.time()
            self.emit("plan_response", {"approved": bool(decision)})
            self.cond.notify_all()
            return bool(decision)

    def _proposal_approver(self, proposal: Any) -> bool:
        with self.cond:
            self.pending_proposal = proposal
            self.state = "pending_confirmation"
            self.updated_at = time.time()
            self._decision = None
            p_dict = proposal.as_dict() if hasattr(proposal, "as_dict") else {"prompt": str(proposal)}
            self.emit("pending_confirmation", {
                "proposal": p_dict,
                "prompt": getattr(proposal, "prompt", str(proposal)),
                "diff": getattr(proposal, "diff", None),
            })
            self.cond.notify_all()
            got = self.cond.wait_for(lambda: self._decision is not None, timeout=self.confirm_timeout)
            decision = self._decision if got else False
            if not got:
                logger.info("[interactive] proposal approval timeout (%.0fs) -> DENY", self.confirm_timeout)
            self.pending_proposal = None
            self._decision = None
            self.state = "running"
            self.updated_at = time.time()
            self.emit("confirmation_response", {"approved": bool(decision)})
            self.cond.notify_all()
            return bool(decision)

    def respond(self, approve: bool) -> None:
        with self.cond:
            self._decision = bool(approve)
            self.updated_at = time.time()
            self.cond.notify_all()
            # Wait until background worker consumes decision
            self.cond.wait_for(lambda: self._decision is None, timeout=10)

    def abort(self) -> None:
        with self.cond:
            self.state = "aborted"
            self.error = "Build aborted by user."
            self._decision = False
            self.updated_at = time.time()
            self.emit("aborted", {"message": self.error})
            self.cond.notify_all()

    def wait_checkpoint(self, wait: float = 30.0) -> Dict[str, Any]:
        with self.cond:
            if self.state not in ("pending_plan", "pending_confirmation", "done", "error", "aborted"):
                self.cond.wait_for(
                    lambda: self.state in ("pending_plan", "pending_confirmation", "done", "error", "aborted"),
                    timeout=wait,
                )
            self.updated_at = time.time()
            return self._snapshot()

    def _snapshot(self) -> Dict[str, Any]:
        base = {
            "session_id": self.session_id,
            "state": self.state,
            "task": self.task,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.state == "pending_plan":
            base["status"] = "pending_plan"
            base["plan"] = self.plan or []
            base["prompt"] = f"Approve build plan with {len(self.plan or [])} step(s)?"
        elif self.state == "pending_confirmation":
            base["status"] = "pending_confirmation"
            if self.pending_proposal and hasattr(self.pending_proposal, "as_dict"):
                base["proposal"] = self.pending_proposal.as_dict()
            else:
                base["proposal"] = {"prompt": str(self.pending_proposal)}
        elif self.state == "done":
            base["status"] = "done"
            base["result"] = self.result
        elif self.state in ("error", "aborted"):
            base["status"] = self.state
            base["message"] = self.error or "Build failed."
            if self.result:
                base["result"] = self.result
        else:
            base["status"] = "running"
        return base

    def run_worker(self, think_fn: Callable[[str], str], max_steps: Optional[int] = None) -> None:
        self.emit("session_start", {"task": self.task, "session_id": self.session_id})
        try:
            agent = CodingAgent(
                think_fn=think_fn,
                plan_approver=self._plan_approver,
                delete_approver=self._proposal_approver,
                shell_approver=self._proposal_approver,
                deploy_approver=self._proposal_approver,
                max_steps=max_steps or 20,
                on_event=lambda evt, data: self.emit(evt, data),
            )
            res = agent.run(self.task)
            with self.cond:
                self.result = res
                self.state = "done" if res.get("status") in ("success", "rejected", "incomplete") else "error"
                self.updated_at = time.time()
                self.cond.notify_all()
            with self._events_lock:
                terminal_sent = any(e.get("event") in ("done", "error", "aborted") for e in self.events)
            if not terminal_sent:
                self.emit("done", {"result": res, "status": res.get("status", self.state)})
        except Exception as exc:
            logger.exception("[interactive] session %s failed", self.session_id)
            with self.cond:
                self.error = str(exc)
                self.state = "error"
                self.updated_at = time.time()
                self.cond.notify_all()
            self.emit("error", {"error": str(exc), "message": str(exc)})


def _reap_sessions() -> None:
    now = time.time()
    with _sessions_lock:
        stale = [sid for sid, s in _sessions.items() if (now - s.updated_at) > SESSION_TTL_S]
        for sid in stale:
            _sessions.pop(sid, None)


def start_session(
    task: str,
    think_fn: Callable[[str], str],
    session_id: Optional[str] = None,
    workspace: Optional[str] = None,
    max_steps: Optional[int] = None,
    confirm_timeout: Optional[float] = None,
) -> InteractiveBuildSession:
    _reap_sessions()
    sid = session_id or uuid.uuid4().hex[:12]

    if workspace:
        grant = guarded.grant_workspace(workspace)
        if grant.get("status") != "success":
            raise ValueError(grant.get("message", "Invalid workspace path"))

    if guarded.active_workspace() is None:
        raise ValueError("No active workspace granted. Call grant_workspace first.")

    session = InteractiveBuildSession(sid, task, confirm_timeout=confirm_timeout)
    with _sessions_lock:
        _sessions[sid] = session

    t = threading.Thread(
        target=session.run_worker,
        args=(think_fn, max_steps),
        name=f"coding-build-{sid}",
        daemon=True,
    )
    session.thread = t
    t.start()
    return session


def get_session(session_id: str) -> Optional[InteractiveBuildSession]:
    with _sessions_lock:
        return _sessions.get(session_id)


def poll_session(session_id: str, wait: float = 30.0) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        return {"status": "error", "marker": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."}
    return session.wait_checkpoint(wait=wait)


def respond_session(session_id: str, approve: bool, wait: float = 30.0) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        return {"status": "error", "marker": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."}
    session.respond(approve)
    return session.wait_checkpoint(wait=wait)


def abort_session(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        return {"status": "error", "marker": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."}
    session.abort()
    return session._snapshot()


def list_active_sessions() -> List[Dict[str, Any]]:
    _reap_sessions()
    with _sessions_lock:
        return [s._snapshot() for s in _sessions.values()]
