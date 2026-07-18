"""
Chhoti Don - Report Exporter
Advanced pentest report generator.
Exports to TXT, JSON, HTML, and Markdown formats.
Phase 2.2 - High Priority Feature
"""

import json
import os
import datetime
from typing import Dict, Generator, List, Optional, Optional

class ReportExporter:
    """
    Advanced Pentest Report Generator
    - Multiple export formats (TXT, JSON, HTML, Markdown)
    - Executive summary
    - Risk scoring visualization
    - CVE findings table
    - Exploit suggestions
    - Remediation roadmap
    - Phase 2.2
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Output directory create karo."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _get_filename(self, target: str, format: str) -> str:
        """Unique filename generate karo."""
        safe_target = target.replace(".", "_").replace("/", "_").replace(":", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"recon_{safe_target}_{timestamp}.{format}")

    # ==================================================
    # 📄 TXT REPORT
    # ==================================================
    def export_txt(self, recon_data: Dict, filepath: str = None) -> str:
        """Plain text report export karo."""
        if not filepath:
            target = recon_data.get("target", "unknown")
            filepath = self._get_filename(target, "txt")

        lines = self._build_txt_report(recon_data)
        content = "\n".join(lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _build_txt_report(self, data: Dict) -> List[str]:
        """TXT report lines build karo."""
        lines = []
        target = data.get("target", "unknown")
        timestamp = data.get("timestamp", datetime.datetime.utcnow().isoformat())
        duration = data.get("duration_sec", 0)
        summary = data.get("executive_summary", {})
        phases = data.get("phases", {})

        # Header
        lines += [
            "=" * 65,
            "  CHHOTI DON — AUTOMATED RECON REPORT",
            "=" * 65,
            f"  Target    : {target}",
            f"  Date      : {timestamp[:19].replace('T', ' ')}",
            f"  Duration  : {duration}s",
            f"  Session   : {data.get('session_id', 'N/A')[:8]}...",
            "=" * 65,
            "",
        ]

        # Executive Summary
        lines += [
            "[ EXECUTIVE SUMMARY ]",
            "-" * 45,
            f"Verdict    : {summary.get('verdict', 'N/A')}",
            f"Risk Score : {summary.get('risk_score', 0)}/100 [{summary.get('risk_level', 'N/A')}]",
            f"Open Ports : {summary.get('open_ports', 0)} → {summary.get('ports_list', [])}",
            f"CVEs Found : {summary.get('cves_found', 0)} ({summary.get('critical_cves', 0)} Critical)",
            f"Exploits   : {summary.get('exploits_available', 0)} ({summary.get('easy_exploits', 0)} Easy)",
            f"Action     : {summary.get('action_required', 'Review findings')}",
            "",
        ]

        # Port Scan Results
        port_phase = phases.get("port_scan", {})
        if port_phase:
            lines += ["[ PORT SCAN RESULTS ]", "-" * 45]
            open_details = port_phase.get("open_port_details", [])
            if open_details:
                for p in open_details:
                    version = f" v{p['version']}" if p.get("version") else ""
                    lines.append(f"  Port {p['port']:5} | {p.get('service', 'unknown'):12} | {p.get('status', '')}{version}")
            else:
                lines.append("  No open ports found.")
            lines.append("")

        # CVE Findings
        cve_phase = phases.get("cve_analysis", {})
        if cve_phase and cve_phase.get("findings"):
            lines += ["[ CVE FINDINGS ]", "-" * 45]
            for finding in cve_phase["findings"]:
                lines.append(f"\n  Port {finding['port']} ({finding['service']})")
                lines.append(f"  CVEs: {finding['cve_count']} | Critical: {finding['critical_count']} | Exploitable: {finding['exploitable_count']}")
                lines.append(f"  Highest CVSS: {finding['highest_cvss']}")
                for cve in finding.get("cves", [])[:3]:
                    lines.append(f"    → {cve['cve_id']} [{cve['severity'].upper()}] CVSS:{cve['cvss']} — {cve['description'][:60]}")
                    lines.append(f"       Fix: {cve.get('remediation', 'N/A')}")
            lines.append("")

        # Exploit Suggestions
        exploit_phase = phases.get("exploit_suggestions", {})
        if exploit_phase and exploit_phase.get("port_exploit_map"):
            lines += ["[ EXPLOIT SUGGESTIONS ]", "-" * 45]
            for port_exp in exploit_phase["port_exploit_map"][:5]:
                lines.append(f"\n  Port {port_exp['port']} ({port_exp['service']}) — {port_exp['exploit_count']} exploit(s)")
                easiest = port_exp.get("easiest", {})
                if easiest:
                    lines.append(f"  ⚡ Easiest: {easiest.get('title')} [{easiest.get('difficulty')}]")
                    if easiest.get("msf_module"):
                        lines.append(f"  🔫 MSF: {easiest['msf_module']}")

            if exploit_phase.get("msf_modules"):
                lines += ["", "  MSF Modules:"]
                for mod in exploit_phase["msf_modules"]:
                    lines.append(f"    use {mod}")
            lines.append("")

        # Pentest Checklist
        checklist_phase = phases.get("pentest_checklist", {})
        if checklist_phase and checklist_phase.get("prioritized_tests"):
            lines += ["[ PENTEST CHECKLIST — TOP PRIORITY ]", "-" * 45]
            critical_tests = [t for t in checklist_phase["prioritized_tests"]
                             if t.get("severity") == "critical"]
            for test in critical_tests[:3]:
                lines.append(f"\n  🔴 {test['service']} (Port {test['port']})")
                for t in test["tests"][:4]:
                    lines.append(f"     • {t}")
            lines.append("")

        # Remediation
        lines += ["[ REMEDIATION ROADMAP ]", "-" * 45]
        lines += self._build_remediation(phases)
        lines.append("")

        # Footer
        lines += [
            "=" * 65,
            "  Generated by Chhoti Don Cyber Engine",
            f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 65,
        ]

        return lines

    # ==================================================
    # 📋 MARKDOWN REPORT
    # ==================================================
    def export_markdown(self, recon_data: Dict, filepath: str = None) -> str:
        """Markdown report export karo."""
        if not filepath:
            target = recon_data.get("target", "unknown")
            filepath = self._get_filename(target, "md")

        content = self._build_markdown_report(recon_data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _build_markdown_report(self, data: Dict) -> str:
        """Markdown report build karo."""
        target = data.get("target", "unknown")
        timestamp = data.get("timestamp", "")[:19].replace("T", " ")
        summary = data.get("executive_summary", {})
        phases = data.get("phases", {})

        md = []

        md.append(f"# 🔍 Recon Report — `{target}`")
        md.append(f"\n**Date:** {timestamp}  |  **Duration:** {data.get('duration_sec', 0)}s\n")

        # Executive Summary
        md.append("## 📊 Executive Summary\n")
        md.append(f"| Field | Value |")
        md.append(f"|-------|-------|")
        md.append(f"| Verdict | {summary.get('verdict', 'N/A')} |")
        md.append(f"| Risk Score | {summary.get('risk_score', 0)}/100 |")
        md.append(f"| Risk Level | **{summary.get('risk_level', 'N/A')}** |")
        md.append(f"| Open Ports | {summary.get('open_ports', 0)} |")
        md.append(f"| CVEs Found | {summary.get('cves_found', 0)} |")
        md.append(f"| Critical CVEs | {summary.get('critical_cves', 0)} |")
        md.append(f"| Exploits | {summary.get('exploits_available', 0)} |")
        md.append(f"| Easy Exploits | {summary.get('easy_exploits', 0)} |")
        md.append("")

        # Port Scan
        port_phase = phases.get("port_scan", {})
        if port_phase:
            md.append("## 🔓 Open Ports\n")
            open_details = port_phase.get("open_port_details", [])
            if open_details:
                md.append("| Port | Service | Version | Status |")
                md.append("|------|---------|---------|--------|")
                for p in open_details:
                    version = p.get("version") or "N/A"
                    md.append(f"| {p['port']} | {p.get('service', 'unknown')} | {version} | {p.get('status', '')} |")
            md.append("")

        # CVE Findings
        cve_phase = phases.get("cve_analysis", {})
        if cve_phase and cve_phase.get("findings"):
            md.append("## 🔴 CVE Findings\n")
            for finding in cve_phase["findings"]:
                md.append(f"### Port {finding['port']} — {finding['service']}")
                md.append(f"- CVEs: **{finding['cve_count']}** | Critical: **{finding['critical_count']}** | CVSS Max: **{finding['highest_cvss']}**\n")
                md.append("| CVE ID | Severity | CVSS | Description | Fix |")
                md.append("|--------|----------|------|-------------|-----|")
                for cve in finding.get("cves", []):
                    desc = cve['description'][:50] + "..." if len(cve['description']) > 50 else cve['description']
                    fix = cve.get('remediation', 'N/A')[:40]
                    md.append(f"| {cve['cve_id']} | {cve['severity'].upper()} | {cve['cvss']} | {desc} | {fix} |")
                md.append("")

        # Exploit Suggestions
        exploit_phase = phases.get("exploit_suggestions", {})
        if exploit_phase and exploit_phase.get("port_exploit_map"):
            md.append("## 💥 Exploit Suggestions\n")
            for port_exp in exploit_phase["port_exploit_map"]:
                md.append(f"### Port {port_exp['port']} — {port_exp['service']}")
                easiest = port_exp.get("easiest", {})
                if easiest:
                    md.append(f"**Easiest:** {easiest.get('title')} | Difficulty: `{easiest.get('difficulty')}`")
                    if easiest.get("msf_module"):
                        md.append(f"```\nuse {easiest['msf_module']}\nset RHOSTS {target}\nrun\n```")
                md.append("")

        # Remediation
        md.append("## 🛡️ Remediation Roadmap\n")
        remediations = self._build_remediation(phases)
        for r in remediations:
            md.append(r)
        md.append("")

        # Footer
        md.append("---")
        md.append(f"*Generated by Chhoti Don Cyber Engine — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(md)

    # ==================================================
    # 🌐 HTML REPORT
    # ==================================================
    def export_html(self, recon_data: Dict, filepath: str = None) -> str:
        """Professional HTML report export karo."""
        if not filepath:
            target = recon_data.get("target", "unknown")
            filepath = self._get_filename(target, "html")

        content = self._build_html_report(recon_data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _build_html_report(self, data: Dict) -> str:
        """HTML report build karo."""
        target = data.get("target", "unknown")
        timestamp = data.get("timestamp", "")[:19].replace("T", " ")
        summary = data.get("executive_summary", {})
        phases = data.get("phases", {})

        risk_score = summary.get("risk_score", 0)
        risk_color = "#e74c3c" if risk_score >= 70 else "#e67e22" if risk_score >= 40 else "#27ae60"
        risk_level = summary.get("risk_level", "N/A")

        # Port table
        port_rows = ""
        port_phase = phases.get("port_scan", {})
        for p in port_phase.get("open_port_details", []):
            version = p.get("version") or "N/A"
            port_rows += f"<tr><td>{p['port']}</td><td>{p.get('service','unknown')}</td><td>{version}</td><td><span class='badge open'>OPEN</span></td></tr>"

        # CVE table
        cve_rows = ""
        cve_phase = phases.get("cve_analysis", {})
        for finding in cve_phase.get("findings", []):
            for cve in finding.get("cves", []):
                sev = cve["severity"].upper()
                sev_color = "#e74c3c" if sev == "CRITICAL" else "#e67e22" if sev == "HIGH" else "#f39c12"
                cve_rows += f"""<tr>
                    <td>{cve['cve_id']}</td>
                    <td><span style='color:{sev_color};font-weight:bold'>{sev}</span></td>
                    <td>{cve['cvss']}</td>
                    <td>{finding['port']} ({finding['service']})</td>
                    <td>{cve['description'][:60]}...</td>
                    <td>{cve.get('remediation','N/A')[:50]}</td>
                </tr>"""

        # Exploit table
        exploit_rows = ""
        exploit_phase = phases.get("exploit_suggestions", {})
        for port_exp in exploit_phase.get("port_exploit_map", []):
            easiest = port_exp.get("easiest", {})
            diff = easiest.get("difficulty", "Unknown")
            diff_color = "#e74c3c" if diff == "Easy" else "#e67e22" if diff == "Medium" else "#27ae60"
            msf = easiest.get("msf_module", "N/A") or "N/A"
            exploit_rows += f"""<tr>
                <td>{port_exp['port']}</td>
                <td>{port_exp['service']}</td>
                <td>{easiest.get('title','N/A')}</td>
                <td><span style='color:{diff_color}'>{diff}</span></td>
                <td><code>{msf}</code></td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Recon Report — {target}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; }}
  .header {{ background: linear-gradient(135deg, #1a1f2e, #0d1117); padding: 30px; border-bottom: 2px solid #21262d; }}
  .header h1 {{ color: #58a6ff; font-size: 1.8em; }}
  .header p {{ color: #8b949e; margin-top: 5px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
  .card {{ background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px; margin: 20px 0; }}
  .card h2 {{ color: #58a6ff; margin-bottom: 15px; font-size: 1.2em; border-bottom: 1px solid #21262d; padding-bottom: 8px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; }}
  .metric {{ background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 15px; text-align: center; }}
  .metric .value {{ font-size: 2em; font-weight: bold; color: #58a6ff; }}
  .metric .label {{ font-size: 0.85em; color: #8b949e; margin-top: 5px; }}
  .risk-bar {{ height: 12px; background: #21262d; border-radius: 6px; overflow: hidden; margin: 10px 0; }}
  .risk-fill {{ height: 100%; background: {risk_color}; width: {risk_score}%; border-radius: 6px; transition: width 1s; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th {{ background: #21262d; color: #8b949e; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #21262d; color: #e6edf3; }}
  tr:hover td {{ background: #1c2129; }}
  .badge {{ padding: 2px 8px; border-radius: 10px; font-size: 0.8em; font-weight: bold; }}
  .badge.open {{ background: #1a4731; color: #3fb950; }}
  code {{ background: #161b22; border: 1px solid #21262d; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; color: #79c0ff; }}
  .verdict {{ font-size: 1.1em; font-weight: bold; padding: 10px 15px; background: #1a1f2e; border-radius: 6px; border-left: 4px solid {risk_color}; }}
</style>
</head>
<body>
<div class="header">
  <h1>🔍 Chhoti Don — Recon Report</h1>
  <p>Target: <strong>{target}</strong> | Date: {timestamp} | Duration: {data.get('duration_sec',0)}s</p>
</div>
<div class="container">

  <!-- Executive Summary -->
  <div class="card">
    <h2>📊 Executive Summary</h2>
    <div class="verdict">{summary.get('verdict','N/A')}</div>
    <br>
    <div style="margin-bottom:10px">
      <strong>Risk Score: {risk_score}/100 [{risk_level}]</strong>
      <div class="risk-bar"><div class="risk-fill"></div></div>
    </div>
    <div class="summary-grid">
      <div class="metric"><div class="value">{summary.get('open_ports',0)}</div><div class="label">Open Ports</div></div>
      <div class="metric"><div class="value">{summary.get('cves_found',0)}</div><div class="label">CVEs Found</div></div>
      <div class="metric"><div class="value" style="color:#e74c3c">{summary.get('critical_cves',0)}</div><div class="label">Critical CVEs</div></div>
      <div class="metric"><div class="value" style="color:#e67e22">{summary.get('exploits_available',0)}</div><div class="label">Exploits</div></div>
      <div class="metric"><div class="value" style="color:#e74c3c">{summary.get('easy_exploits',0)}</div><div class="label">Easy Exploits</div></div>
    </div>
  </div>

  <!-- Port Scan -->
  <div class="card">
    <h2>🔓 Port Scan Results</h2>
    <table>
      <tr><th>Port</th><th>Service</th><th>Version</th><th>Status</th></tr>
      {port_rows if port_rows else '<tr><td colspan="4" style="color:#8b949e">No open ports found</td></tr>'}
    </table>
  </div>

  <!-- CVE Findings -->
  <div class="card">
    <h2>🔴 CVE Findings</h2>
    <table>
      <tr><th>CVE ID</th><th>Severity</th><th>CVSS</th><th>Port/Service</th><th>Description</th><th>Remediation</th></tr>
      {cve_rows if cve_rows else '<tr><td colspan="6" style="color:#8b949e">No CVEs found</td></tr>'}
    </table>
  </div>

  <!-- Exploits -->
  <div class="card">
    <h2>💥 Exploit Suggestions</h2>
    <table>
      <tr><th>Port</th><th>Service</th><th>Exploit</th><th>Difficulty</th><th>MSF Module</th></tr>
      {exploit_rows if exploit_rows else '<tr><td colspan="5" style="color:#8b949e">No exploits identified</td></tr>'}
    </table>
  </div>

  <!-- Footer -->
  <div style="text-align:center;color:#8b949e;padding:20px;font-size:0.85em">
    Generated by Chhoti Don Cyber Engine — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  </div>
</div>
</body>
</html>"""

        return html

    # ==================================================
    # 📦 JSON REPORT
    # ==================================================
    def export_json(self, recon_data: Dict, filepath: str = None) -> str:
        """JSON report export karo."""
        if not filepath:
            target = recon_data.get("target", "unknown")
            filepath = self._get_filename(target, "json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(recon_data, f, indent=2, default=str)

        return filepath

    # ==================================================
    # 🔧 REMEDIATION BUILDER
    # ==================================================
    def _build_remediation(self, phases: Dict) -> List[str]:
        """Remediation roadmap build karo."""
        lines = []
        priority = 1

        cve_phase = phases.get("cve_analysis", {})
        for finding in cve_phase.get("findings", []):
            for cve in finding.get("cves", []):
                if cve.get("remediation"):
                    sev = cve.get("severity", "medium").upper()
                    lines.append(f"  {priority}. [{sev}] {cve['cve_id']}: {cve['remediation']}")
                    priority += 1

        if not lines:
            lines.append("  No specific remediation steps identified.")

        return lines

    # ==================================================
    # 🎯 EXPORT ALL FORMATS
    # ==================================================
    def export_all(self, recon_data: Dict) -> Dict:
        """Sab formats mein export karo."""
        target = recon_data.get("target", "unknown")

        results = {
            "txt": self.export_txt(recon_data),
            "json": self.export_json(recon_data),
            "markdown": self.export_markdown(recon_data),
            "html": self.export_html(recon_data),
        }

        print(f"\n📁 Reports saved:")
        for fmt, path in results.items():
            print(f"   {fmt.upper():8} → {path}")

        return results

    # ==================================================
    # 📊 QUICK SUMMARY PRINT
    # ==================================================
    def print_quick_summary(self, recon_data: Dict) -> None:
        """Terminal pe quick summary print karo."""
        summary = recon_data.get("executive_summary", {})
        print("\n" + "=" * 55)
        print("  QUICK RECON SUMMARY")
        print("=" * 55)
        print(f"  Target  : {recon_data.get('target','N/A')}")
        print(f"  Verdict : {summary.get('verdict','N/A')}")
        print(f"  Risk    : {summary.get('risk_score',0)}/100 [{summary.get('risk_level','N/A')}]")
        print(f"  Ports   : {summary.get('open_ports',0)}")
        print(f"  CVEs    : {summary.get('cves_found',0)} ({summary.get('critical_cves',0)} critical)")
        print(f"  Exploits: {summary.get('exploits_available',0)} ({summary.get('easy_exploits',0)} easy)")
        print("=" * 55)
