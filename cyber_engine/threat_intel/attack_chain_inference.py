"""
Chhoti Don - Attack Chain Inference Engine
Advanced attack chain detection with full MITRE ATT&CK coverage,
kill chain mapping, APT pattern matching, and predictive analysis.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Dict, List, Tuple


# ==================================================
# 🎯 COMPREHENSIVE ATTACK STAGES (PRESERVED + EXPANDED)
# ==================================================

ATTACK_STAGES = {
    "reconnaissance": {
        "order": 1,
        "indicators": [
            "port scan", "nmap", "masscan", "subdomain", "osint",
            "shodan", "censys", "recon", "fingerprint", "enumerate",
            "T1595", "T1592", "T1589", "T1590", "T1591", "T1596",
            "network discovery", "banner grab", "whois",
        ],
        "mitre_tactics": ["TA0043"],
        "kill_chain": "Reconnaissance",
        "risk_weight": 1.0,
        "description": "Target information gathering",
    },
    "resource_development": {
        "order": 2,
        "indicators": [
            "payload creation", "exploit development", "c2 setup",
            "domain registration", "T1583", "T1584", "T1585",
            "infrastructure", "staging",
        ],
        "mitre_tactics": ["TA0042"],
        "kill_chain": "Weaponization",
        "risk_weight": 1.2,
        "description": "Attacker resource preparation",
    },
    "initial_access": {
        "order": 3,
        "indicators": [
            "rce", "exploit public-facing", "T1190", "phishing",
            "spearphishing", "T1566", "valid accounts", "T1078",
            "supply chain", "T1195", "drive-by", "T1189",
            "external remote", "T1133", "vulnerability", "exploit",
            "sql injection", "xss", "shell", "webshell",
        ],
        "mitre_tactics": ["TA0001"],
        "kill_chain": "Delivery/Exploitation",
        "risk_weight": 2.5,
        "description": "First foothold in target environment",
    },
    "execution": {
        "order": 4,
        "indicators": [
            "command execution", "T1059", "powershell", "cmd.exe",
            "bash", "python exec", "wmi", "T1047", "scheduled task",
            "T1053", "service", "T1569", "script", "interpreter",
            "shellcode", "code execution", "run",
        ],
        "mitre_tactics": ["TA0002"],
        "kill_chain": "Exploitation",
        "risk_weight": 2.8,
        "description": "Malicious code execution",
    },
    "persistence": {
        "order": 5,
        "indicators": [
            "registry run key", "T1547", "scheduled task", "T1053",
            "startup folder", "service install", "T1543", "cron",
            "backdoor", "webshell persistence", "autostart",
            "boot autostart", "T1037", "logon script",
        ],
        "mitre_tactics": ["TA0003"],
        "kill_chain": "Installation",
        "risk_weight": 2.0,
        "description": "Maintaining persistent access",
    },
    "privilege_escalation": {
        "order": 6,
        "indicators": [
            "privilege escalation", "sudo misconfiguration", "T1068",
            "suid", "setuid", "token impersonation", "T1134",
            "bypass uac", "T1548", "local exploit", "kernel exploit",
            "privesc", "root", "SYSTEM", "administrator",
        ],
        "mitre_tactics": ["TA0004"],
        "kill_chain": "Exploitation",
        "risk_weight": 3.5,
        "description": "Gaining elevated privileges",
    },
    "defense_evasion": {
        "order": 7,
        "indicators": [
            "obfuscation", "T1027", "disable security", "T1562",
            "log deletion", "T1070", "masquerading", "T1036",
            "process injection", "T1055", "rootkit", "T1014",
            "timestomp", "encode", "base64", "packed",
        ],
        "mitre_tactics": ["TA0005"],
        "kill_chain": "Exploitation",
        "risk_weight": 2.2,
        "description": "Avoiding detection mechanisms",
    },
    "credential_access": {
        "order": 8,
        "indicators": [
            "credential leak", "unsecured credentials", "T1552",
            "mimikatz", "hashdump", "T1003", "brute force", "T1110",
            "pass the hash", "kerberoasting", "T1558", "lsass",
            "sam database", "ntlm", "credential dumping",
        ],
        "mitre_tactics": ["TA0006"],
        "kill_chain": "Actions on Objectives",
        "risk_weight": 3.8,
        "description": "Stealing authentication credentials",
    },
    "discovery": {
        "order": 9,
        "indicators": [
            "network scan", "T1046", "account discovery", "T1087",
            "file discovery", "T1083", "process discovery", "T1057",
            "system info", "T1082", "remote system", "T1018",
            "enumerate", "whoami", "ipconfig", "netstat",
        ],
        "mitre_tactics": ["TA0007"],
        "kill_chain": "Actions on Objectives",
        "risk_weight": 1.5,
        "description": "Post-compromise environment mapping",
    },
    "lateral_movement": {
        "order": 10,
        "indicators": [
            "smb", "pass the hash", "T1021", "psexec", "wmiexec",
            "rdp lateral", "ssh lateral", "T1021.004", "T1021.001",
            "T1021.002", "lateral movement", "pivot", "port forward",
            "eternalblue", "ms17-010",
        ],
        "mitre_tactics": ["TA0008"],
        "kill_chain": "Lateral Movement",
        "risk_weight": 4.0,
        "description": "Moving through target network",
    },
    "collection": {
        "order": 11,
        "indicators": [
            "data collection", "T1005", "clipboard", "T1115",
            "screenshot", "T1113", "keylogging", "T1056",
            "email collection", "T1114", "file collection",
            "archive", "compress", "sensitive data",
        ],
        "mitre_tactics": ["TA0009"],
        "kill_chain": "Actions on Objectives",
        "risk_weight": 2.5,
        "description": "Gathering target data",
    },
    "command_and_control": {
        "order": 12,
        "indicators": [
            "c2", "beacon", "T1071", "reverse shell", "bind shell",
            "cobaltstrike", "meterpreter", "empire", "T1095",
            "dns tunnel", "T1071.004", "http c2", "T1071.001",
            "checkin", "implant", "rat", "botnet",
        ],
        "mitre_tactics": ["TA0011"],
        "kill_chain": "Command & Control",
        "risk_weight": 3.5,
        "description": "C2 channel establishment",
    },
    "exfiltration": {
        "order": 13,
        "indicators": [
            "data exfiltration", "T1041", "exfil", "data leak",
            "T1048", "upload", "ftp transfer", "dns exfil",
            "T1052", "T1567", "cloud storage", "steal", "copy out",
        ],
        "mitre_tactics": ["TA0010"],
        "kill_chain": "Actions on Objectives",
        "risk_weight": 4.0,
        "description": "Data leaving target environment",
    },
    "impact": {
        "order": 14,
        "indicators": [
            "ransomware", "T1486", "data destruction", "T1485",
            "dos", "T1499", "defacement", "T1491", "wiper",
            "encrypt", "delete", "destroy", "corrupt", "disrupt",
        ],
        "mitre_tactics": ["TA0040"],
        "kill_chain": "Actions on Objectives",
        "risk_weight": 5.0,
        "description": "Final destructive/disruptive actions",
    },
}

# Known APT patterns
APT_PATTERNS = {
    "APT28 (Fancy Bear)": {
        "stages": ["initial_access", "credential_access", "lateral_movement", "exfiltration"],
        "indicators": ["x-agent", "sofacy", "fancy bear", "T1566", "T1003"],
        "description": "Russian state-sponsored espionage group",
        "targets": ["government", "military", "defense"],
    },
    "Lazarus Group": {
        "stages": ["initial_access", "execution", "persistence", "lateral_movement", "impact"],
        "indicators": ["wannacry", "lazarus", "hidden cobra", "T1486", "T1059"],
        "description": "North Korean state-sponsored group",
        "targets": ["financial", "cryptocurrency", "defense"],
    },
    "APT41": {
        "stages": ["initial_access", "persistence", "privilege_escalation", "collection", "exfiltration"],
        "indicators": ["double dragon", "T1190", "T1547", "T1068"],
        "description": "Chinese state-sponsored dual espionage/cybercrime",
        "targets": ["healthcare", "telecom", "technology"],
    },
    "Ransomware Gang": {
        "stages": ["initial_access", "execution", "lateral_movement", "exfiltration", "impact"],
        "indicators": ["ransomware", "T1486", "double extortion", "encrypt"],
        "description": "Generic ransomware attack pattern",
        "targets": ["enterprise", "healthcare", "government"],
    },
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def infer_attack_chain(findings: List[Dict]) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Advanced attack chain inference with APT matching.
    """
    engine = AttackChainEngine()
    return engine.infer(findings)


# ==================================================
# 🧠 ATTACK CHAIN ENGINE CLASS
# ==================================================

class AttackChainEngine:
    """
    Advanced Attack Chain Inference Engine.
    """

    def infer(self, findings: List[Dict]) -> Dict:
        """Full attack chain inference."""
        start_time = time.time()

        # Stage detection
        detected_stages, stage_evidence = self._detect_stages(findings)

        # Order stages
        ordered_chain = self._order_stages(detected_stages)

        # Risk scoring
        risk_score, risk_level = self._calculate_risk(ordered_chain)

        # Chain completeness
        completeness = self._assess_completeness(ordered_chain)

        # APT pattern matching
        apt_matches = self._match_apt_patterns(ordered_chain, findings)

        # Predicted next stages
        predictions = self._predict_next_stages(ordered_chain)

        # Kill chain coverage
        kill_chain = self._get_kill_chain_coverage(ordered_chain)

        # MITRE tactics
        mitre_tactics = list(set(
            tactic
            for stage in ordered_chain
            for tactic in ATTACK_STAGES.get(stage, {}).get("mitre_tactics", [])
        ))

        return {
            # Backward compat
            "detected_stages": ordered_chain,
            "chain_length": len(ordered_chain),
            "attack_chain_risk_score": risk_score,
            "risk_assessment": risk_level,

            # Enhanced
            "stage_evidence": stage_evidence,
            "completeness": completeness,
            "apt_pattern_matches": apt_matches,
            "predicted_next_stages": predictions,
            "kill_chain_coverage": kill_chain,
            "mitre_tactics": mitre_tactics,
            "attack_narrative": self._build_narrative(ordered_chain, apt_matches),
            "analysis_time_sec": round(time.time() - start_time, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _detect_stages(self, findings: List[Dict]) -> Tuple[List[str], Dict]:
        """Findings se attack stages detect karo."""
        detected = {}
        evidence = defaultdict(list)

        for finding in findings:
            text_blob = str(finding).lower()

            for stage, data in ATTACK_STAGES.items():
                for indicator in data["indicators"]:
                    if indicator.lower() in text_blob:
                        if stage not in detected:
                            detected[stage] = 0
                        detected[stage] += 1
                        finding_id = (
                            finding.get("cve_id") or
                            finding.get("type") or
                            str(finding)[:50]
                        )
                        if finding_id not in evidence[stage]:
                            evidence[stage].append(finding_id)
                        break

        return list(detected.keys()), dict(evidence)

    def _order_stages(self, stages: List[str]) -> List[str]:
        """Stages ko attack order mein sort karo."""
        return sorted(
            stages,
            key=lambda x: ATTACK_STAGES.get(x, {}).get("order", 99)
        )

    def _calculate_risk(self, stages: List[str]) -> Tuple[float, str]:
        """Risk score calculate karo."""
        if not stages:
            return 0.0, "No Attack Chain Detected"

        # Weighted score
        total_weight = sum(
            ATTACK_STAGES.get(s, {}).get("risk_weight", 1.0)
            for s in stages
        )

        # Chain length bonus
        chain_bonus = len(stages) * 1.5

        # Advanced stage bonus
        advanced_stages = {"exfiltration", "impact", "lateral_movement", "credential_access"}
        advanced_count = sum(1 for s in stages if s in advanced_stages)
        advanced_bonus = advanced_count * 2.0

        risk_score = round(total_weight + chain_bonus + advanced_bonus, 2)
        risk_score = min(risk_score, 50.0)  # Cap at 50

        if risk_score >= 30:
            level = "CRITICAL — Active Sophisticated Attack"
        elif risk_score >= 20:
            level = "HIGH — Multi-Stage Attack in Progress"
        elif risk_score >= 12:
            level = "ELEVATED — Attack Chain Forming"
        elif risk_score >= 6:
            level = "MODERATE — Early Attack Indicators"
        else:
            level = "LOW — Initial Reconnaissance"

        return risk_score, level

    def _assess_completeness(self, stages: List[str]) -> Dict:
        """Attack chain completeness assess karo."""
        critical_stages = [
            "initial_access", "execution", "lateral_movement",
            "exfiltration", "impact"
        ]

        present = [s for s in critical_stages if s in stages]
        missing = [s for s in critical_stages if s not in stages]

        pct = len(present) / len(critical_stages) * 100

        return {
            "percentage": round(pct, 1),
            "critical_stages_present": present,
            "critical_stages_missing": missing,
            "assessment": (
                "COMPLETE ATTACK CHAIN" if pct >= 80
                else "ADVANCED ATTACK" if pct >= 60
                else "DEVELOPING ATTACK" if pct >= 40
                else "EARLY STAGE"
            ),
        }

    def _match_apt_patterns(self, stages: List[str], findings: List[Dict]) -> List[Dict]:
        """Known APT patterns match karo."""
        matches = []
        findings_str = str(findings).lower()

        for apt_name, apt_data in APT_PATTERNS.items():
            # Stage overlap
            apt_stages = apt_data["stages"]
            overlap = [s for s in stages if s in apt_stages]
            overlap_pct = len(overlap) / len(apt_stages) * 100 if apt_stages else 0

            # Indicator match
            indicator_matches = [
                ind for ind in apt_data["indicators"]
                if ind.lower() in findings_str
            ]

            if overlap_pct >= 50 or len(indicator_matches) >= 2:
                confidence = min(
                    (overlap_pct / 100 * 0.6) + (len(indicator_matches) * 0.1),
                    0.99
                )
                matches.append({
                    "apt_name": apt_name,
                    "confidence": round(confidence, 2),
                    "confidence_percent": f"{confidence*100:.0f}%",
                    "stage_overlap": overlap,
                    "indicator_matches": indicator_matches,
                    "description": apt_data["description"],
                    "typical_targets": apt_data["targets"],
                })

        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[:3]

    def _predict_next_stages(self, current_stages: List[str]) -> List[Dict]:
        """Next probable attack stages predict karo."""
        predictions = []

        if not current_stages:
            return [{"stage": "initial_access", "probability": 0.8}]

        last_stage = current_stages[-1]
        last_order = ATTACK_STAGES.get(last_stage, {}).get("order", 0)

        # Find next likely stages
        for stage, data in ATTACK_STAGES.items():
            if stage in current_stages:
                continue

            stage_order = data.get("order", 0)

            # Next 1-2 stages in sequence
            if last_order < stage_order <= last_order + 2:
                probability = 0.8 - (stage_order - last_order - 1) * 0.2
                predictions.append({
                    "stage": stage,
                    "probability": round(probability, 2),
                    "description": data.get("description", ""),
                    "mitre_tactics": data.get("mitre_tactics", []),
                })

        predictions.sort(key=lambda x: x["probability"], reverse=True)
        return predictions[:3]

    def _get_kill_chain_coverage(self, stages: List[str]) -> List[str]:
        """Kill chain phases covered."""
        covered = set()
        for stage in stages:
            kc = ATTACK_STAGES.get(stage, {}).get("kill_chain", "")
            if kc:
                covered.add(kc)
        return list(covered)

    def _build_narrative(self, stages: List[str], apt_matches: List[Dict]) -> str:
        """Attack narrative build karo."""
        if not stages:
            return "No attack chain indicators detected."

        narrative = f"Attack chain detected spanning {len(stages)} stage(s): "
        stage_names = ", ".join(s.replace("_", " ").title() for s in stages)
        narrative += stage_names + ". "

        if "impact" in stages or "exfiltration" in stages:
            narrative += "CRITICAL: Attack has reached final objectives. "

        if apt_matches:
            top_apt = apt_matches[0]
            narrative += f"Pattern resembles {top_apt['apt_name']} ({top_apt['confidence_percent']} confidence). "

        return narrative
