"""
Chhoti Don - PE Analyzer
Advanced Windows PE (Portable Executable) analysis engine.
Analyzes imports, exports, sections, headers, packers,
digital signatures, and malware indicators.
Phase 2.2 - Full Upgrade
"""

import os
import math
import time
import datetime
import hashlib
from typing import Dict, List, Optional, Tuple
from collections import Counter

# ==================================================
# 🎯 SUSPICIOUS INDICATOR DATABASES
# ==================================================

SUSPICIOUS_IMPORTS = {
    "process_injection": [
        "CreateRemoteThread", "CreateRemoteThreadEx",
        "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "VirtualProtectEx",
        "WriteProcessMemory", "ReadProcessMemory",
        "NtCreateThreadEx", "RtlCreateUserThread",
        "QueueUserAPC", "SetThreadContext", "GetThreadContext",
        "OpenProcess", "NtOpenProcess",
        "MapViewOfFile", "CreateFileMapping",
        "NtMapViewOfSection", "NtUnmapViewOfSection",
        "ZwCreateSection", "NtWriteVirtualMemory",
    ],
    "anti_analysis": [
        "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
        "NtQueryInformationProcess", "OutputDebugString",
        "GetTickCount", "QueryPerformanceCounter",
        "FindWindow", "GetForegroundWindow",
        "GetSystemInfo", "GlobalMemoryStatusEx",
        "CreateToolhelp32Snapshot", "Process32First",
        "EnumProcesses", "NtDelayExecution",
    ],
    "privilege_escalation": [
        "AdjustTokenPrivileges", "LookupPrivilegeValue",
        "OpenProcessToken", "OpenThreadToken",
        "ImpersonateLoggedOnUser", "DuplicateToken",
        "SetTokenInformation", "CreateProcessWithToken",
        "LogonUser", "CreateProcessAsUser",
    ],
    "credential_theft": [
        "CryptUnprotectData", "CryptProtectData",
        "CredEnumerate", "CredRead", "CredWrite",
        "SamQueryInformationUser", "SamOpenUser",
        "LsaRetrievePrivateData", "LsaOpenPolicy",
        "CertOpenStore", "CertFindCertificateInStore",
    ],
    "network": [
        "WSAStartup", "socket", "connect", "bind", "recv", "send",
        "InternetOpen", "InternetConnect", "HttpOpenRequest",
        "HttpSendRequest", "InternetReadFile",
        "URLDownloadToFile", "WinHttpOpen",
        "WinHttpSendRequest", "WinHttpReceiveResponse",
        "GetAddrInfo", "gethostbyname",
    ],
    "persistence": [
        "RegSetValueEx", "RegCreateKeyEx", "RegOpenKeyEx",
        "CreateService", "OpenService", "StartService",
        "SetWindowsHookEx", "RegisterHotKey",
        "WritePrivateProfileString",
    ],
    "ransomware": [
        "CryptGenRandom", "CryptAcquireContext",
        "CryptCreateHash", "CryptEncrypt", "CryptDecrypt",
        "BCryptEncrypt", "BCryptDecrypt",
        "BCryptGenerateSymmetricKey", "BCryptOpenAlgorithmProvider",
    ],
    "shellcode": [
        "VirtualAlloc", "HeapAlloc", "LocalAlloc",
        "RtlMoveMemory", "memcpy",
        "WinExec", "ShellExecute", "CreateProcess",
    ],
}

# Known packer signatures (section names)
KNOWN_PACKERS = {
    "UPX": ["UPX0", "UPX1", "UPX2"],
    "Themida": [".themida", ".winlicence"],
    "VMProtect": [".vmp0", ".vmp1", ".vmp2"],
    "MPRESS": [".MPRESS1", ".MPRESS2"],
    "ASPack": [".aspack", ".adata"],
    "PECompact": ["PEC2", "PEC2TO"],
    "Enigma": [".enigma1", ".enigma2"],
    "Obsidium": [".obs"],
}

# PE Characteristics flags
PE_CHARACTERISTICS = {
    0x0001: "RELOCS_STRIPPED",
    0x0002: "EXECUTABLE_IMAGE",
    0x0004: "LINE_NUMS_STRIPPED",
    0x0008: "LOCAL_SYMS_STRIPPED",
    0x0020: "LARGE_ADDRESS_AWARE",
    0x0100: "32BIT_MACHINE",
    0x0200: "DEBUG_STRIPPED",
    0x2000: "DLL",
}

# DLL Characteristics
DLL_CHARACTERISTICS = {
    0x0040: "DYNAMIC_BASE (ASLR)",
    0x0100: "NX_COMPAT (DEP)",
    0x0400: "NO_SEH",
    0x0800: "NO_BIND",
    0x4000: "WDM_DRIVER",
    0x8000: "TERMINAL_SERVER_AWARE",
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def analyze_pe(file_path: str) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Complete PE analysis with all features.
    """
    analyzer = PEAnalyzer()
    return analyzer.analyze(file_path)


# ==================================================
# 🧠 PE ANALYZER CLASS
# ==================================================

class PEAnalyzer:
    """
    Advanced PE File Analysis Engine.
    Complete static analysis for malware research.
    """

    def __init__(self):
        self.pe = None

    # ==================================================
    # 🔍 Main Analysis
    # ==================================================
    def analyze(self, file_path: str) -> Dict:
        """
        Complete PE file analysis.

        Args:
            file_path: Path to PE file

        Returns:
            Complete analysis result
        """
        start_time = time.time()

        # File checks
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        if not os.path.isfile(file_path):
            return {"status": "error", "message": "Path is not a file"}

        file_size = os.path.getsize(file_path)

        # pefile import
        try:
            import pefile
        except ImportError:
            return {
                "status": "error",
                "message": "pefile not installed. Run: pip install pefile"
            }

        try:
            pe = pefile.PE(file_path, fast_load=False)
        except pefile.PEFormatError as e:
            return {"status": "error", "message": f"Not a valid PE file: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

        try:
            # Core analysis
            file_hashes = self._calculate_hashes(file_path)
            headers = self._analyze_headers(pe)
            imports = self._analyze_imports(pe)
            exports = self._analyze_exports(pe)
            sections = self._analyze_sections(pe)
            resources = self._analyze_resources(pe)
            strings = self._extract_pe_strings(file_path)
            debug_info = self._analyze_debug(pe)
            tls = self._analyze_tls(pe)
            overlay = self._analyze_overlay(pe, file_path)
            rich_header = self._analyze_rich_header(pe)

            # Intelligence
            packer = self._detect_packer(sections, pe)
            security_features = self._analyze_security_features(pe)
            suspicious = self._flag_suspicious(imports, sections, strings)
            malware_indicators = self._assess_malware_indicators(
                imports["all_imports"], sections, strings, suspicious
            )
            mitre = self._map_to_mitre(suspicious)
            verdict = self._calculate_verdict(malware_indicators)

        finally:
            try:
                pe.close()
            except Exception:
                pass

        return {
            "status": "success",
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": file_size,
            "file_size_human": self._format_size(file_size),
            "timestamp": datetime.datetime.utcnow().isoformat(),

            # Hashes
            "hashes": file_hashes,
            "md5": file_hashes.get("md5"),
            "sha256": file_hashes.get("sha256"),

            # PE Structure
            "headers": headers,
            "imports": imports["all_imports"],  # backward compat
            "import_analysis": imports,
            "exports": exports,
            "sections": sections,
            "resources": resources,
            "debug_info": debug_info,
            "tls_callbacks": tls,
            "overlay": overlay,
            "rich_header": rich_header,

            # Intelligence
            "metadata": headers.get("metadata", {}),  # backward compat
            "packer_detected": packer,
            "security_features": security_features,
            "suspicious_indicators": suspicious,
            "malware_indicators": malware_indicators,
            "strings_sample": strings[:50],
            "mitre_techniques": mitre,
            "verdict": verdict,

            "analysis_time_sec": round(time.time() - start_time, 3),
        }

    # ==================================================
    # #️⃣ Hash Calculation
    # ==================================================
    def _calculate_hashes(self, file_path: str) -> Dict:
        """Multiple hashes calculate karo."""
        hashers = {
            "md5": hashlib.md5(),
            "sha1": hashlib.sha1(),
            "sha256": hashlib.sha256(),
        }
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    for h in hashers.values():
                        h.update(chunk)
            return {k: v.hexdigest() for k, v in hashers.items()}
        except Exception:
            return {}

    # ==================================================
    # 📋 Header Analysis
    # ==================================================
    def _analyze_headers(self, pe) -> Dict:
        """PE headers analyze karo."""
        result = {
            "metadata": {},
            "file_header": {},
            "optional_header": {},
            "characteristics": [],
            "dll_characteristics": [],
        }

        try:
            # DOS Header
            result["dos_header"] = {
                "magic": hex(pe.DOS_HEADER.e_magic),
                "pe_offset": hex(pe.DOS_HEADER.e_lfanew),
            }

            # File Header
            fh = pe.FILE_HEADER
            machine_map = {
                0x014c: "x86 (32-bit)",
                0x8664: "x64 (64-bit)",
                0x01c4: "ARM Thumb-2",
                0xaa64: "ARM64",
            }
            result["file_header"] = {
                "machine": machine_map.get(fh.Machine, hex(fh.Machine)),
                "number_of_sections": fh.NumberOfSections,
                "time_date_stamp": datetime.datetime.fromtimestamp(
                    fh.TimeDateStamp
                ).isoformat() if fh.TimeDateStamp > 0 else "Invalid",
                "characteristics": fh.Characteristics,
            }

            # Characteristics
            for flag, name in PE_CHARACTERISTICS.items():
                if fh.Characteristics & flag:
                    result["characteristics"].append(name)

            # Optional Header
            if hasattr(pe, "OPTIONAL_HEADER"):
                oh = pe.OPTIONAL_HEADER
                result["optional_header"] = {
                    "magic": "PE32+" if oh.Magic == 0x20b else "PE32",
                    "linker_version": f"{oh.MajorLinkerVersion}.{oh.MinorLinkerVersion}",
                    "entry_point": hex(oh.AddressOfEntryPoint),
                    "image_base": hex(oh.ImageBase),
                    "subsystem": self._get_subsystem(oh.Subsystem),
                    "size_of_image": oh.SizeOfImage,
                    "size_of_headers": oh.SizeOfHeaders,
                    "checksum": hex(oh.CheckSum),
                    "os_version": f"{oh.MajorOperatingSystemVersion}.{oh.MinorOperatingSystemVersion}",
                }

                # DLL Characteristics
                for flag, name in DLL_CHARACTERISTICS.items():
                    if oh.DllCharacteristics & flag:
                        result["dll_characteristics"].append(name)

                # Backward compat metadata
                result["metadata"] = {
                    "entry_point": hex(oh.AddressOfEntryPoint),
                    "image_base": hex(oh.ImageBase),
                }

        except Exception as e:
            result["error"] = str(e)

        return result

    # ==================================================
    # 📥 Import Analysis (PRESERVED + UPGRADED)
    # ==================================================
    def _analyze_imports(self, pe) -> Dict:
        """Import directory analyze karo."""
        all_imports = []
        import_set = set()
        dll_imports = {}
        suspicious_found = {}

        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                try:
                    dll_name = entry.dll.decode(errors="ignore") if entry.dll else "unknown"
                except Exception:
                    dll_name = "unknown"

                dll_funcs = []

                for imp in entry.imports:
                    if imp.name:
                        try:
                            name = imp.name.decode(errors="ignore")
                        except Exception:
                            name = str(imp.name)

                        if name not in import_set:
                            import_set.add(name)
                            all_imports.append(name)

                        dll_funcs.append({
                            "name": name,
                            "address": hex(imp.address) if imp.address else None,
                            "ordinal": imp.ordinal,
                        })

                        # Suspicious check
                        for category, api_list in SUSPICIOUS_IMPORTS.items():
                            if name in api_list:
                                if category not in suspicious_found:
                                    suspicious_found[category] = []
                                if name not in suspicious_found[category]:
                                    suspicious_found[category].append(name)

                dll_imports[dll_name] = dll_funcs

        return {
            "all_imports": all_imports,
            "dll_imports": dll_imports,
            "total_imports": len(all_imports),
            "total_dlls": len(dll_imports),
            "suspicious_by_category": suspicious_found,
        }

    # ==================================================
    # 📤 Export Analysis
    # ==================================================
    def _analyze_exports(self, pe) -> Dict:
        """Export directory analyze karo."""
        exports = []

        if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                name = None
                if exp.name:
                    try:
                        name = exp.name.decode(errors="ignore")
                    except Exception:
                        pass

                exports.append({
                    "name": name,
                    "ordinal": exp.ordinal,
                    "address": hex(exp.address) if exp.address else None,
                })

        return {
            "exports": exports,
            "total_exports": len(exports),
        }

    # ==================================================
    # 📁 Section Analysis
    # ==================================================
    def _analyze_sections(self, pe) -> List[Dict]:
        """PE sections analyze karo."""
        sections = []

        for section in pe.sections:
            try:
                name = section.Name.decode(errors="ignore").strip("\x00")
            except Exception:
                name = "unknown"

            raw_size = section.SizeOfRawData
            virt_size = section.Misc_VirtualSize

            # Entropy
            entropy = 0
            try:
                data = section.get_data()
                entropy = self._calculate_entropy(data)
            except Exception:
                pass

            # Flags
            flags = []
            chars = section.Characteristics
            if chars & 0x20000000:
                flags.append("EXECUTE")
            if chars & 0x40000000:
                flags.append("READ")
            if chars & 0x80000000:
                flags.append("WRITE")

            # Anomalies
            anomalies = []
            if entropy > 7.0:
                anomalies.append(f"High entropy ({entropy:.2f}) — packed/encrypted")
            if "EXECUTE" in flags and "WRITE" in flags:
                anomalies.append("Executable + Writable — code injection risk")
            if virt_size > 0 and raw_size > 0 and virt_size / raw_size > 10:
                anomalies.append("Abnormal size ratio — possible unpacking stub")
            if raw_size == 0 and virt_size > 0:
                anomalies.append("Empty raw section — runtime unpacking")

            sections.append({
                "name": name,
                "virtual_address": hex(section.VirtualAddress),
                "virtual_size": virt_size,
                "raw_size": raw_size,
                "entropy": round(entropy, 4),
                "flags": flags,
                "characteristics": hex(chars),
                "anomalies": anomalies,
                "md5": hashlib.md5(section.get_data()).hexdigest() if raw_size > 0 else None,
            })

        return sections

    # ==================================================
    # 🗂️ Resource Analysis
    # ==================================================
    def _analyze_resources(self, pe) -> Dict:
        """PE resources analyze karo."""
        resources = []
        total_size = 0

        if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
            try:
                for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                    for resource_id in resource_type.directory.entries:
                        for resource_lang in resource_id.directory.entries:
                            data = pe.get_data(
                                resource_lang.data.struct.OffsetToData,
                                resource_lang.data.struct.Size
                            )
                            size = resource_lang.data.struct.Size
                            total_size += size

                            entropy = self._calculate_entropy(data) if data else 0

                            resources.append({
                                "type": str(resource_type.id),
                                "size": size,
                                "entropy": round(entropy, 4),
                                "suspicious": entropy > 7.0,
                            })
            except Exception:
                pass

        return {
            "resources": resources[:20],
            "total_resources": len(resources),
            "total_size": total_size,
            "suspicious_resources": [r for r in resources if r.get("suspicious")],
        }

    # ==================================================
    # 🔤 String Extraction
    # ==================================================
    def _extract_pe_strings(self, file_path: str) -> List[str]:
        """Meaningful strings extract karo."""
        import re
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            # ASCII strings
            ascii_strings = re.findall(rb"[ -~]{5,}", data)
            # Unicode strings
            unicode_strings = re.findall(rb"(?:[ -~]\x00){5,}", data)

            decoded = []
            for s in ascii_strings[:200]:
                decoded.append(s.decode(errors="ignore"))

            for s in unicode_strings[:50]:
                decoded.append(s.decode("utf-16-le", errors="ignore"))

            # Filter interesting strings
            interesting = [
                s for s in decoded
                if any(kw in s.lower() for kw in [
                    "http", "cmd", "powershell", "reg", "system",
                    "password", "encrypt", "decrypt", "token",
                    "inject", "hook", "download", "upload",
                    ".exe", ".dll", ".bat", "\\\\", "://",
                ])
            ]

            return interesting[:100]

        except Exception:
            return []

    # ==================================================
    # 🔍 Debug Info
    # ==================================================
    def _analyze_debug(self, pe) -> Dict:
        """Debug information analyze karo."""
        debug_info = {}

        if hasattr(pe, "DIRECTORY_ENTRY_DEBUG"):
            for dbg in pe.DIRECTORY_ENTRY_DEBUG:
                try:
                    if hasattr(dbg.entry, "PdbFileName"):
                        pdb = dbg.entry.PdbFileName.decode(errors="ignore").rstrip("\x00")
                        debug_info["pdb_path"] = pdb
                        # Extract username from PDB path
                        import re
                        user_match = re.search(r"[Uu]sers\\([^\\]+)\\", pdb)
                        if user_match:
                            debug_info["possible_username"] = user_match.group(1)
                except Exception:
                    pass

        return debug_info

    # ==================================================
    # 🔒 TLS Callbacks
    # ==================================================
    def _analyze_tls(self, pe) -> List[str]:
        """TLS callbacks detect karo — anti-debugging technique."""
        callbacks = []

        if hasattr(pe, "DIRECTORY_ENTRY_TLS"):
            try:
                tls = pe.DIRECTORY_ENTRY_TLS.struct
                if hasattr(tls, "AddressOfCallBacks"):
                    callbacks.append(hex(tls.AddressOfCallBacks))
            except Exception:
                pass

        return callbacks

    # ==================================================
    # 📎 Overlay Analysis
    # ==================================================
    def _analyze_overlay(self, pe, file_path: str) -> Dict:
        """PE overlay analyze karo — data appended after PE."""
        try:
            overlay_offset = pe.get_overlay_data_start_offset()
            if overlay_offset:
                file_size = os.path.getsize(file_path)
                overlay_size = file_size - overlay_offset

                with open(file_path, "rb") as f:
                    f.seek(overlay_offset)
                    overlay_data = f.read(1024)

                entropy = self._calculate_entropy(overlay_data)

                return {
                    "has_overlay": True,
                    "offset": overlay_offset,
                    "size": overlay_size,
                    "entropy": round(entropy, 4),
                    "suspicious": entropy > 7.0,
                    "description": "High entropy overlay — possible embedded file" if entropy > 7.0
                                  else "Overlay data detected",
                }
        except Exception:
            pass

        return {"has_overlay": False}

    # ==================================================
    # 🔧 Rich Header Analysis
    # ==================================================
    def _analyze_rich_header(self, pe) -> Dict:
        """Rich header analyze karo — compiler fingerprinting."""
        try:
            if hasattr(pe, "RICH_HEADER"):
                return {
                    "present": True,
                    "checksum": hex(pe.RICH_HEADER.checksum),
                    "values": pe.RICH_HEADER.values[:10] if pe.RICH_HEADER.values else [],
                }
        except Exception:
            pass
        return {"present": False}

    # ==================================================
    # 📦 Packer Detection
    # ==================================================
    def _detect_packer(self, sections: List[Dict], pe) -> Dict:
        """Known packers detect karo."""
        detected = []
        section_names = [s["name"] for s in sections]

        for packer, signatures in KNOWN_PACKERS.items():
            for sig in signatures:
                if sig in section_names:
                    detected.append({
                        "packer": packer,
                        "signature": sig,
                        "confidence": "high",
                    })
                    break

        # Entropy-based detection
        high_entropy_sections = [s for s in sections if s["entropy"] > 7.2]
        if high_entropy_sections and not detected:
            detected.append({
                "packer": "Unknown Packer",
                "signature": f"High entropy sections: {[s['name'] for s in high_entropy_sections]}",
                "confidence": "medium",
            })

        return {
            "packed": len(detected) > 0,
            "detections": detected,
        }

    # ==================================================
    # 🛡️ Security Features
    # ==================================================
    def _analyze_security_features(self, pe) -> Dict:
        """Security mitigations analyze karo."""
        features = {
            "aslr": False,
            "dep_nx": False,
            "seh": True,
            "cfg": False,
            "authenticode": False,
        }

        try:
            oh = pe.OPTIONAL_HEADER
            dll_chars = oh.DllCharacteristics

            features["aslr"] = bool(dll_chars & 0x0040)
            features["dep_nx"] = bool(dll_chars & 0x0100)
            features["seh"] = not bool(dll_chars & 0x0400)
            features["cfg"] = bool(dll_chars & 0x4000)

            # Authenticode check
            if hasattr(pe, "DIRECTORY_ENTRY_SECURITY"):
                features["authenticode"] = True

        except Exception:
            pass

        missing = []
        if not features["aslr"]:
            missing.append("ASLR disabled — exploit easier")
        if not features["dep_nx"]:
            missing.append("DEP/NX disabled — shellcode execution possible")
        if features["seh"]:
            missing.append("SEH present — SEH overwrite attacks possible")

        features["missing_mitigations"] = missing
        features["security_score"] = sum([
            features["aslr"], features["dep_nx"],
            not features["seh"], features["cfg"],
            features["authenticode"]
        ])

        return features

    # ==================================================
    # ⚠️ Suspicious Flagging
    # ==================================================
    def _flag_suspicious(self, imports: Dict, sections: List, strings: List) -> Dict:
        """Suspicious indicators flag karo."""
        flags = {}

        # Import-based
        suspicious_by_cat = imports.get("suspicious_by_category", {})
        for cat, apis in suspicious_by_cat.items():
            if apis:
                flags[cat] = apis

        # Section-based
        section_anomalies = []
        for section in sections:
            if section.get("anomalies"):
                section_anomalies.extend(section["anomalies"])
        if section_anomalies:
            flags["section_anomalies"] = section_anomalies

        # String-based
        suspicious_strings = []
        for s in strings:
            s_lower = s.lower()
            if any(kw in s_lower for kw in ["mimikatz", "hashdump", "lsass", "meterpreter"]):
                suspicious_strings.append(s)
        if suspicious_strings:
            flags["suspicious_strings"] = suspicious_strings[:10]

        return flags

    def _assess_malware_indicators(
        self,
        imports: List,
        sections: List,
        strings: List,
        suspicious: Dict
    ) -> Dict:
        """Malware indicators assess karo."""
        score = 0
        indicators = []

        category_scores = {
            "process_injection": 3,
            "anti_analysis": 2,
            "privilege_escalation": 2,
            "credential_theft": 3,
            "network": 1,
            "persistence": 2,
            "ransomware": 3,
            "shellcode": 2,
            "section_anomalies": 1,
            "suspicious_strings": 2,
        }

        for category, items in suspicious.items():
            if items:
                score += category_scores.get(category, 1)
                indicators.append(f"{category}: {items[:3]}")

        return {
            "score": min(score, 10),
            "indicators": indicators,
            "total_suspicious_categories": len(suspicious),
        }

    def _map_to_mitre(self, suspicious: Dict) -> List[str]:
        """MITRE techniques map karo."""
        techniques = set()
        mitre_map = {
            "process_injection": ["T1055"],
            "anti_analysis": ["T1497", "T1622"],
            "privilege_escalation": ["T1068", "T1134"],
            "credential_theft": ["T1003", "T1552"],
            "network": ["T1071", "T1095"],
            "persistence": ["T1053", "T1543"],
            "ransomware": ["T1486"],
        }
        for cat in suspicious:
            for tech in mitre_map.get(cat, []):
                techniques.add(tech)
        return list(techniques)

    def _calculate_verdict(self, malware_indicators: Dict) -> Dict:
        """Final verdict calculate karo."""
        score = malware_indicators.get("score", 0)

        if score >= 8:
            verdict = "MALICIOUS"
            confidence = "high"
        elif score >= 5:
            verdict = "HIGHLY_SUSPICIOUS"
            confidence = "high"
        elif score >= 3:
            verdict = "SUSPICIOUS"
            confidence = "medium"
        elif score >= 1:
            verdict = "LOW_RISK"
            confidence = "medium"
        else:
            verdict = "LIKELY_BENIGN"
            confidence = "low"

        return {
            "verdict": verdict,
            "score": score,
            "confidence": confidence,
        }

    # ==================================================
    # 🔧 Helpers
    # ==================================================
    def _calculate_entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        freq = Counter(data)
        total = len(data)
        entropy = -sum((c/total) * math.log2(c/total) for c in freq.values())
        return entropy

    def _get_subsystem(self, subsystem: int) -> str:
        subsystems = {
            1: "Native", 2: "Windows GUI", 3: "Windows Console",
            5: "OS/2 Console", 7: "POSIX Console",
            9: "Windows CE GUI", 10: "EFI Application",
        }
        return subsystems.get(subsystem, f"Unknown ({subsystem})")

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
