"""
Chhoti Don - MITRE ATT&CK Mapper
Advanced MITRE ATT&CK technique mapping with
full tactic coverage, sub-techniques, and kill chain analysis.
Phase 2.2 - Full Upgrade
"""

from typing import Dict, List, Optional


# ==================================================
# 🎯 COMPREHENSIVE MITRE ATT&CK DATABASE
# ==================================================

MITRE_TECHNIQUES = {

    # --------------------------------------------------
    # TA0001 - Initial Access
    # --------------------------------------------------
    "T1190": {
        "id": "T1190",
        "name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
        "description": "Adversaries exploit vulnerabilities in internet-facing applications",
        "keywords": ["rce", "exploit", "vulnerability", "sqli", "sql injection", "xss",
                    "remote code execution", "buffer overflow", "web exploit"],
        "severity": "critical",
        "detection": "Monitor web application logs for unusual requests",
        "mitigations": ["M1048 - Application Isolation", "M1050 - Exploit Protection"],
        "data_sources": ["Application Log", "Network Traffic"],
        "platforms": ["Linux", "Windows", "macOS"],
    },
    "T1566": {
        "id": "T1566",
        "name": "Phishing",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
        "description": "Adversaries send phishing messages to gain access",
        "keywords": ["phishing", "spearphishing", "email attack", "malicious attachment"],
        "severity": "high",
        "detection": "Monitor email gateway logs",
        "mitigations": ["M1049 - Antivirus/Antimalware", "M1017 - User Training"],
        "sub_techniques": ["T1566.001 - Spearphishing Attachment", "T1566.002 - Spearphishing Link"],
    },
    "T1078": {
        "id": "T1078",
        "name": "Valid Accounts",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
        "description": "Use of legitimate credentials to gain access",
        "keywords": ["credential", "valid account", "default password", "brute force",
                    "authentication bypass", "login", "password spray"],
        "severity": "high",
        "detection": "Monitor authentication logs for unusual patterns",
        "mitigations": ["M1032 - Multi-factor Authentication", "M1027 - Password Policies"],
    },

    # --------------------------------------------------
    # TA0002 - Execution
    # --------------------------------------------------
    "T1059": {
        "id": "T1059",
        "name": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "tactic_id": "TA0002",
        "description": "Adversaries abuse command interpreters to execute commands",
        "keywords": ["cmd", "powershell", "bash", "shell", "script execution",
                    "command injection", "code execution", "interpreter"],
        "severity": "high",
        "detection": "Monitor process creation and command line arguments",
        "sub_techniques": ["T1059.001 - PowerShell", "T1059.003 - Windows Command Shell",
                          "T1059.004 - Unix Shell", "T1059.006 - Python"],
    },
    "T1203": {
        "id": "T1203",
        "name": "Exploitation for Client Execution",
        "tactic": "Execution",
        "tactic_id": "TA0002",
        "description": "Adversaries exploit software vulnerabilities in client applications",
        "keywords": ["client exploit", "browser exploit", "office exploit", "pdf exploit"],
        "severity": "critical",
        "detection": "Monitor application crash logs",
    },

    # --------------------------------------------------
    # TA0003 - Persistence
    # --------------------------------------------------
    "T1053": {
        "id": "T1053",
        "name": "Scheduled Task/Job",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
        "description": "Adversaries abuse task scheduling to persist",
        "keywords": ["cron", "crontab", "scheduled task", "at command", "persistence"],
        "severity": "medium",
        "detection": "Monitor scheduled task creation",
    },
    "T1543": {
        "id": "T1543",
        "name": "Create or Modify System Process",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
        "description": "Adversaries create or modify system-level processes",
        "keywords": ["service creation", "systemd", "daemon", "system process"],
        "severity": "high",
        "detection": "Monitor service creation events",
    },

    # --------------------------------------------------
    # TA0004 - Privilege Escalation
    # --------------------------------------------------
    "T1068": {
        "id": "T1068",
        "name": "Exploitation for Privilege Escalation",
        "tactic": "Privilege Escalation",
        "tactic_id": "TA0004",
        "description": "Adversaries exploit vulnerabilities to escalate privileges",
        "keywords": ["privilege escalation", "privesc", "local exploit", "kernel exploit",
                    "sudo exploit", "suid"],
        "severity": "critical",
        "detection": "Monitor privilege use and system call activity",
    },
    "T1055": {
        "id": "T1055",
        "name": "Process Injection",
        "tactic": "Privilege Escalation",
        "tactic_id": "TA0004",
        "description": "Adversaries inject code into processes to evade defenses",
        "keywords": ["process injection", "createremotethread", "virtualalloc",
                    "dll injection", "shellcode injection", "hollowing"],
        "severity": "critical",
        "detection": "Monitor process memory modifications",
        "sub_techniques": ["T1055.001 - DLL Injection", "T1055.012 - Process Hollowing"],
    },

    # --------------------------------------------------
    # TA0005 - Defense Evasion
    # --------------------------------------------------
    "T1027": {
        "id": "T1027",
        "name": "Obfuscated Files or Information",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
        "description": "Adversaries obfuscate content to hide from defenses",
        "keywords": ["obfuscation", "encoding", "base64", "encrypted payload",
                    "packed", "obfuscated"],
        "severity": "medium",
        "detection": "Monitor for high entropy files and suspicious encoding",
    },
    "T1070": {
        "id": "T1070",
        "name": "Indicator Removal",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
        "description": "Adversaries delete or modify artifacts to remove evidence",
        "keywords": ["log deletion", "clear logs", "artifact removal", "timestomp",
                    "cover tracks"],
        "severity": "high",
        "detection": "Monitor log deletion and file modification events",
    },

    # --------------------------------------------------
    # TA0006 - Credential Access
    # --------------------------------------------------
    "T1552": {
        "id": "T1552",
        "name": "Unsecured Credentials",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": "Adversaries search for unsecured credentials in files/registry",
        "keywords": ["credential leak", "password file", "config file credentials",
                    "hardcoded password", "plaintext password", ".env", "credentials"],
        "severity": "critical",
        "detection": "Monitor access to credential files",
        "sub_techniques": ["T1552.001 - Credentials In Files", "T1552.004 - Private Keys"],
    },
    "T1110": {
        "id": "T1110",
        "name": "Brute Force",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": "Adversaries use brute force to gain account access",
        "keywords": ["brute force", "password spray", "credential stuffing",
                    "dictionary attack", "hydra", "medusa"],
        "severity": "high",
        "detection": "Monitor authentication failures",
        "sub_techniques": ["T1110.001 - Password Guessing", "T1110.003 - Password Spraying"],
    },
    "T1003": {
        "id": "T1003",
        "name": "OS Credential Dumping",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": "Adversaries dump credentials from OS and software",
        "keywords": ["mimikatz", "credential dumping", "lsass", "sam database",
                    "hash dump", "ntlm hash", "kerberos"],
        "severity": "critical",
        "detection": "Monitor LSASS access and memory reads",
    },

    # --------------------------------------------------
    # TA0007 - Discovery
    # --------------------------------------------------
    "T1046": {
        "id": "T1046",
        "name": "Network Service Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
        "description": "Adversaries scan networks to discover services",
        "keywords": ["port scan", "service scan", "network scan", "nmap", "masscan",
                    "service enumeration", "banner grabbing"],
        "severity": "medium",
        "detection": "Monitor network scanning activity",
    },
    "T1018": {
        "id": "T1018",
        "name": "Remote System Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
        "description": "Adversaries discover remote systems on the network",
        "keywords": ["host discovery", "ping sweep", "arp scan", "network discovery",
                    "subdomain enumeration"],
        "severity": "medium",
        "detection": "Monitor ICMP and ARP traffic",
    },
    "T1083": {
        "id": "T1083",
        "name": "File and Directory Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
        "description": "Adversaries enumerate files and directories",
        "keywords": ["directory listing", "file enumeration", "gobuster", "dirb",
                    "directory traversal", "file discovery"],
        "severity": "medium",
        "detection": "Monitor file system access",
    },

    # --------------------------------------------------
    # TA0008 - Lateral Movement
    # --------------------------------------------------
    "T1021": {
        "id": "T1021",
        "name": "Remote Services",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
        "description": "Adversaries use remote services to move laterally",
        "keywords": ["lateral movement", "remote service", "ssh lateral", "rdp lateral",
                    "smb lateral", "psexec", "wmi"],
        "severity": "critical",
        "detection": "Monitor remote service authentication",
        "sub_techniques": ["T1021.001 - RDP", "T1021.002 - SMB", "T1021.004 - SSH"],
    },
    "T1210": {
        "id": "T1210",
        "name": "Exploitation of Remote Services",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
        "description": "Adversaries exploit remote services to move laterally",
        "keywords": ["eternalblue", "bluekeep", "ms17-010", "remote exploit",
                    "lateral exploit", "smb exploit"],
        "severity": "critical",
        "detection": "Monitor exploitation of remote services",
    },

    # --------------------------------------------------
    # TA0009 - Collection
    # --------------------------------------------------
    "T1005": {
        "id": "T1005",
        "name": "Data from Local System",
        "tactic": "Collection",
        "tactic_id": "TA0009",
        "description": "Adversaries collect data from local system",
        "keywords": ["data collection", "file access", "data theft", "sensitive files"],
        "severity": "high",
        "detection": "Monitor file access patterns",
    },

    # --------------------------------------------------
    # TA0010 - Exfiltration
    # --------------------------------------------------
    "T1041": {
        "id": "T1041",
        "name": "Exfiltration Over C2 Channel",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
        "description": "Adversaries exfiltrate data over C2 channel",
        "keywords": ["data exfiltration", "c2 exfil", "data leak", "exfiltration"],
        "severity": "critical",
        "detection": "Monitor outbound traffic volumes",
    },

    # --------------------------------------------------
    # TA0011 - Command and Control
    # --------------------------------------------------
    "T1071": {
        "id": "T1071",
        "name": "Application Layer Protocol",
        "tactic": "Command and Control",
        "tactic_id": "TA0011",
        "description": "Adversaries use application layer protocols for C2",
        "keywords": ["c2", "command and control", "beacon", "c2 channel",
                    "http c2", "dns c2", "covert channel"],
        "severity": "critical",
        "detection": "Monitor network traffic for C2 patterns",
        "sub_techniques": ["T1071.001 - Web Protocols", "T1071.004 - DNS"],
    },
    "T1095": {
        "id": "T1095",
        "name": "Non-Application Layer Protocol",
        "tactic": "Command and Control",
        "tactic_id": "TA0011",
        "description": "Adversaries use non-application layer protocols for C2",
        "keywords": ["icmp tunnel", "raw socket c2", "tcp c2", "udp c2"],
        "severity": "high",
        "detection": "Monitor unusual protocol usage",
    },

    # --------------------------------------------------
    # TA0040 - Impact
    # --------------------------------------------------
    "T1486": {
        "id": "T1486",
        "name": "Data Encrypted for Impact",
        "tactic": "Impact",
        "tactic_id": "TA0040",
        "description": "Adversaries encrypt data to disrupt availability",
        "keywords": ["ransomware", "encryption", "file encryption", "wannacry",
                    "cryptolocker"],
        "severity": "critical",
        "detection": "Monitor file modification patterns",
    },
    "T1499": {
        "id": "T1499",
        "name": "Endpoint Denial of Service",
        "tactic": "Impact",
        "tactic_id": "TA0040",
        "description": "Adversaries perform DoS attacks",
        "keywords": ["dos", "ddos", "denial of service", "flood attack"],
        "severity": "high",
        "detection": "Monitor network traffic volumes",
    },
}

# Kill chain stages mapping
KILL_CHAIN_MAPPING = {
    "TA0001": {"stage": 1, "name": "Initial Access", "kill_chain": "Reconnaissance/Weaponization/Delivery"},
    "TA0002": {"stage": 2, "name": "Execution", "kill_chain": "Exploitation"},
    "TA0003": {"stage": 3, "name": "Persistence", "kill_chain": "Installation"},
    "TA0004": {"stage": 4, "name": "Privilege Escalation", "kill_chain": "Exploitation"},
    "TA0005": {"stage": 5, "name": "Defense Evasion", "kill_chain": "Exploitation"},
    "TA0006": {"stage": 6, "name": "Credential Access", "kill_chain": "Exploitation"},
    "TA0007": {"stage": 7, "name": "Discovery", "kill_chain": "Reconnaissance"},
    "TA0008": {"stage": 8, "name": "Lateral Movement", "kill_chain": "Lateral Movement"},
    "TA0009": {"stage": 9, "name": "Collection", "kill_chain": "Actions on Objectives"},
    "TA0010": {"stage": 10, "name": "Exfiltration", "kill_chain": "Actions on Objectives"},
    "TA0011": {"stage": 11, "name": "Command and Control", "kill_chain": "C2"},
    "TA0040": {"stage": 12, "name": "Impact", "kill_chain": "Actions on Objectives"},
}


# ==================================================
# 🎯 MAIN FUNCTIONS
# ==================================================

def map_to_mitre(findings: List[Dict]) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Maps findings to MITRE ATT&CK techniques.
    """
    mapped = []
    technique_ids = set()

    for finding in findings:
        title = (
            finding.get("template") or
            finding.get("name") or
            finding.get("type") or
            finding.get("description") or ""
        ).lower()

        for tech_id, tech_data in MITRE_TECHNIQUES.items():
            for keyword in tech_data["keywords"]:
                if keyword.lower() in title:
                    if tech_id not in technique_ids:
                        technique_ids.add(tech_id)
                        mapped.append({
                            "indicator": keyword,
                            "mitre_technique": f"{tech_id} - {tech_data['name']}",
                            "tactic": tech_data["tactic"],
                            "severity": tech_data["severity"],
                            "finding_source": finding.get("type", "unknown"),
                        })
                    break

    # Kill chain coverage
    tactics_covered = list(set(m["tactic"] for m in mapped))

    return {
        "mapped_techniques": mapped,
        "total_mappings": len(mapped),
        "tactics_covered": tactics_covered,
        "kill_chain_coverage": _get_kill_chain_coverage(technique_ids),
    }


def get_technique(technique_id: str) -> Optional[Dict]:
    """MITRE technique details lo."""
    return MITRE_TECHNIQUES.get(technique_id)


def map_service_to_mitre(service: str, port: int = None) -> List[Dict]:
    """Service name se MITRE techniques map karo."""
    service_technique_map = {
        "ssh": ["T1021", "T1110", "T1078"],
        "ftp": ["T1078", "T1083"],
        "http": ["T1190", "T1059"],
        "https": ["T1190", "T1071"],
        "smb": ["T1021", "T1210"],
        "rdp": ["T1021", "T1110"],
        "mysql": ["T1190", "T1078"],
        "redis": ["T1190", "T1059"],
        "telnet": ["T1021", "T1040"],
        "smtp": ["T1566", "T1078"],
    }

    tech_ids = service_technique_map.get(service.lower(), ["T1046"])
    result = []

    for tech_id in tech_ids:
        tech = MITRE_TECHNIQUES.get(tech_id)
        if tech:
            result.append({
                "technique_id": tech_id,
                "technique_name": tech["name"],
                "tactic": tech["tactic"],
                "severity": tech["severity"],
            })

    return result


def analyze_scan_for_mitre(scan_result: Dict) -> Dict:
    """
    Full scan result se MITRE mapping generate karo.
    """
    all_techniques = {}
    tactic_coverage = {}

    open_details = scan_result.get("open_port_details", [])

    for port_info in open_details:
        service = port_info.get("service", "unknown")
        port = port_info.get("port", 0)

        techniques = map_service_to_mitre(service, port)

        for tech in techniques:
            tech_id = tech["technique_id"]
            if tech_id not in all_techniques:
                all_techniques[tech_id] = tech
                all_techniques[tech_id]["services"] = []
            all_techniques[tech_id]["services"].append(f"{service}:{port}")

            tactic = tech["tactic"]
            if tactic not in tactic_coverage:
                tactic_coverage[tactic] = 0
            tactic_coverage[tactic] += 1

    # CVE findings
    cve_findings = scan_result.get("cve_analysis", {}).get("findings", [])
    for finding in cve_findings:
        for cve in finding.get("cves", []):
            mitre_id = cve.get("mitre", "")
            if mitre_id and mitre_id in MITRE_TECHNIQUES:
                tech = MITRE_TECHNIQUES[mitre_id]
                if mitre_id not in all_techniques:
                    all_techniques[mitre_id] = {
                        "technique_id": mitre_id,
                        "technique_name": tech["name"],
                        "tactic": tech["tactic"],
                        "severity": tech["severity"],
                        "services": [],
                        "source": "cve_analysis"
                    }

    techniques_list = list(all_techniques.values())
    critical = [t for t in techniques_list if t.get("severity") == "critical"]

    return {
        "target": scan_result.get("target", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "techniques": techniques_list,
        "total_techniques": len(techniques_list),
        "tactic_coverage": tactic_coverage,
        "critical_techniques": critical,
        "kill_chain_stages": _get_kill_chain_coverage(set(all_techniques.keys())),
        "attack_sophistication": _calculate_sophistication(techniques_list),
    }


def _get_kill_chain_coverage(technique_ids: set) -> List[str]:
    """Kill chain stages covered."""
    stages = set()
    for tech_id in technique_ids:
        tech = MITRE_TECHNIQUES.get(tech_id)
        if tech:
            tactic_id = tech.get("tactic_id", "")
            kc = KILL_CHAIN_MAPPING.get(tactic_id, {})
            if kc:
                stages.add(kc["kill_chain"])
    return list(stages)


def _calculate_sophistication(techniques: List[Dict]) -> str:
    """Attack sophistication level calculate karo."""
    if not techniques:
        return "Unknown"

    tactics = set(t.get("tactic") for t in techniques)
    critical = sum(1 for t in techniques if t.get("severity") == "critical")

    if len(tactics) >= 5 or critical >= 3:
        return "Advanced"
    elif len(tactics) >= 3 or critical >= 1:
        return "Intermediate"
    else:
        return "Basic"


def get_mitre_navigator_layer(techniques: List[Dict]) -> Dict:
    """MITRE ATT&CK Navigator layer format generate karo."""
    layer_techniques = []

    for tech in techniques:
        tech_id = tech.get("technique_id", "")
        if tech_id:
            score = {"critical": 5, "high": 4, "medium": 3, "low": 2}.get(
                tech.get("severity", "low"), 1
            )
            layer_techniques.append({
                "techniqueID": tech_id,
                "score": score,
                "comment": tech.get("technique_name", ""),
                "enabled": True,
            })

    return {
        "name": "Chhoti Don Scan Results",
        "versions": {"attack": "14", "navigator": "4.9"},
        "domain": "enterprise-attack",
        "techniques": layer_techniques,
    }
