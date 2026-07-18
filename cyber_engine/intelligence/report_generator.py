"""
Chhoti Don - Report Generator
Advanced security report generation with executive summaries,
technical findings, remediation roadmaps, and multi-format export.
Phase 2.2 - Full Upgrade
"""

import datetime
import time
from typing import Dict, Generator, List, Optional# 🎯 REPORT TEMPLATES
# ==================================================

RECOMMENDATION_MAP = {
    "Severe": "EMERGENCY: Immediate remediation required. Isolate affected systems. Engage incident response team.",
    "Critical": "CRITICAL: Remediate within 24 hours. Apply emergency patches. Enable enhanced monitoring.",
    "Elevated": "HIGH PRIORITY: Address within 72 hours. Apply available patches. Implement compensating controls.",
    "Moderate": "MEDIUM PRIORITY: Schedule remediation within 1 week. Review configurations.",
    "Low": "LOW PRIORITY: Monitor and maintain security posture. Include in next maintenance cycle.",
}

CVSS_LABELS = {
    (9.0, 10.0): "Critical",
    (7.0, 8.9): "High",
    (4.0, 6.9): "Medium",
    (0.1, 3.9): "Low",
    (0.0, 0.0): "None",
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def generate_report(
    target: str,
    aggregated_data: Dict,
    threat_summary: Dict,
    scan_metadata: Dict = None,
    priority_data: Dict = None,
) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Generates comprehensive security assessment report.
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    scan_metadata = scan_metadata or {}
    priority_data = priority_data or {}

    # Executive summary
    executive_summary = _build_executive_summary(
        target, aggregated_data, threat_summary
    )

    # Technical findings
    technical_findings = _build_technical_findings(
        aggregated_data.get("findings", [])
    )

    # Remediation roadmap
    remediation = _build_remediation_roadmap(
        aggregated_data.get("findings", []),
        threat_summary
    )

    # Risk matrix
    risk_matrix = _build_risk_matrix(aggregated_data.get("findings", []))

    # Compliance notes
    compliance = _build_compliance_notes(aggregated_data.get("findings", []))

    return {
        "report_id": f"RPT-{int(time.time())}",
        "target": target,
        "timestamp": timestamp,
        "generated_by": "Chhoti Don Intelligence Engine v2.2",

        # Core data (backward compat)
        "summary": {
            "total_findings": aggregated_data.get("total_findings", 0),
            "severity_distribution": aggregated_data.get("severity_distribution", {}),
            "threat_score": threat_summary.get("threat_score", 0),
            "threat_level": threat_summary.get("threat_level", "Unknown"),
        },
        "detailed_findings": aggregated_data.get("findings", []),
        "recommendation": generate_recommendation(threat_summary.get("threat_level", "Unknown")),

        # Enhanced sections
        "executive_summary": executive_summary,
        "technical_findings": technical_findings,
        "remediation_roadmap": remediation,
        "risk_matrix": risk_matrix,
        "compliance_notes": compliance,

        # Priority data
        "top_priority_findings": priority_data.get("top_priority", [])[:5],

        # Metadata
        "scan_metadata": {
            "scan_duration": scan_metadata.get("duration", "N/A"),
            "scan_type": scan_metadata.get("type", "automated"),
            "tool_version": "2.2",
            "timestamp": timestamp,
        },
    }


def generate_recommendation(level: str) -> str:
    """
    Original function — preserved + upgraded.
    """
    return RECOMMENDATION_MAP.get(
        level,
        "Review all findings manually and consult security team."
    )


# ==================================================
# 🎯 SECTION BUILDERS
# ==================================================

def _build_executive_summary(
    target: str,
    aggregated_data: Dict,
    threat_summary: Dict
) -> Dict:
    """Executive summary build karo."""
    total = aggregated_data.get("total_findings", 0)
    sev_dist = aggregated_data.get("severity_distribution", {})
    threat_level = threat_summary.get("threat_level", "Unknown")
    threat_score = threat_summary.get("threat_score", 0)

    critical = sev_dist.get("critical", 0)
    high = sev_dist.get("high", 0)
    medium = sev_dist.get("medium", 0)

    # Overall verdict
    if threat_level in ["Severe", "Critical"] or critical >= 2:
        verdict = "CRITICAL RISK — Immediate action required"
        action_required = True
    elif threat_level == "Elevated" or high >= 3:
        verdict = "HIGH RISK — Urgent remediation needed"
        action_required = True
    elif threat_level == "Moderate":
        verdict = "MODERATE RISK — Remediation recommended"
        action_required = False
    else:
        verdict = "LOW RISK — Maintain security posture"
        action_required = False

    return {
        "target": target,
        "verdict": verdict,
        "threat_level": threat_level,
        "threat_score": threat_score,
        "action_required": action_required,
        "key_findings": {
            "total_vulnerabilities": total,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": sev_dist.get("low", 0),
        },
        "key_risks": _identify_key_risks(aggregated_data.get("findings", [])),
        "business_impact": _assess_business_impact(threat_level, critical, high),
    }


def _build_technical_findings(findings: List[Dict]) -> List[Dict]:
    """Technical findings section build karo."""
    technical = []

    for finding in findings:
        cve_id = finding.get("cve_id", "")
        severity = finding.get("severity", "unknown")
        cvss = finding.get("cvss", 0)

        entry = {
            "id": cve_id or finding.get("type", "UNKNOWN"),
            "title": finding.get("description", finding.get("type", "Unknown Finding"))[:100],
            "severity": severity.upper(),
            "cvss_score": cvss,
            "cvss_label": _cvss_to_label(cvss),
            "affected": finding.get("service") or finding.get("port") or "Unknown",
            "exploit_available": finding.get("exploit_available", False),
            "mitre_technique": finding.get("mitre", ""),
            "remediation": finding.get("remediation", ""),
            "references": finding.get("references", [])[:3],
        }
        technical.append(entry)

    # Sort by CVSS then severity
    technical.sort(
        key=lambda x: (x["cvss_score"] or 0),
        reverse=True
    )

    return technical


def _build_remediation_roadmap(findings: List[Dict], threat_summary: Dict) -> Dict:
    """Remediation roadmap build karo."""
    immediate = []    # Critical/High — within 24h
    short_term = []   # Medium — within 1 week
    long_term = []    # Low — within 1 month

    for finding in findings:
        severity = finding.get("severity", "low").lower()
        cve_id = finding.get("cve_id", "")
        remediation = finding.get("remediation", "Review and patch")

        item = {
            "finding": cve_id or finding.get("type", "Unknown"),
            "severity": severity,
            "action": remediation,
            "exploit_available": finding.get("exploit_available", False),
        }

        if severity in ["critical", "high"]:
            immediate.append(item)
        elif severity == "medium":
            short_term.append(item)
        else:
            long_term.append(item)

    return {
        "immediate_actions": immediate[:5],
        "short_term_actions": short_term[:5],
        "long_term_actions": long_term[:5],
        "total_actions": len(immediate) + len(short_term) + len(long_term),
        "estimated_remediation_time": _estimate_total_time(
            len(immediate), len(short_term), len(long_term)
        ),
    }


def _build_risk_matrix(findings: List[Dict]) -> Dict:
    """Risk matrix build karo — likelihood vs impact."""
    matrix = {
        "high_likelihood_high_impact": [],
        "high_likelihood_low_impact": [],
        "low_likelihood_high_impact": [],
        "low_likelihood_low_impact": [],
    }

    for finding in findings:
        severity = finding.get("severity", "low").lower()
        exploit = finding.get("exploit_available", False)

        high_likelihood = exploit or severity in ["critical"]
        high_impact = severity in ["critical", "high"]

        entry = finding.get("cve_id") or finding.get("type", "Unknown")

        if high_likelihood and high_impact:
            matrix["high_likelihood_high_impact"].append(entry)
        elif high_likelihood:
            matrix["high_likelihood_low_impact"].append(entry)
        elif high_impact:
            matrix["low_likelihood_high_impact"].append(entry)
        else:
            matrix["low_likelihood_low_impact"].append(entry)

    return matrix


def _build_compliance_notes(findings: List[Dict]) -> List[str]:
    """Compliance implications note karo."""
    notes = []
    has_critical = any(f.get("severity") == "critical" for f in findings)
    has_data_findings = any(
        "data" in str(f).lower() or "credential" in str(f).lower()
        for f in findings
    )

    if has_critical:
        notes.append("PCI DSS: Critical vulnerabilities require immediate remediation (Req 6.3)")
        notes.append("ISO 27001: Vulnerability management process review required (A.12.6)")

    if has_data_findings:
        notes.append("GDPR: Data exposure findings may require breach notification assessment")
        notes.append("HIPAA: Review for potential PHI exposure risks")

    if not notes:
        notes.append("No immediate compliance concerns identified")

    return notes


# ==================================================
# 📄 EXPORT FUNCTIONS (NEW)
# ==================================================

def export_report_json(report: Dict, output_path: str = None) -> str:
    """Report ko JSON file mein export karo."""
    if not output_path:
        target = report.get("target", "unknown").replace(".", "_")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"report_{target}_{ts}.json"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return output_path
    except Exception as e:
        return f"Error: {e}"


def export_report_txt(report: Dict, output_path: str = None) -> str:
    """Report ko TXT file mein export karo."""
    if not output_path:
        target = report.get("target", "unknown").replace(".", "_")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"report_{target}_{ts}.txt"

    lines = _build_txt_report(report)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return output_path
    except Exception as e:
        return f"Error: {e}"


def _build_txt_report(report: Dict) -> List[str]:
    """TXT report lines build karo."""
    lines = [
        "=" * 65,
        "  CHHOTI DON SECURITY ASSESSMENT REPORT",
        "=" * 65,
        f"  Report ID : {report.get('report_id', 'N/A')}",
        f"  Target    : {report.get('target', 'N/A')}",
        f"  Generated : {report.get('timestamp', 'N/A')[:19]}",
        "=" * 65,
        "",
    ]

    # Executive Summary
    exec_sum = report.get("executive_summary", {})
    if exec_sum:
        lines += [
            "[ EXECUTIVE SUMMARY ]",
            "-" * 45,
            f"  Verdict      : {exec_sum.get('verdict', 'N/A')}",
            f"  Threat Level : {exec_sum.get('threat_level', 'N/A')}",
            f"  Threat Score : {exec_sum.get('threat_score', 0)}",
            "",
        ]

    # Key findings
    summary = report.get("summary", {})
    sev = summary.get("severity_distribution", {})
    lines += [
        "[ FINDINGS SUMMARY ]",
        "-" * 45,
        f"  Total      : {summary.get('total_findings', 0)}",
        f"  Critical   : {sev.get('critical', 0)}",
        f"  High       : {sev.get('high', 0)}",
        f"  Medium     : {sev.get('medium', 0)}",
        f"  Low        : {sev.get('low', 0)}",
        "",
    ]

    # Recommendations
    lines += [
        "[ RECOMMENDATION ]",
        "-" * 45,
        f"  {report.get('recommendation', 'N/A')}",
        "",
        "=" * 65,
    ]

    return lines


def generate_executive_brief(report: Dict) -> str:
    """Short executive brief generate karo."""
    target = report.get("target", "Unknown")
    exec_sum = report.get("executive_summary", {})
    summary = report.get("summary", {})

    verdict = exec_sum.get("verdict", "Unknown risk level")
    total = summary.get("total_findings", 0)
    critical = summary.get("severity_distribution", {}).get("critical", 0)
    threat_score = summary.get("threat_score", 0)

    brief = (
        f"Security assessment of {target} identified {total} vulnerability(s). "
        f"Threat Score: {threat_score}. "
        f"Verdict: {verdict}. "
    )

    if critical > 0:
        brief += f"{critical} critical finding(s) require immediate attention. "

    brief += report.get("recommendation", "")

    return brief


# ==================================================
# 🔧 HELPERS
# ==================================================

def _identify_key_risks(findings: List[Dict]) -> List[str]:
    """Key risks identify karo."""
    risks = []
    for f in findings:
        if f.get("severity") in ["critical", "high"]:
            desc = f.get("description") or f.get("type") or f.get("cve_id", "")
            if desc:
                risks.append(desc[:80])
    return risks[:5]


def _assess_business_impact(threat_level: str, critical: int, high: int) -> str:
    """Business impact assess karo."""
    if threat_level in ["Severe", "Critical"] or critical >= 2:
        return "SEVERE — Potential for data breach, system compromise, or service disruption"
    elif critical >= 1 or high >= 3:
        return "HIGH — Significant risk to data confidentiality and system integrity"
    elif high >= 1:
        return "MODERATE — Risk to system availability and data security"
    else:
        return "LOW — Limited business impact expected"


def _cvss_to_label(cvss: float) -> str:
    """CVSS score to label."""
    for (low, high), label in CVSS_LABELS.items():
        if low <= cvss <= high:
            return label
    return "None"


def _estimate_total_time(immediate: int, short: int, long: int) -> str:
    """Total remediation time estimate karo."""
    hours = (immediate * 4) + (short * 2) + (long * 1)
    if hours > 40:
        return f"~{hours // 8} days"
    elif hours > 8:
        return f"~{hours} hours"
    else:
        return f"~{hours} hours"
