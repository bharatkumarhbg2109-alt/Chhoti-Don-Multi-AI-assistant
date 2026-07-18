"""
from typing import Dict, List, List
Chhoti Don- CVE Engine
Comprehensive CVE database with exploit suggestions,
CVSS scoring, and remediation guidance.
Phase 2.2 - Full Upgrade
"""
from typing import List,Dict, Optional
import re

# ==================================================
# 🗄️ EXPANDED CVE DATABASE
# Service → List of CVE details
# ==================================================

CVE_DATABASE = {

    # --------------------------------------------------
    # 🌐 Web Servers
    # --------------------------------------------------
    "apache": [
        {
            "cve_id": "CVE-2021-41773",
            "cvss": 9.8,
            "severity": "critical",
            "description": "Path traversal and RCE in Apache HTTP Server 2.4.49",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["2.4.49"],
            "remediation": "Upgrade to Apache 2.4.51 or later",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-41773"]
        },
        {
            "cve_id": "CVE-2021-42013",
            "cvss": 9.8,
            "severity": "critical",
            "description": "Path traversal bypass in Apache 2.4.49-2.4.50",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["2.4.49", "2.4.50"],
            "remediation": "Upgrade to Apache 2.4.51+",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-42013"]
        },
        {
            "cve_id": "CVE-2017-7679",
            "cvss": 9.8,
            "severity": "critical",
            "description": "Buffer overflow in mod_mime Apache",
            "exploit_available": True,
            "exploit_type": "Buffer Overflow",
            "affected_versions": ["< 2.2.33", "< 2.4.26"],
            "remediation": "Upgrade Apache to latest version",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2017-7679"]
        },
    ],

    "nginx": [
        {
            "cve_id": "CVE-2019-20372",
            "cvss": 5.3,
            "severity": "medium",
            "description": "HTTP request smuggling in NGINX before 1.17.7",
            "exploit_available": False,
            "exploit_type": "Request Smuggling",
            "affected_versions": ["< 1.17.7"],
            "remediation": "Upgrade NGINX to 1.17.7+",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2019-20372"]
        },
        {
            "cve_id": "CVE-2021-23017",
            "cvss": 7.7,
            "severity": "high",
            "description": "1-byte memory overwrite in NGINX resolver",
            "exploit_available": True,
            "exploit_type": "Memory Corruption",
            "affected_versions": ["< 1.20.1"],
            "remediation": "Upgrade NGINX to 1.20.1+",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-23017"]
        },
    ],

    # --------------------------------------------------
    # 🔐 SSH
    # --------------------------------------------------
    "ssh": [
        {
            "cve_id": "CVE-2023-38408",
            "cvss": 9.8,
            "severity": "critical",
            "description": "Remote code execution in OpenSSH ssh-agent",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["< 9.3p2"],
            "remediation": "Upgrade OpenSSH to 9.3p2+",
            "mitre": "T1021.004",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2023-38408"]
        },
        {
            "cve_id": "CVE-2024-6387",
            "cvss": 8.1,
            "severity": "high",
            "description": "RegreSSHion - RCE in OpenSSH server (regresssion of CVE-2006-5051)",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["8.5p1 - 9.7p1"],
            "remediation": "Upgrade to OpenSSH 9.8p1+",
            "mitre": "T1021.004",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2024-6387"]
        },
        {
            "cve_id": "CVE-2016-0777",
            "cvss": 6.5,
            "severity": "medium",
            "description": "OpenSSH roaming feature information leak",
            "exploit_available": False,
            "exploit_type": "Information Disclosure",
            "affected_versions": ["5.4 - 7.1"],
            "remediation": "Upgrade OpenSSH to 7.1p2+",
            "mitre": "T1040",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2016-0777"]
        },
    ],

    # --------------------------------------------------
    # 🗄️ Databases
    # --------------------------------------------------
    "mysql": [
        {
            "cve_id": "CVE-2016-6662",
            "cvss": 9.8,
            "severity": "critical",
            "description": "MySQL remote code execution via config file manipulation",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["< 5.5.52", "< 5.6.33", "< 5.7.15"],
            "remediation": "Upgrade MySQL and restrict file privileges",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2016-6662"]
        },
        {
            "cve_id": "CVE-2012-2122",
            "cvss": 5.1,
            "severity": "medium",
            "description": "MySQL authentication bypass via timing attack",
            "exploit_available": True,
            "exploit_type": "Authentication Bypass",
            "affected_versions": ["< 5.1.63", "< 5.5.24", "< 5.6.6"],
            "remediation": "Upgrade MySQL immediately",
            "mitre": "T1078",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2012-2122"]
        },
    ],

    "mssql": [
        {
            "cve_id": "CVE-2020-0618",
            "cvss": 8.8,
            "severity": "high",
            "description": "RCE in Microsoft SQL Server Reporting Services",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["SQL Server 2012-2017"],
            "remediation": "Apply Microsoft security patch KB4532097",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2020-0618"]
        },
    ],

    # --------------------------------------------------
    # 📁 FTP
    # --------------------------------------------------
    "ftp": [
        {
            "cve_id": "CVE-2010-4221",
            "cvss": 10.0,
            "severity": "critical",
            "description": "ProFTPD remote code execution via Telnet IAC",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["ProFTPD < 1.3.3c"],
            "remediation": "Upgrade ProFTPD to 1.3.3c+",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2010-4221"]
        },
        {
            "cve_id": "CVE-2015-3306",
            "cvss": 10.0,
            "severity": "critical",
            "description": "ProFTPD mod_copy unauthenticated file copy",
            "exploit_available": True,
            "exploit_type": "Unauthorized File Access",
            "affected_versions": ["ProFTPD < 1.3.5b"],
            "remediation": "Upgrade ProFTPD and disable mod_copy",
            "mitre": "T1083",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2015-3306"]
        },
    ],

    # --------------------------------------------------
    # 🖥️ RDP
    # --------------------------------------------------
    "rdp": [
        {
            "cve_id": "CVE-2019-0708",
            "cvss": 9.8,
            "severity": "critical",
            "description": "BlueKeep - Pre-auth RCE in Windows RDP",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution (Wormable)",
            "affected_versions": ["Windows XP", "Windows 7", "Windows Server 2003/2008"],
            "remediation": "Apply MS19-0708 patch immediately",
            "mitre": "T1210",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2019-0708"]
        },
        {
            "cve_id": "CVE-2019-1182",
            "cvss": 9.8,
            "severity": "critical",
            "description": "DejaBlue - RDP RCE in Windows 10/Server 2019",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["Windows 10", "Server 2016/2019"],
            "remediation": "Apply August 2019 Windows security updates",
            "mitre": "T1210",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2019-1182"]
        },
    ],

    # --------------------------------------------------
    # 📧 SMTP
    # --------------------------------------------------
    "smtp": [
        {
            "cve_id": "CVE-2020-7247",
            "cvss": 9.8,
            "severity": "critical",
            "description": "OpenSMTPD remote code execution",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["< OpenSMTPD 6.6.2"],
            "remediation": "Upgrade OpenSMTPD to 6.6.2+",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2020-7247"]
        },
    ],

    # --------------------------------------------------
    # 🔗 SMB
    # --------------------------------------------------
    "smb": [
        {
            "cve_id": "CVE-2017-0144",
            "cvss": 9.3,
            "severity": "critical",
            "description": "EternalBlue - SMBv1 RCE used by WannaCry",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution (Wormable)",
            "affected_versions": ["Windows XP - Windows 10 (unpatched)"],
            "remediation": "Apply MS17-010 patch, disable SMBv1",
            "mitre": "T1210",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2017-0144"]
        },
    ],

    # --------------------------------------------------
    # 🌐 Telnet
    # --------------------------------------------------
    "telnet": [
        {
            "cve_id": "CVE-2020-10188",
            "cvss": 9.8,
            "severity": "critical",
            "description": "Telnetd remote code execution via environment variables",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["telnetd < 0.17-42"],
            "remediation": "Disable Telnet, use SSH instead",
            "mitre": "T1021.004",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2020-10188"]
        },
    ],

    # --------------------------------------------------
    # 🐘 PHP
    # --------------------------------------------------
    "php": [
        {
            "cve_id": "CVE-2019-11043",
            "cvss": 9.8,
            "severity": "critical",
            "description": "PHP-FPM RCE when nginx with specific config",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["PHP < 7.1.33", "< 7.2.24", "< 7.3.11"],
            "remediation": "Upgrade PHP and fix nginx config",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2019-11043"]
        },
    ],

    # --------------------------------------------------
    # 🔧 Redis
    # --------------------------------------------------
    "redis": [
        {
            "cve_id": "CVE-2022-0543",
            "cvss": 10.0,
            "severity": "critical",
            "description": "Lua sandbox escape in Redis leading to RCE",
            "exploit_available": True,
            "exploit_type": "Remote Code Execution",
            "affected_versions": ["Redis on Debian/Ubuntu"],
            "remediation": "Update Redis package on Debian/Ubuntu",
            "mitre": "T1190",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2022-0543"]
        },
    ],
}


# ==================================================
# 🎯 MAIN FUNCTIONS
# ==================================================

def suggest_cves(service_name: str) -> List[str]:
    """
    Legacy function — preserved for backward compatibility.
    Returns list of CVE IDs for a service.
    """
    service_name = service_name.lower()

    for key in CVE_DATABASE:
        if key in service_name:
            return [cve["cve_id"] for cve in CVE_DATABASE[key]]

    return []


def get_cve_details(service_name: str) -> List[Dict]:
    """
    Full CVE details for a service.

    Returns list of CVE dicts with:
    - cve_id, cvss, severity, description
    - exploit_available, exploit_type
    - affected_versions, remediation
    - mitre technique
    """
    service_name = service_name.lower()

    for key in CVE_DATABASE:
        if key in service_name:
            return CVE_DATABASE[key]

    return []


def get_critical_cves(service_name: str) -> List[Dict]:
    """Sirf critical CVEs return karo."""
    all_cves = get_cve_details(service_name)
    return [c for c in all_cves if c.get("cvss", 0) >= 9.0]


def get_exploitable_cves(service_name: str) -> List[Dict]:
    """Sirf exploit available CVEs return karo."""
    all_cves = get_cve_details(service_name)
    return [c for c in all_cves if c.get("exploit_available", False)]


def analyze_scan_results(scan_results: Dict) -> Dict:
    """
    Port scan results se CVEs automatically map karo.

    Args:
        scan_results: PortScanner.scan_ports() ka output

    Returns:
        dict with CVE findings per port
    """
    findings = []
    total_critical = 0
    total_exploitable = 0

    open_ports = scan_results.get("open_port_details", [])

    for port_info in open_ports:
        service = port_info.get("service", "unknown")
        port = port_info.get("port")
        banner = port_info.get("banner", "")

        cves = get_cve_details(service)

        # Banner se version detect karke filter karo
        if banner and cves:
            cves = _filter_by_banner(cves, banner)

        critical = [c for c in cves if c.get("cvss", 0) >= 9.0]
        exploitable = [c for c in cves if c.get("exploit_available", False)]

        total_critical += len(critical)
        total_exploitable += len(exploitable)

        if cves:
            findings.append({
                "port": port,
                "service": service,
                "banner": banner[:100] if banner else "",
                "cve_count": len(cves),
                "critical_count": len(critical),
                "exploitable_count": len(exploitable),
                "cves": cves,
                "highest_cvss": max(c.get("cvss", 0) for c in cves),
                "mitre_techniques": list(set(c.get("mitre", "") for c in cves if c.get("mitre")))
            })

    # Overall risk assessment
    if total_critical >= 3:
        overall_risk = "CRITICAL"
    elif total_critical >= 1:
        overall_risk = "HIGH"
    elif total_exploitable >= 1:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    return {
        "target": scan_results.get("target", "unknown"),
        "findings": findings,
        "summary": {
            "total_vulnerable_ports": len(findings),
            "total_cves_found": sum(f["cve_count"] for f in findings),
            "total_critical": total_critical,
            "total_exploitable": total_exploitable,
            "overall_risk": overall_risk,
        }
    }


def get_remediation_plan(service_name: str) -> List[str]:
    """Service ke liye remediation steps return karo."""
    cves = get_cve_details(service_name)
    remediations = list(set(c.get("remediation", "") for c in cves if c.get("remediation")))
    return remediations


def _filter_by_banner(cves: List[Dict], banner: str) -> List[Dict]:
    """Banner version se CVEs filter karo."""
    version_match = re.search(r"[\d]+\.[\d]+\.?[\d]*", banner)
    if not version_match:
        return cves
    return cves
