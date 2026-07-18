"""
Chhoti Don - Execution Controller
Advanced plan execution with validation, retry logic,
timeout management, and telemetry integration.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Dict, List, Tuple, Tuple


class ExecutionController:
    """
    Advanced Plan Execution Controller.
    Preserved + upgraded with telemetry and circuit breaker.
    """

    def __init__(self, validator, tool_executor, telemetry=None):
        self.validator = validator
        self.tool_executor = tool_executor
        self.telemetry = telemetry
        self.retry_limit = 2
        self.execution_history = []
        self._circuit_breaker = {}

    def execute_plan(self, plan: Dict, session_id: str = None) -> Dict:
        """
        Execute a multi-step plan.
        Preserved + upgraded with full pipeline.
        """
        steps = plan.get("steps", [])
        if not steps:
            return {"status": "failed", "reason": "Empty plan", "confidence": 0.0}

        results = []
        success_count = 0
        total_start = time.time()

        for i, step in enumerate(steps):
            action = step.get("action", "")

            # Circuit breaker check
            if self._is_circuit_open(action):
                return {
                    "status": "circuit_broken",
                    "reason": f"Tool '{action}' circuit breaker open",
                    "results": results,
                    "confidence": 0.3,
                }

            # Validate step
            valid, message = self.validator.validate(step, session_id)
            if not valid:
                return {
                    "status": "failed",
                    "reason": message,
                    "step": i + 1,
                    "confidence": 0.3,
                }

            # Execute with retry
            step_result, step_success = self._execute_step_with_retry(
                step, session_id
            )

            # Record telemetry
            if self.telemetry:
                status = "success" if step_success else "error"
                exec_time = step_result.get("execution_time_sec", 0)
                try:
                    self.telemetry.record(action, status, exec_time)
                except Exception:
                    pass

            if step_success:
                success_count += 1
                self._reset_circuit(action)
            else:
                self._increment_circuit(action)
                return {
                    "status": "partial_failure",
                    "results": results,
                    "failed_at_step": i + 1,
                    "confidence": 0.5,
                }

            results.append({
                "step": i + 1,
                "action": action,
                "result": step_result,
                "success": step_success,
            })

        total_steps = len(steps)
        confidence = 0.9 if success_count == total_steps else 0.6

        total_duration = round(time.time() - total_start, 3)

        execution_record = {
            "status": "completed",
            "results": results,
            "confidence": confidence,
            "steps_total": total_steps,
            "steps_succeeded": success_count,
            "execution_time_sec": total_duration,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        self.execution_history.append(execution_record)
        return execution_record

    def _execute_step_with_retry(self, step: Dict, session_id: str) -> Tuple[Dict, bool]:
        """Step execute karo with retry logic."""
        action = step.get("action")
        input_data = step.get("input", {})
        attempts = 0

        while attempts <= self.retry_limit:
            start_time = time.time()
            try:
                result = self.tool_executor.execute(
                    action, input_data, session_id=session_id
                )
                exec_time = round(time.time() - start_time, 3)
                result["execution_time_sec"] = exec_time

                if result.get("status") == "success":
                    return result, True

            except Exception as e:
                result = {"status": "error", "message": str(e)}

            attempts += 1
            if attempts <= self.retry_limit:
                time.sleep(0.2 * attempts)

        return result, False

    def _is_circuit_open(self, action: str) -> bool:
        """Circuit breaker — tool too many failures?"""
        failures = self._circuit_breaker.get(action, 0)
        return failures >= 5

    def _increment_circuit(self, action: str) -> None:
        self._circuit_breaker[action] = self._circuit_breaker.get(action, 0) + 1

    def _reset_circuit(self, action: str) -> None:
        self._circuit_breaker[action] = 0

    def get_history(self, last_n: int = 10) -> List[Dict]:
        """Execution history lo."""
        return self.execution_history[-last_n:]
