"""
Chhoti Don - Cyber Intelligence Controller
Strategic Intelligence Core — Phase 2.2 Upgrade
All medium priority modules integrated.
"""

import logging
import time
from core.response_engine import ResponseEngine
from core.telemetry_engine import TelemetryEngine
from core.error_registry import ErrorCodes


class CyberController:

    def __init__(self):
        self.version = "6.2 - Strategic Intelligence Core (Phase 2.2 Full Upgrade)"

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ChhotiDon")

        from cyber_engine.session.session_manager import SessionManager
        from cyber_engine.config.config_manager import ConfigManager

        self.session_manager = SessionManager()
        self.config_manager = ConfigManager()
        self.telemetry = TelemetryEngine()

        # Reflection config
        self.reflection_enabled = True
        self.max_reflection_attempts = 1
        self.confidence_threshold = 0.65
        self.retry_confidence_decay = 0.15

        # ==================================================
        # 🔧 TOOL REGISTRY — UPGRADED with new modules
        # ==================================================
        self.tool_registry = {
            # Original tools (preserved)
            "basic_scan": self.run_basic_scan,
            "hash_check": self.check_file_hash,
            "pe_analysis": self.analyze_pe_file,
            "nuclei_parse": self.analyze_nuclei_output,
            "cve_suggest": self.suggest_cves,
            "aggregate": self.aggregate_findings,
            "threat_score": self.calculate_threat_score,
            "risk_score": self.calculate_risk,

            # Phase 2.2 — New tools
            "auto_recon": self.run_auto_recon,
            "web_scan": self.run_web_scan,
            "cred_test": self.run_credential_test,
            "payload_gen": self.run_payload_generator,
            "export_report": self.run_report_export,
            "port_scan": self.run_port_scan,
            "subdomain_scan": self.run_subdomain_scan,
            "exploit_suggest": self.run_exploit_suggester,
        }

        self.planner = None
        self.validator = None
        self.execution_controller = None

        try:
            from core.planner import StructuredPlanner
            from core.validator import StepValidator
            from core.execution_controller import ExecutionController

            self.planner = StructuredPlanner(self, self.telemetry)
            self.validator = StepValidator(self.tool_registry, self)
            self.execution_controller = ExecutionController(self.validator, self)

        except Exception as e:
            self.logger.warning(f"Structured autonomy not loaded: {e}")

    # ==================================================
    # 🛡️ SAFE EXECUTE WRAPPER (PRESERVED)
    # ==================================================
    def _safe_execute(self, callable_fn, module_name="unknown"):
        start_time = time.time()
        try:
            result = callable_fn()

            if isinstance(result, dict) and result.get("status") in ["blocked", "error"]:
                response = ResponseEngine.build(
                    status=result.get("status"),
                    code=result.get("code", ErrorCodes.GUARDIAN_BLOCK),
                    message=result.get("reason", "Execution blocked"),
                    data=None, module=module_name,
                    start_time=start_time, confidence=0.5
                )
                self._record_telemetry(module_name, response)
                return response

            response = ResponseEngine.build(
                status="success", code=ErrorCodes.SUCCESS,
                message="Execution completed successfully",
                data=result, module=module_name,
                start_time=start_time, confidence=0.9
            )
            self._record_telemetry(module_name, response)
            return response

        except Exception as e:
            response = ResponseEngine.build(
                status="error", code=ErrorCodes.INTERNAL_ERROR,
                message=str(e), data=None, module=module_name,
                start_time=start_time, confidence=0.2
            )
            self._record_telemetry(module_name, response)
            return response

    def _record_telemetry(self, module_name, response):
        try:
            self.telemetry.record(
                module_name, response.get("status"),
                response.get("meta", {}).get("execution_time", 0),
                response.get("code")
            )
        except Exception:
            pass

    # ==================================================
    # 🚀 GENERIC EXECUTOR (PRESERVED)
    # ==================================================
    def execute(self, action, input_data, session_id=None):
        if action not in self.tool_registry:
            return ResponseEngine.build(
                status="error", code=ErrorCodes.TOOL_NOT_FOUND,
                message=f"Tool '{action}' not found. Available: {list(self.tool_registry.keys())}",
                data=None, module="executor"
            )

        try:
            return self.tool_registry[action](**input_data, session_id=session_id)
        except Exception as e:
            return ResponseEngine.build(
                status="error", code=ErrorCodes.EXECUTION_ERROR,
                message=str(e), data=None, module="executor"
            )

    # ==================================================
    # 🧠 STRUCTURED TASK (PRESERVED)
    # ==================================================
    def run_structured_task(self, goal, session_id=None):
        if not self.planner or not self.execution_controller:
            return ResponseEngine.build(
                status="error", code=ErrorCodes.STRUCTURE_NOT_AVAILABLE,
                message="Structured autonomy layer not available",
                data=None, module="structured_task"
            )

        attempt = 0
        last_response = None
        dynamic_retry_limit = self.max_reflection_attempts

        if self.telemetry.detect_instability():
            dynamic_retry_limit += 1

        while attempt <= dynamic_retry_limit:
            plan_result = self.planner.generate_plan(goal)
            if plan_result.get("status") != "success":
                return plan_result

            response = self.execution_controller.execute_plan(
                plan_result.get("plan"), session_id=session_id
            )
            last_response = response

            status = response.get("status")
            confidence = response.get("confidence", 1)
            error_code = response.get("code")

            if not self.reflection_enabled:
                return response

            if error_code and self.telemetry.is_repeated_error(error_code, threshold=3):
                response["reflection"] = {"attempts": attempt, "suppressed": True, "reason": "Repeated error"}
                return response

            failure_streak = self.telemetry.get_failure_streak("structured_task")
            if failure_streak >= 3:
                response["reflection"] = {"attempts": attempt, "suppressed": True, "reason": "Failure streak"}
                return response

            tool_reliability = self.telemetry.get_tool_reliability("structured_task")
            dynamic_threshold = self.confidence_threshold * tool_reliability

            if self.telemetry.detect_instability():
                dynamic_threshold *= 0.9

            if status == "completed" and confidence >= dynamic_threshold:
                response["reflection"] = {
                    "attempts": attempt,
                    "reflected": attempt > 0,
                    "dynamic_threshold": round(dynamic_threshold, 4),
                    "tool_reliability": tool_reliability
                }
                return response

            attempt += 1
            if attempt > dynamic_retry_limit:
                break

            confidence = max(0, confidence - self.retry_confidence_decay)
            time.sleep(0.05)

        return last_response

    # ==================================================
    # 🎯 SESSION MANAGEMENT (PRESERVED)
    # ==================================================
    def create_scan_session(self, target):
        return self.session_manager.create_session(target)

    def get_scan_session(self, session_id):
        return self.session_manager.get_session(session_id)

    def list_scan_sessions(self):
        return self.session_manager.list_sessions()

    # ==================================================
    # ⚙️ CONFIG (PRESERVED)
    # ==================================================
    def get_config(self):
        return self.config_manager.get_all()

    def update_config(self, key, value):
        self.config_manager.set(key, value)

    # ==================================================
    # 🔍 ORIGINAL MODULES (PRESERVED)
    # ==================================================
    def run_basic_scan(self, target, session_id=None):
        def task():
            from cyber_engine.assessment.basic_scanner import scan_common_ports

            effective_target = target

            if session_id:
                allowed, message = self.session_manager.check_rate_limit(session_id)
                if not allowed:
                    return {"status": "blocked", "reason": message}

                session_data = self.session_manager.get_session(session_id)
                if session_data:
                    effective_target = session_data.get("target")

                session_count = self.session_manager.get_target_session_count(effective_target)
                if session_count >= 3:
                    return {"status": "blocked", "reason": "Repeated target scanning detected"}

            validation = validate_target(effective_target)
            if not validation.get("allowed"):
                return {"status": "blocked", "reason": validation.get("reason")}

            return scan_common_ports(effective_target)

        return self._safe_execute(task, "basic_scanner")

    def check_file_hash(self, file_path, session_id=None):
        def task():
            from cyber_engine.malware_detection.hash_checker import calculate_sha256
            return calculate_sha256(file_path)
        return self._safe_execute(task, "hash_checker")

    def analyze_pe_file(self, file_path, session_id=None):
        def task():
            from cyber_engine.reverse_engineering.pe_analyzer import analyze_pe
            return analyze_pe(file_path)
        return self._safe_execute(task, "pe_analyzer")

    def analyze_nuclei_output(self, json_data, session_id=None):
        def task():
            from cyber_engine.vuln_analysis.nuclei_parser import parse_nuclei_results
            return parse_nuclei_results(json_data)
        return self._safe_execute(task, "nuclei_parser")

    def suggest_cves(self, service_name, session_id=None):
        def task():
            from cyber_engine.vuln_analysis.cve_engine import suggest_cves, get_cve_details
            return {
                "cve_ids": suggest_cves(service_name),
                "cve_details": get_cve_details(service_name)
            }
        return self._safe_execute(task, "cve_engine")

    def aggregate_findings(self, *scan_sources, session_id=None):
        def task():
            from cyber_engine.intelligence.vuln_aggregator import aggregate_findings
            return aggregate_findings(*scan_sources)
        return self._safe_execute(task, "vuln_aggregator")

    def calculate_threat_score(self, severity_distribution, session_id=None):
        def task():
            from cyber_engine.intelligence.threat_scorer import calculate_overall_threat
            return calculate_overall_threat(severity_distribution)
        return self._safe_execute(task, "threat_scorer")

    def calculate_risk(self, severity, confidence=0.8, session_id=None):
        def task():
            from cyber_engine.intelligence.risk_calculator import calculate_risk, generate_risk_report

            if session_id:
                self.session_manager.add_risk_score(session_id, risk_result.get("adjusted_score", 0))
                adjustment = self.session_manager.get_risk_trend_adjustment(session_id)
                risk_result["trend_adjustment"] = adjustment

            return risk_result
        return self._safe_execute(task, "risk_calculator")

    # ==================================================
    # 🔥 NEW — Phase 2.2 Modules
    # ==================================================

    def run_auto_recon(self, target, ports=None, domain=None, session_id=None):
        """Full automated recon pipeline."""
        def task():
            from cyber_engine.assessment.scope_validator import validate_target
            validation = validate_target(target)
            if not validation.get("allowed"):
                return {"status": "blocked", "reason": validation.get("reason")}

            from cyber_engine.recon.auto_recon import AutoRecon
            recon = AutoRecon(
                session_manager=self.session_manager,
                guardian=None
            )
            return recon.run(
                target=target,
                ports=ports,
                scan_subdomains=bool(domain),
                domain=domain,
                session_id=session_id,
                verbose=True
            )
        return self._safe_execute(task, "auto_recon")

    def run_web_scan(self, url, params=None, scan_type="full", session_id=None):
        """Web vulnerability scan."""
        def task():
            from cyber_engine.assessment.web_scanner import WebScanner
            scanner = WebScanner(timeout=5, threads=10)

            if scan_type == "headers":
                return scanner.check_security_headers(url)
            elif scan_type == "sqli":
                return scanner.check_sqli(url, params)
            elif scan_type == "xss":
                return scanner.check_xss(url, params)
            elif scan_type == "paths":
                return scanner.check_sensitive_paths(url)
            elif scan_type == "cors":
                return scanner.check_cors(url)
            else:
                return scanner.full_scan(url, params)

        return self._safe_execute(task, "web_scanner")

    def run_credential_test(self, host, service="auto", port=None, credentials=None, session_id=None):
        """Credential testing."""
        def task():
            from cyber_engine.assessment.scope_validator import validate_target
            validation = validate_target(host)
            if not validation.get("allowed"):
                return {"status": "blocked", "reason": validation.get("reason")}

            from cyber_engine.assessment.credential_tester import CredentialTester
            tester = CredentialTester(timeout=5)

            if service == "ssh":
                return tester.test_ssh(host, port or 22, credentials)
            elif service == "ftp":
                return tester.test_ftp(host, port or 21, credentials)
            elif service == "mysql":
                return tester.test_mysql(host, port or 3306, credentials)
            elif service == "redis":
                return tester.test_redis(host, port or 6379)
            elif service == "http":
                return tester.test_http_basic(host, credentials)
            else:
                # Auto mode — test based on port
                open_ports = [port] if port else [21, 22, 3306, 6379]
                return tester.auto_test(host, open_ports)

        return self._safe_execute(task, "credential_tester")

    def run_payload_generator(self, shell_type, lhost, lport, encode=False, obfuscate=False, session_id=None):
        """Payload generation."""
        def task():
            from cyber_engine.assessment.payload_generator import PayloadGenerator
            gen = PayloadGenerator()
            return gen.generate_reverse_shell(shell_type, lhost, lport, encode, obfuscate)
        return self._safe_execute(task, "payload_generator")

    def run_report_export(self, recon_data, format="all", output_dir="reports", session_id=None):
        """Report export."""
        def task():
            from cyber_engine.report_exporter import ReportExporter
            exporter = ReportExporter(output_dir=output_dir)

            if format == "txt":
                path = exporter.export_txt(recon_data)
                return {"status": "success", "file": path}
            elif format == "html":
                path = exporter.export_html(recon_data)
                return {"status": "success", "file": path}
            elif format == "json":
                path = exporter.export_json(recon_data)
                return {"status": "success", "file": path}
            elif format == "markdown":
                path = exporter.export_markdown(recon_data)
                return {"status": "success", "file": path}
            else:
                paths = exporter.export_all(recon_data)
                return {"status": "success", "files": paths}

        return self._safe_execute(task, "report_exporter")

    def run_port_scan(self, target, ports=None, session_id=None):
        """Advanced port scan."""
        def task():
            from cyber_engine.assessment.scope_validator import validate_target
            validation = validate_target(target)
            if not validation.get("allowed"):
                return {"status": "blocked", "reason": validation.get("reason")}

            from cyber_engine.recon.port_scanner import PortScanner
            scanner = PortScanner(timeout=1, max_threads=50)

            if ports:
                return scanner.scan_ports(target, ports)
            else:
                return scanner.quick_scan(target)

        return self._safe_execute(task, "port_scanner")

    def run_subdomain_scan(self, domain, quick=True, session_id=None):
        """Subdomain discovery."""
        def task():
            from cyber_engine.recon.subdomain_scanner import SubdomainScanner
            scanner = SubdomainScanner(timeout=2, max_threads=30)
            if quick:
                return scanner.quick_scan(domain)
            else:
                return scanner.scan(domain)
        return self._safe_execute(task, "subdomain_scanner")

    def run_exploit_suggester(self, scan_result=None, service=None, cve_ids=None, session_id=None):
        """Exploit suggestions."""
        def task():
            from cyber_engine.assessment.exploit_suggester import (
                analyze_and_suggest, suggest_exploits, suggest_exploits_by_service
            )
            if scan_result:
                return analyze_and_suggest(scan_result)
            elif service:
                return suggest_exploits_by_service(service)
            elif cve_ids:
                return suggest_exploits(cve_ids)
            else:
                return {"status": "error", "message": "Provide scan_result, service, or cve_ids"}
        return self._safe_execute(task, "exploit_suggester")

    # ==================================================
    # 📊 TELEMETRY + INFO (PRESERVED)
    # ==================================================
    def get_telemetry(self):
        return self.telemetry.get_metrics()

    def engine_info(self):
        return {
            "engine": "Chhoti Don Cyber Intelligence Platform",
            "version": self.version,
            "tools_available": list(self.tool_registry.keys()),
            "total_tools": len(self.tool_registry),
            "phase": "2.2"
        }
