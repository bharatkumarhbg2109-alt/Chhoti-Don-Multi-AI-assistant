"""
Chhoti Don - IOC Correlator
Advanced Indicator of Compromise correlation engine.
Detects IPs, domains, URLs, hashes, emails, crypto wallets,
C2 patterns, and threat actor TTPs.
Phase 2.2 - Full Upgrade
"""

import re
import time
import datetime
from typing import Dict, List, Tuple

# 🎯 IOC DATABASES

# Known malicious domains/IPs (sample — real world uses threat feeds)
KNOWN_MALICIOUS_DOMAINS = [
    "iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com",  # WannaCry kill switch
    "evil-c2-domain.xyz",
    "malware-distribution.tk",
]

KNOWN_MALICIOUS_IPS = [
    "185.220.101.1",   # Tor exit node
    "194.165.16.4",    # Known C2
]

# Suspicious keywords (PRESERVED + EXPANDED)
DEFAULT_SUSPICIOUS_KEYWORDS = [
    # Command execution
    "cmd.exe", "powershell", "bash -i", "/bin/sh", "wscript",
    "mshta", "regsvr32", "rundll32", "certutil", "bitsadmin",
    # Download/upload
    "wget", "curl", "nc.exe", "netcat", "ncat",
    "invoke-webrequest", "downloadstring", "webclient",
    # C2/Network
    "http://", "https://", "ftp://",
    "reverse shell", "bind shell", "meterpreter",
    "cobalt strike", "cobaltstrike", "empire", "beacon",
    # Credential theft
    "mimikatz", "hashdump", "lsass", "sekurlsa",
    "pass the hash", "kerberoast",
    # Ransomware
    "encrypt", "decrypt", "ransom", "bitcoin", "btc",
    ".locked", ".encrypted", "wannacry",
    # Evasion
    "base64", "obfuscat", "encode", "pack", "compress",
    # Persistence
    "registry", "startup", "autorun", "crontab",
    "schtasks", "at.exe",
    # Exfiltration
    "exfil", "upload", "transfer", "zip", "tar",
]

# IOC regex patterns
IOC_PATTERNS = {
    "ipv4": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    ),
    "ipv4_port": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):(\d{1,5})\b"
    ),
    "domain": re.compile(
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
        r"(?:com|net|org|edu|gov|mil|int|io|co|xyz|tk|ml|ga|cf|pw|ru|cn|"
        r"onion|bit|bz|cc|info|mobi|name|pro|tel|travel|xxx)\b",
        re.IGNORECASE
    ),
    "url": re.compile(
        r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!$&'()*+,;=:@/~#?]*)?",
        re.IGNORECASE
    ),
    "email": re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    ),
    "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
    "sha1": re.compile(r"\b[a-fA-F0-9]{40}\b"),
    "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
    "bitcoin": re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),
    "onion": re.compile(r"\b[a-z2-7]{16,56}\.onion\b", re.IGNORECASE),
    "registry_key": re.compile(
        r"(?:HKEY_LOCAL_MACHINE|HKLM|HKEY_CURRENT_USER|HKCU|"
        r"HKEY_CLASSES_ROOT|HKCR)\\[^\s\"'<>]+",
        re.IGNORECASE
    ),
    "file_path": re.compile(
        r"[A-Za-z]:\\(?:[^\x00\s\"<>|?*:\\\/]+\\)*[^\x00\s\"<>|?*:\\\/]+"
    ),
    "base64": re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})"),
    "cve": re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE),
}

# IOC severity ratings
IOC_SEVERITY = {
    "onion": "critical",
    "bitcoin": "high",
    "sha256": "high",
    "md5": "medium",
    "sha1": "medium",
    "url": "medium",
    "ipv4": "medium",
    "domain": "medium",
    "email": "low",
    "registry_key": "medium",
    "base64": "low",
    "cve": "high",
}

# TTP patterns
TTP_PATTERNS = {
    "T1059.001": ["powershell", "invoke-expression", "iex", "encoded command"],
    "T1059.003": ["cmd.exe", "command.com", "/c ", "cmd /k"],
    "T1105": ["wget", "curl", "downloadfile", "webclient", "bitsadmin"],
    "T1140": ["base64", "certutil -decode", "decode"],
    "T1055": ["process injection", "virtualalloc", "writeprocessmemory"],
    "T1003": ["mimikatz", "lsass", "hashdump", "sekurlsa"],
    "T1486": ["encrypt", "ransomware", ".locked", "bitcoin", "ransom"],
    "T1021": ["psexec", "wmiexec", "pass the hash", "lateral"],
    "T1071": ["beacon", "c2", "checkin", "meterpreter"],
    "T1041": ["exfil", "upload", "transfer data"],
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def correlate_iocs(
    strings_list: List[str],
    suspicious_keywords: List[str] = None,
    deep_analysis: bool = True,
) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Advanced IOC correlation with pattern matching.
    """
    correlator = IOCCorrelator()
    return correlator.correlate(strings_list, suspicious_keywords, deep_analysis)


# ==================================================
# 🧠 IOC CORRELATOR CLASS
# ==================================================

class IOCCorrelator:
    """
    Advanced IOC Correlation Engine.
    Multi-type IOC detection with threat scoring.
    """

    def __init__(self):
        self.ioc_cache = {}

    def correlate(
        self,
        strings_list: List[str],
        custom_keywords: List[str] = None,
        deep_analysis: bool = True,
    ) -> Dict:
        """
        Full IOC correlation analysis.
        """
        start_time = time.time()
        keywords = custom_keywords or DEFAULT_SUSPICIOUS_KEYWORDS

        # Combine all strings
        combined_text = " ".join(str(s) for s in strings_list)

        # Keyword matches (backward compat)
        keyword_matches = self._match_keywords(strings_list, keywords)

        # Pattern-based IOC extraction
        extracted_iocs = {}
        if deep_analysis:
            extracted_iocs = self._extract_ioc_patterns(combined_text)

        # Known IOC lookup
        threat_intel_matches = self._check_threat_intel(extracted_iocs)

        # TTP detection
        ttp_matches = self._detect_ttps(combined_text)

        # Risk scoring
        risk_score, risk_level = self._calculate_risk(
            keyword_matches, extracted_iocs, ttp_matches, threat_intel_matches
        )

        # Unique IOC count
        total_iocs = sum(len(v) for v in extracted_iocs.values()) + len(keyword_matches)

        return {
            # Backward compat
            "ioc_matches": keyword_matches,
            "ioc_risk_score": round(risk_score, 2),

            # Enhanced
            "risk_level": risk_level,
            "extracted_iocs": extracted_iocs,
            "threat_intel_matches": threat_intel_matches,
            "ttp_matches": ttp_matches,
            "total_iocs_found": total_iocs,
            "high_confidence_iocs": self._get_high_confidence(extracted_iocs),
            "analysis_time_sec": round(time.time() - start_time, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _match_keywords(self, strings_list: List[str], keywords: List[str]) -> List[Dict]:
        """Keyword matching — preserved + upgraded."""
        matches = []
        seen = set()

        for s in strings_list:
            s_lower = str(s).lower()
            for keyword in keywords:
                if keyword.lower() in s_lower:
                    key = f"{keyword}:{s[:50]}"
                    if key not in seen:
                        seen.add(key)
                        matches.append({
                            "indicator": keyword,
                            "matched_string": str(s)[:200],
                            "severity": self._keyword_severity(keyword),
                            "category": self._keyword_category(keyword),
                        })

        return matches

    def _extract_ioc_patterns(self, text: str) -> Dict:
        """Regex patterns se IOCs extract karo."""
        results = {}

        for ioc_type, pattern in IOC_PATTERNS.items():
            matches = list(set(pattern.findall(text)))

            # Filter false positives
            if ioc_type == "ipv4":
                matches = [ip for ip in matches if not self._is_private_ip(ip)]
            elif ioc_type == "md5":
                # MD5s mixed in other text often false positives
                matches = matches[:10]

            if matches:
                results[ioc_type] = {
                    "values": matches[:20],
                    "count": len(matches),
                    "severity": IOC_SEVERITY.get(ioc_type, "low"),
                }

        return results

    def _check_threat_intel(self, extracted_iocs: Dict) -> List[Dict]:
        """Known threat intel database check karo."""
        matches = []

        # Check IPs
        ips = extracted_iocs.get("ipv4", {}).get("values", [])
        for ip in ips:
            if ip in KNOWN_MALICIOUS_IPS:
                matches.append({
                    "type": "malicious_ip",
                    "value": ip,
                    "severity": "critical",
                    "source": "threat_intel_db",
                })

        # Check domains
        domains = extracted_iocs.get("domain", {}).get("values", [])
        for domain in domains:
            if domain in KNOWN_MALICIOUS_DOMAINS:
                matches.append({
                    "type": "malicious_domain",
                    "value": domain,
                    "severity": "critical",
                    "source": "threat_intel_db",
                })

        # Onion domains always suspicious
        onions = extracted_iocs.get("onion", {}).get("values", [])
        for onion in onions:
            matches.append({
                "type": "tor_address",
                "value": onion,
                "severity": "high",
                "source": "pattern_match",
                "note": "Tor onion address — possible C2",
            })

        # Bitcoin addresses suspicious in non-financial context
        btc = extracted_iocs.get("bitcoin", {}).get("values", [])
        for addr in btc:
            matches.append({
                "type": "bitcoin_address",
                "value": addr,
                "severity": "high",
                "source": "pattern_match",
                "note": "Possible ransomware payment address",
            })

        return matches

    def _detect_ttps(self, text: str) -> List[Dict]:
        """MITRE ATT&CK TTPs detect karo."""
        text_lower = text.lower()
        detected = []

        for technique_id, indicators in TTP_PATTERNS.items():
            matches = [ind for ind in indicators if ind.lower() in text_lower]
            if matches:
                detected.append({
                    "technique_id": technique_id,
                    "matched_indicators": matches,
                    "confidence": min(len(matches) * 0.25, 0.99),
                })

        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected

    def _calculate_risk(
        self,
        keywords: List[Dict],
        iocs: Dict,
        ttps: List[Dict],
        threat_intel: List[Dict],
    ) -> Tuple[float, str]:
        """Overall IOC risk score calculate karo."""
        score = 0.0

        # Keyword score (backward compat weight preserved)
        score += len(keywords) * 0.4

        # IOC pattern scores
        severity_weights = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}
        for ioc_type, data in iocs.items():
            sev = data.get("severity", "low")
            score += data.get("count", 0) * severity_weights.get(sev, 0.5)

        # TTP score
        for ttp in ttps:
            score += ttp["confidence"] * 2.0

        # Threat intel matches (highest weight)
        for match in threat_intel:
            sev = match.get("severity", "medium")
            score += severity_weights.get(sev, 1.0) * 3.0

        score = round(score, 2)

        if score >= 20:
            level = "CRITICAL"
        elif score >= 12:
            level = "HIGH"
        elif score >= 6:
            level = "MEDIUM"
        elif score >= 2:
            level = "LOW"
        else:
            level = "INFO"

        return score, level

    def _get_high_confidence(self, iocs: Dict) -> List[Dict]:
        """High confidence IOCs filter karo."""
        high_conf = []
        high_severity = {"critical", "high"}

        for ioc_type, data in iocs.items():
            if data.get("severity") in high_severity:
                for val in data.get("values", [])[:5]:
                    high_conf.append({
                        "type": ioc_type,
                        "value": val,
                        "severity": data["severity"],
                    })

        return high_conf[:20]

    def _is_private_ip(self, ip: str) -> bool:
        """Private IP range check."""
        private = ["192.168.", "10.", "172.16.", "127.", "0.0.0.0", "255."]
        return any(ip.startswith(p) for p in private)

    def _keyword_severity(self, keyword: str) -> str:
        """Keyword severity determine karo."""
        critical_kw = ["mimikatz", "meterpreter", "cobaltstrike", "wannacry", "ransomware"]
        high_kw = ["reverse shell", "beacon", "c2", "hashdump", "lsass"]
        medium_kw = ["powershell", "cmd.exe", "base64", "wget", "curl"]

        kw_lower = keyword.lower()
        if any(c in kw_lower for c in critical_kw):
            return "critical"
        elif any(h in kw_lower for h in high_kw):
            return "high"
        elif any(m in kw_lower for m in medium_kw):
            return "medium"
        return "low"

    def _keyword_category(self, keyword: str) -> str:
        """Keyword category determine karo."""
        categories = {
            "execution": ["cmd.exe", "powershell", "bash", "wscript"],
            "network": ["http://", "https://", "wget", "curl", "nc.exe"],
            "credential": ["mimikatz", "hashdump", "lsass", "pass the hash"],
            "c2": ["beacon", "meterpreter", "cobaltstrike", "empire"],
            "ransomware": ["encrypt", "ransom", "bitcoin", "btc"],
            "evasion": ["base64", "obfuscat", "encode"],
        }
        kw_lower = keyword.lower()
        for cat, words in categories.items():
            if any(w in kw_lower for w in words):
                return cat
        return "other"


# ==================================================
# 🔧 STANDALONE FUNCTIONS
# ==================================================

def extract_iocs_from_text(text: str) -> Dict:
    """Text se all IOCs extract karo."""
    correlator = IOCCorrelator()
    return correlator._extract_ioc_patterns(text)


def check_ioc_in_threat_intel(ioc_value: str, ioc_type: str = "auto") -> Dict:
    """Single IOC ko threat intel mein check karo."""
    if ioc_type == "auto":
        for t, pattern in IOC_PATTERNS.items():
            if pattern.match(ioc_value):
                ioc_type = t
                break

    if ioc_value in KNOWN_MALICIOUS_IPS:
        return {"malicious": True, "type": "ip", "confidence": "high"}
    if ioc_value in KNOWN_MALICIOUS_DOMAINS:
        return {"malicious": True, "type": "domain", "confidence": "high"}

    return {"malicious": False, "type": ioc_type, "confidence": "unknown"}
