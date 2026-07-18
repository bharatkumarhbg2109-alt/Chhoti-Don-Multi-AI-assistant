"""
Chhoti Don - Port Scanner
Advanced TCP port scanner with CVE integration.
Phase 2.2 - Full Upgrade
"""

import socket
import time
import re
from typing import Dict, List, List


class PortScanner:
    """
    Controlled TCP Port Scanner
    Safe, validated, intelligent scanning with CVE integration.
    Phase 2.2 — Concurrent + CVE + Risk Upgrade
    """

    def __init__(self, timeout: int = 1, max_ports: int = 100, max_threads: int = 50):
        self.timeout = timeout
        self.max_ports = max_ports
        self.max_threads = max_threads

    # --------------------------------------------------
    # 🔒 Input Validation (PRESERVED)
    # --------------------------------------------------
    def _validate_ports(self, ports: List[int]) -> List[int]:
        if not isinstance(ports, list):
            raise ValueError("Ports must be a list of integers")

        cleaned_ports = []
        for p in ports:
            if isinstance(p, int) and 1 <= p <= 65535:
                cleaned_ports.append(p)

        cleaned_ports = list(set(cleaned_ports))

        if len(cleaned_ports) > self.max_ports:
            cleaned_ports = cleaned_ports[:self.max_ports]

        return cleaned_ports

    # --------------------------------------------------
    # 🧠 Banner Grab (PRESERVED + Improved)
    # --------------------------------------------------
    def _grab_banner(self, target: str, port: int) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((target, port))

            # HTTP banner
            if port in [80, 8080, 8443]:
                sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
            else:
                sock.send(b"\r\n")

            banner = sock.recv(1024).decode(errors="ignore").strip()
            sock.close()
            return banner[:300] if banner else ""
        except Exception:
            return ""

    # --------------------------------------------------
    # 🔍 Fingerprint Intelligence (PRESERVED + Enhanced)
    # --------------------------------------------------
    def _fingerprint_service(self, port: int, banner: str) -> Dict:
        banner_lower = banner.lower()
        service = "unknown"
        version = None
        confidence = 0.3

        port_service_map = {
            21: "ftp",
            22: "ssh",
            23: "telnet",
            25: "smtp",
            53: "dns",
            80: "http",
            110: "pop3",
            143: "imap",
            443: "https",
            445: "smb",
            1433: "mssql",
            3306: "mysql",
            3389: "rdp",
            5432: "postgresql",
            6379: "redis",
            8080: "http",
            8443: "https",
            27017: "mongodb",
        }

        if port in port_service_map:
            service = port_service_map[port]
            confidence = 0.6

        # Banner-based refinement
        patterns = {
            "ssh": r"openssh[\s/]?([\d\.]+)",
            "ftp": r"(?:proftpd|vsftpd|filezilla)[\s/]?([\d\.]+)?",
            "http": r"server:\s*([^\r\n]+)",
            "mysql": r"mysql[\s\-]?([\d\.]+)?",
            "smtp": r"(?:postfix|sendmail|exim)[\s/]?([\d\.]+)?",
            "redis": r"redis[\s/]?([\d\.]+)?",
        }

        for svc, pattern in patterns.items():
            match = re.search(pattern, banner_lower)
            if match:
                service = svc
                version = match.group(1) if match.groups() else None
                confidence = 0.85
                break

        return {
            "service": service,
            "version": version,
            "confidence": round(confidence, 2)
        }

    # --------------------------------------------------
    # 🔫 Single Port Scan (for threading)
    # --------------------------------------------------
    def _scan_single_port(self, target: str, port: int) -> Dict:
        """Single port scan karo."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((target, port))
            sock.close()

            if result == 0:
                banner = self._grab_banner(target, port)
                fingerprint = self._fingerprint_service(port, banner)

                return {
                    "port": port,
                    "status": "open",
                    "banner": banner,
                    "service": fingerprint["service"],
                    "version": fingerprint["version"],
                    "confidence": fingerprint["confidence"]
                }
            else:
                return {"port": port, "status": "closed"}

        except Exception as e:
            return {"port": port, "status": "error", "error": str(e)}

    # --------------------------------------------------
    # 🚀 Main Scan — Concurrent (UPGRADED)
    # --------------------------------------------------
    def scan_ports(self, target: str, ports: List[int], use_cve: bool = True) -> Dict:
        """
        Main port scan with concurrent threads + CVE integration.

        Args:
            target: IP/hostname to scan
            ports: List of ports
            use_cve: Auto-run CVE analysis on results

        Returns:
            Complete scan + CVE analysis results
        """
        start_time = time.time()
        validated_ports = self._validate_ports(ports)
        results = []

        # Concurrent scanning
        with ThreadPoolExecutor(max_workers=min(self.max_threads, len(validated_ports))) as executor:
            futures = {
                executor.submit(self._scan_single_port, target, port): port
                for port in validated_ports
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    port = futures[future]
                    results.append({"port": port, "status": "error", "error": str(e)})

        # Sort by port number
        results.sort(key=lambda x: x["port"])

        open_ports = [r for r in results if r["status"] == "open"]
        open_port_numbers = [r["port"] for r in open_ports]

        scan_result = {
            "target": target,
            "total_ports_scanned": len(validated_ports),
            "open_ports": open_port_numbers,
            "open_port_details": open_ports,
            "raw_results": results,
            "scan_duration_sec": round(time.time() - start_time, 3)
        }

        # Auto CVE analysis
        if use_cve and open_ports:
            try:
                from cyber_engine.vuln_analysis.cve_engine import analyze_scan_results
                cve_analysis = analyze_scan_results(scan_result)
                scan_result["cve_analysis"] = cve_analysis
            except ImportError:
                pass

        # Auto risk scoring
        try:
            from cyber_engine.intelligence.risk_calculator import generate_risk_report
            risk_report = generate_risk_report(scan_result)
            scan_result["risk_report"] = risk_report
        except ImportError:
            pass

        return scan_result

    # --------------------------------------------------
    # 🎯 Quick Scan — Common ports only
    # --------------------------------------------------
    def quick_scan(self, target: str) -> Dict:
        """Top 20 common ports scan karo."""
        common_ports = [
            21, 22, 23, 25, 53, 80, 110, 135,
            139, 143, 443, 445, 1433, 3306,
            3389, 5432, 6379, 8080, 8443, 27017
        ]
        return self.scan_ports(target, common_ports)

    # --------------------------------------------------
    # 📊 Scan Summary
    # --------------------------------------------------
    def get_summary(self, scan_result: Dict) -> str:
        """Human-readable scan summary."""
        target = scan_result.get("target", "unknown")
        open_ports = scan_result.get("open_ports", [])
        duration = scan_result.get("scan_duration_sec", 0)
        risk = scan_result.get("risk_report", {})

        lines = [
            f"🎯 Target      : {target}",
            f"🔓 Open Ports  : {len(open_ports)} → {open_ports}",
            f"⏱  Duration    : {duration}s",
        ]

        if risk:
            lines.append(f"⚠️  Risk Level  : {risk.get('risk_level', 'N/A')}")
            lines.append(f"📊 Risk Score  : {risk.get('risk_score', 0)}/100")

        cve = scan_result.get("cve_analysis", {})
        if cve:
            summary = cve.get("summary", {})
            lines.append(f"🔴 CVEs Found  : {summary.get('total_cves_found', 0)}")
            lines.append(f"💥 Critical    : {summary.get('total_critical', 0)}")
            lines.append(f"🎯 Exploitable : {summary.get('total_exploitable', 0)}")

        return "\n".join(lines)
