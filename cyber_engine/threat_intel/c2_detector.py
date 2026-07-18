"""
Chhoti Don - C2 Traffic Detector
Advanced Command & Control traffic detection engine.
Detects beaconing, DNS tunneling, HTTP C2, covert channels.
Phase 2.2 - Nice to Have Feature

⚠️  FOR AUTHORIZED SECURITY MONITORING ONLY
"""

import re
import datetime
import math
from typing import Dict, List, Optional, Tuple

# ==================================================

C2_FRAMEWORKS = {
    # Metasploit Meterpreter
    "meterpreter": {
        "name": "Metasploit Meterpreter",
        "indicators": [
            "meterpreter", "metasploit", "msf",
            "/meterpreter/", "TLV_TYPE", "COMMAND_ID"
        ],
        "default_ports": [4444, 4445, 5555],
        "user_agents": [],
        "severity": "critical",
        "mitre": "T1071",
    },
    # Cobalt Strike
    "cobalt_strike": {
        "name": "Cobalt Strike",
        "indicators": [
            "cobaltstrike", "beacon", "sleep_mask",
            "watermark", "CS Beacon", "XXXXXXXX"
        ],
        "default_ports": [443, 80, 8080, 8443, 50050],
        "uri_patterns": [r"/[a-zA-Z0-9]{4,8}\.(js|css|png|gif)", r"/__utm\.gif"],
        "user_agents": [
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64)",
            "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1)",
        ],
        "severity": "critical",
        "mitre": "T1071.001",
    },
    # Empire
    "empire": {
        "name": "PowerShell Empire",
        "indicators": ["empire", "powershell empire", "invoke-empire"],
        "default_ports": [80, 443, 8080],
        "uri_patterns": [r"/news\.php", r"/login/process\.php"],
        "severity": "critical",
        "mitre": "T1059.001",
    },
    # Sliver
    "sliver": {
        "name": "Sliver C2",
        "indicators": ["sliver", "implant", "grpc c2"],
        "default_ports": [443, 80, 31337],
        "severity": "critical",
        "mitre": "T1071",
    },
    # Covenant
    "covenant": {
        "name": "Covenant C2",
        "indicators": ["covenant", "grunt", "gruntstager"],
        "default_ports": [80, 443, 7443],
        "severity": "critical",
        "mitre": "T1071",
    },
    # Generic reverse shells
    "reverse_shell": {
        "name": "Generic Reverse Shell",
        "indicators": [
            "/bin/sh", "/bin/bash", "cmd.exe",
            "nc -e", "bash -i", "python -c",
        ],
        "default_ports": [1234, 4444, 5555, 9001, 9999, 31337],
        "severity": "high",
        "mitre": "T1059",
    },
    # DNS C2
    "dns_c2": {
        "name": "DNS C2 / Tunneling",
        "indicators": ["dns tunnel", "dnscat", "iodine", "dnsx"],
        "default_ports": [53],
        "severity": "high",
        "mitre": "T1071.004",
    },
}

# Suspicious User Agents
SUSPICIOUS_USER_AGENTS = [
    "python-requests", "curl/", "wget/", "libwww-perl",
    "Go-http-client", "Java/", "Apache-HttpClient",
    "masscan", "nmap", "zgrab", "nuclei",
    "sqlmap", "nikto", "dirbuster",
]

# Beaconing detection thresholds
BEACON_INTERVAL_VARIANCE_THRESHOLD = 0.15  # 15% variance = beaconing
BEACON_MIN_CONNECTIONS = 5                  # Minimum connections to detect
BEACON_TIME_WINDOW = 3600                   # 1 hour window


class C2Detector:
    """
    Advanced C2 Traffic Detection Engine.
    Detects beaconing, DNS tunneling, suspicious connections.
    """

    def __init__(self):
        self.detections = []
        self.connection_log = []

    # ==================================================
    # 🔍 C2 Framework Detection
    # ==================================================
    def detect_c2_framework(self, data: str, port: int = None) -> List[Dict]:
        """
        Known C2 framework indicators detect karo.

        Args:
            data: Network data / log content / banner
            port: Connection port (optional)

        Returns:
            List of detected C2 frameworks
        """
        detections = []
        data_lower = data.lower()

        for framework_key, framework_data in C2_FRAMEWORKS.items():

            # Indicator match
            for indicator in framework_data["indicators"]:
                if indicator.lower() in data_lower:
                    detection = {
                        "framework": framework_data["name"],
                        "indicator_matched": indicator,
                        "severity": framework_data["severity"],
                        "mitre": framework_data["mitre"],
                        "confidence": "high",
                        "description": f"C2 framework indicator detected: {indicator}",
                        "recommendation": "Isolate affected system immediately",
                    }
                    detections.append(detection)
                    break

            # Port-based detection
            if port and port in framework_data.get("default_ports", []):
                # Only flag if not already detected
                if not any(d["framework"] == framework_data["name"] for d in detections):
                    detection = {
                        "framework": framework_data["name"],
                        "indicator_matched": f"Default C2 port: {port}",
                        "severity": "medium",
                        "mitre": framework_data["mitre"],
                        "confidence": "medium",
                        "description": f"Connection on known C2 port {port}",
                        "recommendation": f"Investigate traffic on port {port}",
                    }
                    detections.append(detection)

            # URI pattern matching
            for pattern in framework_data.get("uri_patterns", []):
                if re.search(pattern, data):
                    detection = {
                        "framework": framework_data["name"],
                        "indicator_matched": f"URI pattern: {pattern}",
                        "severity": framework_data["severity"],
                        "mitre": framework_data["mitre"],
                        "confidence": "high",
                        "description": f"Known C2 URI pattern detected",
                        "recommendation": "Block and investigate",
                    }
                    detections.append(detection)
                    break

        return detections

    # ==================================================
    # 📡 Beaconing Detection
    # ==================================================
    def detect_beaconing(self, connection_timestamps: List[float]) -> Dict:
        """
        Regular interval connections detect karo (beaconing).

        Args:
            connection_timestamps: List of Unix timestamps

        Returns:
            Beaconing analysis result
        """
        if len(connection_timestamps) < BEACON_MIN_CONNECTIONS:
            return {
                "beaconing_detected": False,
                "reason": f"Insufficient data (min {BEACON_MIN_CONNECTIONS} connections needed)",
                "confidence": "low",
            }

        # Sort timestamps
        timestamps = sorted(connection_timestamps)

        # Calculate intervals
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]

        if not intervals:
            return {"beaconing_detected": False, "reason": "No intervals to analyze"}

        avg_interval = sum(intervals) / len(intervals)

        # Coefficient of variation (CV)
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = math.sqrt(variance)
        cv = std_dev / avg_interval if avg_interval > 0 else 1

        # Jitter detection (C2 frameworks add jitter to evade detection)
        jitter_detected = 0.05 < cv < 0.35  # Low but non-zero variance = jitter

        beaconing = cv <= BEACON_INTERVAL_VARIANCE_THRESHOLD or jitter_detected

        if beaconing:
            if cv < 0.05:
                beacon_type = "Regular Beaconing (no jitter)"
                confidence = "very_high"
            elif jitter_detected:
                beacon_type = "Jittered Beaconing (C2 evasion)"
                confidence = "high"
            else:
                beacon_type = "Possible Beaconing"
                confidence = "medium"

            beacon_interval_sec = round(avg_interval, 2)

            return {
                "beaconing_detected": True,
                "beacon_type": beacon_type,
                "beacon_interval_sec": beacon_interval_sec,
                "beacon_interval_human": self._format_interval(beacon_interval_sec),
                "coefficient_of_variation": round(cv, 4),
                "jitter_detected": jitter_detected,
                "confidence": confidence,
                "connections_analyzed": len(timestamps),
                "severity": "critical",
                "mitre": "T1071",
                "description": f"Beaconing detected — {beacon_type}",
                "recommendation": "Isolate system and investigate C2 channel",
            }

        return {
            "beaconing_detected": False,
            "coefficient_of_variation": round(cv, 4),
            "avg_interval_sec": round(avg_interval, 2),
            "confidence": "high",
            "connections_analyzed": len(timestamps),
        }

    # ==================================================
    # 🌐 DNS Anomaly Detection
    # ==================================================
    def detect_dns_anomalies(self, dns_queries: List[str]) -> Dict:
        """
        DNS tunneling aur anomalies detect karo.

        Args:
            dns_queries: List of DNS query strings

        Returns:
            DNS anomaly analysis
        """
        findings = []

        if not dns_queries:
            return {"findings": [], "dns_tunneling_detected": False}

        # High entropy subdomains (DNS tunneling indicator)
        high_entropy_queries = []
        for query in dns_queries:
            subdomain = query.split(".")[0] if "." in query else query
            entropy = self._calculate_entropy(subdomain)

            if entropy > 3.5 and len(subdomain) > 20:
                high_entropy_queries.append({
                    "query": query,
                    "subdomain": subdomain,
                    "entropy": round(entropy, 3),
                    "length": len(subdomain)
                })

        if high_entropy_queries:
            findings.append({
                "type": "dns_tunneling_suspected",
                "severity": "high",
                "mitre": "T1071.004",
                "description": f"High-entropy DNS subdomains detected — possible DNS tunneling",
                "evidence": high_entropy_queries[:5],
                "count": len(high_entropy_queries),
                "recommendation": "Block suspicious DNS queries and investigate",
            })

        # Excessive NX Domain responses (domain generation algorithm)
        domain_counts = Counter(q.split(".")[-2] + "." + q.split(".")[-1] if "." in q else q
                               for q in dns_queries)

        rare_domains = [d for d, c in domain_counts.items() if c == 1]
        if len(rare_domains) > len(dns_queries) * 0.5:
            findings.append({
                "type": "dga_suspected",
                "severity": "high",
                "mitre": "T1568.002",
                "description": "High rate of unique domain lookups — possible DGA (Domain Generation Algorithm)",
                "unique_domains": len(rare_domains),
                "total_queries": len(dns_queries),
                "recommendation": "Investigate DNS traffic for malware C2",
            })

        # Known bad TLDs
        suspicious_tlds = [".xyz", ".tk", ".ml", ".ga", ".cf", ".gq"]
        bad_tld_queries = [q for q in dns_queries
                          if any(q.endswith(tld) for tld in suspicious_tlds)]
        if bad_tld_queries:
            findings.append({
                "type": "suspicious_tld",
                "severity": "medium",
                "mitre": "T1071.004",
                "description": "Queries to suspicious TLDs detected",
                "queries": bad_tld_queries[:5],
                "recommendation": "Block queries to suspicious TLDs",
            })

        dns_tunneling = any(f["type"] == "dns_tunneling_suspected" for f in findings)

        return {
            "findings": findings,
            "dns_tunneling_detected": dns_tunneling,
            "total_queries_analyzed": len(dns_queries),
            "unique_domains": len(set(dns_queries)),
        }

    # ==================================================
    # 🔍 Suspicious User Agent Detection
    # ==================================================
    def detect_suspicious_useragent(self, user_agents: List[str]) -> List[Dict]:
        """Suspicious User Agents detect karo."""
        findings = []

        for ua in user_agents:
            ua_lower = ua.lower()

            for suspicious in SUSPICIOUS_USER_AGENTS:
                if suspicious.lower() in ua_lower:
                    findings.append({
                        "type": "suspicious_user_agent",
                        "severity": "medium",
                        "user_agent": ua,
                        "matched_signature": suspicious,
                        "description": f"Suspicious User-Agent detected: {ua[:80]}",
                        "recommendation": "Investigate source of requests",
                    })
                    break

        return findings

    # ==================================================
    # 🔌 Port-Based C2 Detection
    # ==================================================
    def detect_c2_ports(self, open_ports: List[int], connections: Dict = None) -> List[Dict]:
        """
        Known C2 ports detect karo.

        Args:
            open_ports: List of open ports
            connections: Optional {port: connection_count} dict

        Returns:
            List of C2 port detections
        """
        findings = []

        all_c2_ports = {}
        for framework, data in C2_FRAMEWORKS.items():
            for port in data.get("default_ports", []):
                if port not in all_c2_ports:
                    all_c2_ports[port] = []
                all_c2_ports[port].append(data["name"])

        for port in open_ports:
            if port in all_c2_ports:
                frameworks = all_c2_ports[port]
                finding = {
                    "type": "c2_port_detected",
                    "port": port,
                    "possible_frameworks": frameworks,
                    "severity": "high",
                    "mitre": "T1071",
                    "description": f"Port {port} matches known C2 framework ports: {', '.join(frameworks)}",
                    "recommendation": f"Investigate traffic on port {port}",
                }
                if connections:
                    finding["connection_count"] = connections.get(port, 0)
                findings.append(finding)

        return findings

    # ==================================================
    # 🚀 Full C2 Analysis
    # ==================================================
    def full_analysis(
        self,
        scan_result: Dict,
        network_logs: str = "",
        dns_queries: List[str] = None,
        user_agents: List[str] = None,
        connection_timestamps: List[float] = None,
    ) -> Dict:
        """
        Complete C2 detection analysis.
        """
        start_time = time.time()
        all_findings = []

        open_ports = scan_result.get("open_ports", [])
        banners = [d.get("banner", "") for d in scan_result.get("open_port_details", [])]

        # 1. Framework detection from banners
        for banner in banners:
            if banner:
                framework_findings = self.detect_c2_framework(banner)
                all_findings.extend(framework_findings)

        # 2. Framework detection from network logs
        if network_logs:
            log_findings = self.detect_c2_framework(network_logs)
            all_findings.extend(log_findings)

        # 3. C2 port detection
        port_findings = self.detect_c2_ports(open_ports)
        all_findings.extend(port_findings)

        # 4. Beaconing detection
        beaconing_result = {}
        if connection_timestamps:
            beaconing_result = self.detect_beaconing(connection_timestamps)
            if beaconing_result.get("beaconing_detected"):
                all_findings.append({
                    "type": "beaconing",
                    **beaconing_result
                })

        # 5. DNS anomaly detection
        dns_result = {}
        if dns_queries:
            dns_result = self.detect_dns_anomalies(dns_queries)
            all_findings.extend(dns_result.get("findings", []))

        # 6. User agent detection
        ua_findings = []
        if user_agents:
            ua_findings = self.detect_suspicious_useragent(user_agents)
            all_findings.extend(ua_findings)

        # Severity summary
        critical = [f for f in all_findings if f.get("severity") == "critical"]
        high = [f for f in all_findings if f.get("severity") == "high"]

        c2_detected = len(critical) > 0 or len(high) > 0

        return {
            "target": scan_result.get("target", "unknown"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "c2_detected": c2_detected,
            "total_findings": len(all_findings),
            "findings": all_findings,
            "beaconing_analysis": beaconing_result,
            "dns_analysis": dns_result,
            "severity_summary": {
                "critical": len(critical),
                "high": len(high),
                "medium": len([f for f in all_findings if f.get("severity") == "medium"]),
            },
            "verdict": "🔴 C2 ACTIVITY DETECTED" if c2_detected else "✅ No C2 indicators found",
            "analysis_time_sec": round(time.time() - start_time, 3),
        }

    # ==================================================
    # 🔧 Helpers
    # ==================================================
    def _calculate_entropy(self, text: str) -> float:
        """Shannon entropy calculate karo."""
        if not text:
            return 0
        freq = Counter(text.lower())
        total = len(text)
        entropy = -sum((c/total) * math.log2(c/total) for c in freq.values())
        return entropy

    def _format_interval(self, seconds: float) -> str:
        """Seconds ko human-readable format mein."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
