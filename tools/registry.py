"""Module Description"""

from tools.calculator import run_calculator
from tools.file_reader import read_file
from tools.sandbox import run_python
from tools.search import search_web
from browser.guarded import (
    web_search, open_page,
    browser_navigate, browser_read, browser_get_content,
)
from tools.image_analyzer import analyze_image
from tools.feature_builder import (
    feature_builder,
    load_generated_tools,
    TOOL_DEFINITION as FEATURE_BUILDER_DEF,
)

# 💻 Coding-agent read-only workspace tools (Phase 1). Guarded wrappers only —
# path-jailed through the WorkspaceSandbox and gated LOW-tier by the Guardian.
from coding_agent.guarded import (
    fs_list_dir, fs_read_file, fs_search,
    grant_workspace as _grant_workspace,
)

# 🔎 Recon Imports
from cyber_engine.recon.port_scanner import PortScanner
from cyber_engine.recon.subdomain_scanner import SubdomainScanner

# 💻 Coding Engine Imports
from tools.code_generator import generate_code
from tools.code_executor import execute_code
from tools.code_debugger import debug_code, explain_code
from typing import List, Optional

# Nmap is optional
try:
    from cyber_engine.recon.nmap_wrapper import NmapWrapper
    NMAP_IMPORT_AVAILABLE = True
except Exception:
    NMAP_IMPORT_AVAILABLE = False

    """Class Description"""

class ToolRegistry:
    """Class Description"""

    def __init__(self, brain=None):
        """
        Central registry for all executable tools.
        Add new tools here only.

        Args:
            brain: Optional brain instance for AI-powered coding tools.
        """

        # Brain reference (used by coding tools)
        self.brain = brain

        # Always available tools
        self.port_scanner = PortScanner()
        self.subdomain_scanner = SubdomainScanner()

        # Optional Nmap initialization
        self.nmap = None
        self.nmap_available = False

        if NMAP_IMPORT_AVAILABLE:
            try:
                self.nmap = NmapWrapper()
                self.nmap_available = True
            except Exception:
                self.nmap_available = False

        # ------------------------------
        # Core Tools (Preserved)
        # ------------------------------
        self.tools = {
            "calculator": run_calculator,
            "read_file": read_file,
            "search": search_web,
            # Browser operations are intentionally the guarded wrappers, never
            # browser.search's raw blocking functions.
            "web_search": web_search,
            "open_page": open_page,
            # Playwright headed browser — READ-ONLY research (Phase 1). Guarded
            # wrappers only; for JS-heavy / render-required pages (open_page is
            # the cheaper static path for ordinary pages). See browser/routing.py.
            "browser_navigate": browser_navigate,
            "browser_read": browser_read,
            "browser_get_content": browser_get_content,
            # Phase 2: read-only multi-step research agent (guarded browser loop).
            "browser_research": self._run_browser_research,
            "analyze_image": analyze_image,
            "run_python": run_python,
            "port_scan": self._run_port_scan,
            "subdomain_scan": self._run_subdomain_scan,

            # ---------------------------
            # 💻 Coding Engine Tools
            # ---------------------------
            "generate_code": self._run_generate_code,
            "execute_code": self._run_execute_code,
            "debug_code": self._run_debug_code,
            "explain_code": self._run_explain_code,

            # ---------------------------
            # 🧩 Self-extension
            # ---------------------------
            "feature_builder": feature_builder,

            # ---------------------------
            # 💻 Coding Agent — read-only workspace (Phase 1)
            # ---------------------------
            # Path-jailed through the WorkspaceSandbox; Guardian assigns these the
            # LOW risk tier (auto-allow), mirroring the read-only web_ tools. NO
            # write/delete/shell capability exists in this phase.
            "fs_list_dir": fs_list_dir,
            "fs_read_file": fs_read_file,
            "fs_search": fs_search,
        }

        # Add Nmap only if available
        if self.nmap_available:
            self.tools["nmap_scan"] = self._run_nmap

        self.tool_definitions = {
            "web_search": {
                "name": "web_search",
                "description": "Search the web and return links with snippets only; it does not answer the question.",
                "args": {"query": "string", "max_results": "integer (optional, 1-10)"},
            },
            "open_page": {
                "name": "open_page",
                "description": "Read one specific http(s) URL and return clean text as untrusted data for citation.",
                "args": {"url": "string"},
            },
            "browser_read": {
                "name": "browser_read",
                "description": ("Open a REAL headed browser, render a JS-heavy page and return its "
                                "clean readable text as untrusted data. Read-only; no clicking/typing. "
                                "Use only for pages open_page cannot render, or when the user asks to "
                                "'open the browser'."),
                "args": {"url": "string"},
            },
            "browser_navigate": {
                "name": "browser_navigate",
                "description": "Open a REAL headed browser and navigate to an http(s) URL; return the page title and final URL. Read-only.",
                "args": {"url": "string"},
            },
            "browser_get_content": {
                "name": "browser_get_content",
                "description": "Render a page in a REAL headed browser and return a compact markdown outline of its accessibility tree (untrusted). Read-only.",
                "args": {"url": "string"},
            },
            "browser_research": {
                "name": "browser_research",
                "description": ("Autonomous READ-ONLY multi-step research: given a goal, a fast local "
                                "model plans and runs several guarded search/navigate/read steps and "
                                "returns a synthesized answer. No clicking/typing. Use for 'open the "
                                "browser and find out X'."),
                "args": {"goal": "string", "max_steps": "integer (optional)"},
            },
            "analyze_image": {
                "name": "analyze_image",
                "description": "Look at a LOCAL image file and describe it (objects, text, colors) using a local vision model. No internet.",
                "args": {"image_path": "string (local file)", "prompt": "string (optional question about the image)"},
            },
            "feature_builder": FEATURE_BUILDER_DEF,
            "fs_list_dir": {
                "name": "fs_list_dir",
                "description": ("List the directory tree of the granted code workspace (read-only). "
                                "Skips heavy dirs (node_modules/.git/__pycache__/venv). A workspace "
                                "must be granted first; every path is jailed to that folder."),
                "args": {"path": "string (optional, relative to workspace root, default '.')",
                         "max_depth": "integer (optional)"},
            },
            "fs_read_file": {
                "name": "fs_read_file",
                "description": ("Read a text file inside the granted workspace (read-only). Size-capped "
                                "and returned line-numbered. Jailed to the workspace root."),
                "args": {"path": "string (relative to workspace root)",
                         "max_bytes": "integer (optional)"},
            },
            "fs_search": {
                "name": "fs_search",
                "description": ("Grep-style search across the granted workspace (read-only); returns "
                                "file:line:match rows. Uses ripgrep if available. Jailed to the root."),
                "args": {"query": "string", "glob": "string (optional file glob filter)"},
            },
        }

        # Assistant-generated tools (added via feature_builder). Guarded so a
        # broken generated tool can never break the registry at startup.
        try:
            for _gname, _gspec in load_generated_tools().items():
                if _gname == "_errors":
                    continue
                self.tools[_gname] = _gspec["callable"]
                self.tool_definitions[_gname] = _gspec["definition"]
        except Exception:
            pass

    # --------------------------------------------------
    # 💻 Coding Agent — grant a workspace (control-plane)
    # --------------------------------------------------
    def grant_workspace(self, path):
        """Grant a folder as the coding agent's jailed workspace root.

        Not a LOW-tier model tool — this DEFINES the sandbox that the read-only
        fs_* tools operate inside, so it is exposed as an explicit registry
        method. Returns the resolved root or a structured error.
        """
        return _grant_workspace(path)

    # --------------------------------------------------
    # 📋 List Tools (Preserved)
    # --------------------------------------------------
    def list_tools(self):
        return list(self.tools.keys())

    def get_available_tools(self):
        return list(self.tools.keys())

    def get_tool_definitions(self):
        """Return LLM-facing metadata for tools that expose typed arguments."""
        return dict(self.tool_definitions)

    # --------------------------------------------------
    # 🚀 Execute Tool (Safe Version)
    # --------------------------------------------------
    def execute(self, tool_name, input_data):

        if tool_name not in self.tools:
            return {
                "status": "error",
                "tool": tool_name,
                "message": f"Tool '{tool_name}' not found",
                "available_tools": self.list_tools(),
                "confidence": 0.0
            }

        try:
            result = self.tools[tool_name](input_data)

            return {
                "status": "success",
                "tool": tool_name,
                "result": result,
                "confidence": self._calculate_confidence(result)
            }

        except Exception as e:
            return {
                "status": "error",
                "tool": tool_name,
                "message": str(e),
                "confidence": 0.0
            }

    # ==================================================
    # 🔎 RECON WRAPPERS (Preserved)
    # ==================================================

    def _run_nmap(self, input_data):
        if not self.nmap_available:
            return {
                "status": "error",
                "message": "Nmap is not available in this environment."
            }

        target = input_data.get("target")
        scan_type = input_data.get("scan_type", "basic")
        ports = input_data.get("ports")

        if not target:
            raise ValueError("Target is required for nmap_scan")

        return self.nmap.run_scan(
            target=target,
            scan_type=scan_type,
            ports=ports
        )

    def _run_port_scan(self, input_data):
        target = input_data.get("target")
        ports = input_data.get("ports")

        if not target or not ports:
            raise ValueError("Target and ports are required for port_scan")

        return self.port_scanner.scan_ports(target, ports)

    def _run_subdomain_scan(self, input_data):
        domain = input_data.get("domain")

        if not domain:
            raise ValueError("Domain is required for subdomain_scan")

        return self.subdomain_scanner.scan(domain)

    # ==================================================
    # 🌐 BROWSER RESEARCH AGENT (Phase 2 — READ-ONLY)
    # ==================================================
    def _run_browser_research(self, input_data):
        """Run the read-only browser research agent. Requires a brain for the
        navigation model; every browser action goes through the guardian gate."""
        goal = str(input_data.get("goal") or input_data.get("input") or "").strip()
        if not goal:
            return {"status": "error", "marker": "EMPTY_GOAL",
                    "message": "A research goal is required."}
        if self.brain is None:
            return {"status": "error", "marker": "NO_BRAIN",
                    "message": "Navigation brain unavailable."}
        from browser.agent import run_research

        def _think(prompt):
            return self.brain.think_fast(prompt, brain_type="navigation")

        def _synth(prompt):
            return self.brain.think_fast(
                prompt, brain_type="navigation", num_predict=400,
                system_prompt="You are a concise research assistant. Answer in plain text.")

        kw = {}
        if input_data.get("max_steps") is not None:
            kw["max_steps"] = int(input_data["max_steps"])
        res = run_research(goal, think_fn=_think, synth_fn=_synth, **kw)
        return {"status": "success", **res}

    # ==================================================
    # 💻 CODING ENGINE WRAPPERS
    # ==================================================

    def _run_generate_code(self, input_data):
        """
        Generate code from natural language prompt.

        input_data:
            - prompt (str): What to build e.g. "ek calculator banao"
            - language (str, optional): 'python', 'javascript', 'cpp', 'c', 'sql', 'bash'
            - context (str, optional): Extra requirements
        """
        # Inject brain for AI-powered generation
        input_data["brain"] = self.brain
        return generate_code(input_data)

    def _run_execute_code(self, input_data):
        """
        Execute code and return output.

        input_data:
            - code (str): Code to run
            - language (str): Language of code
            - stdin (str, optional): Input for the program
        """
        return execute_code(input_data)

    def _run_debug_code(self, input_data):
        """
        Debug code — find bugs and suggest fixes.

        input_data:
            - code (str): Buggy code
            - error (str): Error message/traceback
            - language (str): Language
        """
        input_data["brain"] = self.brain
        return debug_code(input_data)

    def _run_explain_code(self, input_data):
        """
        Explain what code does in simple terms.

        input_data:
            - code (str): Code to explain
            - language (str): Language
            - detail_level (str): 'simple' or 'detailed'
        """
        input_data["brain"] = self.brain
        return explain_code(input_data)

    # ==================================================
    # 📊 Confidence Engine (Preserved)
    # ==================================================
    def _calculate_confidence(self, result):

        if isinstance(result, dict):

            if result.get("status") == "error":
                return 0.0

            if "confidence_score" in result:
                try:
                    return float(result["confidence_score"]) / 100
                except Exception:
                    return 0.8

        return 0.9
