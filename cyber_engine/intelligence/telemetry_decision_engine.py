"""
Chhoti Don EvolveX - Telemetry Decision Engine
Advanced system health monitoring, rule stability analysis,
performance tracking, and adaptive decision making.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
import math
from typing import Any, Dict, List


# ==================================================
# 🎯 THRESHOLDS
# ==================================================

HEALTH_THRESHOLDS = {
    "unstable_ratio": 0.60,      # failure ratio for unstable
    "overconfident_min_attempts": 5,
    "min_attempts_for_analysis": 3,
    "stability_recovery_threshold": 0.70,
}

HEALTH_GRADES = {
    "excellent": {"min_score": 85, "label": "Excellent", "color": "#27ae60"},
    "good": {"min_score": 70, "label": "Good", "color": "#2ecc71"},
    "moderate": {"min_score": 50, "label": "Moderate", "color": "#f39c12"},
    "unstable": {"min_score": 30, "label": "Unstable", "color": "#e67e22"},
    "critical": {"min_score": 0, "label": "Critical", "color": "#e74c3c"},
}

# Performance metrics history
_performance_history = []
_system_events = []


# ==================================================
# 📊 RULE STABILITY ANALYSIS (PRESERVED + UPGRADED)
# ==================================================

def analyze_rule_stability() -> Dict[str, Any]:
    """
    Analyze rule stability from fix stats.
    Preserved + upgraded with trend analysis.
    """
    try:
        from cyber_engine.code_intelligence.fix_rules import RULE_STATS
    except ImportError:
        return {
            "unstable_rules": [],
            "stable_rules": [],
            "overconfident_rules": [],
            "trending_rules": [],
            "error": "fix_rules not available",
        }

    unstable_rules = []
    overconfident_rules = []
    stable_rules = []
    trending_rules = []
    rule_details = {}

    for rule, stats in RULE_STATS.items():
        success = stats.get("success", 0)
        failure = stats.get("failure", 0)
        total = success + failure

        if total < HEALTH_THRESHOLDS["min_attempts_for_analysis"]:
            continue

        failure_ratio = failure / total if total > 0 else 0
        success_ratio = success / total if total > 0 else 0

        rule_details[rule] = {
            "success": round(success, 2),
            "failure": round(failure, 2),
            "total": round(total, 2),
            "failure_ratio": round(failure_ratio, 3),
            "success_ratio": round(success_ratio, 3),
        }

        if failure_ratio > HEALTH_THRESHOLDS["unstable_ratio"]:
            unstable_rules.append(rule)
        elif success_ratio > 0.80:
            stable_rules.append(rule)

        if (success > HEALTH_THRESHOLDS["overconfident_min_attempts"]
                and failure > success):
            overconfident_rules.append(rule)

        # Trending (recently improving or degrading)
        if total >= 10:
            recent_ratio = success / total
            if 0.40 <= recent_ratio <= 0.60:
                trending_rules.append(rule)

    return {
        "unstable_rules": unstable_rules,
        "stable_rules": stable_rules,
        "overconfident_rules": overconfident_rules,
        "trending_rules": trending_rules,
        "rule_details": rule_details,
        "total_rules_analyzed": len(rule_details),
    }


# ==================================================
# 📈 SYSTEM HEALTH GRADING (PRESERVED + UPGRADED)
# ==================================================

def evaluate_system_health(stability_data: Dict[str, Any]) -> str:
    """
    Evaluate system health grade.
    Preserved + upgraded with numeric scoring.
    """
    score = _calculate_health_score(stability_data)

    if score >= 85:
        return "stable"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "moderate"
    elif score >= 30:
        return "unstable"
    else:
        return "critical"


def _calculate_health_score(stability_data: Dict) -> float:
    """Numeric health score calculate karo (0-100)."""
    score = 100.0

    unstable = len(stability_data.get("unstable_rules", []))
    overconfident = len(stability_data.get("overconfident_rules", []))
    total_analyzed = stability_data.get("total_rules_analyzed", 0)

    if total_analyzed > 0:
        # Deductions
        score -= unstable * 15
        score -= overconfident * 10

        # Bonus for stable rules
        stable = len(stability_data.get("stable_rules", []))
        score += (stable / total_analyzed) * 20

    return max(0, min(100, score))


# ==================================================
# 🚨 ALERT GENERATOR (PRESERVED + UPGRADED)
# ==================================================

def generate_alerts(stability_data: Dict[str, Any]) -> List[str]:
    """
    Generate system alerts.
    Preserved + upgraded with severity levels.
    """
    alerts = []

    unstable = stability_data.get("unstable_rules", [])
    overconfident = stability_data.get("overconfident_rules", [])
    trending = stability_data.get("trending_rules", [])
    total = stability_data.get("total_rules_analyzed", 0)

    if unstable:
        alerts.append(
            f"Unstable rules detected: {', '.join(unstable)}"
        )

    if overconfident:
        alerts.append(
            f"Overconfidence detected in rules: {', '.join(overconfident)}"
        )

    if trending:
        alerts.append(
            f"Rules in flux (monitor): {', '.join(trending[:3])}"
        )

    if total == 0:
        alerts.append("No rule statistics available — run auto-fix first")

    return alerts


# ==================================================
# 📊 PERFORMANCE TRACKER (NEW)
# ==================================================

def record_performance_metric(
    operation: str,
    duration_sec: float,
    success: bool,
    metadata: Dict = None,
) -> None:
    """Performance metric record karo."""
    _performance_history.append({
        "operation": operation,
        "duration_sec": duration_sec,
        "success": success,
        "timestamp": time.time(),
        "metadata": metadata or {},
    })

    # Keep last 1000 metrics
    if len(_performance_history) > 1000:
        _performance_history.pop(0)


def get_performance_metrics() -> Dict:
    """Performance metrics analyze karo."""
    if not _performance_history:
        return {"status": "no_data"}

    by_operation = defaultdict(list)
    for metric in _performance_history:
        by_operation[metric["operation"]].append(metric)

    analysis = {}
    for op, metrics in by_operation.items():
        durations = [m["duration_sec"] for m in metrics]
        successes = sum(1 for m in metrics if m["success"])

        analysis[op] = {
            "total_calls": len(metrics),
            "success_rate": round(successes / len(metrics) * 100, 1),
            "avg_duration": round(sum(durations) / len(durations), 3),
            "max_duration": round(max(durations), 3),
            "min_duration": round(min(durations), 3),
        }

    return {
        "operations": analysis,
        "total_metrics": len(_performance_history),
        "time_range": {
            "start": datetime.datetime.fromtimestamp(
                _performance_history[0]["timestamp"]
            ).isoformat(),
            "end": datetime.datetime.fromtimestamp(
                _performance_history[-1]["timestamp"]
            ).isoformat(),
        }
    }


# ==================================================
# 📋 SYSTEM EVENTS (NEW)
# ==================================================

def log_system_event(
    event_type: str,
    message: str,
    severity: str = "info",
    data: Dict = None,
) -> None:
    """System event log karo."""
    _system_events.append({
        "event_type": event_type,
        "message": message,
        "severity": severity,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "data": data or {},
    })

    if len(_system_events) > 500:
        _system_events.pop(0)


def get_recent_events(n: int = 20, severity: str = None) -> List[Dict]:
    """Recent system events lo."""
    events = _system_events
    if severity:
        events = [e for e in events if e["severity"] == severity]
    return events[-n:]


# ==================================================
# 🔍 ANOMALY DETECTION (NEW)
# ==================================================

def detect_anomalies() -> List[Dict]:
    """System anomalies detect karo."""
    anomalies = []

    if len(_performance_history) < 10:
        return anomalies

    # Slow operation detection
    by_op = defaultdict(list)
    for m in _performance_history[-100:]:
        by_op[m["operation"]].append(m["duration_sec"])

    for op, durations in by_op.items():
        if len(durations) < 3:
            continue

        avg = sum(durations) / len(durations)
        std = math.sqrt(sum((d - avg) ** 2 for d in durations) / len(durations))

        # Check last operation
        last = durations[-1]
        if std > 0 and last > avg + (2 * std):
            anomalies.append({
                "type": "slow_operation",
                "operation": op,
                "current_duration": last,
                "avg_duration": round(avg, 3),
                "severity": "warning",
            })

    # High failure rate
    recent = _performance_history[-50:]
    if recent:
        failure_rate = sum(1 for m in recent if not m["success"]) / len(recent)
        if failure_rate > 0.3:
            anomalies.append({
                "type": "high_failure_rate",
                "failure_rate": round(failure_rate * 100, 1),
                "severity": "error",
                "description": f"High failure rate: {failure_rate*100:.1f}% in last 50 operations",
            })

    return anomalies


# ==================================================
# 🧠 MAIN DECISION ENGINE (PRESERVED + UPGRADED)
# ==================================================

def run_telemetry_decision_engine() -> Dict[str, Any]:
    """
    Main telemetry decision engine.
    Preserved + upgraded with full analysis.
    """
    start_time = time.time()

    # Core analysis
    stability = analyze_rule_stability()
    health = evaluate_system_health(stability)
    alerts = generate_alerts(stability)

    # Health score
    health_score = _calculate_health_score(stability)

    # Performance metrics
    perf_metrics = get_performance_metrics()

    # Anomaly detection
    anomalies = detect_anomalies()

    # Recent events
    recent_events = get_recent_events(10)

    # Recommendations
    recommendations = _generate_recommendations(
        health, stability, anomalies
    )

    # Decision actions
    actions = _determine_actions(health, stability, anomalies)

    result = {
        "system_health": health,
        "health_score": round(health_score, 1),
        "alerts": alerts,
        "stability_snapshot": stability,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "actions": actions,
        "performance_summary": perf_metrics.get("operations", {}),
        "recent_events": recent_events,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "analysis_time_sec": round(time.time() - start_time, 3),
    }

    # Log this run
    log_system_event(
        "telemetry_run",
        f"Health: {health} ({health_score:.1f}), Alerts: {len(alerts)}",
        severity="warning" if health in ["unstable", "critical"] else "info",
    )

    return result


def _generate_recommendations(
    health: str,
    stability: Dict,
    anomalies: List[Dict],
) -> List[str]:
    """System recommendations generate karo."""
    recs = []

    if health == "critical":
        recs.append("CRITICAL: Disable auto-fix mode immediately and review manually")
        recs.append("Run full diagnostic on all unstable rules")

    elif health == "unstable":
        recs.append("Switch to restricted governance mode")
        recs.append("Review and manually fix failing rules")

    elif health == "moderate":
        recs.append("Switch to cautious governance mode")
        recs.append("Monitor unstable rules closely")

    unstable = stability.get("unstable_rules", [])
    if unstable:
        recs.append(f"Disable or retrain rules: {', '.join(unstable[:3])}")

    if anomalies:
        recs.append("Investigate detected anomalies in system performance")

    if not recs:
        recs.append("System operating normally — continue monitoring")

    return recs


def _determine_actions(
    health: str,
    stability: Dict,
    anomalies: List[Dict],
) -> List[Dict]:
    """Automatic actions determine karo."""
    actions = []

    if health in ["unstable", "critical"]:
        actions.append({
            "action": "set_governance_mode",
            "value": "restricted" if health == "critical" else "cautious",
            "reason": f"Health is {health}",
            "auto_apply": True,
        })

    unstable = stability.get("unstable_rules", [])
    for rule in unstable[:3]:
        actions.append({
            "action": "disable_rule",
            "rule": rule,
            "reason": "High failure ratio",
            "auto_apply": True,
        })

    return actions
