"""
Chhoti Don - Web Scanner
Advanced web vulnerability scanner.
Detects SQLi, XSS, CSRF, Directory Traversal,
Security Headers, and more.
Phase 2.2 - Medium Priority Feature

⚠️  FOR AUTHORIZED PENETRATION TESTING ONLY
"""

import urllib.request
import urllib.parse
import urllib.error
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Type
# ==================================================
# ==================================================

# SQL Injection payloads
SQLI_PAYLOADS = [
    "'", "''", "`", "``", ",", "\"",
    "' OR '1'='1", "' OR 1=1--", "' OR 1=1#",
    "1' ORDER BY 1--", "1' ORDER BY 2--",
    "' UNION SELECT NULL--", "' UNION SELECT NULL,NULL--",
    "1; DROP TABLE users--",
    "' AND SLEEP(3)--",  # Time-based blind
    "1 AND 1=1", "1 AND 1=2",
]

# XSS payloads
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
    "'><script>alert('XSS')</script>",
    "\"><script>alert('XSS')</script>",
    "<svg onload=alert('XSS')>",
    "';alert('XSS')//",
    "<iframe src=javascript:alert('XSS')>",
]

# Directory traversal payloads
TRAVERSAL_PAYLOADS = [
    "../etc/passwd",
    "../../etc/passwd",
    "../../../etc/passwd",
    "../../../../etc/passwd",
    "..%2F..%2Fetc%2Fpasswd",
    "..%252F..%252Fetc%252Fpasswd",
    "....//....//etc/passwd",
    "%2e%2e%2fetc%2fpasswd",
]

# Common sensitive paths
SENSITIVE_PATHS = [
    "/.git/HEAD",
    "/.env",
    "/config.php",
    "/wp-config.php",
    "/admin",
    "/admin/login",
    "/administrator",
    "/phpmyadmin",
    "/backup",
    "/backup.zip",
    "/backup.sql",
    "/.htaccess",
    "/robots.txt",
    "/sitemap.xml",
    "/api/v1/users",
    "/api/users",
    "/.DS_Store",
    "/web.config",
    "/server-status",
    "/server-info",
    "/crossdomain.xml",
    "/clientaccesspolicy.xml",
]

# Security headers to check
SECURITY_HEADERS = {
    "Strict-Transport-Security": "HSTS missing — HTTP downgrade possible",
    "X-Frame-Options": "Clickjacking protection missing",
    "X-Content-Type-Options": "MIME sniffing protection missing",
    "Content-Security-Policy": "CSP missing — XSS risk increased",
    "X-XSS-Protection": "XSS filter header missing",
    "Referrer-Policy": "Referrer policy missing — info leakage risk",
    "Permissions-Policy": "Permissions policy missing",
}

# Timeout for requests
REQUEST_TIMEOUT = 5


class WebScanner:
    """
    Advanced Web Vulnerability Scanner.
    Detects common web vulnerabilities for authorized pentesting.
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT, threads: int = 10):
        self.timeout = timeout
        self.threads = threads
        self.findings = []
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    # --------------------------------------------------
    # 🌐 HTTP Request Helper
    # --------------------------------------------------
    def _request(self, url: str, method: str = "GET", data: bytes = None, headers: Dict = None) -> Tuple[int, Dict, str]:
        """Safe HTTP request."""
        try:
            req_headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ChhotiDon/1.0)",
                "Accept": "text/html,application/json,*/*",
            }
            if headers:
                req_headers.update(headers)

            req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
            response = urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx)

            body = response.read(8192).decode(errors="ignore")
            resp_headers = dict(response.headers)
            return response.status, resp_headers, body

        except urllib.error.HTTPError as e:
            body = e.read(2048).decode(errors="ignore") if e.fp else ""
            return e.code, {}, body
        except Exception:
            return 0, {}, ""

    # --------------------------------------------------
    # 🔍 Security Headers Check
    # --------------------------------------------------
    def check_security_headers(self, url: str) -> Dict:
        """Security headers analyze karo."""
        status, headers, _ = self._request(url)

        if status == 0:
            return {"status": "error", "message": "Could not connect to target"}

        missing = []
        present = []
        findings = []

        headers_lower = {k.lower(): v for k, v in headers.items()}

        for header, risk in SECURITY_HEADERS.items():
            if header.lower() in headers_lower:
                present.append({
                    "header": header,
                    "value": headers_lower[header.lower()]
                })
            else:
                missing.append(header)
                findings.append({
                    "type": "missing_security_header",
                    "header": header,
                    "severity": "medium",
                    "description": risk,
                    "recommendation": f"Add '{header}' header to server response"
                })

        # Server version disclosure
        server = headers_lower.get("server", "")
        if server and any(v.isdigit() for v in server):
            findings.append({
                "type": "server_version_disclosure",
                "severity": "low",
                "description": f"Server version disclosed: {server}",
                "recommendation": "Hide server version information"
            })

        # X-Powered-By disclosure
        powered_by = headers_lower.get("x-powered-by", "")
        if powered_by:
            findings.append({
                "type": "technology_disclosure",
                "severity": "low",
                "description": f"Technology disclosed: {powered_by}",
                "recommendation": "Remove X-Powered-By header"
            })

        return {
            "status": "success",
            "url": url,
            "http_status": status,
            "missing_headers": missing,
            "present_headers": present,
            "findings": findings,
            "score": len(present),
            "max_score": len(SECURITY_HEADERS),
            "security_grade": self._grade_headers(len(present), len(SECURITY_HEADERS))
        }

    # --------------------------------------------------
    # 💉 SQL Injection Detection
    # --------------------------------------------------
    def check_sqli(self, url: str, params: List[str] = None) -> Dict:
        """
        Basic SQL injection detection.
        Tests common SQLi payloads in URL parameters.
        """
        findings = []
        tested = 0

        # Extract params from URL if not provided
        if not params:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            params = list(query.keys())

        if not params:
            # Try common parameter names
            params = ["id", "page", "search", "q", "user", "name", "cat", "item"]

        # SQLi error signatures
        sqli_errors = [
            "sql syntax", "mysql_fetch", "ora-", "syntax error",
            "unclosed quotation", "quoted string not properly terminated",
            "microsoft ole db", "odbc sql server driver", "postgresql error",
            "warning: mysql", "you have an error in your sql syntax",
        ]

        for param in params[:5]:  # Limit to 5 params
            for payload in SQLI_PAYLOADS[:8]:  # Limit payloads
                test_url = self._inject_param(url, param, payload)
                status, _, body = self._request(test_url)
                tested += 1

                body_lower = body.lower()
                for error in sqli_errors:
                    if error in body_lower:
                        findings.append({
                            "type": "sql_injection",
                            "severity": "critical",
                            "parameter": param,
                            "payload": payload,
                            "evidence": error,
                            "url": test_url,
                            "description": f"Possible SQLi in parameter '{param}' — SQL error detected",
                            "recommendation": "Use parameterized queries / prepared statements"
                        })
                        break

                # Time-based detection
                if "SLEEP" in payload or "WAITFOR" in payload:
                    start = time.time()
                    self._request(test_url)
                    elapsed = time.time() - start
                    if elapsed >= 2.5:
                        findings.append({
                            "type": "sql_injection_blind_time",
                            "severity": "critical",
                            "parameter": param,
                            "payload": payload,
                            "evidence": f"Response delayed {elapsed:.1f}s",
                            "description": f"Time-based blind SQLi in parameter '{param}'",
                            "recommendation": "Use parameterized queries"
                        })

        return {
            "status": "success",
            "url": url,
            "parameters_tested": params[:5],
            "payloads_tested": tested,
            "findings": findings,
            "vulnerable": len(findings) > 0,
        }

    # --------------------------------------------------
    # 🔴 XSS Detection
    # --------------------------------------------------
    def check_xss(self, url: str, params: List[str] = None) -> Dict:
        """
        Reflected XSS detection.
        """
        findings = []
        tested = 0

        if not params:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            params = list(query.keys()) or ["q", "search", "name", "input"]

        for param in params[:5]:
            for payload in XSS_PAYLOADS[:5]:
                test_url = self._inject_param(url, param, payload)
                status, _, body = self._request(test_url)
                tested += 1

                if payload.lower() in body.lower():
                    findings.append({
                        "type": "xss_reflected",
                        "severity": "high",
                        "parameter": param,
                        "payload": payload,
                        "evidence": "Payload reflected in response",
                        "url": test_url,
                        "description": f"Reflected XSS in parameter '{param}'",
                        "recommendation": "Encode output, implement CSP"
                    })

        return {
            "status": "success",
            "url": url,
            "parameters_tested": params[:5],
            "payloads_tested": tested,
            "findings": findings,
            "vulnerable": len(findings) > 0,
        }

    # --------------------------------------------------
    # 📁 Directory Traversal
    # --------------------------------------------------
    def check_traversal(self, url: str) -> Dict:
        """Directory traversal detection."""
        findings = []
        base_url = url.rstrip("/")

        passwd_signatures = ["root:", "daemon:", "bin:", "/bin/bash", "/bin/sh"]

        for payload in TRAVERSAL_PAYLOADS:
            test_url = f"{base_url}/{payload}"
            status, _, body = self._request(test_url)

            for sig in passwd_signatures:
                if sig in body:
                    findings.append({
                        "type": "directory_traversal",
                        "severity": "critical",
                        "payload": payload,
                        "evidence": sig,
                        "url": test_url,
                        "description": "Directory traversal — /etc/passwd accessible!",
                        "recommendation": "Validate and sanitize file paths, use chroot"
                    })
                    break

        return {
            "status": "success",
            "url": url,
            "payloads_tested": len(TRAVERSAL_PAYLOADS),
            "findings": findings,
            "vulnerable": len(findings) > 0,
        }

    # --------------------------------------------------
    # 🔍 Sensitive Path Discovery
    # --------------------------------------------------
    def check_sensitive_paths(self, base_url: str) -> Dict:
        """Sensitive files/paths dhundho."""
        findings = []
        base = base_url.rstrip("/")

        def check_path(path):
            url = base + path
            status, headers, body = self._request(url)
            if status in [200, 301, 302, 403]:
                severity = "high" if status == 200 else "medium"
                return {
                    "type": "sensitive_path",
                    "severity": severity,
                    "path": path,
                    "url": url,
                    "status_code": status,
                    "content_length": len(body),
                    "description": f"Sensitive path accessible: {path} (HTTP {status})",
                    "recommendation": f"Restrict access to {path}"
                }
            return None

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(check_path, path): path for path in SENSITIVE_PATHS}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    findings.append(result)

        return {
            "status": "success",
            "base_url": base_url,
            "paths_tested": len(SENSITIVE_PATHS),
            "findings": findings,
            "accessible_paths": [f["path"] for f in findings],
        }

    # --------------------------------------------------
    # 🔒 CORS Misconfiguration
    # --------------------------------------------------
    def check_cors(self, url: str) -> Dict:
        """CORS misconfiguration check."""
        findings = []

        # Test with malicious origin
        test_origins = [
            "https://evil.com",
            "null",
            "https://attacker.com",
        ]

        for origin in test_origins:
            status, headers, _ = self._request(url, headers={"Origin": origin})
            headers_lower = {k.lower(): v for k, v in headers.items()}

            acao = headers_lower.get("access-control-allow-origin", "")
            acac = headers_lower.get("access-control-allow-credentials", "")

            if acao == "*":
                findings.append({
                    "type": "cors_wildcard",
                    "severity": "medium",
                    "description": "CORS allows all origins (*)",
                    "recommendation": "Restrict CORS to specific trusted origins"
                })

            if acao == origin and "evil" in origin:
                severity = "critical" if acac.lower() == "true" else "high"
                findings.append({
                    "type": "cors_arbitrary_origin",
                    "severity": severity,
                    "origin_tested": origin,
                    "description": f"CORS reflects arbitrary origin: {origin}" +
                                  (" with credentials!" if acac.lower() == "true" else ""),
                    "recommendation": "Validate Origin header against whitelist"
                })

        return {
            "status": "success",
            "url": url,
            "findings": findings,
            "vulnerable": len(findings) > 0,
        }

    # --------------------------------------------------
    # 🚀 FULL SCAN
    # --------------------------------------------------
    def full_scan(self, url: str, params: List[str] = None) -> Dict:
        """
        Complete web vulnerability scan.
        Runs all checks in sequence.
        """
        start_time = time.time()

        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"

        print(f"[WebScanner] Starting full scan: {url}")
        all_findings = []
        scan_results = {}

        # 1. Security Headers
        print("[WebScanner] Checking security headers...")
        headers_result = self.check_security_headers(url)
        scan_results["security_headers"] = headers_result
        all_findings.extend(headers_result.get("findings", []))

        # 2. Sensitive Paths
        print("[WebScanner] Discovering sensitive paths...")
        paths_result = self.check_sensitive_paths(url)
        scan_results["sensitive_paths"] = paths_result
        all_findings.extend(paths_result.get("findings", []))

        # 3. SQLi
        print("[WebScanner] Testing SQL injection...")
        sqli_result = self.check_sqli(url, params)
        scan_results["sqli"] = sqli_result
        all_findings.extend(sqli_result.get("findings", []))

        # 4. XSS
        print("[WebScanner] Testing XSS...")
        xss_result = self.check_xss(url, params)
        scan_results["xss"] = xss_result
        all_findings.extend(xss_result.get("findings", []))

        # 5. Directory Traversal
        print("[WebScanner] Testing directory traversal...")
        traversal_result = self.check_traversal(url)
        scan_results["traversal"] = traversal_result
        all_findings.extend(traversal_result.get("findings", []))

        # 6. CORS
        print("[WebScanner] Checking CORS...")
        cors_result = self.check_cors(url)
        scan_results["cors"] = cors_result
        all_findings.extend(cors_result.get("findings", []))

        # Severity summary
        critical = [f for f in all_findings if f.get("severity") == "critical"]
        high = [f for f in all_findings if f.get("severity") == "high"]
        medium = [f for f in all_findings if f.get("severity") == "medium"]
        low = [f for f in all_findings if f.get("severity") == "low"]

        duration = round(time.time() - start_time, 2)
        print(f"[WebScanner] Scan complete in {duration}s — {len(all_findings)} findings")

        return {
            "status": "success",
            "url": url,
            "scan_duration_sec": duration,
            "total_findings": len(all_findings),
            "findings": all_findings,
            "severity_summary": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
            "scan_results": scan_results,
            "risk_level": "CRITICAL" if critical else "HIGH" if high else "MEDIUM" if medium else "LOW",
        }

    # --------------------------------------------------
    # 🔧 Helpers
    # --------------------------------------------------
    def _inject_param(self, url: str, param: str, payload: str) -> str:
        """URL mein parameter inject karo."""
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        query[param] = [payload]
        new_query = urllib.parse.urlencode(query, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    def _grade_headers(self, present: int, total: int) -> str:
        """Security grade calculate karo."""
        ratio = present / total if total > 0 else 0
        if ratio >= 0.9:
            return "A"
        elif ratio >= 0.7:
            return "B"
        elif ratio >= 0.5:
            return "C"
        elif ratio >= 0.3:
            return "D"
        else:
            return "F"
