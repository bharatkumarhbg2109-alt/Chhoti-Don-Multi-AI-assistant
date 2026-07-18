"""
Chhoti Don - Adaptive Learning Engine
Advanced learning system with tool reliability tracking,
confidence adaptation, trend analysis, and persistent state.
Phase 2.2 - Full Upgrade
"""

import json
import os
import datetime
import math
from collections import defaultdict
from typing import Dict, List, List


LEARNING_STATE_FILE= "core/learning_state.json"
MAX_HISTORY_PER_TOOL = 50


class AdaptiveLearningEngine:
    """
    Advanced Adaptive Learning Engine.
    Learns from tool execution history to improve routing decisions.
    """

    def __init__(self, filepath: str = LEARNING_STATE_FILE):
        self.filepath = filepath
        self.state = {
            "tool_stats": {},
            "global_bias": 0.0,
            "session_count": 0,
            "total_executions": 0,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "last_updated": None,
        }
        self._execution_buffer = []
        self._load()

    # ==================================================
    # 💾 Persistence
    # ==================================================
    def _load(self) -> None:
        """Load state from file."""
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.state.update(loaded)
        except Exception:
            pass

    def _save(self) -> None:
        """Save state to file."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.state["last_updated"] = datetime.datetime.utcnow().isoformat()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass

    # ==================================================
    # 📊 Core Recording (PRESERVED + UPGRADED)
    # ==================================================
    def record_execution(
        self,
        tool_name: str,
        success: bool,
        confidence: float,
        execution_time: float = 0.0,
        error_code: str = None,
        context: Dict = None,
    ) -> None:
        """
        Record tool execution result.
        Preserved + upgraded with time tracking and error codes.
        """
        if tool_name not in self.state["tool_stats"]:
            self.state["tool_stats"][tool_name] = {
                "success": 0,
                "failure": 0,
                "avg_confidence": 0.0,
                "avg_execution_time": 0.0,
                "last_10": [],
                "error_codes": {},
                "streak": 0,
                "best_confidence": 0.0,
                "first_seen": datetime.datetime.utcnow().isoformat(),
                "last_seen": None,
            }

        stats = self.state["tool_stats"][tool_name]

        # Update counts
        if success:
            stats["success"] += 1
            stats["streak"] = max(0, stats.get("streak", 0)) + 1
        else:
            stats["failure"] += 1
            stats["streak"] = min(0, stats.get("streak", 0)) - 1
            if error_code:
                stats["error_codes"][error_code] = stats["error_codes"].get(error_code, 0) + 1

        total = stats["success"] + stats["failure"]

        # Rolling confidence average
        stats["avg_confidence"] = round(
            (stats["avg_confidence"] * (total - 1) + confidence) / total, 4
        )

        # Best confidence
        if confidence > stats.get("best_confidence", 0):
            stats["best_confidence"] = confidence

        # Execution time average
        if execution_time > 0:
            prev_avg = stats.get("avg_execution_time", 0)
            stats["avg_execution_time"] = round(
                (prev_avg * (total - 1) + execution_time) / total, 4
            )

        # Last 10 results (rolling window)
        stats.setdefault("last_10", []).append("S" if success else "F")
        if len(stats["last_10"]) > 10:
            stats["last_10"].pop(0)

        stats["last_seen"] = datetime.datetime.utcnow().isoformat()

        # Global bias adjustment
        if success:
            self.state["global_bias"] += 0.01
        else:
            self.state["global_bias"] -= 0.01
        self.state["global_bias"] = max(-0.2, min(0.2, self.state["global_bias"]))

        self.state["total_executions"] = self.state.get("total_executions", 0) + 1

        self._save()

    # ==================================================
    # 📈 Reliability & Confidence
    # ==================================================
    def get_tool_reliability(self, tool_name: str) -> float:
        """
        Tool reliability score (0-1).
        Preserved + upgraded with recency weighting.
        """
        stats = self.state["tool_stats"].get(tool_name)
        if not stats:
            return 1.0

        total = stats["success"] + stats["failure"]
        if total == 0:
            return 1.0

        # Base reliability
        base = stats["success"] / total

        # Recency weighting — last 10 results matter more
        last_10 = stats.get("last_10", [])
        if len(last_10) >= 5:
            recent_rate = last_10.count("S") / len(last_10)
            reliability = (base * 0.4) + (recent_rate * 0.6)
        else:
            reliability = base

        return round(reliability, 4)

    def get_adjusted_confidence(
        self,
        tool_name: str,
        base_confidence: float,
    ) -> float:
        """
        Learning-adjusted confidence score.
        """
        reliability = self.get_tool_reliability(tool_name)
        global_bias = self.get_global_bias()

        adjusted = base_confidence * reliability + global_bias
        return round(max(0.0, min(1.0, adjusted)), 4)

    def get_global_bias(self) -> float:
        """Global success bias. Preserved."""
        return self.state.get("global_bias", 0.0)

    # ==================================================
    # 🔍 Analysis & Insights
    # ==================================================
    def get_best_tools(self, top_n: int = 5) -> List[Dict]:
        """Most reliable tools list karo."""
        tool_scores = []
        for tool, stats in self.state["tool_stats"].items():
            reliability = self.get_tool_reliability(tool)
            total = stats["success"] + stats["failure"]
            tool_scores.append({
                "tool": tool,
                "reliability": reliability,
                "total_runs": total,
                "avg_confidence": stats.get("avg_confidence", 0),
            })

        tool_scores.sort(key=lambda x: x["reliability"], reverse=True)
        return tool_scores[:top_n]

    def get_worst_tools(self, bottom_n: int = 5) -> List[Dict]:
        """Least reliable tools."""
        tool_scores = self.get_best_tools(len(self.state["tool_stats"]))
        return tool_scores[-bottom_n:]

    def get_tool_trend(self, tool_name: str) -> str:
        """Recent performance trend."""
        stats = self.state["tool_stats"].get(tool_name)
        if not stats:
            return "unknown"

        last_10 = stats.get("last_10", [])
        if len(last_10) < 4:
            return "insufficient_data"

        recent = last_10[-4:]
        older = last_10[:-4] if len(last_10) > 4 else last_10[:4]

        recent_rate = recent.count("S") / len(recent)
        older_rate = older.count("S") / len(older) if older else 0.5

        if recent_rate > older_rate + 0.2:
            return "improving"
        elif recent_rate < older_rate - 0.2:
            return "degrading"
        return "stable"

    def get_learning_report(self) -> Dict:
        """Full learning state report."""
        return {
            "total_tools_tracked": len(self.state["tool_stats"]),
            "total_executions": self.state.get("total_executions", 0),
            "global_bias": self.state.get("global_bias", 0.0),
            "best_tools": self.get_best_tools(3),
            "worst_tools": self.get_worst_tools(3),
            "last_updated": self.state.get("last_updated"),
        }

    def reset_tool(self, tool_name: str) -> bool:
        """Single tool stats reset karo."""
        if tool_name in self.state["tool_stats"]:
            del self.state["tool_stats"][tool_name]
            self._save()
            return True
        return False

    def reset_all(self) -> None:
        """Full reset."""
        self.__init__(self.filepath)
