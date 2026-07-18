"""
Chhoti Don - Strings Extractor
Advanced string extraction and analysis engine.
Extracts ASCII, Unicode, URLs, IPs, emails, crypto keys,
and malware indicators from binary files.
Phase 2.2 - Full Upgrade
"""

import re
import os
import time
import datetime
import math
from typing import Dict, List, Mapping
# ==================================================
# 🎯 PATTERN DATABASES
# ==================================================

# Regex patterns for interesting strings
PATTERNS = {
    "urls": re.compile(
        rb"https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s\"'<>]*)?",
        re.IGNORECASE
    ),
    "ip_addresses": re.compile(
        rb"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{2,5})?\b"
    ),
    "ipv6": re.compile(
        rb"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
    ),
    "emails": re.compile(
        rb"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    ),
    "registry_keys": re.compile(
        rb"(?:HKEY_LOCAL_MACHINE|HKLM|HKEY_CURRENT_USER|HKCU|"
        rb"HKEY_CLASSES_ROOT|HKCR|HKEY_USERS|HKU|SOFTWARE|SYSTEM)"
        rb"(?:\\[^\x00\s\"'<>]{2,})+",
        re.IGNORECASE
    ),
    "file_paths": re.compile(
        rb"[A-Za-z]:\\(?:[^\x00\s\"<>|?*:\\\/]+\\)*[^\x00\s\"<>|?*:\\\/]*",
    ),
    "unix_paths": re.compile(
        rb"(?:/(?:etc|tmp|var|usr|bin|sbin|home|root|proc|sys|dev)"
        rb"(?:/[^\x00\s\"'<>]{1,64})*)",
    ),
    "base64": re.compile(
        rb"(?:[A-Za-z0-9+/]{40,}={0,2})"
    ),
    "hex_strings": re.compile(
        rb"(?:0x)?[0-9a-fA-F]{16,}"
    ),
    "powershell": re.compile(
        rb"(?:powershell|Invoke-|IEX|EncodedCommand|downloadstring|"
        rb"webclient|DownloadFile|bypass|hidden|nop|noni|enc)\b",
        re.IGNORECASE
    ),
    "cmd_commands": re.compile(
        rb"(?:cmd\.exe|command\.com)\s+/[cCkK]\s+[^\x00\n\r\"]{5,}",
        re.IGNORECASE
    ),
    "crypto_keys": re.compile(
        rb"-----BEGIN\s+(?:RSA\s+)?(?:PRIVATE|PUBLIC)\s+KEY-----"
    ),
    "bitcoin_addresses": re.compile(
        rb"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
    ),
    "tor_domains": re.compile(
        rb"[a-z2-7]{16,56}\.onion",
        re.IGNORECASE
    ),
    "mutex_names": re.compile(
        rb"Global\\[A-Za-z0-9_\-]{8,}"
    ),
    "guids": re.compile(
        rb"\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        rb"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}"
    ),
}

# Suspicious keyword patterns
SUSPICIOUS_KEYWORDS = {
    "malware_tools": [
        b"mimikatz", b"meterpreter", b"cobalt", b"empire",
        b"metasploit", b"shellcode", b"payload",
        b"hashdump", b"sekurlsa", b"lsadump",
    ],
    "persistence": [
        b"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        b"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        b"Startup", b"autostart", b"taskschd",
        b"schtasks", b"at.exe",
    ],
    "evasion": [
        b"IsDebuggerPresent", b"VirtualBox", b"VMware",
        b"sandbox", b"wireshark", b"procmon",
        b"SbieDll", b"snxhk", b"api_log",
        b"dir_watch", b"cuckoomon",
    ],
    "network_c2": [
        b"beacon", b"C2", b"command and control",
        b"checkin", b"sleep", b"implant",
        b"reverse shell", b"bind shell",
    ],
    "ransomware": [
        b"encrypt", b"decrypt", b"AES", b"RSA",
        b"bitcoin", b"BTC", b"wallet",
        b"your files", b"ransom", b".locked",
        b"how to recover", b"pay",
    ],
    "credential_theft": [
        b"password", b"passwd", b"credential",
        b"logon", b"SAM", b"NTDS",
        b"kerberos", b"ticket", b"hash",
    ],
    "injection": [
        b"CreateRemoteThread", b"VirtualAllocEx",
        b"WriteProcessMemory", b"NtCreateThreadEx",
        b"RtlCreateUserThread", b"SetThreadContext",
    ],
}

# MITRE mapping for found patterns
PATTERN_MITRE = {
    "malware_tools": ["T1588", "T1059"],
    "persistence": ["T1547", "T1053"],
    "evasion": ["T1497", "T1622"],
    "network_c2": ["T1071", "T1095"],
    "ransomware": ["T1486", "T1140"],
    "credential_theft": ["T1003", "T1552"],
    "injection": ["T1055"],
    "powershell": ["T1059.001"],
    "base64": ["T1027"],
    "crypto_keys": ["T1553"],
    "tor_domains": ["T1090.003"],
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def extract_strings(file_path: str) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Complete string extraction and analysis.
    """
    extractor = StringsExtractor()
    return extractor.extract(file_path)


# ==================================================
# 🧠 STRINGS EXTRACTOR CLASS
# ==================================================

class StringsExtractor:
    """
    Advanced String Extraction and Analysis Engine.
    Extracts and categorizes strings from binary files.
    """

    def __init__(self, min_length: int = 4, max_strings: int = 10000):
        self.min_length = min_length
        self.max_strings = max_strings

    # ==================================================
    # 🔍 Main Extraction
    # ==================================================
    def extract(self, file_path: str, deep_analysis: bool = True) -> Dict:
        """
        Complete string extraction and analysis.

        Args:
            file_path: Path to binary file
            deep_analysis: Run full pattern analysis

        Returns:
            Complete strings analysis result
        """
        start_time = time.time()

        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        file_size = os.path.getsize(file_path)

        try:
            with open(file_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return {"status": "error", "message": str(e)}

        # Extract basic strings
        ascii_strings = self._extract_ascii(data)
        unicode_strings = self._extract_unicode(data)
        all_strings = ascii_strings + unicode_strings
        all_strings_decoded = [s.decode(errors="ignore") for s in all_strings]

        # Pattern extraction
        patterns_found = {}
        if deep_analysis:
            patterns_found = self._extract_patterns(data)

        # Keyword analysis
        keyword_findings = self._analyze_keywords(data)

        # String categorization
        categorized = self._categorize_strings(all_strings_decoded)

        # Entropy analysis
        entropy_data = self._analyze_entropy(data)

        # MITRE mapping
        mitre = self._map_to_mitre(patterns_found, keyword_findings)

        # Interesting strings
        interesting = self._find_interesting(all_strings_decoded)

        # Verdict
        verdict = self._assess_verdict(keyword_findings, patterns_found)

        return {
            "status": "success",
            "file_path": file_path,
            "file_size": file_size,
            "timestamp": datetime.datetime.utcnow().isoformat(),

            # Backward compat
            "strings_sample": all_strings_decoded[:100],

            # Full results
            "total_strings": len(all_strings),
            "ascii_strings": [s.decode(errors="ignore") for s in ascii_strings[:500]],
            "unicode_strings": [s.decode("utf-16-le", errors="ignore") for s in unicode_strings[:100]],
            "interesting_strings": interesting,

            # Pattern results
            "patterns": patterns_found,
            "keyword_findings": keyword_findings,
            "categorized": categorized,

            # Analysis
            "entropy": entropy_data,
            "mitre_techniques": mitre,
            "verdict": verdict,

            "analysis_time_sec": round(time.time() - start_time, 3),
        }

    # ==================================================
    # 🔤 String Extraction
    # ==================================================
    def _extract_ascii(self, data: bytes) -> List[bytes]:
        """ASCII printable strings extract karo."""
        pattern = re.compile(rb"[ -~]{" + str(self.min_length).encode() + rb",}")
        strings = pattern.findall(data)
        return strings[:self.max_strings]

    def _extract_unicode(self, data: bytes) -> List[bytes]:
        """Unicode (UTF-16 LE) strings extract karo."""
        pattern = re.compile(
            rb"(?:[ -~]\x00){" + str(self.min_length).encode() + rb",}"
        )
        raw = pattern.findall(data)
        return raw[:1000]

    # ==================================================
    # 🎯 Pattern Extraction
    # ==================================================
    def _extract_patterns(self, data: bytes) -> Dict:
        """Known patterns extract karo."""
        results = {}

        for pattern_name, pattern in PATTERNS.items():
            matches = pattern.findall(data)
            if matches:
                decoded = []
                for m in matches[:20]:
                    try:
                        decoded.append(m.decode(errors="ignore"))
                    except Exception:
                        pass
                # Deduplicate
                decoded = list(set(decoded))
                results[pattern_name] = {
                    "matches": decoded[:20],
                    "count": len(matches),
                }

        return results

    # ==================================================
    # 🔍 Keyword Analysis
    # ==================================================
    def _analyze_keywords(self, data: bytes) -> Dict:
        """Suspicious keyword groups detect karo."""
        findings = {}
        data_lower = data.lower()

        for category, keywords in SUSPICIOUS_KEYWORDS.items():
            matched = []
            for kw in keywords:
                if kw.lower() in data_lower:
                    matched.append(kw.decode(errors="ignore"))

            if matched:
                findings[category] = {
                    "matched": matched,
                    "count": len(matched),
                    "severity": self._get_category_severity(category),
                }

        return findings

    # ==================================================
    # 📊 String Categorization
    # ==================================================
    def _categorize_strings(self, strings: List[str]) -> Dict:
        """Strings ko categories mein sort karo."""
        categories = {
            "executables": [],
            "dlls": [],
            "registry": [],
            "network": [],
            "file_paths": [],
            "error_messages": [],
            "version_info": [],
            "crypto": [],
            "other": [],
        }

        for s in strings[:2000]:
            s_lower = s.lower()
            if s.endswith((".exe", ".bat", ".com", ".scr")):
                categories["executables"].append(s)
            elif s.endswith(".dll"):
                categories["dlls"].append(s)
            elif s.startswith(("HKEY", "HKLM", "HKCU", "SOFTWARE\\")):
                categories["registry"].append(s)
            elif s.startswith(("http://", "https://", "ftp://")) or re.match(r"\d+\.\d+\.\d+\.\d+", s):
                categories["network"].append(s)
            elif re.match(r"[A-Za-z]:\\", s) or s.startswith("/"):
                categories["file_paths"].append(s)
            elif any(kw in s_lower for kw in ["error", "failed", "invalid", "warning"]):
                categories["error_messages"].append(s)
            elif re.match(r"\d+\.\d+\.\d+\.\d+", s) and not s.count(".") == 3:
                categories["version_info"].append(s)
            elif any(kw in s_lower for kw in ["aes", "rsa", "key", "encrypt", "decrypt"]):
                categories["crypto"].append(s)

        # Limit each category
        return {k: v[:20] for k, v in categories.items() if v}

    # ==================================================
    # 📊 Entropy Analysis
    # ==================================================
    def _analyze_entropy(self, data: bytes) -> Dict:
        """Overall file entropy analyze karo."""
        if not data:
            return {"entropy": 0, "assessment": "empty"}

        sample = data[:65536]
        freq = Counter(sample)
        total = len(sample)

        entropy = -sum(
            (c/total) * math.log2(c/total)
            for c in freq.values()
        )
        entropy = round(entropy, 4)

        if entropy > 7.5:
            assessment = "Very High — heavily packed/encrypted"
        elif entropy > 7.0:
            assessment = "High — possibly packed/obfuscated"
        elif entropy > 6.0:
            assessment = "Medium-High — some compression"
        elif entropy > 4.0:
            assessment = "Normal — typical executable"
        else:
            assessment = "Low — plain data/text"

        return {
            "entropy": entropy,
            "assessment": assessment,
            "suspicious": entropy > 7.0,
        }

    # ==================================================
    # 🌟 Interesting Strings
    # ==================================================
    def _find_interesting(self, strings: List[str]) -> List[Dict]:
        """Most interesting strings filter karo."""
        interesting = []
        seen = set()

        interesting_patterns = [
            (r"https?://\S+", "URL", "medium"),
            (r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?", "IP Address", "medium"),
            (r"[a-z2-7]{16,}\.onion", "Tor Onion Address", "high"),
            (r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}", "Bitcoin Address", "high"),
            (r"[A-Za-z0-9+/]{40,}={0,2}", "Base64 Encoded", "medium"),
            (r"[A-Za-z]:\\[^\s]+", "Windows Path", "low"),
            (r"(?:password|passwd|pwd)\s*[=:]\s*\S+", "Possible Credentials", "critical"),
            (r"(?:api[_-]?key|apikey|secret|token)\s*[=:]\s*\S+", "API Key/Token", "critical"),
        ]

        for s in strings[:5000]:
            if s in seen or len(s) < 5:
                continue

            for pattern, category, severity in interesting_patterns:
                if re.search(pattern, s, re.IGNORECASE):
                    interesting.append({
                        "string": s[:200],
                        "category": category,
                        "severity": severity,
                    })
                    seen.add(s)
                    break

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        interesting.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return interesting[:100]

    # ==================================================
    # 🎯 MITRE Mapping
    # ==================================================
    def _map_to_mitre(self, patterns: Dict, keywords: Dict) -> List[str]:
        """MITRE techniques map karo."""
        techniques = set()

        for pattern_name in patterns:
            for tech in PATTERN_MITRE.get(pattern_name, []):
                techniques.add(tech)

        for keyword_cat in keywords:
            for tech in PATTERN_MITRE.get(keyword_cat, []):
                techniques.add(tech)

        return list(techniques)

    # ==================================================
    # ⚖️ Verdict
    # ==================================================
    def _assess_verdict(self, keywords: Dict, patterns: Dict) -> Dict:
        """String analysis se verdict generate karo."""
        score = 0

        severity_scores = {
            "critical": 4, "high": 3, "medium": 2, "low": 1
        }

        for cat_data in keywords.values():
            sev = cat_data.get("severity", "low")
            score += severity_scores.get(sev, 1) * cat_data.get("count", 1)

        # Pattern bonuses
        if "tor_domains" in patterns:
            score += 5
        if "bitcoin_addresses" in patterns:
            score += 3
        if "crypto_keys" in patterns:
            score += 3
        if "powershell" in patterns:
            score += 2

        score = min(score, 10)

        if score >= 7:
            verdict = "HIGHLY_SUSPICIOUS"
        elif score >= 4:
            verdict = "SUSPICIOUS"
        elif score >= 2:
            verdict = "LOW_RISK"
        else:
            verdict = "LIKELY_BENIGN"

        return {
            "verdict": verdict,
            "score": score,
            "malware_indicators_found": len(keywords),
        }

    def _get_category_severity(self, category: str) -> str:
        """Category ke liye severity."""
        severity_map = {
            "malware_tools": "critical",
            "injection": "critical",
            "credential_theft": "critical",
            "ransomware": "critical",
            "persistence": "high",
            "network_c2": "high",
            "evasion": "medium",
        }
        return severity_map.get(category, "medium")
