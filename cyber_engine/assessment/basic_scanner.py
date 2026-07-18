"""
Chhoti Don - Basic Scanner
Advanced port scanner with service detection, banner grabbing,
CVE integration, risk scoring, and concurrent scanning.
Phase 2.2 - Full Upgrade
"""

import socket
import time
import datetime
import re
from typing import Dict, List, Optional, Tuple, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==================================================
# 🎯 PORT DEFINITIONS
# ==================================================

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143,
                443, 445, 1433, 3306, 3389, 5432, 6379, 8080,
                8443, 27017]

TOP_100_PORTS = [
    7, 9, 13, 21, 22, 23, 25, 26, 37, 53, 79, 80, 81, 88,
    106, 110, 111, 113, 119, 135, 139, 143, 144, 179, 199,
    389, 427, 443, 444, 445, 465, 513, 514, 515, 543, 544,
    548, 554, 587, 631, 646, 873, 990, 993, 995, 1025, 1026,
    1027, 1028, 1029, 1110, 1433, 1720, 1723, 1755, 1900,
    2000, 2001, 2049, 2121, 2717, 3000, 3128, 3306, 3389,
    3986, 4899, 5000, 5009, 5051, 5060, 5101, 5190, 5357,
    5432, 5631, 5666, 5800, 5900, 6000, 6001, 6646, 6379,
    7070, 8000, 8008, 8009, 8080, 8081, 8443, 8888, 9100,
    9999, 10000, 32768, 49152, 49153, 49154, 49155, 49156, 27017
]

# Port → Service mapping
PORT_SERVICE_MAP = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
    53: "dns", 80: "http", 110: "pop3", 111: "rpcbind",
    135: "msrpc", 139: "netbios", 143: "imap", 179: "bgp",
    389: "ldap", 443: "https", 445: "smb", 465: "smtps",
    587: "smtp", 631: "ipp", 993: "imaps", 995: "pop3s",
    1433: "mssql", 1723: "pptp", 3306: "mysql", 3389: "rdp",
    5432: "postgresql", 5900: "vnc", 6379: "redis",
    8080: "http-proxy", 8443: "https-alt", 8888: "http-alt",
    27017: "mongodb", 9200: "elasticsearch",
}

# Service risk weights
SERVICE_RISK = {
    "telnet": 9, "rdp": 8, "smb": 8, "redis": 8,
    "mongodb": 7, "mysql": 7, "mssql": 7, "ftp": 6,
    "ssh": 5, "smtp": 4, "http": 3, "https": 2,
    "dns": 2, "unknown": 1,
}

# Banner patterns for service detection
BANNER_PATTERNS = {
    "ssh": re.compile(r"SSH-\d+\.\d+-([\w\.\-]+)", re.IGNORECASE),
    "ftp": re.compile(r"^\d{3}[\s-].*(?:ftp|FileZilla|ProFTPD|vsftpd)", re.IGNORECASE),
    "smtp": re.compile(r"^\d{3}[\s-].*(?:SMTP|ESMTP|Postfix|Sendmail|Exim)", re.IGNORECASE),
    "http": re.compile(r"HTTP/\d+\.\d+|Server:\s*([^\r\n]+)", re.IGNORECASE),
    "mysql": re.compile(r"mysql|mariadb", re.IGNORECASE),
    "redis": re.compile(r"PONG|\+OK|Redis", re.IGNORECASE),
    "mongodb": re.compile(r"ismaster|MongoDB", re.IGNORECASE),
}

# HTTP probe request
HTTP_PROBE = b"HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n"
REDIS_PROBE = b"PING\r\n"
GENERIC_PROBE = b"\r\n"


class BasicScanner:
    """
    Advanced Basic Scanner.
    Fast, concurrent port scanning with service detection.
    """

    def __init__(
        self,
        timeout: float = 1.0,
        max_threads: int = 100,
        grab_banners: bool = True,
    ):
        self.timeout = timeout
        self.max_threads = max_threads
        self.grab_banners = grab_banners

    # ==================================================
    # 🚀 Main Scan (PRESERVED + UPGRADED)
    # ==================================================
    def scan(self, target: str, ports: List[int] = None) -> Dict:
        """
        Main scan function.
        Preserved interface + advanced internals.
        """
        ports = ports or COMMON_PORTS
        start_time = time.time()

        # Validate target
        resolved_ip = self._resolve_target(target)
        if not resolved_ip:
            return {
                "status": "error",
                "target": target,
                "message": "Could not resolve target",
            }

        # Concurrent port scan
        results = self._concurrent_scan(resolved_ip, ports)

        # Extract open ports
        open_results = [r for r in results if r["status"] == "open"]
        open_port_numbers = [r["port"] for r in open_results]

        # Risk assessment
        risk = self._assess_risk(open_results)

        # CVE hints
        cve_hints = self._get_cve_hints(open_results)

        duration = round(time.time() - start_time, 3)

        return {
            "status": "success",
            "target": target,
            "resolved_ip": resolved_ip,

            # Backward compat
            "open_ports": open_port_numbers,
            "total_open": len(open_port_numbers),

            # Enhanced
            "open_port_details": open_results,
            "closed_ports": len(ports) - len(open_results),
            "total_scanned": len(ports),
            "risk_assessment": risk,
            "cve_hints": cve_hints,
            "scan_duration_sec": duration,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    # ==================================================
    # ⚡ Concurrent Scanning
    # ==================================================
    def _concurrent_scan(self, target: str, ports: List[int]) -> List[Dict]:
        """Concurrent port scanning."""
        results = []

        with ThreadPoolExecutor(max_workers=min(self.max_threads, len(ports))) as executor:
            futures = {
                executor.submit(self._scan_port, target, port): port
                for port in ports
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception:
                    pass

        # Sort by port number
        results.sort(key=lambda x: x["port"])
        return results

    def _scan_port(self, target: str, port: int) -> Optional[Dict]:
        """Single port scan."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((target, port))
            sock.close()

            if result == 0:
                # Port is open
                service = PORT_SERVICE_MAP.get(port, "unknown")
                banner = ""
                version = None

                if self.grab_banners:
                    banner, version = self._grab_banner(target, port, service)

                return {
                    "port": port,
                    "status": "open",
                    "service": service,
                    "version": version,
                    "banner": banner[:200] if banner else "",
                    "risk_weight": SERVICE_RISK.get(service, 1),
                }
            else:
                return {"port": port, "status": "closed"}

        except socket.timeout:
            return {"port": port, "status": "filtered"}
        except Exception:
            return {"port": port, "status": "error"}

    # ==================================================
    # 🔍 Banner Grabbing
    # ==================================================
    def _grab_banner(
        self,
        target: str,
        port: int,
        service: str
    ) -> Tuple[str, Optional[str]]:
        """Banner grab karo."""
        banner = ""
        version = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((target, port))

            # Service-specific probes
            if port in [80, 8080, 8443, 443]:
                sock.send(HTTP_PROBE)
            elif port == 6379:
                sock.send(REDIS_PROBE)
            else:
                sock.send(GENERIC_PROBE)

            banner = sock.recv(1024).decode(errors="ignore").strip()
            sock.close()

            # Version extraction
            version = self._extract_version(banner, service)

        except Exception:
            pass

        return banner, version

    def _extract_version(self, banner: str, service: str) -> Optional[str]:
        """Banner se version extract karo."""
        if not banner:
            return None

        pattern = BANNER_PATTERNS.get(service)
        if pattern:
            match = pattern.search(banner)
            if match and match.groups():
                return match.group(1)[:50]

        # Generic version extraction
        ver_match = re.search(r"[\d]+\.[\d]+\.?[\d]*", banner)
        if ver_match:
            return ver_match.group()

        return None

    # ==================================================
    # ⚠️ Risk Assessment
    # ==================================================
    def _assess_risk(self, open_results: List[Dict]) -> Dict:
        """Open ports se risk assess karo."""
        if not open_results:
            return {"score": 0, "level": "NONE", "factors": []}

        score = 0
        factors = []
        critical_services = []

        for port_info in open_results:
            service = port_info.get("service", "unknown")
            risk_w = port_info.get("risk_weight", 1)
            score += risk_w

            if risk_w >= 7:
                critical_services.append(f"{service}:{port_info['port']}")
                factors.append(f"High-risk service: {service} on port {port_info['port']}")

        # Telnet special case
        if any(p["port"] == 23 for p in open_results):
            score += 5
            factors.append("⚠️ TELNET open — plaintext protocol, critical risk!")

        # Redis without auth
        if any(p["port"] == 6379 for p in open_results):
            pong = any("PONG" in p.get("banner", "") for p in open_results if p["port"] == 6379)
            if pong:
                score += 8
                factors.append("⚠️ Redis unauthenticated access detected!")

        # MongoDB
        if any(p["port"] == 27017 for p in open_results):
            score += 5
            factors.append("MongoDB exposed — check for unauthenticated access")

        # Normalize
        normalized = min(score * 3, 100)

        if normalized >= 80:
            level = "CRITICAL"
        elif normalized >= 60:
            level = "HIGH"
        elif normalized >= 40:
            level = "MEDIUM"
        elif normalized >= 20:
            level = "LOW"
        else:
            level = "INFO"

        return {
            "score": normalized,
            "level": level,
            "raw_score": score,
            "critical_services": critical_services,
            "factors": factors[:5],
        }

    # ==================================================
    # 🔴 CVE Hints
    # ==================================================
    def _get_cve_hints(self, open_results: List[Dict]) -> List[Dict]:
        """Open services ke liye CVE hints."""
        hints = []

        high_risk_cves = {
            "rdp": [("CVE-2019-0708", "BlueKeep - Pre-auth RCE", "critical")],
            "smb": [("CVE-2017-0144", "EternalBlue - WannaCry", "critical")],
            "ftp": [("CVE-2015-3306", "ProFTPD mod_copy", "critical")],
            "mysql": [("CVE-2012-2122", "Auth bypass timing attack", "high")],
            "redis": [("CVE-2022-0543", "Lua sandbox escape RCE", "critical")],
            "telnet": [("CVE-2020-10188", "Telnetd RCE", "critical")],
            "ssh": [("CVE-2024-6387", "RegreSSHion RCE", "high")],
        }

        for port_info in open_results:
            service = port_info.get("service", "unknown")
            cves = high_risk_cves.get(service, [])

            for cve_id, desc, severity in cves:
                hints.append({
                    "port": port_info["port"],
                    "service": service,
                    "cve_id": cve_id,
                    "description": desc,
                    "severity": severity,
                    "note": "Verify version before confirming",
                })

        return hints

    # ==================================================
    # 🌐 Target Resolution
    # ==================================================
    def _resolve_target(self, target: str) -> Optional[str]:
        """Hostname resolve karo."""
        try:
            return socket.gethostbyname(target)
        except socket.gaierror:
            return None

    # ==================================================
    # 📊 Summary
    # ==================================================
    def get_summary(self, scan_result: Dict) -> str:
        """Human-readable summary."""
        lines = [
            f"🎯 Target    : {scan_result.get('target')}",
            f"🔓 Open Ports: {scan_result.get('total_open', 0)} → {scan_result.get('open_ports', [])}",
            f"⏱  Duration  : {scan_result.get('scan_duration_sec', 0)}s",
        ]

        risk = scan_result.get("risk_assessment", {})
        if risk:
            lines.append(f"⚠️  Risk Level : {risk.get('level', 'N/A')}")
            lines.append(f"📊 Risk Score : {risk.get('score', 0)}/100")

        cves = scan_result.get("cve_hints", [])
        if cves:
            lines.append(f"🔴 CVE Hints  : {len(cves)}")

        return "\n".join(lines)


# ==================================================
# 🔧 STANDALONE FUNCTIONS (PRESERVED + UPGRADED)
# ==================================================

def scan_common_ports(target: str) -> Dict:
    """
    Original function — preserved + upgraded.
    """
    scanner = BasicScanner(timeout=1.0, max_threads=50)
    return scanner.scan(target, COMMON_PORTS)


def quick_scan(target: str) -> Dict:
    """Fast scan — top 20 ports."""
    scanner = BasicScanner(timeout=0.5, max_threads=20, grab_banners=False)
    top20 = [21, 22, 23, 25, 53, 80, 110, 139, 143, 443,
             445, 1433, 3306, 3389, 5432, 6379, 8080, 8443, 8888, 27017]
    return scanner.scan(target, top20)


def full_scan(target: str) -> Dict:
    """Full top-100 ports scan."""
    scanner = BasicScanner(timeout=1.0, max_threads=100)
    return scanner.scan(target, TOP_100_PORTS)


def check_port(target: str, port: int) -> bool:
    """Single port check — True if open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex((target, port))
        sock.close()
        return result == 0
    except Exception:
        return False
