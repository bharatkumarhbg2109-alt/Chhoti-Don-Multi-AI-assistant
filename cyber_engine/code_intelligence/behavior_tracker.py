"""
Chhoti Don EvolveX - Behavior Tracker
Advanced file-based adaptive memory layer with trend analysis,
anomaly detection, and predictive stability scoring.
Phase 2.2 - Full Upgrade
"""

import json
import os
import math
from typing import Dict, List, Optional, Optional

STABILITY_THRESHOLD= 40


# ==================================================
# 💾 MEMORY OPERATIONS (PRESERVED + UPGRADED)
# ==================================================

def _load_memory() -> Dict:
    """Load behavior memory from file."""
    if not os.path.exists(BEHAVIOR_FILE):
        return {}
    try:
        with open(BEHAVIOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_memory(data: Dict) -> None:
    """Save behavior memory to file."""
    try:
        with open(BEHAVIOR_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


# ==================================================
# 🔧 CORE FUNCTIONS (PRESERVED + UPGRADED)
# ==================================================

def update_file_behavior(file_path: str, error_count: int, fix_applied: bool) -> None:
    """
    Track file error history and fix success.
    Preserved + upgraded with trend analysis.
    """
    memory = _load_memory()

    file_data = memory.get(file_path, {
        "error_history": [],
        "fix_attempts": 0,
        "successful_fixes": 0,
        "stability_score": 100,
        "trend": "stable",
        "anomaly_count": 0,
        "last_updated": None,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "total_analyses": 0,
    })

    # Update error history
    file_data["error_history"].append(error_count)
    file_data["total_analyses"] = file_data.get("total_analyses", 0) + 1

    # Keep history bounded
    if len(file_data["error_history"]) > MAX_HISTORY_LENGTH:
        file_data["error_history"].pop(0)

    # Track fixes
    if fix_applied:
        file_data["fix_attempts"] += 1
        if error_count == 0:
            file_data["successful_fixes"] += 1

    # Stability score calculation (enhanced)
    history = file_data["error_history"]
    avg_errors = sum(history) / max(len(history), 1)

    stability = 100 - (avg_errors * 5)

    if file_data["fix_attempts"] > 0:
        success_rate = file_data["successful_fixes"] / file_data["fix_attempts"]
        stability += success_rate * 10

    # Trend penalty
    trend = _calculate_trend(history)
    file_data["trend"] = trend
    if trend == "degrading":
        stability -= 10
    elif trend == "improving":
        stability += 5

    # Anomaly detection
    if _is_anomaly(history, error_count):
        file_data["anomaly_count"] = file_data.get("anomaly_count", 0) + 1
        stability -= 5

    file_data["stability_score"] = max(0, min(100, int(stability)))
    file_data["last_updated"] = datetime.datetime.utcnow().isoformat()
    file_data["last_error_count"] = error_count

    memory[file_path] = file_data
    _save_memory(memory)


def get_file_behavior(file_path: str) -> Dict:
    """Get file behavior data."""
    memory = _load_memory()
    return memory.get(file_path, {})


def is_file_stable(file_path: str) -> bool:
    """
    Check if file stability is above safe threshold.
    Returns True if safe for auto-fix.
    """
    memory = _load_memory()
    file_data = memory.get(file_path)

    if not file_data:
        return True  # No history = assume safe

    stability = file_data.get("stability_score", 100)
    anomaly_count = file_data.get("anomaly_count", 0)

    # Extra caution for anomalous files
    if anomaly_count >= 3:
        return stability >= STABILITY_THRESHOLD + 20

    return stability >= STABILITY_THRESHOLD


# ==================================================
# 📊 ADVANCED ANALYSIS FUNCTIONS (NEW)
# ==================================================

def get_project_health(project_path: str = None) -> Dict:
    """
    Full project behavior health report.
    """
    memory = _load_memory()

    if not memory:
        return {
            "status": "no_data",
            "message": "No behavior data collected yet",
        }

    # Filter by project path
    if project_path:
        project_path = project_path.replace("\\", "/")
        files = {
            k: v for k, v in memory.items()
            if project_path in k.replace("\\", "/")
        }
    else:
        files = memory

    if not files:
        return {"status": "no_data", "files": 0}

    # Aggregate stats
    stability_scores = [f.get("stability_score", 100) for f in files.values()]
    avg_stability = sum(stability_scores) / len(stability_scores)

    # Risk categorization
    critical_files = [
        k for k, v in files.items()
        if v.get("stability_score", 100) < 30
    ]
    unstable_files = [
        k for k, v in files.items()
        if 30 <= v.get("stability_score", 100) < STABILITY_THRESHOLD
    ]
    stable_files = [
        k for k, v in files.items()
        if v.get("stability_score", 100) >= STABILITY_THRESHOLD
    ]

    # Trending analysis
    degrading = [
        k for k, v in files.items()
        if v.get("trend") == "degrading"
    ]

    # Overall health
    if avg_stability >= 80:
        health = "excellent"
    elif avg_stability >= 60:
        health = "good"
    elif avg_stability >= 40:
        health = "moderate"
    else:
        health = "poor"

    return {
        "status": "success",
        "overall_health": health,
        "avg_stability": round(avg_stability, 1),
        "total_files_tracked": len(files),
        "stable_files": len(stable_files),
        "unstable_files": len(unstable_files),
        "critical_files": critical_files[:5],
        "degrading_files": degrading[:5],
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


def get_fix_effectiveness() -> Dict:
    """Overall fix effectiveness analyze karo."""
    memory = _load_memory()

    total_attempts = sum(f.get("fix_attempts", 0) for f in memory.values())
    total_successes = sum(f.get("successful_fixes", 0) for f in memory.values())

    effectiveness = (total_successes / max(total_attempts, 1)) * 100

    return {
        "total_fix_attempts": total_attempts,
        "total_successes": total_successes,
        "effectiveness_percent": round(effectiveness, 1),
        "files_tracked": len(memory),
    }


def reset_file_behavior(file_path: str) -> bool:
    """File ki behavior history reset karo."""
    memory = _load_memory()
    if file_path in memory:
        del memory[file_path]
        _save_memory(memory)
        return True
    return False


def get_most_problematic_files(top_n: int = 5) -> List[Dict]:
    """Sabse zyada problematic files lo."""
    memory = _load_memory()

    file_scores = [
        {
            "file": k,
            "stability_score": v.get("stability_score", 100),
            "anomaly_count": v.get("anomaly_count", 0),
            "trend": v.get("trend", "stable"),
            "fix_attempts": v.get("fix_attempts", 0),
        }
        for k, v in memory.items()
    ]

    # Sort by stability (ascending = most problematic first)
    file_scores.sort(key=lambda x: x["stability_score"])

    return file_scores[:top_n]


# ==================================================
# 🔧 INTERNAL HELPERS
# ==================================================

def _calculate_trend(history: List[int]) -> str:
    """Error history se trend calculate karo."""
    if len(history) < 3:
        return "stable"

    recent = history[-3:]
    older = history[-6:-3] if len(history) >= 6 else history[:3]

    recent_avg = sum(recent) / len(recent)
    older_avg = sum(older) / len(older)

    if recent_avg > older_avg * 1.2:
        return "degrading"
    elif recent_avg < older_avg * 0.8:
        return "improving"
    return "stable"


def _is_anomaly(history: List[int], new_value: int) -> bool:
    """Anomaly detection — sudden spike."""
    if len(history) < 5:
        return False

    avg = sum(history[:-1]) / len(history[:-1])
    std_dev = math.sqrt(
        sum((x - avg) ** 2 for x in history[:-1]) / len(history[:-1])
    ) if len(history) > 1 else 0

    # More than 2 standard deviations = anomaly
    return new_value > avg + (2 * std_dev) if std_dev > 0 else False
