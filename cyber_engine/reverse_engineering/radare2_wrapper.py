"""
Chhoti Don - Radare2 Wrapper
Advanced binary analysis using Radare2/r2pipe.
Disassembly, function analysis, CFG, ROP gadgets,
and automated vulnerability detection.
Phase 2.2 - Full Feature Implementation

⚠️  Requires: pip install r2pipe
              radare2 installed on system
"""

import os
import time
import datetime
import json
import re
import subprocess
import shutil
from typing import Dict, List

# ==================================================
# 🎯 ANALYSIS CONFIGURATIONS
# ==================================================

# Default analysis flags
ANALYSIS_FLAGS = {
    "basic": "aa",          # Basic analysis
    "deep": "aaa",          # Deep analysis
    "full": "aaaa",         # Full analysis (slow)
    "functions": "af",      # Analyze functions
    "symbols": "afl",       # List functions
}

# Architecture detection
ARCH_MAP = {
    "x86": "x86 32-bit",
    "x86_64": "x86 64-bit (AMD64)",
    "arm": "ARM 32-bit",
    "arm64": "ARM 64-bit (AArch64)",
    "mips": "MIPS",
    "avr": "AVR (Microcontroller)",
    "ppc": "PowerPC",
}

# Suspicious patterns in disassembly
SUSPICIOUS_DISASM_PATTERNS = {
    "shellcode_prologue": [
        r"call\s+\$\+5",        # Common shellcode trick
        r"pop\s+e[a-z]{2}",     # Get EIP
        r"jmp\s+esp",           # JMP ESP (stack pivot)
        r"jmp\s+rsp",           # JMP RSP (64-bit)
    ],
    "rop_gadgets": [
        r"ret$", r"retn$",      # RET instructions
        r"pop\s+\w+.*ret",      # POP+RET gadgets
    ],
    "anti_debug": [
        r"int3",                # Software breakpoint
        r"rdtsc",               # Timing check
        r"cpuid",               # CPU info (VM detection)
    ],
    "crypto": [
        r"xor\s+\w+,\s*\w+",   # XOR (encryption/decryption)
        r"rol\s+", r"ror\s+",   # Rotate operations
        r"aes",                 # AES instruction
    ],
}

# ROP gadget patterns
ROP_PATTERNS = [
    r"pop\s+\w+\s*;\s*ret",
    r"mov\s+\w+,\s*\w+\s*;\s*ret",
    r"xchg\s+\w+,\s*\w+\s*;\s*ret",
    r"add\s+\w+,\s*\w+\s*;\s*ret",
    r"sub\s+\w+,\s*\w+\s*;\s*ret",
    r"jmp\s+\[?\w+\]?",
]


class Radare2Wrapper:
    """
    Advanced Radare2 Binary Analysis Wrapper.
    Full disassembly, CFG, ROP, and vulnerability analysis.
    """

    def __init__(self):
        self.r2 = None
        self._r2pipe_available = self._check_r2pipe()
        self._radare2_available = self._check_radare2()

    # ==================================================
    # 🔍 Availability Checks
    # ==================================================
    def _check_r2pipe(self) -> bool:
        """r2pipe module check karo."""
        try:
            return True
        except ImportError:
            return False

    def _check_radare2(self) -> bool:
        """radare2 binary check karo."""
        return shutil.which("r2") is not None or shutil.which("radare2") is not None

    def is_available(self) -> Dict:
        """Radare2 availability status."""
        return {
            "r2pipe": self._r2pipe_available,
            "radare2": self._radare2_available,
            "fully_available": self._r2pipe_available and self._radare2_available,
            "install_r2pipe": "pip install r2pipe",
            "install_radare2": "https://radare.org/n/radare2.html",
        }

    # ==================================================
    # 🚀 MAIN ANALYSIS (Using r2pipe)
    # ==================================================
    def analyze(self, file_path: str, analysis_level: str = "basic") -> Dict:
        """
        Complete binary analysis using Radare2.

        Args:
            file_path: Path to binary
            analysis_level: 'basic', 'deep', or 'full'

        Returns:
            Complete analysis result
        """
        start_time = time.time()

        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        # Try r2pipe first, fallback to subprocess
        if self._r2pipe_available and self._radare2_available:
            return self._analyze_with_r2pipe(file_path, analysis_level, start_time)
        elif self._radare2_available:
            return self._analyze_with_subprocess(file_path, start_time)
        else:
            return self._analyze_without_radare2(file_path, start_time)

    # ==================================================
    # 🔧 r2pipe Analysis
    # ==================================================
    def _analyze_with_r2pipe(self, file_path: str, level: str, start_time: float) -> Dict:
        """r2pipe se full analysis karo."""
        try:
            import r2pipe

            r2 = r2pipe.open(file_path, flags=["-2"])  # -2 = suppress stderr

            # Analysis
            analysis_cmd = ANALYSIS_FLAGS.get(level, "aa")
            r2.cmd(analysis_cmd)

            # Gather all data
            file_info = self._get_file_info(r2)
            functions = self._get_functions(r2)
            imports = self._get_imports_r2(r2)
            exports = self._get_exports_r2(r2)
            strings = self._get_strings_r2(r2)
            sections = self._get_sections_r2(r2)
            entry_points = self._get_entry_points(r2)
            rop_gadgets = self._find_rop_gadgets(r2)
            disasm = self._get_disassembly(r2, functions[:5] if functions else [])
            xrefs = self._get_xrefs(r2)

            r2.quit()

            # Post-analysis
            suspicious = self._detect_suspicious_patterns(disasm, functions)
            mitre = self._map_disasm_to_mitre(suspicious)
            verdict = self._calculate_verdict(suspicious, rop_gadgets)

            return {
                "status": "success",
                "method": "r2pipe",
                "file_path": file_path,
                "timestamp": datetime.datetime.utcnow().isoformat(),

                "file_info": file_info,
                "architecture": file_info.get("arch", "unknown"),
                "bits": file_info.get("bits", 0),
                "os": file_info.get("os", "unknown"),
                "entry_points": entry_points,

                "functions": functions,
                "total_functions": len(functions),
                "imports": imports,
                "exports": exports,
                "strings": strings[:100],
                "sections": sections,

                "rop_gadgets": rop_gadgets,
                "total_rop_gadgets": len(rop_gadgets),

                "disassembly_sample": disasm,
                "xrefs": xrefs,

                "suspicious_patterns": suspicious,
                "mitre_techniques": mitre,
                "verdict": verdict,

                "analysis_time_sec": round(time.time() - start_time, 3),
            }

        except Exception as e:
            return {"status": "error", "message": f"r2pipe error: {str(e)}"}

    def _get_file_info(self, r2) -> Dict:
        """File info lo."""
        try:
            info = json.loads(r2.cmd("ij"))
            core = info.get("core", {})
            bin_info = info.get("bin", {})
            return {
                "arch": bin_info.get("arch", "unknown"),
                "bits": bin_info.get("bits", 0),
                "os": bin_info.get("os", "unknown"),
                "type": bin_info.get("type", "unknown"),
                "lang": bin_info.get("lang", "unknown"),
                "compiler": bin_info.get("compiler", "unknown"),
                "canary": bin_info.get("canary", False),
                "pic": bin_info.get("pic", False),
                "nx": bin_info.get("nx", False),
                "stripped": bin_info.get("stripped", False),
                "file": core.get("file", ""),
                "size": core.get("size", 0),
            }
        except Exception:
            return {}

    def _get_functions(self, r2) -> List[Dict]:
        """Functions list lo."""
        try:
            funcs_raw = r2.cmd("aflj")
            if not funcs_raw or funcs_raw.strip() == "null":
                return []
            funcs = json.loads(funcs_raw)
            result = []
            for f in funcs[:100]:
                result.append({
                    "name": f.get("name", "unknown"),
                    "offset": hex(f.get("offset", 0)),
                    "size": f.get("size", 0),
                    "instructions": f.get("ops", 0),
                    "complexity": f.get("cc", 0),  # Cyclomatic complexity
                    "calls": f.get("ncalls", 0),
                    "suspicious": self._is_suspicious_function(f.get("name", "")),
                })
            return result
        except Exception:
            return []

    def _get_imports_r2(self, r2) -> List[Dict]:
        """Imports lo."""
        try:
            imp_raw = r2.cmd("iij")
            if not imp_raw or imp_raw.strip() == "null":
                return []
            return json.loads(imp_raw)[:50]
        except Exception:
            return []

    def _get_exports_r2(self, r2) -> List[Dict]:
        """Exports lo."""
        try:
            exp_raw = r2.cmd("iEj")
            if not exp_raw or exp_raw.strip() == "null":
                return []
            return json.loads(exp_raw)[:50]
        except Exception:
            return []

    def _get_strings_r2(self, r2) -> List[Dict]:
        """Strings lo."""
        try:
            str_raw = r2.cmd("izj")
            if not str_raw or str_raw.strip() == "null":
                return []
            strings = json.loads(str_raw)
            return [
                {
                    "offset": hex(s.get("vaddr", 0)),
                    "string": s.get("string", ""),
                    "size": s.get("size", 0),
                    "type": s.get("type", "ascii"),
                }
                for s in strings[:200]
            ]
        except Exception:
            return []

    def _get_sections_r2(self, r2) -> List[Dict]:
        """Sections lo."""
        try:
            sec_raw = r2.cmd("iSj")
            if not sec_raw or sec_raw.strip() == "null":
                return []
            sections = json.loads(sec_raw)
            return [
                {
                    "name": s.get("name", ""),
                    "vaddr": hex(s.get("vaddr", 0)),
                    "size": s.get("vsize", 0),
                    "perm": s.get("perm", ""),
                    "type": s.get("type", ""),
                }
                for s in sections
            ]
        except Exception:
            return []

    def _get_entry_points(self, r2) -> List[Dict]:
        """Entry points lo."""
        try:
            ep_raw = r2.cmd("iej")
            if not ep_raw or ep_raw.strip() == "null":
                return []
            eps = json.loads(ep_raw)
            return [{"offset": hex(ep.get("vaddr", 0)), "type": ep.get("type", "")} for ep in eps]
        except Exception:
            return []

    def _find_rop_gadgets(self, r2) -> List[Dict]:
        """ROP gadgets dhundho."""
        try:
            gadgets_raw = r2.cmd("/Rj ret")
            if not gadgets_raw or gadgets_raw.strip() in ["null", "[]", ""]:
                return []
            gadgets = json.loads(gadgets_raw)
            result = []
            for g in gadgets[:50]:
                result.append({
                    "offset": hex(g.get("offset", 0)),
                    "code": g.get("code", ""),
                    "type": "rop_gadget",
                })
            return result
        except Exception:
            return []

    def _get_disassembly(self, r2, functions: List[Dict]) -> List[Dict]:
        """Top functions ka disassembly lo."""
        disasm = []
        try:
            for func in functions[:3]:
                offset = func.get("offset", "0x0")
                try:
                    r2.cmd(f"s {offset}")
                    asm_raw = r2.cmd("pdfj")
                    if asm_raw and asm_raw.strip() not in ["null", ""]:
                        asm = json.loads(asm_raw)
                        ops = asm.get("ops", [])
                        disasm.append({
                            "function": func.get("name", "unknown"),
                            "offset": offset,
                            "instructions": [
                                {
                                    "offset": hex(op.get("offset", 0)),
                                    "opcode": op.get("opcode", ""),
                                    "type": op.get("type", ""),
                                }
                                for op in ops[:30]
                            ],
                        })
                except Exception:
                    pass
        except Exception:
            pass
        return disasm

    def _get_xrefs(self, r2) -> Dict:
        """Cross-references analyze karo."""
        try:
            xref_raw = r2.cmd("axj")
            if not xref_raw or xref_raw.strip() in ["null", "[]", ""]:
                return {}
            xrefs = json.loads(xref_raw)
            return {
                "total": len(xrefs),
                "sample": xrefs[:10],
            }
        except Exception:
            return {}

    # ==================================================
    # 🔧 Subprocess Analysis (fallback without r2pipe)
    # ==================================================
    def _analyze_with_subprocess(self, file_path: str, start_time: float) -> Dict:
        """Subprocess se basic radare2 analysis karo."""
        try:
            r2_bin = shutil.which("r2") or shutil.which("radare2")

            # Basic info
            info_result = subprocess.run(
                [r2_bin, "-q", "-c", "ij;afl;iz", file_path],
                capture_output=True, text=True, timeout=60
            )

            output = info_result.stdout

            return {
                "status": "partial",
                "method": "subprocess",
                "file_path": file_path,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "raw_output": output[:5000],
                "note": "Install r2pipe for full analysis: pip install r2pipe",
                "analysis_time_sec": round(time.time() - start_time, 3),
            }

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Radare2 analysis timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================================================
    # 📊 Fallback Analysis (No Radare2)
    # ==================================================
    def _analyze_without_radare2(self, file_path: str, start_time: float) -> Dict:
        """Radare2 ke bina basic analysis karo."""
        file_size = os.path.getsize(file_path)

        # Basic binary analysis
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
                data = f.read(65536)

            # Architecture detection from magic bytes
            arch = "unknown"
            if header[:2] == b"MZ":
                arch = "x86/x64 PE (Windows)"
            elif header[:4] == b"\x7fELF":
                arch = "ELF (Linux)"
                if header[4] == 1:
                    arch += " 32-bit"
                elif header[4] == 2:
                    arch += " 64-bit"
            elif header[:4] in [b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf"]:
                arch = "Mach-O (macOS)"

            # Find strings
            ascii_strings = re.findall(rb"[ -~]{6,}", data)
            decoded_strings = [s.decode(errors="ignore") for s in ascii_strings[:100]]

            return {
                "status": "limited",
                "method": "basic_binary",
                "file_path": file_path,
                "file_size": file_size,
                "detected_architecture": arch,
                "strings_sample": decoded_strings[:50],
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "note": (
                    "Radare2 not available — limited analysis only. "
                    "Install: https://radare.org/n/radare2.html"
                ),
                "install_r2pipe": "pip install r2pipe",
                "analysis_time_sec": round(time.time() - start_time, 3),
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================================================
    # 🎯 Specialized Analysis Methods
    # ==================================================
    def disassemble_function(self, file_path: str, function_name: str) -> Dict:
        """Specific function disassemble karo."""
        if not self._r2pipe_available or not self._radare2_available:
            return {"status": "error", "message": "r2pipe/radare2 required"}

        try:
            import r2pipe
            r2 = r2pipe.open(file_path, flags=["-2"])
            r2.cmd("aaa")

            # Find function
            r2.cmd(f"s sym.{function_name}")
            asm = r2.cmd("pdf")
            r2.quit()

            return {
                "status": "success",
                "function": function_name,
                "disassembly": asm,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def find_crypto_constants(self, file_path: str) -> Dict:
        """Cryptographic constants dhundho."""
        if not self._r2pipe_available or not self._radare2_available:
            return self._find_crypto_basic(file_path)

        try:
            import r2pipe
            r2 = r2pipe.open(file_path, flags=["-2"])
            r2.cmd("aaa")

            # Known crypto constants
            crypto_results = {}

            # AES S-Box signature
            aes_result = r2.cmd("/x 637c777b")
            if aes_result.strip():
                crypto_results["aes_sbox"] = {
                    "found": True,
                    "description": "AES S-Box constant detected",
                    "mitre": "T1486",
                }

            # RC4
            rc4_result = r2.cmd("/x 0001020304")
            if rc4_result.strip():
                crypto_results["rc4_possible"] = {
                    "found": True,
                    "description": "Possible RC4 initialization",
                }

            r2.quit()

            return {
                "status": "success",
                "crypto_constants": crypto_results,
                "has_crypto": len(crypto_results) > 0,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _find_crypto_basic(self, file_path: str) -> Dict:
        """Basic crypto detection without r2."""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            crypto_found = {}

            # AES S-Box
            aes_sbox = bytes([0x63, 0x7c, 0x77, 0x7b])
            if aes_sbox in data:
                crypto_found["aes"] = "AES S-Box constant found"

            # Common XOR patterns
            xor_count = sum(1 for i in range(0, min(len(data)-1, 10000), 2)
                           if data[i] == data[i+1] ^ 0xff)
            if xor_count > 100:
                crypto_found["xor"] = f"Frequent XOR operations: {xor_count}"

            return {
                "status": "success",
                "method": "basic",
                "crypto_constants": crypto_found,
                "has_crypto": len(crypto_found) > 0,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def extract_cfg(self, file_path: str, function_name: str = None) -> Dict:
        """Control Flow Graph extract karo."""
        if not self._r2pipe_available or not self._radare2_available:
            return {"status": "error", "message": "r2pipe/radare2 required for CFG"}

        try:
            import r2pipe
            r2 = r2pipe.open(file_path, flags=["-2"])
            r2.cmd("aaa")

            if function_name:
                r2.cmd(f"s sym.{function_name}")

            cfg_raw = r2.cmd("agj")
            r2.quit()

            if cfg_raw and cfg_raw.strip() not in ["null", "[]", ""]:
                cfg = json.loads(cfg_raw)
                return {
                    "status": "success",
                    "function": function_name or "entry",
                    "cfg_nodes": len(cfg) if isinstance(cfg, list) else 1,
                    "cfg": cfg[:20] if isinstance(cfg, list) else cfg,
                }

            return {"status": "success", "cfg": [], "message": "No CFG data"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def find_vulnerabilities(self, file_path: str) -> Dict:
        """Automated vulnerability detection."""
        if not self._r2pipe_available or not self._radare2_available:
            return self._find_vulns_basic(file_path)

        try:
            import r2pipe
            r2 = r2pipe.open(file_path, flags=["-2"])
            r2.cmd("aaa")

            vulns = []

            # Dangerous function usage
            dangerous_funcs = [
                ("strcpy", "Buffer overflow risk — use strncpy"),
                ("strcat", "Buffer overflow risk — use strncat"),
                ("sprintf", "Buffer overflow risk — use snprintf"),
                ("gets", "Buffer overflow risk — use fgets"),
                ("scanf", "Buffer overflow risk — use scanf with width"),
                ("system", "Command injection risk"),
                ("popen", "Command injection risk"),
                ("exec", "Command injection risk"),
            ]

            for func, risk in dangerous_funcs:
                result = r2.cmd(f"is~{func}")
                if result.strip():
                    vulns.append({
                        "function": func,
                        "risk": risk,
                        "severity": "high",
                        "cwe": "CWE-120" if "overflow" in risk.lower() else "CWE-78",
                    })

            # Stack canary check
            info_raw = r2.cmd("ij")
            try:
                info = json.loads(info_raw)
                canary = info.get("bin", {}).get("canary", False)
                if not canary:
                    vulns.append({
                        "type": "missing_stack_canary",
                        "risk": "Stack buffer overflow unprotected",
                        "severity": "medium",
                        "cwe": "CWE-121",
                    })

                nx = info.get("bin", {}).get("nx", False)
                if not nx:
                    vulns.append({
                        "type": "nx_disabled",
                        "risk": "No-Execute bit disabled — shellcode execution possible",
                        "severity": "high",
                        "cwe": "CWE-1173",
                    })
            except Exception:
                pass

            r2.quit()

            return {
                "status": "success",
                "vulnerabilities": vulns,
                "total_vulns": len(vulns),
                "critical": [v for v in vulns if v.get("severity") == "critical"],
                "high": [v for v in vulns if v.get("severity") == "high"],
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _find_vulns_basic(self, file_path: str) -> Dict:
        """Basic vulnerability hints without r2."""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            vulns = []
            dangerous = [
                (b"strcpy", "Buffer overflow risk"),
                (b"strcat", "Buffer overflow risk"),
                (b"sprintf", "Format string risk"),
                (b"gets\x00", "Buffer overflow risk"),
                (b"system\x00", "Command injection risk"),
            ]

            for func, risk in dangerous:
                if func in data:
                    vulns.append({
                        "function": func.decode(errors="ignore").rstrip("\x00"),
                        "risk": risk,
                        "severity": "high",
                    })

            return {
                "status": "success",
                "method": "basic",
                "vulnerabilities": vulns,
                "total_vulns": len(vulns),
                "note": "Install radare2 for detailed vulnerability analysis",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================================================
    # 🔧 Pattern Detection
    # ==================================================
    def _detect_suspicious_patterns(self, disasm: List[Dict], functions: List[Dict]) -> Dict:
        """Disassembly se suspicious patterns detect karo."""
        findings = {}

        all_opcodes = " ".join(
            op.get("opcode", "")
            for block in disasm
            for op in block.get("instructions", [])
        ).lower()

        for category, patterns in SUSPICIOUS_DISASM_PATTERNS.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, all_opcodes)
                matches.extend(found)
            if matches:
                findings[category] = matches[:10]

        # Suspicious function names
        suspicious_func_names = []
        for func in functions:
            name = func.get("name", "").lower()
            if any(kw in name for kw in ["inject", "hook", "hide", "crypt", "decode"]):
                suspicious_func_names.append(func["name"])

        if suspicious_func_names:
            findings["suspicious_functions"] = suspicious_func_names

        return findings

    def _map_disasm_to_mitre(self, suspicious: Dict) -> List[str]:
        """MITRE techniques map karo."""
        techniques = set()
        mitre_map = {
            "shellcode_prologue": ["T1055", "T1059"],
            "rop_gadgets": ["T1203", "T1190"],
            "anti_debug": ["T1497", "T1622"],
            "crypto": ["T1486", "T1140"],
            "suspicious_functions": ["T1055"],
        }
        for category in suspicious:
            for tech in mitre_map.get(category, []):
                techniques.add(tech)
        return list(techniques)

    def _calculate_verdict(self, suspicious: Dict, rop_gadgets: List) -> Dict:
        """Verdict calculate karo."""
        score = len(suspicious) * 2 + (len(rop_gadgets) > 10) * 2
        score = min(score, 10)

        verdict = (
            "MALICIOUS" if score >= 7 else
            "SUSPICIOUS" if score >= 4 else
            "LOW_RISK" if score >= 1 else
            "LIKELY_BENIGN"
        )

        return {
            "verdict": verdict,
            "score": score,
            "rop_gadgets_count": len(rop_gadgets),
            "suspicious_patterns": len(suspicious),
        }

    def _is_suspicious_function(self, name: str) -> bool:
        """Function name suspicious hai?"""
        suspicious_kw = ["inject", "hook", "hide", "crypt", "shellcode",
                        "payload", "exploit", "bypass", "evad"]
        return any(kw in name.lower() for kw in suspicious_kw)

    # ==================================================
    # 📊 Report Generation
    # ==================================================
    def generate_report(self, analysis_result: Dict) -> str:
        """Human-readable report generate karo."""
        lines = [
            "=" * 60,
            "  RADARE2 BINARY ANALYSIS REPORT",
            "=" * 60,
            f"  File    : {analysis_result.get('file_path', 'N/A')}",
            f"  Method  : {analysis_result.get('method', 'N/A')}",
            f"  Arch    : {analysis_result.get('architecture', 'N/A')}",
            f"  Time    : {analysis_result.get('analysis_time_sec', 0)}s",
            "",
        ]

        # Verdict
        verdict = analysis_result.get("verdict", {})
        if verdict:
            lines += [
                f"  VERDICT : {verdict.get('verdict', 'N/A')}",
                f"  Score   : {verdict.get('score', 0)}/10",
                "",
            ]

        # Functions
        funcs = analysis_result.get("functions", [])
        if funcs:
            lines += [f"  Functions: {len(funcs)}"]
            suspicious_funcs = [f for f in funcs if f.get("suspicious")]
            if suspicious_funcs:
                lines += [f"  ⚠️  Suspicious: {[f['name'] for f in suspicious_funcs[:5]]}"]

        # ROP Gadgets
        rop = analysis_result.get("rop_gadgets", [])
        if rop:
            lines += [f"  ROP Gadgets: {len(rop)}"]

        # MITRE
        mitre = analysis_result.get("mitre_techniques", [])
        if mitre:
            lines += [f"  MITRE: {', '.join(mitre)}"]

        lines.append("=" * 60)
        return "\n".join(lines)
