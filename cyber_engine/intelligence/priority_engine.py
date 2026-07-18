"""
Chhoti Don - Priority Engine
Advanced finding prioritization with CVSS scoring,
exploit availability weighting, business impact,
MITRE ATT&CK stage analysis, and SLA-based urgency.
Phase 2.2 - Full Upgrade
"""

from typing import Dict, List, Optional, Tuple
# ==================================================

SEVERITY_WEIGHTS = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 2,
    "info": 0.5,
    "unknown": 3,
}

# MITRE ATT&CK stage danger weights
STAGE_WEIGHTS = {
    "initial_access": 1.8,
    "execution": 1.7,
    "persistence": 1.5,
    "privilege_escalation": 1.9,
    "defense_evasion": 1.4,
    "credential_access": 1.8,
    "lateral_movement": 2.0,
    "collection": 1.3,
    "command_and_control": 1.7,
    "exfiltration": 1.9,
    "impact": 2.0,
    "reconnaissance": 1.0,
    "resource_development": 1.0,
}

# Exploit availability multipliers
EXPLOIT_MULTIPLIERS = {
    "public_exploit": 2.0,
    "metasploit": 1.8,
    "poc_available": 1.5,
    "no_exploit": 1.0,
    "unknown": 1.2,
}

# Asset criticality multipliers
ASSET_CRITICALITY = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 1.2,
    "low": 1.0,
    "unknown": 1.1,
}

# SLA timeframes by priority score
SLA_TIMEFRAMES = {
    (8.0, 10.0): {"urgency": "EMERGENCY", "sla": "4 hours", "color": "#e74c3c"},
    (6.0, 7.9): {"urgency": "CRITICAL", "sla": "24 hours", "color": "#c0392b"},
    (4.0, 5.9): {"urgency": "HIGH", "sla": "72 hours", "color": "#e67e22"},
    (2.0, 3.9): {"urgency": "MEDIUM", "sla": "1 week", "color": "#f39c12"},
    (0.0, 1.9): {"urgency": "LOW", "sla": "1 month", "color": "#27ae60"},
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def prioritize_findings(
    findings: List[Dict],
    heatmap: Dict = None,
    breach_probability: float = 0.5,
    asset_criticality: str = "medium",
    context: Dict = None,
) -> Dict:
    """
    Advanced finding prioritization.
    Preserved + massively upgraded.

    Args:
        findings: List of vulnerability/finding dicts
        heatmap: Threat heatmap data
        breach_probability: 0.0-1.0 breach likelihood
        asset_criticality: Asset importance level
        context: Additional context (internet_facing, patch_level, etc.)

    Returns:
        Prioritized findings with scores, SLAs, and recommendations
    """
    if not findings:
        return {
            "prioritized_findings": [],
            "top_priority": [],
            "summary": {"total": 0},
        }

    context = context or {}
    heatmap = heatmap or {}
    prioritized = []

    for finding in findings:
        score_data = calculate_priority_score(
            finding=finding,
            heatmap=heatmap,
            breach_probability=breach_probability,
            asset_criticality=asset_criticality,
            context=context,
        )

        prioritized.append({
            "finding": finding,
            "priority_score": score_data["final_score"],
            "score_breakdown": score_data["breakdown"],
            "urgency": score_data["urgency"],
            "sla": score_data["sla"],
            "remediation_priority": score_data["remediation_priority"],
        })

    # Sort by priority score
    prioritized.sort(key=lambda x: x["priority_score"], reverse=True)

    # Add rank
    for i, item in enumerate(prioritized, 1):
        item["rank"] = i

    # Statistics
    urgency_counts = {}
    for item in prioritized:
        urg = item["urgency"]
        urgency_counts[urg] = urgency_counts.get(urg, 0) + 1

    return {
        "prioritized_findings": prioritized,
        "top_priority": prioritized[:5],
        "emergency_items": [p for p in prioritized if p["urgency"] == "EMERGENCY"],
        "critical_items": [p for p in prioritized if p["urgency"] == "CRITICAL"],
        "summary": {
            "total": len(prioritized),
            "urgency_distribution": urgency_counts,
            "breach_probability": breach_probability,
            "asset_criticality": asset_criticality,
        },
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


def calculate_priority_score(
    finding: Dict,
    heatmap: Dict = None,
    breach_probability: float = 0.5,
    asset_criticality: str = "medium",
    context: Dict = None,
) -> Dict:
    """
    Single finding ka priority score calculate karo.
    """
    context = context or {}
    heatmap = heatmap or {}

    breakdown = {}

    # Base severity score
    severity = finding.get("severity", "unknown").lower()
    base_score = SEVERITY_WEIGHTS.get(severity, 3)
    breakdown["severity"] = base_score

    # CVSS score integration
    cvss = finding.get("cvss", 0)
    if cvss > 0:
        cvss_contribution = cvss / 2  # Normalize to 0-5
        base_score = max(base_score, cvss_contribution)
        breakdown["cvss"] = round(cvss_contribution, 2)

    # Stage/heatmap bonus
    stage_multiplier = 1.0
    finding_str = str(finding).lower()
    for stage, weight in STAGE_WEIGHTS.items():
        if stage.replace("_", " ") in finding_str or stage in finding_str:
            if weight > stage_multiplier:
                stage_multiplier = weight
            break

    # Also check heatmap stages
    for stage in heatmap.get("stage_heatmap", {}):
        if stage.replace("_", " ") in finding_str:
            heatmap_weight = STAGE_WEIGHTS.get(stage, 1.2)
            if heatmap_weight > stage_multiplier:
                stage_multiplier = heatmap_weight

    breakdown["stage_multiplier"] = stage_multiplier

    # Exploit availability
    exploit_type = finding.get("exploit_available", "unknown")
    if isinstance(exploit_type, bool):
        exploit_type = "public_exploit" if exploit_type else "no_exploit"
    exploit_mult = EXPLOIT_MULTIPLIERS.get(exploit_type, 1.2)
    breakdown["exploit_multiplier"] = exploit_mult

    # Asset criticality
    asset_mult = ASSET_CRITICALITY.get(asset_criticality, 1.1)
    breakdown["asset_criticality"] = asset_mult

    # Breach probability factor
    breach_factor = 0.5 + (breach_probability * 0.5)
    breakdown["breach_factor"] = round(breach_factor, 3)

    # Context bonuses
    context_bonus = 1.0
    if context.get("internet_facing"):
        context_bonus += 0.3
    if context.get("patch_level") == "outdated":
        context_bonus += 0.2
    if context.get("has_sensitive_data"):
        context_bonus += 0.25
    if context.get("no_mfa"):
        context_bonus += 0.15
    breakdown["context_bonus"] = round(context_bonus, 2)

    # Final score calculation
    final_score = (
        base_score
        * stage_multiplier
        * exploit_mult
        * asset_mult
        * breach_factor
        * context_bonus
    )

    # Normalize to 0-10
    final_score = round(min(final_score, 10.0), 2)
    breakdown["final_score"] = final_score

    # SLA determination
    sla_data = _get_sla(final_score)

    # Remediation priority
    remediation = _get_remediation_steps(finding, severity, final_score)

    return {
        "final_score": final_score,
        "breakdown": breakdown,
        "urgency": sla_data["urgency"],
        "sla": sla_data["sla"],
        "color": sla_data["color"],
        "remediation_priority": remediation,
    }


def prioritize_by_attack_path(
    findings: List[Dict],
    attack_stages: List[str],
) -> List[Dict]:
    """
    Attack path ke hisaab se findings prioritize karo.
    Most dangerous path findings get highest priority.
    """
    stage_order = list(STAGE_WEIGHTS.keys())
    prioritized = []

    for finding in findings:
        finding_str = str(finding).lower()

        # Find which attack stage this finding belongs to
        stage_index = len(stage_order)  # Default = last
        for i, stage in enumerate(attack_stages):
            if stage.replace("_", " ") in finding_str or stage in finding_str:
                stage_index = i
                break

        # Earlier in attack chain = higher priority (more to lose)
        path_score = (len(stage_order) - stage_index) / len(stage_order)

        severity = finding.get("severity", "medium").lower()
        base = SEVERITY_WEIGHTS.get(severity, 3)

        score = round(base * (1 + path_score), 2)

        prioritized.append({
            "finding": finding,
            "path_score": score,
            "attack_stage_position": stage_index,
        })

    prioritized.sort(key=lambda x: x["path_score"], reverse=True)
    return prioritized


def generate_remediation_roadmap(prioritized_findings: List[Dict]) -> Dict:
    """
    Prioritized findings se remediation roadmap generate karo.
    """
    roadmap = {
        "immediate": [],    # Emergency/Critical
        "short_term": [],   # High — within week
        "medium_term": [],  # Medium — within month
        "long_term": [],    # Low — backlog
    }

    for item in prioritized_findings:
        urgency = item.get("urgency", "MEDIUM")
        finding = item.get("finding", {})
        score = item.get("priority_score", 0)

        entry = {
            "rank": item.get("rank", 0),
            "finding": finding.get("type") or finding.get("cve_id") or str(finding)[:50],
            "severity": finding.get("severity", "unknown"),
            "score": score,
            "sla": item.get("sla", "Unknown"),
            "remediation": item.get("remediation_priority", {}).get("steps", [])[:2],
        }

        if urgency in ["EMERGENCY", "CRITICAL"]:
            roadmap["immediate"].append(entry)
        elif urgency == "HIGH":
            roadmap["short_term"].append(entry)
        elif urgency == "MEDIUM":
            roadmap["medium_term"].append(entry)
        else:
            roadmap["long_term"].append(entry)

    return {
        "roadmap": roadmap,
        "total_items": sum(len(v) for v in roadmap.values()),
        "immediate_count": len(roadmap["immediate"]),
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


# ==================================================
# 🔧 HELPERS
# ==================================================

def _get_sla(score: float) -> Dict:
    """Score se SLA determine karo."""
    for (low, high), sla_data in SLA_TIMEFRAMES.items():
        if low <= score <= high:
            return sla_data
    return {"urgency": "LOW", "sla": "1 month", "color": "#27ae60"}


def _get_remediation_steps(finding: Dict, severity: str, score: float) -> Dict:
    """Finding ke liye remediation steps generate karo."""
    finding_type = finding.get("type", "").lower()
    cve_id = finding.get("cve_id", "")

    steps = []

    # Generic steps by severity
    if severity == "critical":
        steps = [
            "Patch/update affected component immediately",
            "Isolate affected systems if actively exploited",
            "Enable monitoring for exploitation attempts",
            "Apply compensating controls if patch unavailable",
        ]
    elif severity == "high":
        steps = [
            "Apply available patches within 24-72 hours",
            "Implement compensating controls",
            "Monitor for exploitation attempts",
        ]
    elif severity == "medium":
        steps = [
            "Schedule patching in next maintenance window",
            "Review and harden configuration",
        ]
    else:
        steps = [
            "Review and document finding",
            "Schedule for next security review",
        ]

    # CVE-specific
    if cve_id:
        steps.insert(0, f"Apply patch for {cve_id}")
        steps.append(f"Check vendor advisory for {cve_id}")

    return {
        "steps": steps,
        "estimated_effort": _estimate_effort(severity),
        "requires_restart": severity in ["critical", "high"],
    }


def _estimate_effort(severity: str) -> str:
    """Remediation effort estimate karo."""
    effort_map = {
        "critical": "High (4-8 hours)",
        "high": "Medium (2-4 hours)",
        "medium": "Low (1-2 hours)",
        "low": "Minimal (< 1 hour)",
        "info": "Minimal",
    }
    return effort_map.get(severity, "Unknown")
