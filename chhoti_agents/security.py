"""
Chhoti Don - Security Agent
Advanced cybersecurity analyst agent with threat analysis,
vulnerability assessment, MITRE mapping, and incident response.
Phase 2.2 - Full Upgrade

⚠️ For authorized security research and penetration testing only.
"""

import re
import time
import datetime
from typing import Any, Dict, List, Optional
 
from chhoti_agents.base import BaseAgent
 
 
class SecurityAgent(BaseAgent):
    """
    Advanced Cybersecurity Analyst Agent.
    Preserved interface + full security capabilities.
    """

    def __init__(self, brain=None):
        super().__init__(
            name="SecurityAgent",
            role="Senior Cybersecurity Analyst",
            goal="Analyze threats, vulnerabilities, and attack patterns for authorized security assessment",
            brain=brain,
        )
        self._brain_type = "malware"

    # ==================================================
    # 🛡️ MAIN ACT (PRESERVED + UPGRADED)
    # ==================================================

    def act(self, task: str) -> Any:
        """
        Execute security analysis task.
        Preserved + massively upgraded.
        """
        task_lower = task.lower()

        # Route to specialized analysis
        if any(kw in task_lower for kw in [".exe", ".dll", ".bin", "binary", "malware", "virus"]):
            return self._malware_analysis(task)

        elif any(kw in task_lower for kw in ["port scan", "nmap", "network scan", "open port"]):
            return self._network_security_analysis(task)

        elif any(kw in task_lower for kw in ["xss", "sql injection", "sqli", "csrf", "ssrf", "lfi", "rfi"]):
            return self._web_vulnerability_analysis(task)

        elif any(kw in task_lower for kw in ["phishing", "social engineering", "email", "spear"]):
            return self._phishing_analysis(task)

        elif any(kw in task_lower for kw in ["ransomware", "encrypt", "crypto", "locked"]):
            return self._ransomware_analysis(task)

        elif any(kw in task_lower for kw in ["cve", "vulnerability", "patch", "exploit"]):
            return self._vulnerability_assessment(task)

        elif any(kw in task_lower for kw in ["log", "incident", "breach", "alert", "ioc"]):
            return self._incident_analysis(task)

        elif any(kw in task_lower for kw in ["mitre", "att&ck", "technique", "tactic"]):
            return self._mitre_analysis(task)

        elif any(kw in task_lower for kw in ["pentest", "penetration", "audit", "assessment"]):
            return self._pentest_guidance(task)

        else:
            return self._general_security_analysis(task)

    # ==================================================
    # 🦠 MALWARE ANALYSIS (PRESERVED + UPGRADED)
    # ==================================================

    def _malware_analysis(self, task: str) -> Dict:
        """Malware/executable analysis."""
        task_lower = task.lower()

        indicators = []
        mitre_techniques = []
        risk_level = "medium"

        # Static checks (preserved logic + expanded)
        if ".exe" in task_lower or ".dll" in task_lower:
            indicators.append("Executable file detected")
            mitre_techniques.append("T1059 — Command and Scripting Interpreter")

        # Suspicious strings
        suspicious_patterns = {
            "createremotethread": ("Process injection detected", "T1055", "critical"),
            "virtualalloc": ("Memory allocation for shellcode", "T1055.001", "high"),
            "writeprocessmemory": ("Process memory manipulation", "T1055", "critical"),
            "mimikatz": ("Credential theft tool detected!", "T1003", "critical"),
            "reverse shell": ("Reverse shell payload", "T1059", "critical"),
            "bitcoin": ("Possible ransomware C2", "T1486", "high"),
            "encrypt": ("Encryption routine detected", "T1486", "high"),
            "base64": ("Encoded payload", "T1027", "medium"),
            "powershell -enc": ("Encoded PowerShell", "T1059.001", "high"),
            "cmd /c": ("Command execution via CMD", "T1059.003", "medium"),
        }

        for pattern, (indicator, technique, severity) in suspicious_patterns.items():
            if pattern in task_lower:
                indicators.append(indicator)
                mitre_techniques.append(technique)
                if severity == "critical":
                    risk_level = "critical"
                elif severity == "high" and risk_level != "critical":
                    risk_level = "high"

        # Brain-enhanced analysis
        if self.brain:
            prompt = (
                f"As a malware analyst, analyze this security finding:\n{task}\n\n"
                "Provide: 1) Threat classification 2) Behavior analysis "
                "3) IOCs 4) MITRE techniques 5) Remediation steps"
            )
            brain_response = self.brain.think(prompt, brain_type="malware")
        else:
            brain_response = None

        return {
            "analysis_type": "malware",
            "task": task[:150],
            "risk_level": risk_level.upper(),
            "indicators": indicators,
            "mitre_techniques": mitre_techniques,
            "immediate_actions": self._get_malware_actions(risk_level),
            "brain_analysis": brain_response,
            "agent": self.name,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    # ==================================================
    # 🌐 NETWORK SECURITY (PRESERVED + UPGRADED)
    # ==================================================

    def _network_security_analysis(self, task: str) -> Dict:
        """Network security analysis."""
        # Extract IPs/ports if present
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', task)
        ports = re.findall(r'\b(\d{1,5})\b', task)
        ports = [int(p) for p in ports if 1 <= int(p) <= 65535]

        # Dangerous port warnings (preserved + expanded)
        dangerous_services = {
            21: ("FTP", "Plaintext credentials risk", "T1078"),
            22: ("SSH", "Brute-force / Remote access risk", "T1021.004"),
            23: ("Telnet", "CRITICAL: Plaintext protocol!", "T1021"),
            25: ("SMTP", "Email relay risk", "T1071"),
            80: ("HTTP", "Web attack surface", "T1190"),
            443: ("HTTPS", "Encrypted C2 possible", "T1071"),
            445: ("SMB", "EternalBlue/WannaCry risk (T1210)", "T1021.002"),
            1433: ("MSSQL", "Database exposure risk", "T1046"),
            3306: ("MySQL", "Database credential attack", "T1046"),
            3389: ("RDP", "BlueKeep/Remote access risk", "T1021.001"),
            5432: ("PostgreSQL", "Database exposure", "T1046"),
            6379: ("Redis", "Unauthenticated access possible", "T1046"),
            27017: ("MongoDB", "Database exposure risk", "T1046"),
        }

        port_risks = []
        mitre = []
        for port in ports[:20]:
            if port in dangerous_services:
                service, risk, technique = dangerous_services[port]
                port_risks.append({"port": port, "service": service, "risk": risk})
                if technique not in mitre:
                    mitre.append(technique)

        nmap_command = f"nmap -sV -sC --script=vuln {ips[0] if ips else 'TARGET_IP'}"

        return {
            "analysis_type": "network_security",
            "task": task[:150],
            "ips_detected": ips[:5],
            "ports_analyzed": ports[:20],
            "port_risks": port_risks,
            "mitre_techniques": mitre,
            "scan_command": nmap_command,
            "note": "⚠️ Run only in authorized environments",
            "recommendations": self._get_network_recommendations(port_risks),
            "agent": self.name,
        }

    # ==================================================
    # 🕷️ WEB VULNERABILITY (PRESERVED + UPGRADED)
    # ==================================================

    def _web_vulnerability_analysis(self, task: str) -> Dict:
        """Web vulnerability analysis."""
        task_lower = task.lower()

        vuln_map = {
            "sql injection": {
                "severity": "critical",
                "description": "SQL injection allows database manipulation/extraction",
                "mitre": "T1190",
                "test_payload": "' OR '1'='1",
                "fix": "Use parameterized queries / prepared statements",
                "references": ["OWASP A03:2021", "CWE-89"],
            },
            "sqli": {
                "severity": "critical",
                "description": "SQL injection vulnerability",
                "mitre": "T1190",
                "test_payload": "' OR 1=1--",
                "fix": "Parameterized queries, input validation",
                "references": ["OWASP A03:2021"],
            },
            "xss": {
                "severity": "high",
                "description": "Cross-Site Scripting allows JS injection",
                "mitre": "T1059.007",
                "test_payload": "<script>alert('XSS')</script>",
                "fix": "Output encoding, Content Security Policy (CSP)",
                "references": ["OWASP A03:2021", "CWE-79"],
            },
            "csrf": {
                "severity": "medium",
                "description": "Cross-Site Request Forgery",
                "mitre": "T1185",
                "fix": "CSRF tokens, SameSite cookies",
                "references": ["OWASP A01:2021", "CWE-352"],
            },
            "ssrf": {
                "severity": "high",
                "description": "Server-Side Request Forgery — internal network access",
                "mitre": "T1190",
                "fix": "Whitelist allowed URLs, disable internal access",
                "references": ["OWASP A10:2021", "CWE-918"],
            },
            "lfi": {
                "severity": "high",
                "description": "Local File Inclusion — read server files",
                "mitre": "T1083",
                "test_payload": "../../../../etc/passwd",
                "fix": "Input validation, disable file inclusion",
            },
            "rfi": {
                "severity": "critical",
                "description": "Remote File Inclusion — execute remote code",
                "mitre": "T1190",
                "fix": "Disable allow_url_include, input validation",
            },
        }

        found_vulns = []
        for vuln, data in vuln_map.items():
            if vuln in task_lower:
                found_vulns.append({"vulnerability": vuln.upper(), **data})

        if self.brain and not found_vulns:
            response = self.brain.think(
                f"Analyze this web security issue:\n{task}",
                brain_type="malware"
            )
            return {
                "analysis_type": "web_vulnerability",
                "task": task[:150],
                "analysis": response,
                "agent": self.name,
            }

        return {
            "analysis_type": "web_vulnerability",
            "task": task[:150],
            "vulnerabilities_found": found_vulns,
            "severity": found_vulns[0]["severity"].upper() if found_vulns else "unknown",
            "immediate_action": "Patch before deploying to production",
            "agent": self.name,
        }

    # ==================================================
    # 📧 PHISHING ANALYSIS
    # ==================================================

    def _phishing_analysis(self, task: str) -> Dict:
        """Phishing / social engineering analysis."""
        indicators = []
        task_lower = task.lower()

        phishing_patterns = [
            ("urgent", "Urgency tactics detected"),
            ("click here", "Suspicious call-to-action"),
            ("verify your account", "Account verification phishing"),
            ("password", "Credential harvesting attempt"),
            ("wire transfer", "Financial fraud indicator"),
            ("lottery", "Lottery scam indicator"),
            ("free", "Too-good-to-be-true offer"),
        ]

        for pattern, indicator in phishing_patterns:
            if pattern in task_lower:
                indicators.append(indicator)

        return {
            "analysis_type": "phishing",
            "task": task[:150],
            "risk_level": "HIGH" if len(indicators) >= 3 else "MEDIUM" if indicators else "LOW",
            "indicators": indicators,
            "mitre_technique": "T1566 — Phishing",
            "recommendations": [
                "Don't click links in suspicious emails",
                "Verify sender through official channels",
                "Report to IT security team",
                "Enable email filtering",
            ],
            "agent": self.name,
        }

    # ==================================================
    # 🔐 RANSOMWARE ANALYSIS
    # ==================================================

    def _ransomware_analysis(self, task: str) -> Dict:
        """Ransomware incident analysis."""
        return {
            "analysis_type": "ransomware",
            "task": task[:150],
            "risk_level": "CRITICAL",
            "mitre_techniques": ["T1486 — Data Encrypted for Impact", "T1490 — Inhibit System Recovery"],
            "immediate_actions": [
                "🚨 DISCONNECT from network IMMEDIATELY",
                "Do NOT pay ransom — no guarantee of recovery",
                "Preserve forensic evidence",
                "Contact incident response team",
                "Check backup integrity",
                "Document affected systems",
            ],
            "recovery_steps": [
                "Isolate infected systems",
                "Identify ransomware family",
                "Check decryption tools (nomoreransom.org)",
                "Restore from clean backups",
                "Patch vulnerabilities used for entry",
            ],
            "agent": self.name,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    # ==================================================
    # 🔍 VULNERABILITY ASSESSMENT
    # ==================================================

    def _vulnerability_assessment(self, task: str) -> Dict:
        """CVE/vulnerability assessment."""
        cves = re.findall(r'CVE-\d{4}-\d{4,7}', task, re.IGNORECASE)

        if self.brain:
            prompt = (
                f"Analyze this vulnerability:\n{task}\n\n"
                "Provide: 1) Severity 2) Attack vector 3) Affected systems "
                "4) Exploit likelihood 5) Patch/mitigation"
            )
            response = self.brain.think(prompt, brain_type="malware")
        else:
            response = None

        return {
            "analysis_type": "vulnerability_assessment",
            "task": task[:150],
            "cves_mentioned": cves,
            "brain_analysis": response,
            "recommendations": [
                "Apply patches immediately for Critical/High CVEs",
                "Check vendor advisories",
                "Implement virtual patching if patch unavailable",
                "Monitor for exploitation attempts",
            ],
            "agent": self.name,
        }

    # ==================================================
    # 📋 INCIDENT ANALYSIS
    # ==================================================

    def _incident_analysis(self, task: str) -> Dict:
        """Security incident analysis."""
        if self.brain:
            prompt = (
                f"Analyze this security incident/log:\n{task}\n\n"
                "Provide: 1) Incident type 2) Severity 3) Timeline "
                "4) Affected systems 5) Containment steps"
            )
            response = self.brain.think(prompt, brain_type="malware")
        else:
            response = f"Incident analysis for: {task}"

        return {
            "analysis_type": "incident_response",
            "task": task[:150],
            "analysis": response,
            "ir_phases": ["Identification", "Containment", "Eradication", "Recovery", "Lessons Learned"],
            "agent": self.name,
        }

    # ==================================================
    # 🎯 MITRE ATT&CK ANALYSIS
    # ==================================================

    def _mitre_analysis(self, task: str) -> Dict:
        """MITRE ATT&CK technique analysis."""
        techniques = re.findall(r'T\d{4}(?:\.\d{3})?', task)

        mitre_db = {
            "T1055": {"name": "Process Injection", "tactic": "Defense Evasion"},
            "T1059": {"name": "Command Scripting", "tactic": "Execution"},
            "T1486": {"name": "Data Encrypted for Impact", "tactic": "Impact"},
            "T1190": {"name": "Exploit Public-Facing App", "tactic": "Initial Access"},
            "T1078": {"name": "Valid Accounts", "tactic": "Initial Access"},
            "T1003": {"name": "OS Credential Dumping", "tactic": "Credential Access"},
            "T1021": {"name": "Remote Services", "tactic": "Lateral Movement"},
            "T1071": {"name": "Application Layer Protocol", "tactic": "C2"},
        }

        found = []
        for tech in techniques:
            if tech in mitre_db:
                found.append({"technique": tech, **mitre_db[tech]})

        return {
            "analysis_type": "mitre_attack",
            "task": task[:150],
            "techniques_identified": found,
            "total_techniques": len(found),
            "reference": "https://attack.mitre.org",
            "agent": self.name,
        }

    # ==================================================
    # 🔓 PENTEST GUIDANCE
    # ==================================================

    def _pentest_guidance(self, task: str) -> Dict:
        """Penetration testing methodology guidance."""
        if self.brain:
            prompt = (
                f"Provide penetration testing guidance for:\n{task}\n\n"
                "Include: methodology, tools, MITRE techniques, and reporting format. "
                "⚠️ For authorized testing only."
            )
            response = self.brain.think(prompt, brain_type="malware")
        else:
            response = None

        return {
            "analysis_type": "pentest",
            "task": task[:150],
            "methodology": ["Reconnaissance", "Scanning", "Exploitation", "Post-Exploitation", "Reporting"],
            "key_tools": ["Nmap", "Metasploit", "Burp Suite", "Nikto", "SQLMap"],
            "guidance": response,
            "warning": "⚠️ Only perform on authorized systems with written permission",
            "agent": self.name,
        }

    def _general_security_analysis(self, task: str) -> Dict:
        """General security analysis fallback."""
        if self.brain:
            system_prompt = (
                f"You are {self.name}, a {self.role}. "
                "Analyze security implications, identify risks, "
                "and provide actionable recommendations."
            )
            response = self.brain.think(task, brain_type="malware", system_override=system_prompt)
            return {
                "analysis_type": "general_security",
                "task": task[:150],
                "analysis": response,
                "agent": self.name,
            }

        return {
            "analysis_type": "general_security",
            "task": task[:150],
            "analysis": f"Security analysis for: {task}",
            "recommendations": ["Assess scope", "Identify assets", "Evaluate threats"],
            "agent": self.name,
        }

    # ==================================================
    # 🔧 HELPERS
    # ==================================================

    def _get_malware_actions(self, risk_level: str) -> List[str]:
        actions = {
            "critical": [
                "🚨 ISOLATE system from network IMMEDIATELY",
                "Capture memory dump for forensics",
                "Preserve disk image",
                "Report to incident response team",
                "Block known IOCs at firewall",
            ],
            "high": [
                "Quarantine suspicious file",
                "Run full system antivirus scan",
                "Check for lateral movement",
                "Review recent network connections",
            ],
            "medium": [
                "Submit file for sandbox analysis",
                "Check hash against threat intel",
                "Monitor system behavior",
            ],
            "low": [
                "Log and monitor",
                "Update antivirus signatures",
            ],
        }
        return actions.get(risk_level, ["Investigate further"])

    def _get_network_recommendations(self, port_risks: List[Dict]) -> List[str]:
        recs = []
        for risk in port_risks:
            port = risk["port"]
            if port == 23:
                recs.append("Disable Telnet — use SSH instead")
            elif port == 21:
                recs.append("Replace FTP with SFTP/FTPS")
            elif port == 3389:
                recs.append("Restrict RDP to VPN only, enable NLA")
            elif port in [3306, 5432, 1433, 27017]:
                recs.append(f"Remove database port {port} from internet exposure")
            elif port == 6379:
                recs.append("Add Redis authentication, bind to localhost only")

        if not recs:
            recs.append("Review firewall rules and close unnecessary ports")

        return list(set(recs))[:5]
