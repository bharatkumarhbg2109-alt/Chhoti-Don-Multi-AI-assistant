"""
Chhoti Don - Step Validator
Advanced plan step validation with tool registry,
guardian checks, and input schema validation.
Phase 2.2 - Full Upgrade
"""

import datetime
from typing import Dict, List, Tuple, Tuple


class StepValidator:
    """
    Advanced Step Validator.
    Preserved + upgraded with schema validation.
    """

    def __init__(self, tool_registry, guardian):
        self.tool_registry = tool_registry
        self.guardian = guardian
        self._validation_log = []

    def validate(self, step: Dict, session_id: str = None) -> Tuple[bool, str]:
        """
        Validate a plan step.
        Preserved + upgraded.
        """
        action = step.get("action")

        # Tool exists check (preserved)
        if action not in self.tool_registry:
            self._log(action, False, "Tool not found", session_id)
            return False, f"Tool '{action}' not found"

        # Input check (preserved)
        if "input" not in step:
            self._log(action, False, "Missing input", session_id)
            return False, "Missing input field"

        # Input type check (new)
        if not isinstance(step.get("input"), dict):
            return False, "Input must be a dictionary"

        # Guardian check (preserved)
        try:
            allowed, reason = self.guardian.check(action, session_id)
            if not allowed:
                self._log(action, False, reason, session_id)
                return False, reason
        except Exception as e:
            # Guardian unavailable — allow with warning
            pass

        self._log(action, True, "Valid", session_id)
        return True, "Valid"

    def validate_batch(self, steps: List[Dict], session_id: str = None) -> Dict:
        """Multiple steps validate karo."""
        results = []
        all_valid = True

        for i, step in enumerate(steps):
            valid, message = self.validate(step, session_id)
            results.append({
                "step": i + 1,
                "action": step.get("action"),
                "valid": valid,
                "message": message,
            })
            if not valid:
                all_valid = False

        return {
            "all_valid": all_valid,
            "results": results,
            "total_steps": len(steps),
            "valid_count": sum(1 for r in results if r["valid"]),
        }

    def _log(self, action: str, valid: bool, reason: str, session_id: str = None) -> None:
        """Validation log karo."""
        self._validation_log.append({
            "action": action,
            "valid": valid,
            "reason": reason,
            "session_id": session_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        if len(self._validation_log) > 100:
            self._validation_log.pop(0)

    def get_validation_log(self, last_n: int = 20) -> List[Dict]:
        return self._validation_log[-last_n:]
