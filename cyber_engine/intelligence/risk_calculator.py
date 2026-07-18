"""
from typing import Any, Dict, List, Optional, Tuple, Union, Union
Chhoti Don- Risk Calculator
Comprehensive risk scoring engine.
Phase 2.2 - Full Upgrade
"""

import time
from typing import Dict, List, Optional, Union, Any, Tuple


# ==================================================
# 🎯 SEVERITY MAP
# ==================================================
SEVERITY_MAP = {
    "critical": 9.5,
    "high": 8.0,
    "medium": 5.5,
    "low": 3.0,
    "info": 1.0
}

# Service danger weights
SERVICE_WEIGHTS = {
    "telnet": 25,
    "rdp": 20,
    "smb": 18,
    "mysql": 15,
    "mssql": 15,
    "redis": 15,
    "ftp": 12,
    "ssh": 8,
    "smtp": 6,
    "http": 5,
    "https": 4,
    "dns": 3,
}

# Port danger weights
PORT_WEIGHTS = {
    23: 25,    # Telnet
    3389: 20,  # RDP
    445: 18,   # SMB
    3306: 15,  # MySQL
    1433: 15,  # MSSQL
    6379: 15,  # Redis
    21: 12,    # FTP
    22: 8,     # SSH
    25: 6,     # SMTP
    80: 5,     # HTTP
    443: 4,    # HTTPS
}


# ==================================================
# 🎯 Original Severity-Based Risk (PRESERVED)
# ==================================================
def calculate_risk(severity: str, confidence: float = 0.8) -> Dict[str, Union[float, str]]:
    """
    Original feature preserved.
    Converts severity label into adjusted risk score.
    """
    base_score = SEVERITY_MAP.get(str(severity).lower(), 5.0)
    adjusted_score = round(base_score * confidence, 2)

    if adjusted_score >= 9:
        level = "Critical"
    elif adjusted_score >= 7:
        level = "High"
    elif adjusted_score >= 4:
        level = "Medium"
    else:
        level = "Low"

    return {
        "severity": severity,
        "confidence": confidence,
        "base_score": base_score,
        "adjusted_score": adjusted_score,
        "risk_level": level
    }


# ==================================================
# 🚀 XML-Based Risk (PRESERVED)
# ==================================================
def calculate_risk_score(scan_output: str) -> int:
    """
    Used by NmapWrapper (string XML input).
    Returns numeric risk score (0-100).
    """
    if not isinstance(scan_output, str):
        return 10

    open_ports = scan_output.count("<port")

    if open_ports == 0:
        return 10
    elif open_ports < 5:
        return 40
    elif open_ports < 15:
        return 65
    else:
        return 85


# ==================================================
# 🧠 Structured Recon Risk (PRESERVED + Enhanced)
# ==================================================
def calculate_structured_risk(data: Dict) -> int:
    """
    Risk based on structured scan results.
    Phase 2.2 - CVE + Service Weighted Upgrade
    """
    if not isinstance(data, dict):
        return 10

    open_ports = len(data.get("open_ports", []))
    services = data.get("services", [])
    open_port_details = data.get("open_port_details", [])

    score = 10

    # Base port exposure
    if open_ports > 0:
        score += open_ports * 4

    # Service-based weight
    for svc in services:
        service_name = (svc.get("service") or "").lower()
        for keyword, weight in SERVICE_WEIGHTS.items():
            if keyword in service_name:
                score += weight
                break

    # Port-based weight (from open_port_details)
    for port_info in open_port_details:
        port = port_info.get("port", 0)
        if port in PORT_WEIGHTS:
            score += PORT_WEIGHTS[port] // 2  # Half weight (service already counted)

    # CVE-based boost
    cve_boost = _calculate_cve_boost(data)
    score += cve_boost

    return min(score, 100)


def _calculate_cve_boost(data: Dict) -> int:
    """CVE findings se risk boost calculate karo."""
    cve_analysis = data.get("cve_analysis", {})
    if not cve_analysis:
        return 0

    summary = cve_analysis.get("summary", {})
    critical = summary.get("total_critical", 0)
    exploitable = summary.get("total_exploitable", 0)

    boost = 0
    boost += critical * 8
    boost += exploitable * 5

    return min(boost, 30)


# ==================================================
# 🔥 Pre-Execution Risk Scoring (PRESERVED + Enhanced)
# ==================================================
def calculate_pre_execution_risk(
    target: str,
    port_range: int = 100,
    aggressive: bool = False,
    scan_type: str = "basic"
) -> Dict:
    """
    Used BEFORE scan execution.
    Returns detailed pre-execution risk assessment.
    """
    score = 0
    warnings = []

    # Target analysis
    if isinstance(target, str):
        if "." in target:
            score += 5
        if _is_private_ip(target):
            score -= 2
            warnings.append("Private IP range — internal network scan")
        else:
            score += 5
            warnings.append("Public IP — external target detected")

    # Port range analysis
    if port_range > 10000:
        score += 15
        warnings.append("Large port range — high scan footprint")
    elif port_range > 1000:
        score += 8
        warnings.append("Medium port range scan")
    elif port_range > 100:
        score += 4

    # Scan type analysis
    scan_weights = {
        "aggressive": 15,
        "full": 10,
        "stealth": 5,
        "basic": 2,
    }
    score += scan_weights.get(scan_type, 2)
    if scan_type == "aggressive":
        warnings.append("Aggressive scan — high detection risk")

    # Aggressive flag
    if aggressive:
        score += 5
        warnings.append("Aggressive mode enabled")

    score = min(score, 100)

    # Risk level
    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "pre_execution_score": score,
        "risk_level": level,
        "warnings": warnings,
        "recommendation": _get_recommendation(level),
        "allow_execution": score < 80
    }


def _is_private_ip(ip: str) -> bool:
    """Private IP range check."""
    private_ranges = ["192.168.", "10.", "172.16.", "172.17.",
                      "172.18.", "172.19.", "172.2", "127."]
    return any(ip.startswith(r) for r in private_ranges)


def _get_recommendation(level: str) -> str:
    recommendations = {
        "HIGH": "Guardian approval required. Proceed with extreme caution.",
        "MEDIUM": "Verify target authorization before proceeding.",
        "LOW": "Standard scan. Ensure proper authorization."
    }
    return recommendations.get(level, "Verify authorization.")


# ==================================================
# 🔥 Risk Trend Weighting (PRESERVED + Enhanced)
# ==================================================
def apply_risk_trend(current_score: int, history: List[int]) -> Dict:
    """
    Adjusts risk based on trend pattern.
    Phase 2.2 — Returns detailed trend analysis.
    """
    if not history or len(history) < 2:
        return {
            "original_score": current_score,
            "adjusted_score": current_score,
            "trend": "insufficient_data",
            "trend_boost": 0
        }

    trend_boost = 0
    trend = "stable"

    # Consecutive increase
    if history[-1] > history[-2]:
        trend_boost += 2
        trend = "increasing"

    # 3-point consecutive increase
    if len(history) >= 3 and history[-1] > history[-2] > history[-3]:
        trend_boost += 3
        trend = "rapidly_increasing"

    # Spike detection
    if current_score > (sum(history) / len(history)) * 1.5:
        trend_boost += 5
        trend = "spike_detected"

    adjusted = min(current_score + trend_boost, 100)

    return {
        "original_score": current_score,
        "adjusted_score": adjusted,
        "trend": trend,
        "trend_boost": trend_boost,
        "history_avg": round(sum(history) / len(history), 1)
    }


# ==================================================
# 🎯 Comprehensive Risk Report
# ==================================================
def generate_risk_report(scan_data: Dict, history: List[int] = None) -> Dict:
    """
    Full risk report generate karo from scan data.

    Args:
        scan_data: PortScanner output
        history: Previous risk scores list

    Returns:
        Complete risk assessment report
    """
    # Base structured risk
    base_score = calculate_structured_risk(scan_data)

    # Trend adjustment
    trend_result = apply_risk_trend(base_score, history or [])
    final_score = trend_result["adjusted_score"]

    # Risk level
    if final_score >= 80:
        risk_level = "CRITICAL"
        action = "Immediate investigation required"
    elif final_score >= 60:
        risk_level = "HIGH"
        action = "Prioritize remediation"
    elif final_score >= 40:
        risk_level = "MEDIUM"
        action = "Schedule remediation"
    elif final_score >= 20:
        risk_level = "LOW"
        action = "Monitor and review"
    else:
        risk_level = "INFO"
        action = "No immediate action required"

    # Top risky ports
    open_details = scan_data.get("open_port_details", [])
    risky_ports = []
    for p in open_details:
        port = p.get("port", 0)
        service = p.get("service", "unknown")
        weight = PORT_WEIGHTS.get(port, 0)
        if weight > 0:
            risky_ports.append({
                "port": port,
                "service": service,
                "danger_weight": weight
            })
    risky_ports.sort(key=lambda x: x["danger_weight"], reverse=True)

    return {
        "target": scan_data.get("target", "unknown"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "risk_score": final_score,
        "risk_level": risk_level,
        "action_required": action,
        "base_score": base_score,
        "trend": trend_result["trend"],
        "trend_boost": trend_result["trend_boost"],
        "risky_ports": risky_ports[:5],
        "open_port_count": len(scan_data.get("open_ports", [])),
        "scan_duration": scan_data.get("scan_duration_sec", 0),
    }
