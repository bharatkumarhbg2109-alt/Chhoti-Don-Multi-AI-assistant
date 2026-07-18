"""
Chhoti Don - Response Engine
Standardized response building with metadata, timing, and formatting.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Any, Dict, Dict


class ResponseEngine:
    """
    Standardized response builder.
    Preserved + upgraded with full metadata.
    """

    @staticmethod
    def build(
        status: str,
        code: str,
        message: str,
        data: Any = None,
        module: str = "unknown",
        start_time: float = None,
        confidence: float = None,
        intent: str = None,
        model: str = None,
    ) -> Dict:
        """Build standardized response. Preserved + upgraded."""
        execution_time = None
        if start_time:
            execution_time = round(time.time() - start_time, 4)

        return {
            "status": status,
            "code": code,
            "message": message,
            "data": data,
            "meta": {
                "module": module,
                "execution_time": execution_time,
                "confidence": confidence,
                "intent": intent,
                "model": model,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        }

    @staticmethod
    def success(data: Any, module: str = "unknown", start_time: float = None, **kwargs) -> Dict:
        """Quick success response."""
        return ResponseEngine.build(
            status="success",
            code="SUCCESS",
            message="Operation completed",
            data=data,
            module=module,
            start_time=start_time,
            **kwargs,
        )

    @staticmethod
    def error(code: str, message: str, module: str = "unknown", data: Any = None) -> Dict:
        """Quick error response."""
        return ResponseEngine.build(
            status="error",
            code=code,
            message=message,
            data=data,
            module=module,
        )

    @staticmethod
    def blocked(reason: str, module: str = "guardian") -> Dict:
        """Guardian blocked response."""
        return ResponseEngine.build(
            status="blocked",
            code="GUARDIAN_BLOCK",
            message=f"Operation blocked: {reason}",
            module=module,
            confidence=0.0,
        )
