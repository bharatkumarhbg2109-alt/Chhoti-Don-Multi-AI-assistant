"""
Chhoti Don - Vulnerability Aggregator
Advanced vulnerability aggregation, deduplication,
correlation, and intelligence enrichment.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
import hashlib
from typing import Dict, List


# ==================================================
# 🎯 AGGREGATION CONFIG
# ==================================================

SEVERITY_ORDER = {
    "critical": 0, "high": 1, "medium": 2,
    "low": 3, "info": 4, "unknown": 5
}

SEVERITY_SCORES = {
    "critical": 10, "high": 7,
    "medium": 4, "low": 2, "info": 0.5, "unknown": 1
}

# Finding type categories
FINDING_CATEGORIES = {
    "web": ["sql_injection", "xss", "csrf", "ssrf", "lfi", "rfi",
            "sqli", "directory_traversal", "cors_misconfiguration"],
    "network": ["open_port", "service_exposed", "unencrypted_protocol",
                "firewall_bypass", "port_scan"],
    "authentication": ["weak_credentials", "brute_force", "default_password",
                       "auth_bypass", "credential_exposure"],
    "software": ["cve", "outdated_software", "missing_patch",
                 "vulnerable_dependency"],
    "configuration": ["misconfiguration", "missing_header", "insecure_setting",
                      "excessive_permissions"],
    "malware": ["c2_indicator", "malicious_file", "suspicious_process",
                "ransomware", "trojan"],
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def aggregate_findings(*sources) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Advanced vulnerability aggregation with deduplication.
    """
    aggregator = VulnAggregator()
    return aggregator.aggregate(*sources)


# ==================================================
# 🧠 VULNERABILITY AGGREGATOR CLASS
# ==================================================

class VulnAggregator:
    """
    Advanced Vulnerability Aggregation Engine.
    Deduplicates, correlates, and enriches findings.
    """

    def __init__(self):
        self.findings_db = {}
        self.correlation_map = defaultdict(list)

    # ==================================================
    # 🚀 Main Aggregation
    # ==================================================
    def aggregate(self, *sources) -> Dict:
        """
        Multiple sources se findings aggregate karo.

        Args:
            *sources: Dicts with 'findings' key or direct finding lists

        Returns:
            Aggregated findings with analysis
        """
        start_time = time.time()
        all_findings = []

        # Extract findings from all sources
        for source in sources:
            if isinstance(source, dict):
                if "findings" in source:
                    all_findings.extend(source["findings"])
                elif "open_port_details" in source:
                    # Port scan result
                    all_findings.extend(
                        self._convert_port_findings(source)
                    )
                elif "severity" in source:
                    # Single finding
                    all_findings.append(source)
            elif isinstance(source, list):
                all_findings.extend(source)

        # Deduplicate
        deduplicated = self._deduplicate(all_findings)

        # Categorize
        categorized = self._categorize(deduplicated)

        # Severity distribution
        severity_dist = self._count_severities(deduplicated)

        # Critical findings
        critical = [f for f in deduplicated if f.get("severity") == "critical"]
        exploitable = [f for f in deduplicated if f.get("exploit_available")]

        # Correlations
        correlations = self._find_correlations(deduplicated)

        # Attack chains
        attack_chains = self._identify_attack_chains(deduplicated)

        # Enrichment
        enriched = self._enrich_findings(deduplicated)

        # Risk score
        risk_score = self._calculate_aggregate_risk(deduplicated)

        return {
            # Backward compat
            "total_findings": len(deduplicated),
            "severity_distribution": severity_dist,
            "findings": deduplicated,

            # Enhanced
            "deduplicated_count": len(all_findings) - len(deduplicated),
            "categorized": categorized,
            "critical_findings": critical,
            "exploitable_findings": exploitable,
            "correlations": correlations,
            "attack_chains": attack_chains,
            "risk_score": risk_score,
            "top_findings": self._get_top_findings(deduplicated, 5),
            "sources_processed": len(sources),
            "aggregation_time_sec": round(time.time() - start_time, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    # ==================================================
    # 🔍 Deduplication
    # ==================================================
    def _deduplicate(self, findings: List[Dict]) -> List[Dict]:
        """Duplicate findings remove karo."""
        seen_hashes = set()
        unique = []

        for finding in findings:
            fhash = self._finding_hash(finding)

            if fhash not in seen_hashes:
                seen_hashes.add(fhash)
                unique.append(finding)

        return unique

    def _finding_hash(self, finding: Dict) -> str:
        """Finding ka unique hash generate karo."""
        key_parts = [
            str(finding.get("cve_id", "")),
            str(finding.get("type", "")),
            str(finding.get("port", "")),
            str(finding.get("service", "")),
            str(finding.get("severity", "")),
        ]
        key = "|".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()

    # ==================================================
    # 📊 Categorization
    # ==================================================
    def _categorize(self, findings: List[Dict]) -> Dict:
        """Findings ko categories mein group karo."""
        categories = defaultdict(list)

        for finding in findings:
            ftype = (finding.get("type") or finding.get("cve_id") or "").lower()
            categorized = False

            for category, keywords in FINDING_CATEGORIES.items():
                if any(kw in ftype for kw in keywords):
                    categories[category].append(finding)
                    categorized = True
                    break

            if not categorized:
                categories["other"].append(finding)

        return {
            cat: {
                "count": len(items),
                "critical": sum(1 for f in items if f.get("severity") == "critical"),
                "items": items[:5],  # Sample
            }
            for cat, items in categories.items()
        }

    # ==================================================
    # 🔗 Correlation Analysis
    # ==================================================
    def _find_correlations(self, findings: List[Dict]) -> List[Dict]:
        """Related findings correlate karo."""
        correlations = []

        # Group by service/port
        by_service = defaultdict(list)
        by_port = defaultdict(list)

        for finding in findings:
            service = finding.get("service", "")
            port = finding.get("port", 0)

            if service:
                by_service[service].append(finding)
            if port:
                by_port[port].append(finding)

        # Service correlations
        for service, service_findings in by_service.items():
            if len(service_findings) >= 2:
                severities = [f.get("severity", "unknown") for f in service_findings]
                worst = min(severities, key=lambda s: SEVERITY_ORDER.get(s, 5))
                correlations.append({
                    "type": "service_correlation",
                    "service": service,
                    "finding_count": len(service_findings),
                    "worst_severity": worst,
                    "description": f"Multiple findings on {service} service",
                })

        # Attack chain correlations
        has_recon = any(
            f.get("type", "") in ["port_scan", "service_scan"]
            for f in findings
        )
        has_exploit = any(f.get("exploit_available") for f in findings)
        has_privesc = any(
            "privesc" in str(f).lower() or "privilege" in str(f).lower()
            for f in findings
        )

        if has_recon and has_exploit:
            correlations.append({
                "type": "attack_chain",
                "stages": ["reconnaissance", "exploitation"],
                "description": "Recon + exploitable vulnerabilities detected — complete attack path possible",
                "severity": "critical",
            })

        if has_exploit and has_privesc:
            correlations.append({
                "type": "attack_chain",
                "stages": ["exploitation", "privilege_escalation"],
                "description": "Exploit + privilege escalation path detected",
                "severity": "critical",
            })

        return correlations[:10]

    # ==================================================
    # ⛓️ Attack Chain Identification
    # ==================================================
    def _identify_attack_chains(self, findings: List[Dict]) -> List[Dict]:
        """Possible attack chains identify karo."""
        chains = []

        # Network → Web → Data
        has_network = any(
            f.get("type") in ["open_port", "service_exposed"]
            for f in findings
        )
        has_web_vuln = any(
            f.get("type") in ["sql_injection", "xss", "sqli"]
            for f in findings
        )
        has_cred = any(
            "credential" in str(f).lower() or "auth" in str(f).lower()
            for f in findings
        )

        if has_network and has_web_vuln and has_cred:
            chains.append({
                "name": "Full Compromise Chain",
                "steps": ["Network Access", "Web Exploitation", "Credential Theft"],
                "likelihood": "high",
                "impact": "critical",
            })

        # RCE → Lateral Movement
        has_rce = any(
            "rce" in str(f).lower() or "remote code" in str(f).lower()
            for f in findings
        )
        has_smb = any(
            f.get("service") == "smb" or f.get("port") == 445
            for f in findings
        )

        if has_rce and has_smb:
            chains.append({
                "name": "RCE + Lateral Movement",
                "steps": ["Remote Code Execution", "SMB Lateral Movement"],
                "likelihood": "high",
                "impact": "critical",
            })

        return chains

    # ==================================================
    # 🌟 Enrichment
    # ==================================================
    def _enrich_findings(self, findings: List[Dict]) -> List[Dict]:
        """Findings ko additional context se enrich karo."""
        enriched = []

        for finding in findings:
            enriched_finding = finding.copy()

            # Add CVSS label if CVSS present
            cvss = finding.get("cvss", 0)
            if cvss > 0:
                if cvss >= 9.0:
                    enriched_finding["cvss_label"] = "Critical"
                elif cvss >= 7.0:
                    enriched_finding["cvss_label"] = "High"
                elif cvss >= 4.0:
                    enriched_finding["cvss_label"] = "Medium"
                else:
                    enriched_finding["cvss_label"] = "Low"

            # Add remediation urgency
            severity = finding.get("severity", "unknown")
            urgency_map = {
                "critical": "Immediate (< 4 hours)",
                "high": "Urgent (< 24 hours)",
                "medium": "High (< 1 week)",
                "low": "Normal (< 1 month)",
            }
            enriched_finding["remediation_urgency"] = urgency_map.get(severity, "Review")

            # Exploit risk label
            if finding.get("exploit_available"):
                enriched_finding["exploit_risk"] = "ACTIVELY EXPLOITABLE"
            elif finding.get("cvss", 0) >= 9.0:
                enriched_finding["exploit_risk"] = "HIGH EXPLOIT POTENTIAL"
            else:
                enriched_finding["exploit_risk"] = "standard"

            enriched.append(enriched_finding)

        return enriched

    # ==================================================
    # 📊 Risk Calculation
    # ==================================================
    def _calculate_aggregate_risk(self, findings: List[Dict]) -> Dict:
        """Overall aggregate risk calculate karo."""
        if not findings:
            return {"score": 0, "level": "NONE"}

        total_score = 0
        for finding in findings:
            severity = finding.get("severity", "unknown").lower()
            base = SEVERITY_SCORES.get(severity, 1)

            # Exploit bonus
            if finding.get("exploit_available"):
                base *= 1.5

            # CVSS override
            cvss = finding.get("cvss", 0)
            if cvss > 0:
                base = max(base, cvss)

            total_score += base

        # Normalize
        normalized = min(total_score / max(len(findings), 1) * 2, 100)

        if normalized >= 80:
            level = "CRITICAL"
        elif normalized >= 60:
            level = "HIGH"
        elif normalized >= 40:
            level = "MEDIUM"
        elif normalized >= 20:
            level = "LOW"
        else:
            level = "MINIMAL"

        return {
            "score": round(normalized, 1),
            "level": level,
            "raw_score": round(total_score, 1),
        }

    def _get_top_findings(self, findings: List[Dict], n: int) -> List[Dict]:
        """Top N most critical findings lo."""
        sorted_findings = sorted(
            findings,
            key=lambda f: (
                SEVERITY_ORDER.get(f.get("severity", "unknown"), 5),
                -(f.get("cvss", 0)),
                not f.get("exploit_available", False),
            )
        )
        return sorted_findings[:n]

    def _count_severities(self, findings: List[Dict]) -> Dict:
        """Severity counts."""
        counts = {}
        for f in findings:
            sev = f.get("severity", "unknown")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def _convert_port_findings(self, scan_result: Dict) -> List[Dict]:
        """Port scan results ko findings format mein convert karo."""
        findings = []
        for port_info in scan_result.get("open_port_details", []):
            findings.append({
                "type": "open_port",
                "severity": "info",
                "port": port_info.get("port"),
                "service": port_info.get("service"),
                "description": f"Open port: {port_info.get('port')} ({port_info.get('service', 'unknown')})",
            })
        return findings


# ==================================================
# 🔧 STANDALONE FUNCTIONS (BACKWARD COMPAT)
# ==================================================

def merge_findings(*finding_lists) -> List[Dict]:
    """Multiple finding lists merge karo."""
    aggregator = VulnAggregator()
    all_findings = []
    for lst in finding_lists:
        if isinstance(lst, list):
            all_findings.extend(lst)
    return aggregator._deduplicate(all_findings)


def get_critical_findings(aggregated: Dict) -> List[Dict]:
    """Aggregated result se critical findings lo."""
    return [
        f for f in aggregated.get("findings", [])
        if f.get("severity") == "critical"
    ]


def summarize_by_service(findings: List[Dict]) -> Dict:
    """Findings ko service ke hisaab se summarize karo."""
    by_service = defaultdict(list)
    for f in findings:
        service = f.get("service", "unknown")
        by_service[service].append(f)

    return {
        service: {
            "count": len(items),
            "severities": [f.get("severity", "unknown") for f in items],
            "worst": min(
                [f.get("severity", "unknown") for f in items],
                key=lambda s: SEVERITY_ORDER.get(s, 5)
            ),
        }
        for service, items in by_service.items()
    }
