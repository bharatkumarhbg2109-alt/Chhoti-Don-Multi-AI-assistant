"""
Chhoti Don - Auto Recon
Fully automated reconnaissance pipeline.
Port scan → Subdomain → CVE → Exploit → Report
Phase 2.2 - High Priority Feature
"""

import time
import datetime
from typing import Dict, List, List

class AutoRecon:
    """
    Automated Reconnaissance Engine
    Full pipeline: Recon → Analysis → Exploit Suggestions

    Pipeline:
    1. Port Scan
    2. Subdomain Discovery
    3. CVE Analysis
    4. Risk Scoring
    5. Exploit Suggestions
    6. Pentest Checklist
    7. Session Storage
    """

    def __init__(self, session_manager=None, guardian=None):
        self.session_manager = session_manager
        self.guardian = guardian
        self.results = {}

    # ==================================================
    # 🚀 FULL AUTO RECON PIPELINE
    # ==================================================
    def run(
        self,
        target: str,
        ports: List[int] = None,
        scan_subdomains: bool = True,
        domain: str = None,
        session_id: str = None,
        verbose: bool = True
    ) -> Dict:
        """
        Full automated recon pipeline.

        Args:
            target     : IP/hostname to scan
            ports      : Port list (None = common ports)
            scan_subdomains: Subdomain scan karna hai?
            domain     : Domain for subdomain scan
            session_id : Existing session ID (optional)
            verbose    : Print progress

        Returns:
            Complete recon report dict
        """
        start_time = time.time()
        timestamp = datetime.datetime.utcnow().isoformat()

        if verbose:
            self._log(f"🎯 AUTO RECON STARTED — Target: {target}")

        # Create session
        if self.session_manager and not session_id:
            session_id = self.session_manager.create_session(
                target,
                metadata={"mode": "auto_recon", "started_at": timestamp}
            )

        # Guardian check
        if self.guardian:
            try:
                if self.guardian.requires_approval("auto_recon"):
                    approved = self.guardian.request_permission("auto_recon")
                    if not approved:
                        return self._blocked_result(target, "Guardian blocked auto_recon")
            except Exception:
                pass

        # Rate limit check
        if self.session_manager and session_id:
            allowed, msg = self.session_manager.check_rate_limit(session_id)
            if not allowed:
                return self._blocked_result(target, f"Rate limit: {msg}")

        recon_data = {
            "target": target,
            "session_id": session_id,
            "timestamp": timestamp,
            "status": "running",
            "phases": {}
        }

        # --------------------------------------------------
        # PHASE 1: PORT SCAN
        # --------------------------------------------------
        if verbose:
            self._log("📡 Phase 1: Port Scanning...")

        port_result = self._run_port_scan(target, ports, verbose)
        recon_data["phases"]["port_scan"] = port_result

        if self.session_manager and session_id:
            self.session_manager.store_scan_result(session_id, "port_scan", port_result)

        open_ports = port_result.get("open_ports", [])
        if verbose:
            self._log(f"   ✅ {len(open_ports)} open port(s): {open_ports}")

        # --------------------------------------------------
        # PHASE 2: SUBDOMAIN SCAN
        # --------------------------------------------------
        subdomain_result = {}
        if scan_subdomains and domain:
            if verbose:
                self._log("🌐 Phase 2: Subdomain Discovery...")

            subdomain_result = self._run_subdomain_scan(domain, verbose)
            recon_data["phases"]["subdomain_scan"] = subdomain_result

            if self.session_manager and session_id:
                self.session_manager.store_scan_result(session_id, "subdomain_scan", subdomain_result)

            if verbose:
                count = subdomain_result.get("count", 0)
                self._log(f"   ✅ {count} subdomain(s) discovered")

        # --------------------------------------------------
        # PHASE 3: CVE ANALYSIS
        # --------------------------------------------------
        if verbose:
            self._log("🔍 Phase 3: CVE Analysis...")

        cve_result = self._run_cve_analysis(port_result, verbose)
        recon_data["phases"]["cve_analysis"] = cve_result

        total_cves = cve_result.get("summary", {}).get("total_cves_found", 0)
        if verbose:
            self._log(f"   ✅ {total_cves} CVE(s) found")

        # --------------------------------------------------
        # PHASE 4: RISK SCORING
        # --------------------------------------------------
        if verbose:
            self._log("⚠️  Phase 4: Risk Scoring...")

        risk_result = self._run_risk_scoring(port_result, verbose)
        recon_data["phases"]["risk_assessment"] = risk_result

        if self.session_manager and session_id:
            risk_score = risk_result.get("risk_score", 0)
            self.session_manager.add_risk_score(session_id, risk_score)

        if verbose:
            self._log(f"   ✅ Risk: {risk_result.get('risk_level')} ({risk_result.get('risk_score')}/100)")

        # --------------------------------------------------
        # PHASE 5: EXPLOIT SUGGESTIONS
        # --------------------------------------------------
        if verbose:
            self._log("💥 Phase 5: Exploit Suggestions...")

        exploit_result = self._run_exploit_suggestions(port_result, verbose)
        recon_data["phases"]["exploit_suggestions"] = exploit_result

        total_exploits = exploit_result.get("total_exploits_found", 0)
        if verbose:
            self._log(f"   ✅ {total_exploits} exploit(s) identified")

        # --------------------------------------------------
        # PHASE 6: PENTEST CHECKLIST
        # --------------------------------------------------
        if verbose:
            self._log("📋 Phase 6: Pentest Checklist...")

        pentest_result = self._run_pentest_checklist(open_ports, verbose)
        recon_data["phases"]["pentest_checklist"] = pentest_result

        if verbose:
            self._log(f"   ✅ {pentest_result.get('total_tests', 0)} test(s) generated")

        # --------------------------------------------------
        # FINAL SUMMARY
        # --------------------------------------------------
        duration = round(time.time() - start_time, 3)

        recon_data["status"] = "complete"
        recon_data["duration_sec"] = duration
        recon_data["executive_summary"] = self._build_executive_summary(
            target, port_result, cve_result, risk_result, exploit_result
        )

        if self.session_manager and session_id:
            self.session_manager.update_session(session_id, "recon_complete", True)
            self.session_manager.update_session(session_id, "final_report", recon_data)

        if verbose:
            self._log(f"\n✅ AUTO RECON COMPLETE in {duration}s")
            self._print_summary(recon_data["executive_summary"])

        return recon_data

    # ==================================================
    # 🔧 PHASE RUNNERS
    # ==================================================

    def _run_port_scan(self, target: str, ports: List[int], verbose: bool) -> Dict:
        """Port scan phase."""
        try:
            from cyber_engine.recon.port_scanner import PortScanner

            scanner = PortScanner(timeout=1, max_threads=50)

            if ports:
                return scanner.scan_ports(target, ports, use_cve=False)
            else:
                return scanner.quick_scan(target)

        except Exception as e:
            return {"error": str(e), "open_ports": [], "target": target}

    def _run_subdomain_scan(self, domain: str, verbose: bool) -> Dict:
        """Subdomain scan phase."""
        try:
            from cyber_engine.recon.subdomain_scanner import SubdomainScanner

            scanner = SubdomainScanner(timeout=2, max_threads=30)
            return scanner.quick_scan(domain)

        except Exception as e:
            return {"error": str(e), "count": 0, "domain": domain}

    def _run_cve_analysis(self, port_result: Dict, verbose: bool) -> Dict:
        """CVE analysis phase."""
        try:
            from cyber_engine.vuln_analysis.cve_engine import analyze_scan_results
            return analyze_scan_results(port_result)
        except Exception as e:
            return {"error": str(e), "findings": [], "summary": {}}

    def _run_risk_scoring(self, port_result: Dict, verbose: bool) -> Dict:
        """Risk scoring phase."""
        try:
            from cyber_engine.intelligence.risk_calculator import generate_risk_report
            return generate_risk_report(port_result)
        except Exception as e:
            return {"error": str(e), "risk_score": 0, "risk_level": "UNKNOWN"}

    def _run_exploit_suggestions(self, port_result: Dict, verbose: bool) -> Dict:
        """Exploit suggestions phase."""
        try:
            from cyber_engine.assessment.exploit_suggester import analyze_and_suggest
            return analyze_and_suggest(port_result)
        except Exception as e:
            return {"error": str(e), "total_exploits_found": 0}

    def _run_pentest_checklist(self, open_ports: List[int], verbose: bool) -> Dict:
        """Pentest checklist phase."""
        try:
            from cyber_engine.assessment.pentest_helper import generate_pentest_checklist
            return generate_pentest_checklist(open_ports)
        except Exception as e:
            return {"error": str(e), "recommended_tests": [], "total_tests": 0}

    # ==================================================
    # 📊 EXECUTIVE SUMMARY
    # ==================================================
    def _build_executive_summary(
        self,
        target: str,
        port_result: Dict,
        cve_result: Dict,
        risk_result: Dict,
        exploit_result: Dict
    ) -> Dict:
        """Executive summary build karo."""

        open_ports = port_result.get("open_ports", [])
        cve_summary = cve_result.get("summary", {})
        exploit_summary = exploit_result.get("summary", {})

        risk_score = risk_result.get("risk_score", 0)
        risk_level = risk_result.get("risk_level", "UNKNOWN")

        # Overall verdict
        if risk_score >= 80 or cve_summary.get("total_critical", 0) >= 2:
            verdict = "🔴 CRITICAL — Immediate action required"
        elif risk_score >= 60 or cve_summary.get("total_exploitable", 0) >= 2:
            verdict = "🟠 HIGH — Prioritize remediation"
        elif risk_score >= 40:
            verdict = "🟡 MEDIUM — Schedule remediation"
        elif risk_score >= 20:
            verdict = "🟢 LOW — Monitor and review"
        else:
            verdict = "✅ MINIMAL — No immediate action"

        return {
            "target": target,
            "verdict": verdict,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "open_ports": len(open_ports),
            "ports_list": open_ports,
            "cves_found": cve_summary.get("total_cves_found", 0),
            "critical_cves": cve_summary.get("total_critical", 0),
            "exploitable_cves": cve_summary.get("total_exploitable", 0),
            "exploits_available": exploit_result.get("total_exploits_found", 0),
            "easy_exploits": exploit_summary.get("easy_exploits", 0),
            "msf_modules": exploit_result.get("msf_modules", []),
            "action_required": risk_result.get("action_required", "Review findings"),
        }

    # ==================================================
    # 🖨️ HELPERS
    # ==================================================

    def _log(self, message: str) -> None:
        """Print with timestamp."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {message}")

    def _print_summary(self, summary: Dict) -> None:
        """Print executive summary."""
        print("\n" + "=" * 55)
        print("📊 EXECUTIVE SUMMARY")
        print("=" * 55)
        print(f"🎯 Target      : {summary['target']}")
        print(f"⚠️  Verdict     : {summary['verdict']}")
        print(f"📊 Risk Score  : {summary['risk_score']}/100")
        print(f"🔓 Open Ports  : {summary['open_ports']} → {summary['ports_list']}")
        print(f"🔴 CVEs Found  : {summary['cves_found']} ({summary['critical_cves']} critical)")
        print(f"💥 Exploits    : {summary['exploits_available']} ({summary['easy_exploits']} easy)")
        if summary.get("msf_modules"):
            print(f"🔫 MSF Modules : {len(summary['msf_modules'])}")
        print(f"✅ Action      : {summary['action_required']}")
        print("=" * 55)

    def _blocked_result(self, target: str, reason: str) -> Dict:
        return {
            "target": target,
            "status": "blocked",
            "reason": reason,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    # ==================================================
    # 🎯 QUICK RECON — Single target fast scan
    # ==================================================
    def quick_recon(self, target: str) -> Dict:
        """
        Fast recon — top 20 ports, no subdomain scan.
        """
        return self.run(
            target=target,
            scan_subdomains=False,
            verbose=True
        )

    def full_recon(self, target: str, domain: str) -> Dict:
        """
        Complete recon — all ports + subdomains.
        """
        common_ports = [
            21, 22, 23, 25, 53, 80, 110, 135, 139,
            143, 443, 445, 1433, 3306, 3389, 5432,
            6379, 8080, 8443, 27017
        ]
        return self.run(
            target=target,
            ports=common_ports,
            scan_subdomains=True,
            domain=domain,
            verbose=True
        )
