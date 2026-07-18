"""
Chhoti Don - Nmap Wrapper
Advanced Nmap execution wrapper with full scan types,
CVE integration, OS detection, script scanning, and reporting.
Phase 2.2 - Full Upgrade

⚠️  FOR AUTHORIZED PENETRATION TESTING ONLY
"""

import shutil
import subprocess
import time
import datetime
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Mapping, Optional, Tuple, Type# Scope validation
try:
    from cyber_engine.assessment.scope_validator import validate_target_scope, validate_target
except ImportError:
    def validate_target_scope(target: str) -> bool:
        return True
    def validate_target(target: str) -> Dict:
        return {"allowed": True}

# Risk calculator
try:
    from cyber_engine.intelligence.risk_calculator import calculate_risk_score, generate_risk_report
except ImportError:
    def calculate_risk_score(xml_output: str) -> int:
        return 50
    def generate_risk_report(data: Dict) -> Dict:
        return {"risk_score": 50, "risk_level": "MEDIUM"}

# CVE engine
try:
    from cyber_engine.vuln_analysis.cve_engine import analyze_scan_results, get_cve_details
    CVE_ENGINE_AVAILABLE = True
except ImportError:
    CVE_ENGINE_AVAILABLE = False

# MITRE mapper
try:
    from cyber_engine.threat_intel.mitre_mapper import analyze_scan_for_mitre
    MITRE_AVAILABLE = True
except ImportError:
    MITRE_AVAILABLE = False


# ==================================================
# 🎯 SCAN TYPE DEFINITIONS
# ==================================================

SCAN_TYPES = {
    # Original types (preserved)
    "basic": {
        "args": ["-sS", "-T3"],
        "description": "Basic SYN scan",
        "requires_root": True,
        "severity": "low",
    },
    "version": {
        "args": ["-sV", "-T3"],
        "description": "Version detection scan",
        "requires_root": False,
        "severity": "low",
    },
    "safe": {
        "args": ["-sS", "-sV", "--script=safe", "-T3"],
        "description": "Safe script scan",
        "requires_root": True,
        "severity": "low",
    },

    # New scan types
    "quick": {
        "args": ["-T4", "-F"],
        "description": "Fast scan — top 100 ports",
        "requires_root": False,
        "severity": "low",
    },
    "full": {
        "args": ["-sS", "-sV", "-sC", "-T3", "-p-"],
        "description": "Full port scan with scripts",
        "requires_root": True,
        "severity": "medium",
    },
    "os_detect": {
        "args": ["-sS", "-sV", "-O", "-T3"],
        "description": "OS and version detection",
        "requires_root": True,
        "severity": "medium",
    },
    "vuln": {
        "args": ["-sV", "--script=vuln", "-T3"],
        "description": "Vulnerability scan using NSE scripts",
        "requires_root": False,
        "severity": "high",
    },
    "stealth": {
        "args": ["-sS", "-T2", "-f", "--data-length", "24"],
        "description": "Stealth fragmented scan",
        "requires_root": True,
        "severity": "medium",
    },
    "udp": {
        "args": ["-sU", "-T3", "--top-ports", "100"],
        "description": "UDP scan — top 100 ports",
        "requires_root": True,
        "severity": "medium",
    },
    "smb": {
        "args": ["-sV", "-p", "139,445",
                 "--script=smb-vuln-ms17-010,smb-vuln-ms08-067,smb-security-mode,smb-enum-shares"],
        "description": "SMB vulnerability scan",
        "requires_root": False,
        "severity": "high",
    },
    "http": {
        "args": ["-sV", "-p", "80,443,8080,8443",
                 "--script=http-headers,http-methods,http-title,http-robots.txt"],
        "description": "HTTP/HTTPS scan with headers",
        "requires_root": False,
        "severity": "medium",
    },
    "ssh": {
        "args": ["-sV", "-p", "22",
                 "--script=ssh-auth-methods,ssh-hostkey,ssh2-enum-algos"],
        "description": "SSH detailed scan",
        "requires_root": False,
        "severity": "medium",
    },
    "aggressive": {
        "args": ["-A", "-T4"],
        "description": "Aggressive scan — OS, version, scripts, traceroute",
        "requires_root": True,
        "severity": "high",
    },
    "firewall_bypass": {
        "args": ["-sA", "-T3"],
        "description": "ACK scan for firewall rule detection",
        "requires_root": True,
        "severity": "medium",
    },
}

# Known NSE scripts mapping
NSE_SCRIPTS = {
    "smb_vulns": "smb-vuln-ms17-010,smb-vuln-ms08-067,smb-vuln-cve2009-3103",
    "http_vulns": "http-shellshock,http-phpself-xss,http-sql-injection",
    "ssh_vulns": "ssh-auth-methods,sshv1",
    "ftp_vulns": "ftp-anon,ftp-bounce,ftp-proftpd-backdoor",
    "mysql_vulns": "mysql-empty-password,mysql-vuln-cve2012-2122",
    "rdp_vulns": "rdp-vuln-ms12-020,rdp-enum-encryption",
    "all_safe": "safe",
    "all_vulns": "vuln",
}


class NmapWrapper:
    """
    Advanced Controlled Nmap Execution Wrapper.
    Full scan pipeline with CVE, MITRE, and risk integration.
    Phase 2.2 Upgrade
    """

    def __init__(self, timeout: int = 120):
        if not shutil.which("nmap"):
            raise EnvironmentError(
                "Nmap is not installed or not found in PATH. "
                "Install: sudo apt install nmap (Linux) or https://nmap.org/download"
            )
        self.timeout = timeout
        self.scan_history = []

    # ==================================================
    # 🚀 MAIN SCAN FUNCTION (PRESERVED + UPGRADED)
    # ==================================================
    def run_scan(
        self,
        target: str,
        scan_type: str = "basic",
        ports: Optional[str] = None,
        scripts: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        run_cve: bool = True,
        run_mitre: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute Nmap scan with full pipeline.

        Args:
            target: IP/hostname to scan
            scan_type: Scan type key from SCAN_TYPES
            ports: Custom port string e.g. "22,80,443" or "1-1000"
            scripts: NSE scripts to run
            extra_args: Additional nmap arguments
            run_cve: Auto-run CVE analysis
            run_mitre: Auto-run MITRE mapping

        Returns:
            Complete scan result with analysis
        """
        start_time = time.time()
        start_dt = datetime.datetime.utcnow()

        # ==================================================
        # Step 1: Scope Validation (PRESERVED + UPGRADED)
        # ==================================================
        validation = validate_target(target)
        if not validation.get("allowed"):
            return {
                "status": "blocked",
                "target": target,
                "reason": validation.get("reason", "Target not in authorized scope"),
                "code": "SCOPE_VIOLATION",
            }

        # ==================================================
        # Step 2: Scan Type Validation (PRESERVED + UPGRADED)
        # ==================================================
        if scan_type not in SCAN_TYPES:
            available = list(SCAN_TYPES.keys())
            return {
                "status": "error",
                "message": f"Scan type '{scan_type}' not allowed. Available: {available}",
            }

        scan_config = SCAN_TYPES[scan_type]

        # ==================================================
        # Step 3: Build Command (UPGRADED)
        # ==================================================
        command = self._build_command(
            target, scan_type, ports, scripts, extra_args, scan_config
        )

        print(f"[NmapWrapper] Running: {' '.join(command[:8])}...")

        # ==================================================
        # Step 4: Execute Scan (PRESERVED + UPGRADED)
        # ==================================================
        try:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "target": target,
                "error": f"Scan timed out after {self.timeout}s",
            }
        except Exception as e:
            return {
                "status": "error",
                "target": target,
                "error": str(e),
            }

        if process.returncode != 0 and not process.stdout:
            return {
                "status": "error",
                "target": target,
                "error": process.stderr.strip()[:500],
            }

        xml_output = process.stdout
        warnings = process.stderr.strip() if process.stderr else None

        # ==================================================
        # Step 5: Parse XML (PRESERVED + UPGRADED)
        # ==================================================
        structured_data = self._parse_nmap_xml(xml_output)

        # ==================================================
        # Step 6: Risk Scoring (UPGRADED)
        # ==================================================
        risk_score_raw = calculate_risk_score(xml_output)
        risk_report = generate_risk_report(structured_data) if structured_data.get("open_ports") else {}

        # ==================================================
        # Step 7: CVE Analysis (NEW)
        # ==================================================
        cve_analysis = {}
        if run_cve and CVE_ENGINE_AVAILABLE and structured_data.get("open_port_details"):
            try:
                cve_analysis = analyze_scan_results(structured_data)
            except Exception:
                pass

        # ==================================================
        # Step 8: MITRE Mapping (NEW)
        # ==================================================
        mitre_analysis = {}
        if run_mitre and MITRE_AVAILABLE and structured_data.get("open_ports"):
            try:
                mitre_analysis = analyze_scan_for_mitre(structured_data)
            except Exception:
                pass

        # ==================================================
        # Step 9: NSE Script Results (NEW)
        # ==================================================
        script_results = self._extract_script_results(xml_output)

        # ==================================================
        # Step 10: Build Final Result (UPGRADED)
        # ==================================================
        duration = round(time.time() - start_time, 3)

        result = {
            "status": "success",
            "target": target,
            "scan_type": scan_type,
            "scan_description": scan_config["description"],

            # Risk scores
            "risk_score": risk_score_raw,
            "confidence_score": self._calculate_confidence(structured_data),
            "risk_report": risk_report,

            # Core results
            "open_ports": structured_data.get("open_ports", []),
            "open_port_details": structured_data.get("open_port_details", []),
            "services": structured_data.get("services", []),
            "os_detection": structured_data.get("os_detection", {}),

            # Analysis
            "cve_analysis": cve_analysis,
            "mitre_analysis": mitre_analysis,
            "script_results": script_results,
            "vulnerability_findings": self._extract_vuln_findings(script_results),

            # Metadata
            "metadata": {
                "timestamp_utc": start_dt.isoformat(),
                "duration_seconds": duration,
                "nmap_version": self._get_nmap_version(),
                "command": " ".join(command),
                "warnings": warnings,
            },

            # Raw data
            "structured_results": structured_data,  # Preserved for backward compat
            "raw_output": xml_output,
        }

        # Store history
        self.scan_history.append({
            "target": target,
            "scan_type": scan_type,
            "timestamp": time.time(),
            "open_ports_count": len(structured_data.get("open_ports", [])),
            "risk_score": risk_score_raw,
        })

        print(f"[NmapWrapper] Scan complete in {duration}s — "
              f"{len(result['open_ports'])} open ports found")

        return result

    # ==================================================
    # 🎯 SPECIALIZED SCAN METHODS (NEW)
    # ==================================================

    def quick_scan(self, target: str) -> Dict:
        """Fast scan — top 100 ports."""
        return self.run_scan(target, scan_type="quick")

    def full_scan(self, target: str) -> Dict:
        """Full port scan with service detection."""
        return self.run_scan(target, scan_type="full")

    def vuln_scan(self, target: str, ports: str = None) -> Dict:
        """NSE vulnerability scan."""
        return self.run_scan(target, scan_type="vuln", ports=ports)

    def smb_scan(self, target: str) -> Dict:
        """SMB vulnerability scan — EternalBlue, MS08-067."""
        return self.run_scan(target, scan_type="smb")

    def os_detect(self, target: str) -> Dict:
        """OS and version detection."""
        return self.run_scan(target, scan_type="os_detect")

    def http_scan(self, target: str) -> Dict:
        """HTTP/HTTPS headers and methods scan."""
        return self.run_scan(target, scan_type="http")

    def ssh_scan(self, target: str) -> Dict:
        """SSH algorithms and auth methods scan."""
        return self.run_scan(target, scan_type="ssh")

    def custom_scan(self, target: str, ports: str, scripts: str = None, extra_args: List[str] = None) -> Dict:
        """Custom scan with specific ports and scripts."""
        return self.run_scan(
            target,
            scan_type="version",
            ports=ports,
            scripts=scripts,
            extra_args=extra_args
        )

    # ==================================================
    # 🔧 COMMAND BUILDER (UPGRADED)
    # ==================================================
    def _build_command(
        self,
        target: str,
        scan_type: str,
        ports: Optional[str],
        scripts: Optional[str],
        extra_args: Optional[List[str]],
        scan_config: Dict,
    ) -> List[str]:
        """Build nmap command."""
        command = ["nmap", *scan_config["args"]]

        # Port specification
        if ports and "-p" not in scan_config["args"]:
            command.extend(["-p", ports])

        # Scripts
        if scripts:
            # Map script aliases
            script_str = NSE_SCRIPTS.get(scripts, scripts)
            command.extend([f"--script={script_str}"])

        # Extra args
        if extra_args:
            command.extend(extra_args)

        # Always output XML
        command.extend(["-oX", "-"])

        # Target
        command.append(target)

        return command

    # ==================================================
    # 📊 XML PARSER (PRESERVED + UPGRADED)
    # ==================================================
    def _parse_nmap_xml(self, xml_data: str) -> Dict[str, Any]:
        """
        Parse Nmap XML output — preserved + upgraded.
        Now extracts OS detection, scripts, and more.
        """
        result: Dict[str, Any] = {
            "open_ports": [],
            "open_port_details": [],  # New — rich port info
            "services": [],
            "os_detection": {},
            "host_status": "unknown",
        }

        if not xml_data or not xml_data.strip():
            result["parse_error"] = "Empty XML output"
            return result

        try:
            root = ET.fromstring(xml_data)

            for host in root.findall("host"):
                # Host status
                status = host.find("status")
                if status is not None:
                    result["host_status"] = status.attrib.get("state", "unknown")

                # OS Detection
                os_elem = host.find("os")
                if os_elem is not None:
                    os_match = os_elem.find("osmatch")
                    if os_match is not None:
                        result["os_detection"] = {
                            "name": os_match.attrib.get("name", "Unknown"),
                            "accuracy": os_match.attrib.get("accuracy", "0"),
                            "type": os_match.find("osclass").attrib.get("type", "") if os_match.find("osclass") is not None else "",
                        }

                # Ports
                for port in host.findall(".//port"):
                    state = port.find("state")
                    if state is None:
                        continue

                    port_state = state.attrib.get("state", "")
                    if port_state != "open":
                        continue

                    port_id = port.attrib.get("portid")
                    protocol = port.attrib.get("protocol", "tcp")

                    if not port_id:
                        continue

                    port_num = int(port_id)

                    # Service info
                    service_info = port.find("service")
                    service_name = None
                    service_version = None
                    service_product = None
                    service_extrainfo = None
                    service_tunnel = None

                    if service_info is not None:
                        service_name = service_info.attrib.get("name")
                        service_version = service_info.attrib.get("version")
                        service_product = service_info.attrib.get("product")
                        service_extrainfo = service_info.attrib.get("extrainfo")
                        service_tunnel = service_info.attrib.get("tunnel")

                    # Script outputs for this port
                    port_scripts = {}
                    for script in port.findall("script"):
                        script_id = script.attrib.get("id")
                        script_output = script.attrib.get("output", "")
                        if script_id:
                            port_scripts[script_id] = script_output

                    # Build port entry (backward compat)
                    result["open_ports"].append({
                        "port": port_num,
                        "protocol": protocol,
                    })

                    # Rich port details (new)
                    result["open_port_details"].append({
                        "port": port_num,
                        "protocol": protocol,
                        "status": "open",
                        "service": service_name or "unknown",
                        "version": service_version,
                        "product": service_product,
                        "extrainfo": service_extrainfo,
                        "tunnel": service_tunnel,
                        "banner": service_extrainfo or "",
                        "scripts": port_scripts,
                        "confidence": 0.9 if service_version else 0.6,
                    })

                    result["services"].append({
                        "port": port_num,
                        "service": service_name,
                        "version": service_version,
                        "product": service_product,
                    })

        except ET.ParseError as e:
            result["parse_error"] = f"XML parse error: {str(e)}"

        return result

    # ==================================================
    # 🔍 SCRIPT RESULT EXTRACTOR (NEW)
    # ==================================================
    def _extract_script_results(self, xml_data: str) -> Dict:
        """NSE script results extract karo."""
        results = {}

        if not xml_data:
            return results

        try:
            root = ET.fromstring(xml_data)

            for host in root.findall("host"):
                # Host-level scripts
                host_scripts = host.find("hostscript")
                if host_scripts is not None:
                    for script in host_scripts.findall("script"):
                        script_id = script.attrib.get("id")
                        output = script.attrib.get("output", "")
                        if script_id:
                            results[script_id] = {
                                "output": output,
                                "level": "host",
                            }

                # Port-level scripts
                for port in host.findall(".//port"):
                    port_id = port.attrib.get("portid", "0")
                    for script in port.findall("script"):
                        script_id = script.attrib.get("id")
                        output = script.attrib.get("output", "")
                        if script_id:
                            key = f"{script_id}:port{port_id}"
                            results[key] = {
                                "output": output,
                                "port": int(port_id),
                                "level": "port",
                            }

        except ET.ParseError:
            pass

        return results

    def _extract_vuln_findings(self, script_results: Dict) -> List[Dict]:
        """Script results se vulnerability findings extract karo."""
        findings = []

        vuln_keywords = [
            "VULNERABLE", "CVE-", "EXPLOIT", "RCE", "CRITICAL",
            "vulnerable", "exploitable"
        ]

        for script_id, data in script_results.items():
            output = data.get("output", "")
            for keyword in vuln_keywords:
                if keyword in output:
                    # Extract CVE if present
                    import re
                    cves = re.findall(r"CVE-\d{4}-\d+", output)

                    findings.append({
                        "script": script_id.split(":")[0],
                        "port": data.get("port"),
                        "severity": "critical" if "CRITICAL" in output else "high",
                        "output": output[:300],
                        "cves_mentioned": cves,
                        "description": f"NSE script {script_id.split(':')[0]} found vulnerability",
                    })
                    break

        return findings

    # ==================================================
    # 📊 CONFIDENCE SCORING (PRESERVED + UPGRADED)
    # ==================================================
    def _calculate_confidence(self, structured_data: Dict[str, Any]) -> int:
        """Confidence score calculate karo — preserved + upgraded."""
        if "parse_error" in structured_data:
            return 40

        open_ports = structured_data.get("open_ports", [])
        services = structured_data.get("services", [])
        os_detected = bool(structured_data.get("os_detection"))

        if not open_ports:
            return 85

        # Service version info availability
        versioned = sum(1 for s in services if s.get("version"))
        version_ratio = versioned / len(services) if services else 0

        base = 65

        if version_ratio >= 0.7:
            base += 15
        elif version_ratio >= 0.4:
            base += 8

        if os_detected:
            base += 5

        if len(open_ports) < 5:
            base += 5
        elif len(open_ports) > 20:
            base -= 5

        return min(base, 99)

    # ==================================================
    # 🔧 UTILITIES (NEW)
    # ==================================================
    def _get_nmap_version(self) -> str:
        """Nmap version get karo."""
        try:
            result = subprocess.run(
                ["nmap", "--version"],
                capture_output=True, text=True, timeout=5
            )
            first_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
            return first_line
        except Exception:
            return "unknown"

    def get_scan_history(self) -> List[Dict]:
        """Scan history return karo."""
        return self.scan_history

    def get_available_scan_types(self) -> Dict:
        """Available scan types aur descriptions."""
        return {
            k: v["description"]
            for k, v in SCAN_TYPES.items()
        }

    def get_available_scripts(self) -> Dict:
        """Available script aliases."""
        return NSE_SCRIPTS

    def get_summary(self, scan_result: Dict) -> str:
        """Human-readable scan summary."""
        target = scan_result.get("target", "unknown")
        open_ports = scan_result.get("open_ports", [])
        risk = scan_result.get("risk_report", {})
        cve = scan_result.get("cve_analysis", {})
        duration = scan_result.get("metadata", {}).get("duration_seconds", 0)

        lines = [
            f"🎯 Target      : {target}",
            f"🔓 Open Ports  : {len(open_ports)} → {[p['port'] for p in open_ports]}",
            f"⏱  Duration    : {duration}s",
            f"📊 Risk Score  : {scan_result.get('risk_score', 0)}",
            f"🎯 Confidence  : {scan_result.get('confidence_score', 0)}%",
        ]

        if risk:
            lines.append(f"⚠️  Risk Level  : {risk.get('risk_level', 'N/A')}")

        if cve:
            summary = cve.get("summary", {})
            lines.append(f"🔴 CVEs Found  : {summary.get('total_cves_found', 0)}")
            lines.append(f"💥 Critical    : {summary.get('total_critical', 0)}")

        vuln_findings = scan_result.get("vulnerability_findings", [])
        if vuln_findings:
            lines.append(f"🚨 NSE Vulns   : {len(vuln_findings)}")

        return "\n".join(lines)
