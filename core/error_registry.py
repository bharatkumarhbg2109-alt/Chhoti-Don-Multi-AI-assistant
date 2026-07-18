"""
Chhoti Don - Error Registry
Centralized error codes, messages, and error handling utilities.
Phase 2.2 - Full Upgrade
"""

import datetime
from typing import Dict, List, Optional, Optional

class ErrorCodes:
    """All error codes. Preserved + expanded."""

    # Success
    SUCCESS = "SUCCESS"

    # Internal Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    PARSE_ERROR = "PARSE_ERROR"

    # Tool Errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"

    # Guardian / Control
    GUARDIAN_BLOCK = "GUARDIAN_BLOCK"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TARGET_BLOCKED = "TARGET_BLOCKED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # AI / Brain Errors
    BRAIN_UNAVAILABLE = "BRAIN_UNAVAILABLE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    OLLAMA_OFFLINE = "OLLAMA_OFFLINE"
    PLAN_FAILED = "PLAN_FAILED"
    CONTEXT_OVERFLOW = "CONTEXT_OVERFLOW"

    # Validation
    VALIDATION_FAILED = "VALIDATION_FAILED"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Structured Layer
    STRUCTURE_NOT_AVAILABLE = "STRUCTURE_NOT_AVAILABLE"
    PLAN_INVALID = "PLAN_INVALID"
    STEP_FAILED = "STEP_FAILED"

    # Network
    NETWORK_ERROR = "NETWORK_ERROR"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"

    # File/IO
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    IO_ERROR = "IO_ERROR"


# Error messages map
ERROR_MESSAGES: Dict[str, str] = {
    ErrorCodes.SUCCESS: "Operation completed successfully",
    ErrorCodes.INTERNAL_ERROR: "An internal error occurred",
    ErrorCodes.EXECUTION_ERROR: "Execution failed",
    ErrorCodes.TIMEOUT_ERROR: "Operation timed out",
    ErrorCodes.TOOL_NOT_FOUND: "Requested tool not found in registry",
    ErrorCodes.GUARDIAN_BLOCK: "Operation blocked by Guardian security layer",
    ErrorCodes.RATE_LIMIT_EXCEEDED: "Rate limit exceeded — try again later",
    ErrorCodes.TARGET_BLOCKED: "Target is outside authorized scope",
    ErrorCodes.OLLAMA_OFFLINE: "Ollama server is not running",
    ErrorCodes.VALIDATION_FAILED: "Input validation failed",
    ErrorCodes.BRAIN_UNAVAILABLE: "AI brain is not available",
    ErrorCodes.FILE_NOT_FOUND: "File or path not found",
}

# Error severity levels
ERROR_SEVERITY: Dict[str, str] = {
    ErrorCodes.GUARDIAN_BLOCK: "critical",
    ErrorCodes.TARGET_BLOCKED: "critical",
    ErrorCodes.PERMISSION_DENIED: "critical",
    ErrorCodes.INTERNAL_ERROR: "high",
    ErrorCodes.EXECUTION_ERROR: "high",
    ErrorCodes.BRAIN_UNAVAILABLE: "high",
    ErrorCodes.TOOL_NOT_FOUND: "medium",
    ErrorCodes.VALIDATION_FAILED: "medium",
    ErrorCodes.TIMEOUT_ERROR: "medium",
    ErrorCodes.RATE_LIMIT_EXCEEDED: "low",
    ErrorCodes.FILE_NOT_FOUND: "low",
}

# Error log
_error_log: List[Dict] = []


class ErrorRegistry:
    """
    Centralized error registry with logging and analysis.
    """

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.recent_errors: List[Dict] = []

    def record(
        self,
        code: str,
        message: str = None,
        module: str = "unknown",
        context: Dict = None,
    ) -> Dict:
        """Record an error."""
        error_entry = {
            "code": code,
            "message": message or ERROR_MESSAGES.get(code, "Unknown error"),
            "module": module,
            "severity": ERROR_SEVERITY.get(code, "medium"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "context": context or {},
        }

        self.error_counts[code] = self.error_counts.get(code, 0) + 1
        self.recent_errors.append(error_entry)
        _error_log.append(error_entry)

        # Keep last 100
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)

        return error_entry

    def get_most_common(self, top_n: int = 5) -> List[Dict]:
        """Most common errors."""
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"code": k, "count": v} for k, v in sorted_errors[:top_n]]

    def get_recent(self, n: int = 10) -> List[Dict]:
        """Recent errors."""
        return self.recent_errors[-n:]

    def has_critical_errors(self) -> bool:
        """Critical errors present?"""
        return any(
            e.get("severity") == "critical"
            for e in self.recent_errors[-10:]
        )

    def build_error_response(self, code: str, message: str = None) -> Dict:
        """Standard error response dict."""
        return {
            "status": "error",
            "code": code,
            "message": message or ERROR_MESSAGES.get(code, "Unknown error"),
            "severity": ERROR_SEVERITY.get(code, "medium"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }


# Global instance
error_registry = ErrorRegistry()
