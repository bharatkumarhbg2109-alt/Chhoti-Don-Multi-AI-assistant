"""
Chhoti Don - Lateral Movement Detector
Advanced network lateral movement detection and path analysis.
Detects SMB, RDP, SSH, Pass-the-Hash, and other lateral techniques.
Phase 2.2 - Nice to Have Feature

⚠️  FOR AUTHORIZED SECURITY MONITORING ONLY
"""

from typing import Dict, List, Optional, Tuple

# ==================================================
# ==================================================

LATERAL_TECHNIQUES = {
    # SMB
    "smb_lateral": {
        "name": "SMB Lateral Movement",
        "mitre": "T1021.002",
        "ports": [445, 139],
        "indicators": ["psexec", "smbexec", "wmiexec", "impacket"],
        "severity": "critical",
        "description": "SMB-based lateral movement detected",
        "detection_method": "Monitor SMB authentication events across multiple hosts",
    },
    # RDP
    "rdp_lateral": {
        "name": "RDP Lateral Movement",
        "mitre": "T1021.001",
        "ports": [3389],
        "indicators": ["rdp", "remote desktop", "mstsc"],
        "severity": "high",
        "description": "RDP-based lateral movement detected",
        "detection_method": "Monitor RDP session creation across hosts",
    },
    # SSH
    "ssh_lateral": {
        "name": "SSH Lateral Movement",
        "mitre": "T1021.004",
        "ports": [22],
        "indicators": ["ssh", "scp", "sftp"],
        "severity": "high",
        "description": "SSH-based lateral movement detected",
        "detection_method": "Monitor SSH connections originating from internal hosts",
    },
    # WMI
    "wmi_lateral": {
        "name": "WMI Lateral Movement",
        "mitre": "T1047",
        "ports": [135, 445],
        "indicators": ["wmi", "wbem", "winmgmt", "wmic"],
        "severity": "critical",
        "description": "WMI-based lateral movement detected",
        "detection_method": "Monitor WMI activity and remote process creation",
    },
    # Pass the Hash
    "pass_the_hash": {
        "name": "Pass-the-Hash",
        "mitre": "T1550.002",
        "ports": [445, 139],
        "indicators": ["pth", "pass the hash", "ntlm hash", "overpass"],
        "severity": "critical",
        "description": "Pass-the-Hash attack detected",
        "detection_method": "Monitor NTLM authentication without interactive logon",
    },
    # Pass the Ticket
    "pass_the_ticket": {
        "name": "Pass-the-Ticket (Kerberos)",
        "mitre": "T1550.003",
        "ports": [88, 389],
        "indicators": ["kerberos", "ticket", "golden ticket", "silver ticket", "mimikatz"],
        "severity": "critical",
        "description": "Kerberos ticket abuse detected",
        "detection_method": "Monitor Kerberos ticket requests from unusual sources",
    },
    # Remote Service Exploitation
    "remote_exploit": {
        "name": "Remote Service Exploitation",
        "mitre": "T1210",
        "ports": [445, 3389, 22],
        "indicators": ["eternalblue", "bluekeep", "ms17-010"],
        "severity": "critical",
        "description": "Remote service exploitation for lateral movement",
        "detection_method": "Monitor exploitation attempts against internal services",
    },
}

# Internal network ranges
INTERNAL_RANGES = [
    "10.", "192.168.", "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
    "172.29.", "172.30.", "172.31.", "127."
]


class LateralMovementDetector:
    """
    Advanced Lateral Movement Detection Engine.
    Detects and maps lateral movement across network.
    """

    def __init__(self):
        self.movement_graph = defaultdict(list)
        self.detected_movements = []
        self.hop_count = {}

    # ==================================================
    # 🔍 Detect from Port Scan
    # ==================================================
    def detect_from_scan(self, scan_result: Dict) -> Dict:
        """
        Port scan results se lateral movement risks detect karo.
        """
        target = scan_result.get("target", "unknown")
        open_ports = scan_result.get("open_ports", [])
        open_details = scan_result.get("open_port_details", [])

        findings = []
        risk_score = 0

        for port_info in open_details:
            port = port_info.get("port", 0)
            service = port_info.get("service", "unknown").lower()

            for tech_key, tech_data in LATERAL_TECHNIQUES.items():
                if port in tech_data["ports"]:
                    severity = tech_data["severity"]
                    sev_score = {"critical": 10, "high": 7, "medium": 4}.get(severity, 2)
                    risk_score += sev_score

                    findings.append({
                        "technique": tech_data["name"],
                        "mitre": tech_data["mitre"],
                        "port": port,
                        "service": service,
                        "severity": severity,
                        "description": tech_data["description"],
                        "detection_method": tech_data["detection_method"],
                        "risk_score": sev_score,
                    })
                    break

        # Deduplicate
        seen = set()
        unique_findings = []
        for f in findings:
            key = f["technique"]
            if key not in seen:
                seen.add(key)
                unique_findings.append(f)

        return {
            "target": target,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "findings": unique_findings,
            "total_findings": len(unique_findings),
            "lateral_risk_score": min(risk_score, 100),
            "lateral_movement_risk": len(unique_findings) > 0,
            "high_risk_techniques": [f for f in unique_findings if f["severity"] == "critical"],
            "recommended_mitigations": self._get_mitigations(unique_findings),
        }

    # ==================================================
    # 🗺️ Movement Path Analysis
    # ==================================================
    def analyze_movement_path(
        self,
        source_host: str,
        discovered_hosts: List[str],
        connections: List[Tuple[str, str, int]] = None
    ) -> Dict:
        """
        Network lateral movement path analyze karo.

        Args:
            source_host: Initial compromised host
            discovered_hosts: Hosts discovered from source
            connections: Optional [(src, dst, port), ...] list

        Returns:
            Movement path analysis
        """
        movement_graph = defaultdict(list)
        hop_analysis = {}

        # Build movement graph
        if connections:
            for src, dst, port in connections:
                if self._is_internal(dst):
                    tech = self._port_to_technique(port)
                    movement_graph[src].append({
                        "target": dst,
                        "port": port,
                        "technique": tech,
                    })
        else:
            # Estimate from discovered hosts
            for host in discovered_hosts:
                if self._is_internal(host) and host != source_host:
                    movement_graph[source_host].append({
                        "target": host,
                        "port": 445,
                        "technique": "SMB/Unknown",
                    })

        # Calculate hop distances from source
        visited = set()
        queue = [(source_host, 0)]

        while queue:
            host, depth = queue.pop(0)
            if host in visited:
                continue
            visited.add(host)
            hop_analysis[host] = depth

            for connection in movement_graph.get(host, []):
                next_host = connection["target"]
                if next_host not in visited:
                    queue.append((next_host, depth + 1))

        # Critical paths (deep penetration)
        max_depth = max(hop_analysis.values()) if hop_analysis else 0
        critical_hosts = [h for h, d in hop_analysis.items() if d >= 3]

        # Pivot points (hosts with multiple outgoing connections)
        pivot_points = [
            host for host, conns in movement_graph.items()
            if len(conns) >= 2
        ]

        return {
            "source_host": source_host,
            "total_hosts_reached": len(hop_analysis),
            "max_hop_depth": max_depth,
            "hop_analysis": hop_analysis,
            "movement_graph": dict(movement_graph),
            "critical_hosts": critical_hosts,
            "pivot_points": pivot_points,
            "blast_radius": self._calculate_blast_radius(hop_analysis, max_depth),
            "containment_priority": self._get_containment_priority(pivot_points, critical_hosts),
        }

    # ==================================================
    # 🛡️ Containment Recommendations
    # ==================================================
    def get_containment_plan(self, movement_analysis: Dict) -> Dict:
        """
        Lateral movement containment plan generate karo.
        """
        pivot_points = movement_analysis.get("pivot_points", [])
        critical_hosts = movement_analysis.get("critical_hosts", [])
        max_depth = movement_analysis.get("max_hop_depth", 0)

        immediate_actions = []
        short_term = []
        long_term = []

        # Immediate actions
        if pivot_points:
            immediate_actions.append(f"ISOLATE pivot points immediately: {pivot_points[:3]}")
        if critical_hosts:
            immediate_actions.append(f"Quarantine deep-penetrated hosts: {critical_hosts[:3]}")

        immediate_actions += [
            "Block SMB (445) traffic between workstations",
            "Force password reset for all compromised accounts",
            "Revoke Kerberos tickets (klist purge)",
            "Enable enhanced authentication logging",
        ]

        # Short-term
        short_term = [
            "Deploy EDR on all endpoints",
            "Implement network segmentation",
            "Enable SMB signing across all systems",
            "Disable NTLM where possible, enforce Kerberos",
            "Audit privileged account usage",
            "Review and rotate service account credentials",
        ]

        # Long-term
        long_term = [
            "Implement Zero Trust Network Architecture",
            "Deploy Privileged Access Workstations (PAWs)",
            "Implement JIT (Just-in-Time) privileged access",
            "Regular purple team exercises",
            "Automated threat hunting for lateral movement",
        ]

        urgency = "CRITICAL" if max_depth >= 3 else "HIGH" if max_depth >= 2 else "MEDIUM"

        return {
            "urgency": urgency,
            "immediate_actions": immediate_actions,
            "short_term_actions": short_term,
            "long_term_actions": long_term,
            "estimated_blast_radius": movement_analysis.get("blast_radius", "Unknown"),
            "containment_priority": movement_analysis.get("containment_priority", []),
        }

    # ==================================================
    # 🔍 Detect from Logs
    # ==================================================
    def detect_from_logs(self, log_content: str) -> List[Dict]:
        """
        Log content se lateral movement detect karo.
        """
        findings = []
        log_lower = log_content.lower()

        for tech_key, tech_data in LATERAL_TECHNIQUES.items():
            for indicator in tech_data["indicators"]:
                if indicator.lower() in log_lower:
                    findings.append({
                        "technique": tech_data["name"],
                        "mitre": tech_data["mitre"],
                        "indicator": indicator,
                        "severity": tech_data["severity"],
                        "description": tech_data["description"],
                    })
                    break

        return findings

    # ==================================================
    # 🔧 Helpers
    # ==================================================
    def _is_internal(self, ip: str) -> bool:
        """Internal IP check."""
        return any(ip.startswith(r) for r in INTERNAL_RANGES)

    def _port_to_technique(self, port: int) -> str:
        """Port se technique name."""
        port_map = {
            445: "SMB", 139: "NetBIOS/SMB",
            3389: "RDP", 22: "SSH",
            135: "WMI/RPC", 5985: "WinRM",
            88: "Kerberos",
        }
        return port_map.get(port, f"Port {port}")

    def _calculate_blast_radius(self, hop_analysis: Dict, max_depth: int) -> str:
        """Blast radius calculate karo."""
        total_hosts = len(hop_analysis)
        if total_hosts >= 20 or max_depth >= 4:
            return "CRITICAL — Network-wide compromise likely"
        elif total_hosts >= 10 or max_depth >= 3:
            return "HIGH — Multiple segments compromised"
        elif total_hosts >= 5 or max_depth >= 2:
            return "MEDIUM — Multiple hosts compromised"
        elif total_hosts >= 2:
            return "LOW — Limited spread"
        else:
            return "MINIMAL — Single host"

    def _get_containment_priority(self, pivot_points: List, critical_hosts: List) -> List[str]:
        """Containment priority order."""
        priority = []
        for host in pivot_points:
            priority.append(f"[PIVOT] {host}")
        for host in critical_hosts:
            if host not in pivot_points:
                priority.append(f"[DEEP] {host}")
        return priority[:10]

    def _get_mitigations(self, findings: List[Dict]) -> List[str]:
        """Mitigations list."""
        mitigations = set()
        mitigation_map = {
            "SMB": "Enable SMB signing, block SMB between workstations",
            "RDP": "Enable NLA, restrict RDP access, use VPN",
            "SSH": "Key-based auth only, restrict SSH to jump hosts",
            "WMI": "Restrict WMI access, monitor WMI activity",
            "Pass-the-Hash": "Enable Protected Users group, disable NTLM",
            "Kerberos": "Enable Kerberos armoring, monitor TGT requests",
        }
        for finding in findings:
            for key, mitigation in mitigation_map.items():
                if key.lower() in finding.get("technique", "").lower():
                    mitigations.add(mitigation)

        return list(mitigations)
