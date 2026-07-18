"""
Chhoti Don - Base Agent
Advanced base class for all agents with brain integration,
memory, telemetry, task history, and lifecycle management.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Any, Any
from typing import Dict, List, Optional
class BaseAgent:
    """
    Advanced Base Agent.
    All agents inherit from this class.
    Preserved interface + full upgrade.
    """

    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        tools: List = None,
        brain=None,
    ):
        # Core identity (PRESERVED)
        self.name = name
        self.role = role
        self.goal = goal
        self.tools = tools or []

        # Brain integration (NEW)
        self.brain = brain
        self._brain_type = "default"

        # Task tracking (NEW)
        self.task_history: List[Dict] = []
        self.success_count = 0
        self.failure_count = 0
        self._start_time = time.time()

        # State
        self.is_active = True
        self.current_task: Optional[str] = None
        self._metadata: Dict = {}

    # ==================================================
    # 🧠 CORE METHODS (PRESERVED + UPGRADED)
    # ==================================================

    def think(self, task: str) -> Dict:
        """
        Think about the task.
        Preserved + upgraded with brain routing.
        """
        self.current_task = task

        thinking = {
            "agent": self.name,
            "role": self.role,
            "task": task,
            "status": "thinking",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        # Brain-assisted thinking
        if self.brain:
            try:
                analysis = self.brain.think(
                    f"As a {self.role}, analyze this task briefly: {task}",
                    brain_type=self._brain_type,
                )
                thinking["analysis"] = analysis[:300] if analysis else None
            except Exception:
                pass

        return thinking

    def act(self, task: str) -> Any:
        """
        Execute the task.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(f"{self.name} must implement act()")

    def report(self, result: Any) -> Dict:
        """
        Format execution report.
        Preserved + upgraded with metadata.
        """
        success = result is not None and "error" not in str(result).lower()[:50]

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        report = {
            "agent": self.name,
            "role": self.role,
            "result": result,
            "success": success,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        # Log to history
        self._log_task(self.current_task or "unknown", result, success)

        return report

    # ==================================================
    # 🔧 LIFECYCLE METHODS (NEW)
    # ==================================================

    def execute(self, task: str) -> Dict:
        """
        Full execution pipeline — think → act → report.
        """
        start_time = time.time()

        # Think
        thinking = self.think(task)

        # Act
        try:
            result = self.act(task)
            status = "success"
        except Exception as e:
            result = f"Agent error: {str(e)}"
            status = "error"

        # Report
        report = self.report(result)
        report["thinking"] = thinking.get("analysis", "")
        report["execution_time_sec"] = round(time.time() - start_time, 3)
        report["status"] = status

        return report

    def reset(self) -> None:
        """Agent state reset karo."""
        self.task_history = []
        self.success_count = 0
        self.failure_count = 0
        self.current_task = None

    def set_brain(self, brain) -> None:
        """Brain inject karo."""
        self.brain = brain

    # ==================================================
    # 📊 STATS & HISTORY (NEW)
    # ==================================================

    def get_stats(self) -> Dict:
        """Agent performance stats."""
        total = self.success_count + self.failure_count
        return {
            "agent": self.name,
            "role": self.role,
            "total_tasks": total,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_count / max(total, 1) * 100, 1),
            "uptime_sec": round(time.time() - self._start_time, 1),
            "tools_available": len(self.tools),
        }

    def get_history(self, last_n: int = 10) -> List[Dict]:
        """Task history lo."""
        return self.task_history[-last_n:]

    def _log_task(self, task: str, result: Any, success: bool) -> None:
        """Task history mein log karo."""
        self.task_history.append({
            "task": str(task)[:200],
            "result_preview": str(result)[:200],
            "success": success,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        if len(self.task_history) > 50:
            self.task_history.pop(0)

    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get_metadata(self, key: str, default=None) -> Any:
        return self._metadata.get(key, default)

    def __repr__(self) -> str:
        return f"<{self.name} | Role: {self.role} | Tasks: {self.success_count + self.failure_count}>"
