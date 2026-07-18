"""
Chhoti Don - Threat Scorer
Advanced threat scoring engine with multi-factor analysis,
contextual scoring, and threat intelligence integration.
Phase 2.2 - Full Upgrade
"""

import datetime
from typing import Dict, List


# ==================================================
# 🎯 SCORING WEIGHTS
# ==================================================

SEVERITY_WEIGHTS = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 2,
    "info": 0.5
}

CVSS_WEIGHT_MAP = {
    (9.0, 10.0): 10,
    (7.0, 8.9): 7,
    (4.0, 6.9): 4,
    (0.1, 3.9): 2,
    (0.0, 0.0): 0,
}

# Service danger scores
SERVICE_DANGER_SCORES = {
    "telnet": 9,
    "rdp": 8,
    "smb": 8,
    "redis": 8,
    "mongodb": 7,
    "mysql": 7,
    "mssql": 7,
    "ftp": 6,
    "ssh": 5,
    "smtp": 4,
    "http": 4,
    "https": 3,
    "dns": 2,
}

# Threat category multipliers
THREAT_MULTIPLIERS = {
    "ransomware": 2.0,
    "apt": 1.8,
    "worm": 1.7,
    "targeted_attack": 1.6,
    "mass_exploit": 1.5,
    "brute_force": 1.2,
    "scan": 0.8,
    "generic": 1.0,
}


# ==================================================
# 🎯 MAIN SCORING FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def calculate_overall_threat(severity_distribution: Dict) -> Dict:
    """
    Original function — preserved + upgraded.
    Multi-factor threat score calculation.
    """
    score = 0
    breakdown = {}

    for sev, count in severity_distribution.items():
        weight = SEVERITY_WEIGHTS.get(sev.lower(), 1)
        contribution = weight * count
        score += contribution
        breakdown[sev] = {
            "count": count,
            "weight": weight,
            "contribution": contribution
        }

    # Exponential penalty for critical findings
    critical_count = severity_distribution.get("critical", 0)
    if critical_count >= 3:
        score *= 1.5
    elif critical_count >= 1:
        score *= 1.2

    score = round(score, 2)

    # Level determination
    if score >= 50:
        level = "Severe"
        action = "Emergency response required"
        color = "#e74c3c"
    elif score >= 30:
        level = "Critical"
        action = "Immediate remediation required"
        color = "#c0392b"
    elif score >= 15:
        level = "Elevated"
        action = "Prioritize remediation"
        color = "#e67e22"
    elif score >= 5:
        level = "Moderate"
        action = "Schedule remediation"
        color = "#f39c12"
    else:
        level = "Low"
        action = "Monitor and review"
        color = "#27ae60"

    return {
        "threat_score": score,
        "threat_level": level,
        "action_required": action,
        "severity_breakdown": breakdown,
        "critical_multiplier_applied": critical_count >= 1,
        "color": color,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


# ==================================================
# 🎯 ADVANCED SCORING CLASS
# ==================================================

class ThreatScorer:
    """
    Advanced Multi-Factor Threat Scorer.
    Combines CVE scores, service risks, exploit availability,
    and contextual factors for comprehensive threat assessment.
    """

    def __init__(self):
        self.scoring_history = []

    # --------------------------------------------------
    # 🔍 CVE-Based Scoring
    # --------------------------------------------------
    def score_from_cves(self, cve_findings: List[Dict]) -> Dict:
        """CVE findings se threat score calculate karo."""
        total_score = 0
        critical_cves = []
        exploitable_cves = []

        for finding in cve_findings:
            for cve in finding.get("cves", []):
                cvss = cve.get("cvss", 0)
                weight = self._cvss_to_weight(cvss)
                total_score += weight

                if cvss >= 9.0:
                    critical_cves.append(cve["cve_id"])
                if cve.get("exploit_available"):
                    exploitable_cves.append(cve["cve_id"])
                    total_score += 2  # Exploit availability bonus

        return {
            "cve_score": round(total_score, 2),
            "critical_cves": critical_cves,
            "exploitable_cves": exploitable_cves,
            "total_cves_scored": sum(len(f.get("cves", [])) for f in cve_findings),
        }

    # --------------------------------------------------
    # 🔌 Service-Based Scoring
    # --------------------------------------------------
    def score_from_services(self, open_port_details: List[Dict]) -> Dict:
        """Open services se threat score calculate karo."""
        total_score = 0
        high_risk_services = []

        for port_info in open_port_details:
            service = port_info.get("service", "unknown").lower()
            danger = SERVICE_DANGER_SCORES.get(service, 1)
            total_score += danger

            if danger >= 7:
                high_risk_services.append({
                    "port": port_info.get("port"),
                    "service": service,
                    "danger_score": danger,
                })

        return {
            "service_score": round(total_score, 2),
            "high_risk_services": high_risk_services,
            "total_services_scored": len(open_port_details),
        }

    # --------------------------------------------------
    # 🧠 Contextual Scoring
    # --------------------------------------------------
    def score_contextual(
        self,
        exploit_count: int = 0,
        easy_exploits: int = 0,
        lateral_movement_risk: bool = False,
        internet_facing: bool = True,
        patch_level: str = "unknown"
    ) -> Dict:
        """Contextual factors se additional scoring."""
        score = 0
        factors = []

        if exploit_count > 0:
            score += exploit_count * 3
            factors.append(f"Exploits available: +{exploit_count * 3}")

        if easy_exploits > 0:
            score += easy_exploits * 5
            factors.append(f"Easy exploits: +{easy_exploits * 5}")

        if lateral_movement_risk:
            score += 15
            factors.append("Lateral movement risk: +15")

        if internet_facing:
            score += 10
            factors.append("Internet-facing target: +10")

        patch_scores = {"outdated": 10, "unknown": 5, "partial": 3, "current": 0}
        patch_score = patch_scores.get(patch_level, 5)
        score += patch_score
        if patch_score > 0:
            factors.append(f"Patch level ({patch_level}): +{patch_score}")

        return {
            "contextual_score": round(score, 2),
            "factors": factors,
        }

    # --------------------------------------------------
    # 🚀 Comprehensive Score
    # --------------------------------------------------
    def comprehensive_score(self, scan_result: Dict) -> Dict:
        """
        Full comprehensive threat score from scan result.
        Combines all scoring factors.
        """
        start_time = time.time()

        # Extract data
        open_details = scan_result.get("open_port_details", [])
        cve_findings = scan_result.get("cve_analysis", {}).get("findings", [])
        exploit_data = scan_result.get("exploit_suggestions", {})
        risk_report = scan_result.get("risk_report", {})

        # Component scores
        cve_score_data = self.score_from_cves(cve_findings)
        service_score_data = self.score_from_services(open_details)

        exploit_count = exploit_data.get("total_exploits_found", 0) if exploit_data else 0
        easy_exploits = exploit_data.get("summary", {}).get("easy_exploits", 0) if exploit_data else 0

        contextual_data = self.score_contextual(
            exploit_count=exploit_count,
            easy_exploits=easy_exploits,
            lateral_movement_risk=any(
                p.get("service") in ["smb", "rdp", "ssh"]
                for p in open_details
            ),
            internet_facing=True,
        )

        # Final score
        cve_score = cve_score_data["cve_score"]
        service_score = service_score_data["service_score"]
        context_score = contextual_data["contextual_score"]

        # Weighted combination
        final_score = (cve_score * 0.45) + (service_score * 0.30) + (context_score * 0.25)
        final_score = round(min(final_score, 100), 2)

        # Threat level
        if final_score >= 80:
            threat_level = "CRITICAL"
            urgency = "EMERGENCY"
            action = "Immediate incident response required"
        elif final_score >= 60:
            threat_level = "HIGH"
            urgency = "URGENT"
            action = "Remediate within 24 hours"
        elif final_score >= 40:
            threat_level = "MEDIUM"
            urgency = "HIGH"
            action = "Remediate within 1 week"
        elif final_score >= 20:
            threat_level = "LOW"
            urgency = "MEDIUM"
            action = "Schedule remediation"
        else:
            threat_level = "MINIMAL"
            urgency = "LOW"
            action = "Monitor and review"

        result = {
            "target": scan_result.get("target", "unknown"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "final_score": final_score,
            "threat_level": threat_level,
            "urgency": urgency,
            "action_required": action,
            "score_breakdown": {
                "cve_score": cve_score,
                "cve_weight": "45%",
                "service_score": service_score,
                "service_weight": "30%",
                "contextual_score": context_score,
                "contextual_weight": "25%",
            },
            "cve_analysis": cve_score_data,
            "service_analysis": service_score_data,
            "contextual_factors": contextual_data["factors"],
            "analysis_time_sec": round(time.time() - start_time, 3),
        }

        # Store history
        self.scoring_history.append({
            "target": scan_result.get("target"),
            "score": final_score,
            "level": threat_level,
            "timestamp": time.time(),
        })

        return result

    # --------------------------------------------------
    # 📊 Threat Trend Analysis
    # --------------------------------------------------
    def get_threat_trend(self, target: str = None) -> Dict:
        """Historical threat trend analyze karo."""
        history = self.scoring_history

        if target:
            history = [h for h in history if h.get("target") == target]

        if not history:
            return {"trend": "no_data", "scores": []}

        scores = [h["score"] for h in history]
        avg = sum(scores) / len(scores)

        if len(scores) >= 2:
            if scores[-1] > scores[-2]:
                trend = "increasing"
            elif scores[-1] < scores[-2]:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "current_score": scores[-1] if scores else 0,
            "average_score": round(avg, 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "scores": scores[-10:],
            "assessments": len(scores),
        }

    # --------------------------------------------------
    # 🔧 Helpers
    # --------------------------------------------------
    def _cvss_to_weight(self, cvss: float) -> float:
        """CVSS score ko weight mein convert karo."""
        if cvss >= 9.0:
            return 10
        elif cvss >= 7.0:
            return 7
        elif cvss >= 4.0:
            return 4
        elif cvss >= 0.1:
            return 2
        return 0
