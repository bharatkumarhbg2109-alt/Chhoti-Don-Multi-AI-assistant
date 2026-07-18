"""
Chhoti Don - Attack Timeline Builder
Advanced attack timeline visualization and reconstruction.
Builds chronological attack narrative with MITRE mapping.
Phase 2.2 - Nice to Have Feature
"""

import time
import datetime
from typing import Dict
# ==================================================
# 🎯 TIMELINE EVENT TYPES
# ==================================================

EVENT_TYPES = {
    "reconnaissance": {
        "icon": "🔍",
        "color": "#3498db",
        "phase": "Pre-Attack",
        "mitre_tactic": "TA0007",
    },
    "initial_access": {
        "icon": "💥",
        "color": "#e74c3c",
        "phase": "Intrusion",
        "mitre_tactic": "TA0001",
    },
    "execution": {
        "icon": "⚡",
        "color": "#c0392b",
        "phase": "Intrusion",
        "mitre_tactic": "TA0002",
    },
    "persistence": {
        "icon": "🔒",
        "color": "#8e44ad",
        "phase": "Establishment",
        "mitre_tactic": "TA0003",
    },
    "privilege_escalation": {
        "icon": "⬆️",
        "color": "#d35400",
        "phase": "Establishment",
        "mitre_tactic": "TA0004",
    },
    "defense_evasion": {
        "icon": "🛡️",
        "color": "#7f8c8d",
        "phase": "Establishment",
        "mitre_tactic": "TA0005",
    },
    "credential_access": {
        "icon": "🔑",
        "color": "#f39c12",
        "phase": "Expansion",
        "mitre_tactic": "TA0006",
    },
    "lateral_movement": {
        "icon": "↔️",
        "color": "#e74c3c",
        "phase": "Expansion",
        "mitre_tactic": "TA0008",
    },
    "collection": {
        "icon": "📁",
        "color": "#2980b9",
        "phase": "Actions",
        "mitre_tactic": "TA0009",
    },
    "command_and_control": {
        "icon": "📡",
        "color": "#8e44ad",
        "phase": "Establishment",
        "mitre_tactic": "TA0011",
    },
    "exfiltration": {
        "icon": "📤",
        "color": "#c0392b",
        "phase": "Actions",
        "mitre_tactic": "TA0010",
    },
    "impact": {
        "icon": "💣",
        "color": "#e74c3c",
        "phase": "Actions",
        "mitre_tactic": "TA0040",
    },
    "scan": {
        "icon": "📡",
        "color": "#3498db",
        "phase": "Pre-Attack",
        "mitre_tactic": "TA0007",
    },
    "vulnerability_found": {
        "icon": "⚠️",
        "color": "#e67e22",
        "phase": "Discovery",
        "mitre_tactic": "TA0007",
    },
    "exploit_attempt": {
        "icon": "💀",
        "color": "#c0392b",
        "phase": "Intrusion",
        "mitre_tactic": "TA0001",
    },
    "c2_detected": {
        "icon": "📻",
        "color": "#8e44ad",
        "phase": "Establishment",
        "mitre_tactic": "TA0011",
    },
}


class AttackTimeline:
    """
    Attack Timeline Builder and Visualizer.
    Reconstructs attack chronology from scan/detection data.
    """

    def __init__(self):
        self.events = []
        self.start_time = None
        self.end_time = None

    # ==================================================
    # ➕ Add Events
    # ==================================================
    def add_event(
        self,
        event_type: str,
        description: str,
        timestamp: float = None,
        severity: str = "medium",
        mitre_technique: str = None,
        target: str = None,
        source: str = None,
        evidence: str = None,
        metadata: Dict = None,
    ) -> Dict:
        """
        Timeline mein event add karo.
        """
        if timestamp is None:
            timestamp = time.time()

        event_info = EVENT_TYPES.get(event_type, {
            "icon": "📌",
            "color": "#95a5a6",
            "phase": "Unknown",
            "mitre_tactic": "",
        })

        event = {
            "id": len(self.events) + 1,
            "timestamp": timestamp,
            "datetime": datetime.datetime.fromtimestamp(timestamp).isoformat(),
            "event_type": event_type,
            "icon": event_info["icon"],
            "color": event_info["color"],
            "phase": event_info["phase"],
            "description": description,
            "severity": severity,
            "mitre_technique": mitre_technique or event_info.get("mitre_tactic", ""),
            "target": target,
            "source": source,
            "evidence": evidence,
            "metadata": metadata or {},
            "elapsed_from_start": 0,
        }

        self.events.append(event)
        self.events.sort(key=lambda e: e["timestamp"])

        # Update start/end times
        if self.events:
            self.start_time = self.events[0]["timestamp"]
            self.end_time = self.events[-1]["timestamp"]
            # Recalculate elapsed times
            for e in self.events:
                e["elapsed_from_start"] = round(e["timestamp"] - self.start_time, 2)

        return event

    # ==================================================
    # 🔧 Build from Recon Data
    # ==================================================
    def build_from_recon(self, recon_data: Dict) -> "AttackTimeline":
        """
        Full recon result se timeline automatically build karo.
        """
        target = recon_data.get("target", "unknown")
        base_time = time.time()

        # Recon phase
        self.add_event(
            "scan",
            f"Automated reconnaissance initiated against {target}",
            timestamp=base_time,
            severity="info",
            mitre_technique="T1046",
            target=target,
        )

        # Port scan results
        phases = recon_data.get("phases", {})
        port_scan = phases.get("port_scan", {})
        open_ports = port_scan.get("open_ports", [])

        if open_ports:
            self.add_event(
                "reconnaissance",
                f"Port scan complete — {len(open_ports)} open ports discovered: {open_ports}",
                timestamp=base_time + 5,
                severity="medium",
                mitre_technique="T1046",
                target=target,
                evidence=f"Open ports: {open_ports}",
            )

        # Subdomain scan
        subdomain_scan = phases.get("subdomain_scan", {})
        if subdomain_scan.get("count", 0) > 0:
            self.add_event(
                "reconnaissance",
                f"Subdomain discovery: {subdomain_scan['count']} subdomains found",
                timestamp=base_time + 10,
                severity="medium",
                mitre_technique="T1590",
                target=target,
                evidence=str(subdomain_scan.get("discovered_subdomains", [])[:5]),
            )

        # CVE findings
        cve_analysis = phases.get("cve_analysis", {})
        cve_summary = cve_analysis.get("summary", {})
        if cve_summary.get("total_cves_found", 0) > 0:
            self.add_event(
                "vulnerability_found",
                f"CVE analysis: {cve_summary['total_cves_found']} vulnerabilities found "
                f"({cve_summary.get('total_critical', 0)} critical)",
                timestamp=base_time + 15,
                severity="critical" if cve_summary.get("total_critical", 0) > 0 else "high",
                mitre_technique="T1190",
                target=target,
                evidence=f"Critical CVEs: {cve_summary.get('total_critical', 0)}",
            )

        # Exploit suggestions
        exploit_phase = phases.get("exploit_suggestions", {})
        if exploit_phase.get("total_exploits_found", 0) > 0:
            easy = exploit_phase.get("summary", {}).get("easy_exploits", 0)
            self.add_event(
                "exploit_attempt",
                f"Exploit analysis: {exploit_phase['total_exploits_found']} exploits identified "
                f"({easy} easy)",
                timestamp=base_time + 20,
                severity="critical" if easy > 0 else "high",
                mitre_technique="T1190",
                target=target,
            )

        # Risk assessment
        risk = phases.get("risk_assessment", {})
        if risk:
            risk_score = risk.get("risk_score", 0)
            risk_level = risk.get("risk_level", "UNKNOWN")
            if risk_score >= 60:
                self.add_event(
                    "initial_access",
                    f"High-risk target identified — Risk Score: {risk_score}/100 [{risk_level}]",
                    timestamp=base_time + 25,
                    severity="critical" if risk_score >= 80 else "high",
                    mitre_technique="T1190",
                    target=target,
                    evidence=f"Risk Score: {risk_score}",
                )

        return self

    # ==================================================
    # 📊 Timeline Analysis
    # ==================================================
    def analyze(self) -> Dict:
        """Timeline analysis aur statistics."""
        if not self.events:
            return {"status": "empty", "message": "No events in timeline"}

        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0

        # Phase breakdown
        phase_counts = defaultdict(int)
        for event in self.events:
            phase_counts[event["phase"]] += 1

        # Severity breakdown
        severity_counts = defaultdict(int)
        for event in self.events:
            severity_counts[event["severity"]] += 1

        # Critical events
        critical_events = [e for e in self.events if e["severity"] == "critical"]

        # MITRE techniques
        mitre_techniques = list(set(
            e["mitre_technique"] for e in self.events
            if e.get("mitre_technique")
        ))

        # Attack phases covered
        phases_covered = list(phase_counts.keys())

        # Attack narrative
        narrative = self._build_narrative()

        return {
            "total_events": len(self.events),
            "duration_sec": round(duration, 2),
            "duration_human": self._format_duration(duration),
            "start_time": datetime.datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "end_time": datetime.datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "phase_breakdown": dict(phase_counts),
            "severity_breakdown": dict(severity_counts),
            "critical_events": len(critical_events),
            "mitre_techniques": mitre_techniques,
            "phases_covered": phases_covered,
            "attack_narrative": narrative,
            "attack_complexity": self._assess_complexity(),
        }

    # ==================================================
    # 📝 Export Formats
    # ==================================================
    def to_text(self) -> str:
        """Plain text timeline."""
        lines = [
            "=" * 60,
            "  ATTACK TIMELINE",
            "=" * 60,
            f"  Events  : {len(self.events)}",
        ]

        if self.start_time:
            lines.append(f"  Start   : {datetime.datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if self.end_time:
            lines.append(f"  End     : {datetime.datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d %H:%M:%S')}")

        lines.append("=" * 60)

        for event in self.events:
            elapsed = event.get("elapsed_from_start", 0)
            elapsed_str = f"+{elapsed:.0f}s"

            lines.append(
                f"\n  {event['icon']} [{elapsed_str:>6}] {event['description']}"
            )
            lines.append(f"     Phase    : {event['phase']}")
            lines.append(f"     Severity : {event['severity'].upper()}")
            if event.get("mitre_technique"):
                lines.append(f"     MITRE    : {event['mitre_technique']}")
            if event.get("target"):
                lines.append(f"     Target   : {event['target']}")
            if event.get("evidence"):
                lines.append(f"     Evidence : {event['evidence'][:80]}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def to_html(self) -> str:
        """Professional HTML timeline visualization."""
        events_html = ""

        for event in self.events:
            elapsed = event.get("elapsed_from_start", 0)
            color = event.get("color", "#95a5a6")
            icon = event.get("icon", "📌")
            sev_color = {
                "critical": "#e74c3c", "high": "#e67e22",
                "medium": "#f39c12", "low": "#27ae60", "info": "#3498db"
            }.get(event["severity"], "#95a5a6")

            events_html += f"""
            <div class="timeline-event" style="border-left: 4px solid {color}">
                <div class="event-header">
                    <span class="event-icon">{icon}</span>
                    <span class="event-time">+{elapsed:.0f}s</span>
                    <span class="event-phase" style="background:{color}">{event['phase']}</span>
                    <span class="event-severity" style="color:{sev_color}">{event['severity'].upper()}</span>
                </div>
                <div class="event-description">{event['description']}</div>
                <div class="event-meta">
                    {f'<span>🎯 MITRE: {event["mitre_technique"]}</span>' if event.get("mitre_technique") else ""}
                    {f'<span>🖥 Target: {event["target"]}</span>' if event.get("target") else ""}
                    {f'<span>🔍 Evidence: {str(event["evidence"])[:60]}</span>' if event.get("evidence") else ""}
                </div>
            </div>"""

        analysis = self.analyze()

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Attack Timeline</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }}
  h1 {{ color: #58a6ff; margin-bottom: 20px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 25px; }}
  .stat {{ background: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 12px; text-align: center; }}
  .stat .val {{ font-size: 1.8em; font-weight: bold; color: #58a6ff; }}
  .stat .lbl {{ font-size: 0.8em; color: #8b949e; }}
  .timeline {{ position: relative; padding-left: 20px; }}
  .timeline::before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px; background: #21262d; }}
  .timeline-event {{ background: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 12px; margin-bottom: 12px; position: relative; }}
  .event-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }}
  .event-icon {{ font-size: 1.2em; }}
  .event-time {{ color: #8b949e; font-size: 0.85em; font-family: monospace; }}
  .event-phase {{ padding: 2px 8px; border-radius: 10px; font-size: 0.75em; color: white; }}
  .event-severity {{ font-size: 0.8em; font-weight: bold; }}
  .event-description {{ color: #e6edf3; margin-bottom: 6px; }}
  .event-meta {{ display: flex; gap: 15px; flex-wrap: wrap; font-size: 0.8em; color: #8b949e; }}
  .narrative {{ background: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 15px; margin-bottom: 20px; }}
  .narrative h3 {{ color: #58a6ff; margin-bottom: 10px; }}
</style>
</head>
<body>
<h1>⏱️ Attack Timeline</h1>

<div class="stats">
  <div class="stat"><div class="val">{analysis['total_events']}</div><div class="lbl">Events</div></div>
  <div class="stat"><div class="val">{analysis['duration_human']}</div><div class="lbl">Duration</div></div>
  <div class="stat"><div class="val" style="color:#e74c3c">{analysis['critical_events']}</div><div class="lbl">Critical</div></div>
  <div class="stat"><div class="val">{len(analysis['mitre_techniques'])}</div><div class="lbl">MITRE Techniques</div></div>
  <div class="stat"><div class="val">{analysis['attack_complexity']}</div><div class="lbl">Complexity</div></div>
</div>

<div class="narrative">
  <h3>📖 Attack Narrative</h3>
  <p style="color:#8b949e; line-height:1.6">{analysis['attack_narrative']}</p>
</div>

<div class="timeline">
{events_html}
</div>

<p style="text-align:center;color:#8b949e;margin-top:20px;font-size:0.85em">
  Generated by Chhoti Don — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</p>
</body>
</html>"""

    def to_dict(self) -> Dict:
        """Full timeline as dict."""
        return {
            "events": self.events,
            "analysis": self.analyze(),
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }

    # ==================================================
    # 🔧 Helpers
    # ==================================================
    def _build_narrative(self) -> str:
        """Attack narrative text build karo."""
        if not self.events:
            return "No events recorded."

        phases = list(set(e["phase"] for e in self.events))
        critical = sum(1 for e in self.events if e["severity"] == "critical")
        targets = list(set(e["target"] for e in self.events if e.get("target")))

        narrative = f"Attack sequence spanning {len(phases)} phase(s) detected"
        if targets:
            narrative += f" against {', '.join(targets[:3])}"
        narrative += f". {len(self.events)} events recorded"
        if critical > 0:
            narrative += f" with {critical} critical severity finding(s)"
        narrative += f". Phases: {', '.join(phases)}."

        return narrative

    def _assess_complexity(self) -> str:
        """Attack complexity assess karo."""
        phases = set(e["phase"] for e in self.events)
        techniques = set(e.get("mitre_technique") for e in self.events if e.get("mitre_technique"))

        if len(phases) >= 4 or len(techniques) >= 5:
            return "Advanced"
        elif len(phases) >= 2 or len(techniques) >= 3:
            return "Intermediate"
        else:
            return "Basic"

    def _format_duration(self, seconds: float) -> str:
        """Duration format karo."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    def clear(self):
        """Timeline clear karo."""
        self.events = []
        self.start_time = None
        self.end_time = None


# ==================================================
# 🔧 STANDALONE BUILDER
# ==================================================

def build_timeline_from_recon(recon_data: Dict) -> Dict:
    """
    Standalone function — recon data se full timeline banao.
    """
    timeline = AttackTimeline()
    timeline.build_from_recon(recon_data)

    return {
        "timeline": timeline.to_dict(),
        "text_report": timeline.to_text(),
        "html_report": timeline.to_html(),
    }
