"""
Chhoti Don - Session Manager
Advanced session management with rate limiting,
risk tracking, fingerprinting, and audit logging.
Phase 2.2 - Full Upgrade
"""

import uuid
import datetime
import time
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Tuple


class SessionManager:
    """
    Advanced Session Manager
    - Adaptive rate limiting
    - Risk history tracking
    - Session fingerprinting
    - Audit logging
    - Multi-target tracking
    - Phase 2.2 Upgrade
    """

    WINDOW = 60              # seconds
    MAX_SCANS = 5            # default scans per window
    COOLDOWN_SECONDS = 120   # base cooldown duration
    MAX_SESSIONS = 100       # max active sessions
    SESSION_TTL = 3600       # session timeout (1 hour)

    def __init__(self):
        self.sessions = {}
        self.audit_log = []
        self.target_registry = {}  # target → session_ids mapping
        self._session_counter = 0

    # ==================================================
    # 🔧 Session Creation (UPGRADED)
    # ==================================================
    def create_session(self, target: str, metadata: Dict = None) -> str:
        """
        Create a new session with full tracking.

        Args:
            target: IP/domain being scanned
            metadata: Optional extra info (user, mode, etc.)

        Returns:
            session_id (str)
        """
        # Cleanup expired sessions first
        self._cleanup_expired()

        # Max session check
        if len(self.sessions) >= self.MAX_SESSIONS:
            oldest = min(self.sessions.items(),
                        key=lambda x: x[1]["created_timestamp"])
            del self.sessions[oldest[0]]

        session_id = str(uuid.uuid4())
        now = time.time()
        self._session_counter += 1

        self.sessions[session_id] = {
            # Identity
            "session_id": session_id,
            "session_number": self._session_counter,
            "target": target,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "created_timestamp": now,
            "last_activity": now,

            # Data storage
            "data": {},
            "scan_results": [],
            "metadata": metadata or {},

            # Rate limiting
            "scan_log": [],
            "rate_violation_count": 0,
            "cooldown_until": None,
            "cooldown_multiplier": 1,

            # Risk tracking
            "risk_history": [],
            "risk_peak": 0,
            "risk_trend": "unknown",

            # Fingerprinting
            "fingerprint": self._generate_fingerprint(target, now),

            # Stats
            "total_scans": 0,
            "total_findings": 0,
            "status": "active",
        }

        # Target registry update
        if target not in self.target_registry:
            self.target_registry[target] = []
        self.target_registry[target].append(session_id)

        # Audit log
        self._audit(session_id, "SESSION_CREATED", f"Target: {target}")

        return session_id

    # ==================================================
    # 📝 Session Operations (PRESERVED + UPGRADED)
    # ==================================================
    def update_session(self, session_id: str, key: str, value) -> bool:
        """Update session data."""
        if session_id in self.sessions:
            self.sessions[session_id]["data"][key] = value
            self.sessions[session_id]["last_activity"] = time.time()
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        session = self.sessions.get(session_id)
        if session:
            # Update last activity
            session["last_activity"] = time.time()
        return session

    def list_sessions(self) -> List[Dict]:
        """List all active sessions."""
        return [
            {
                "session_id": sid,
                "target": s["target"],
                "created_at": s["created_at"],
                "total_scans": s["total_scans"],
                "status": s["status"],
                "risk_peak": s.get("risk_peak", 0),
            }
            for sid, s in self.sessions.items()
        ]

    def close_session(self, session_id: str) -> bool:
        """Session close karo."""
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "closed"
            self.sessions[session_id]["closed_at"] = datetime.datetime.utcnow().isoformat()
            self._audit(session_id, "SESSION_CLOSED", "Session closed by user")
            return True
        return False

    def get_target_session_count(self, target: str) -> int:
        """Target ke liye session count."""
        return len(self.target_registry.get(target, []))

    # ==================================================
    # 📊 Scan Result Storage
    # ==================================================
    def store_scan_result(self, session_id: str, scan_type: str, result: Dict) -> bool:
        """Scan result session mein store karo."""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        entry = {
            "scan_type": scan_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "result": result,
        }

        session["scan_results"].append(entry)
        session["total_scans"] += 1
        session["last_activity"] = time.time()

        # Update findings count
        if isinstance(result, dict):
            findings = result.get("open_ports", []) or result.get("findings", [])
            if findings:
                session["total_findings"] += len(findings)

        self._audit(session_id, "SCAN_STORED", f"Type: {scan_type}")
        return True

    def get_scan_history(self, session_id: str) -> List[Dict]:
        """Session ki scan history lo."""
        session = self.sessions.get(session_id, {})
        return session.get("scan_results", [])

    # ==================================================
    # 🔥 Adaptive Guardian Scan Limit (PRESERVED)
    # ==================================================
    def get_dynamic_scan_limit(self, session_id: str) -> int:
        """Risk-based dynamic scan limit."""
        session = self.sessions.get(session_id)
        if not session:
            return self.MAX_SCANS

        history = session.get("risk_history", [])
        if not history:
            return self.MAX_SCANS

        latest_risk = history[-1]

        if latest_risk >= 9:
            return 1
        elif latest_risk >= 7:
            return 2
        elif latest_risk >= 4:
            return 3
        else:
            return self.MAX_SCANS

    # ==================================================
    # 🔥 Rate Limiting (PRESERVED + UPGRADED)
    # ==================================================
    def check_rate_limit(self, session_id: str) -> Tuple[bool, str]:
        """
        Advanced rate limiting with dynamic cooldown.

        Returns:
            (allowed: bool, message: str)
        """
        if session_id not in self.sessions:
            return False, "Invalid session"

        session = self.sessions[session_id]
        now = time.time()

        # Cooldown check
        if session["cooldown_until"]:
            remaining = round(session["cooldown_until"] - now)
            if now < session["cooldown_until"]:
                self._audit(session_id, "RATE_BLOCKED", f"Cooldown: {remaining}s remaining")
                return False, f"Session in cooldown — {remaining}s remaining"
            else:
                session["cooldown_until"] = None
                session["cooldown_multiplier"] = 1
                self._audit(session_id, "COOLDOWN_EXPIRED", "Rate limit reset")

        # Sliding window cleanup
        session["scan_log"] = [
            t for t in session["scan_log"]
            if now - t < self.WINDOW
        ]

        # Dynamic limit
        dynamic_limit = self.get_dynamic_scan_limit(session_id)

        if len(session["scan_log"]) >= dynamic_limit:
            session["rate_violation_count"] += 1

            if session["rate_violation_count"] >= 3:
                cooldown_time = self.COOLDOWN_SECONDS * session["cooldown_multiplier"]
                session["cooldown_until"] = now + cooldown_time
                session["cooldown_multiplier"] = min(session["cooldown_multiplier"] * 2, 16)

                self._audit(session_id, "COOLDOWN_ACTIVATED",
                           f"Duration: {cooldown_time}s | Multiplier: {session['cooldown_multiplier']}")
                return False, f"Rate limit exceeded — cooldown {cooldown_time}s activated"

            self._audit(session_id, "RATE_VIOLATION",
                       f"Count: {session['rate_violation_count']}")
            return False, f"Rate limit exceeded ({session['rate_violation_count']}/3 violations)"

        session["scan_log"].append(now)
        return True, "Allowed"

    # ==================================================
    # 🔥 Risk History Tracking (PRESERVED + UPGRADED)
    # ==================================================
    def add_risk_score(self, session_id: str, risk_score: int) -> None:
        """Risk score add karo aur trend update karo."""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        session["risk_history"].append(risk_score)

        # Update peak
        if risk_score > session.get("risk_peak", 0):
            session["risk_peak"] = risk_score

        # Update trend
        history = session["risk_history"]
        if len(history) >= 2:
            if history[-1] > history[-2]:
                session["risk_trend"] = "increasing"
            elif history[-1] < history[-2]:
                session["risk_trend"] = "decreasing"
            else:
                session["risk_trend"] = "stable"

        self._audit(session_id, "RISK_UPDATED",
                   f"Score: {risk_score} | Trend: {session['risk_trend']}")

    def get_risk_trend_adjustment(self, session_id: str) -> int:
        """Risk trend se adjustment value lo."""
        if session_id not in self.sessions:
            return 0

        history = self.sessions[session_id]["risk_history"]

        if len(history) < 2:
            return 0

        adjustment = 0

        if history[-1] > history[-2]:
            adjustment += 2

        if len(history) >= 3 and history[-1] > history[-2] > history[-3]:
            adjustment += 3

        # Spike detection
        if len(history) >= 2:
            avg = sum(history[:-1]) / len(history[:-1])
            if history[-1] > avg * 1.5:
                adjustment += 5

        return adjustment

    def get_risk_summary(self, session_id: str) -> Dict:
        """Session ki full risk summary."""
        if session_id not in self.sessions:
            return {}

        session = self.sessions[session_id]
        history = session.get("risk_history", [])

        if not history:
            return {"status": "no_data"}

        return {
            "current": history[-1] if history else 0,
            "peak": session.get("risk_peak", 0),
            "average": round(sum(history) / len(history), 1),
            "trend": session.get("risk_trend", "unknown"),
            "history": history[-10:],  # Last 10
            "total_assessments": len(history),
        }

    # ==================================================
    # 🔒 Session Fingerprinting
    # ==================================================
    def _generate_fingerprint(self, target: str, timestamp: float) -> str:
        """Unique session fingerprint generate karo."""
        raw = f"{target}:{timestamp}:{uuid.uuid4()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def verify_fingerprint(self, session_id: str, fingerprint: str) -> bool:
        """Session fingerprint verify karo."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        return session.get("fingerprint") == fingerprint

    # ==================================================
    # 📋 Audit Logging
    # ==================================================
    def _audit(self, session_id: str, event: str, details: str = "") -> None:
        """Audit log entry add karo."""
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "session_id": session_id[:8] + "...",
            "event": event,
            "details": details,
        }
        self.audit_log.append(entry)

        # Keep last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, session_id: str = None, last_n: int = 20) -> List[Dict]:
        """Audit log lo — session filter optional."""
        if session_id:
            short_id = session_id[:8] + "..."
            logs = [e for e in self.audit_log if e["session_id"] == short_id]
        else:
            logs = self.audit_log

        return logs[-last_n:]

    # ==================================================
    # 🧹 Session Cleanup
    # ==================================================
    def _cleanup_expired(self) -> int:
        """Expired sessions cleanup karo."""
        now = time.time()
        expired = [
            sid for sid, s in self.sessions.items()
            if now - s.get("created_timestamp", now) > self.SESSION_TTL
            and s.get("status") != "closed"
        ]

        for sid in expired:
            self.sessions[sid]["status"] = "expired"
            self._audit(sid, "SESSION_EXPIRED", "TTL exceeded")

        return len(expired)

    def cleanup_all(self) -> int:
        """Sab expired/closed sessions remove karo."""
        to_remove = [
            sid for sid, s in self.sessions.items()
            if s.get("status") in ["expired", "closed"]
        ]
        for sid in to_remove:
            del self.sessions[sid]

        return len(to_remove)

    # ==================================================
    # 📊 Statistics
    # ==================================================
    def get_stats(self) -> Dict:
        """Global session statistics."""
        active = sum(1 for s in self.sessions.values() if s["status"] == "active")
        total_scans = sum(s.get("total_scans", 0) for s in self.sessions.values())
        unique_targets = len(self.target_registry)

        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active,
            "unique_targets": unique_targets,
            "total_scans_performed": total_scans,
            "audit_log_entries": len(self.audit_log),
        }

    def export_session(self, session_id: str) -> Optional[str]:
        """Session data JSON export karo."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        try:
            return json.dumps(session, indent=2, default=str)
        except Exception:
            return None
