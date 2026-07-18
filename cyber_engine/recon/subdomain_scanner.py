"""
Chhoti Don - Subdomain Scanner
Advanced subdomain discovery with DNS resolution,
IP mapping, port hints, and takeover detection.
Phase 2.2 - Full Upgrade
"""

import socket
import time
import concurrent.futures
import re
from typing import Dict, List, Optional, Optional

class SubdomainScanner:
    """
    Advanced Subdomain Scanner
    - Passive DNS resolution
    - Concurrent scanning
    - IP mapping & geolocation hints
    - Subdomain takeover detection
    - CDN/WAF detection
    - Phase 2.2 Upgrade
    """

    # Expanded wordlist — 80+ subdomains
    COMMON_SUBDOMAINS: List[str] = [
        # Standard
        "www", "mail", "api", "dev", "test", "staging",
        "admin", "portal", "dashboard", "app", "apps",
        # Infrastructure
        "ftp", "ssh", "vpn", "remote", "rdp", "citrix",
        "proxy", "gateway", "firewall", "router",
        # Services
        "smtp", "pop", "imap", "webmail", "mx", "ns1", "ns2",
        "dns", "ntp", "ldap", "ad", "dc", "dc1", "dc2",
        # Development
        "dev", "dev1", "dev2", "staging", "stage", "uat",
        "qa", "test", "testing", "sandbox", "beta", "alpha",
        "demo", "preview", "preprod", "pre-prod",
        # Databases
        "db", "db1", "db2", "mysql", "postgres", "mongo",
        "redis", "elasticsearch", "es", "kibana",
        # Monitoring
        "monitor", "monitoring", "grafana", "prometheus",
        "nagios", "zabbix", "logs", "logging", "metrics",
        # Cloud/CDN
        "cdn", "static", "assets", "media", "img", "images",
        "files", "uploads", "download", "downloads",
        # API versions
        "api", "api1", "api2", "apiv1", "apiv2", "v1", "v2",
        "rest", "graphql", "ws", "websocket",
        # Business
        "shop", "store", "payment", "pay", "billing",
        "support", "help", "helpdesk", "ticket", "crm",
        "hr", "erp", "internal", "intranet", "extranet",
        # Security
        "vpn", "sso", "auth", "login", "oauth", "saml",
        "cert", "pki", "ca",
        # Misc
        "old", "legacy", "backup", "bkp", "archive",
        "new", "temp", "tmp", "web", "web1", "web2",
        "host", "server", "server1", "server2",
    ]

    # Known CDN/WAF IP ranges (partial)
    CDN_SIGNATURES = {
        "cloudflare": ["104.16.", "104.17.", "104.18.", "104.19.", "172.64.", "172.65."],
        "akamai": ["23.32.", "23.64.", "23.192."],
        "fastly": ["151.101.", "199.27."],
        "aws_cloudfront": ["13.32.", "13.35.", "52.84.", "52.85."],
        "azure_cdn": ["13.107.", "23.103."],
    }

    # Subdomain takeover signatures
    TAKEOVER_SIGNATURES = {
        "github": ["There isn't a GitHub Pages site here"],
        "heroku": ["No such app", "herokucdn.com"],
        "shopify": ["Sorry, this shop is currently unavailable"],
        "aws_s3": ["NoSuchBucket", "The specified bucket does not exist"],
        "azure": ["404 Web Site not found"],
        "pantheon": ["The gods are wise", "pantheonsite.io"],
        "fastly": ["Fastly error: unknown domain"],
        "tumblr": ["There's nothing here"],
        "wordpress": ["Do you want to register"],
    }

    def __init__(self, timeout: float = 2.0, max_threads: int = 50):
        self.timeout = timeout
        self.max_threads = max_threads
        socket.setdefaulttimeout(self.timeout)

    # --------------------------------------------------
    # 🔍 DNS Resolution
    # --------------------------------------------------
    def _resolve(self, full_domain: str) -> Optional[str]:
        """Resolve domain to IP."""
        try:
            ip = socket.gethostbyname(full_domain)
            return ip
        except socket.gaierror:
            return None
        except Exception:
            return None

    def _resolve_all(self, full_domain: str) -> List[str]:
        """Resolve all IPs for a domain."""
        try:
            results = socket.getaddrinfo(full_domain, None)
            ips = list(set(r[4][0] for r in results))
            return ips
        except Exception:
            return []

    def _reverse_dns(self, ip: str) -> Optional[str]:
        """Reverse DNS lookup."""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except Exception:
            return None

    # --------------------------------------------------
    # 🛡️ CDN/WAF Detection
    # --------------------------------------------------
    def _detect_cdn(self, ip: str) -> Optional[str]:
        """IP se CDN/WAF detect karo."""
        for cdn_name, prefixes in self.CDN_SIGNATURES.items():
            for prefix in prefixes:
                if ip.startswith(prefix):
                    return cdn_name
        return None

    # --------------------------------------------------
    # ⚠️ Subdomain Takeover Detection
    # --------------------------------------------------
    def _check_takeover(self, full_domain: str) -> Optional[str]:
        """
        Subdomain takeover vulnerability check.
        CNAME pointing to unclaimed service detect karo.
        """
        try:
            import urllib.request
            import urllib.error

            url = f"http://{full_domain}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

            try:
                response = urllib.request.urlopen(req, timeout=3)
                body = response.read(2048).decode(errors="ignore")

                for service, signatures in self.TAKEOVER_SIGNATURES.items():
                    for sig in signatures:
                        if sig.lower() in body.lower():
                            return f"POSSIBLE TAKEOVER: {service}"

            except urllib.error.HTTPError as e:
                body = str(e.reason)
                for service, signatures in self.TAKEOVER_SIGNATURES.items():
                    for sig in signatures:
                        if sig.lower() in body.lower():
                            return f"POSSIBLE TAKEOVER: {service}"

        except Exception:
            pass

        return None

    # --------------------------------------------------
    # 🔫 Single Subdomain Scan
    # --------------------------------------------------
    def _scan_single(self, subdomain: str, domain: str) -> Optional[Dict]:
        """Single subdomain scan karo."""
        full_domain = f"{subdomain}.{domain}"

        ip = self._resolve(full_domain)
        if not ip:
            return None

        # All IPs
        all_ips = self._resolve_all(full_domain)

        # CDN detection
        cdn = self._detect_cdn(ip)

        # Reverse DNS
        rdns = self._reverse_dns(ip)

        # Takeover check (only for non-CDN)
        takeover = None
        if not cdn:
            takeover = self._check_takeover(full_domain)

        return {
            "subdomain": full_domain,
            "name": subdomain,
            "ip": ip,
            "all_ips": all_ips,
            "cdn": cdn,
            "reverse_dns": rdns,
            "takeover_risk": takeover,
            "is_internal": self._is_private_ip(ip),
        }

    # --------------------------------------------------
    # 🚀 Main Scan — Concurrent
    # --------------------------------------------------
    def scan(self, domain: str, custom_wordlist: List[str] = None) -> Dict:
        """
        Advanced subdomain scan with concurrent resolution.

        Args:
            domain: Target domain (e.g., example.com)
            custom_wordlist: Optional custom subdomain list

        Returns:
            Complete subdomain discovery results
        """
        if not domain or "." not in domain:
            return {
                "domain": domain,
                "discovered_subdomains": [],
                "count": 0,
                "error": "Invalid domain format"
            }

        wordlist = custom_wordlist or self.COMMON_SUBDOMAINS
        start_time = time.time()
        discovered = []

        # Concurrent scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self._scan_single, sub, domain): sub
                for sub in wordlist
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        discovered.append(result)
                except Exception:
                    pass

        # Sort by subdomain name
        discovered.sort(key=lambda x: x["subdomain"])

        # Analysis
        cdn_protected = [d for d in discovered if d.get("cdn")]
        internal_hosts = [d for d in discovered if d.get("is_internal")]
        takeover_risks = [d for d in discovered if d.get("takeover_risk")]
        unique_ips = list(set(d["ip"] for d in discovered))

        duration = round(time.time() - start_time, 3)

        return {
            "domain": domain,
            "discovered_subdomains": [d["subdomain"] for d in discovered],
            "detailed_results": discovered,
            "count": len(discovered),
            "unique_ips": unique_ips,
            "cdn_protected": [d["subdomain"] for d in cdn_protected],
            "internal_hosts": [d["subdomain"] for d in internal_hosts],
            "takeover_risks": takeover_risks,
            "scan_duration_sec": duration,
            "wordlist_size": len(wordlist),
            "summary": self._generate_summary(discovered, domain),
        }

    # --------------------------------------------------
    # 📊 Summary
    # --------------------------------------------------
    def _generate_summary(self, discovered: List[Dict], domain: str) -> str:
        if not discovered:
            return f"No subdomains found for {domain}"

        takeovers = sum(1 for d in discovered if d.get("takeover_risk"))
        cdns = sum(1 for d in discovered if d.get("cdn"))

        summary = f"{len(discovered)} subdomain(s) found for {domain}"
        if takeovers:
            summary += f" — ⚠️ {takeovers} potential takeover(s)!"
        if cdns:
            summary += f" — {cdns} CDN-protected"

        return summary

    def _is_private_ip(self, ip: str) -> bool:
        private = ["192.168.", "10.", "172.16.", "172.17.", "127.", "::1"]
        return any(ip.startswith(p) for p in private)

    # --------------------------------------------------
    # 🎯 Quick Scan — Top 20 only
    # --------------------------------------------------
    def quick_scan(self, domain: str) -> Dict:
        """Top 20 most common subdomains only."""
        top20 = ["www", "mail", "api", "dev", "staging", "admin",
                 "portal", "app", "ftp", "vpn", "smtp", "remote",
                 "test", "beta", "db", "cdn", "static", "auth",
                 "login", "dashboard"]
        return self.scan(domain, custom_wordlist=top20)
