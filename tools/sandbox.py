"""
Chhoti Don - Sandbox
Advanced Python code execution sandbox with safety controls,
output capture, timeout, and resource limits.
Phase 2.2 - Full Upgrade
"""

import sys
import os
import time
import io
import traceback
import ast
import signal
from typing import Dict, Any, Optional, List, Tuple

# Constants
MAX_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_SIZE = 50000    # chars
MAX_MEMORY_MB = 50         # MB limit hint

# Forbidden imports and operations
FORBIDDEN_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "socket",
    "requests", "urllib", "http", "ftplib", "smtplib",
    "multiprocessing", "threading", "concurrent",
    "ctypes", "cffi", "importlib", "builtins",
    "signal", "resource", "mmap", "fcntl",
    "pathlib",  # file system ops
    "pickle", "marshal",  # code execution
    "eval", "exec", "compile",
}

FORBIDDEN_BUILTINS = {
    "exec", "eval", "compile", "open", "__import__",
    "input", "breakpoint", "exit", "quit",
    "globals", "locals", "vars", "dir",
    "memoryview", "bytearray",
}

# Allowed safe builtins
SAFE_BUILTINS = {
    "print": print,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter,
    "sorted": sorted, "reversed": reversed,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "int": int, "float": float, "str": str, "bool": bool,
    "bytes": bytes,
    "min": min, "max": max, "sum": sum, "abs": abs,
    "round": round, "pow": pow, "divmod": divmod,
    "isinstance": isinstance, "issubclass": issubclass,
    "type": type, "id": id, "hash": hash,
    "repr": repr, "format": format,
    "any": any, "all": all,
    "chr": chr, "ord": ord, "hex": hex, "oct": oct, "bin": bin,
    "True": True, "False": False, "None": None,
    "NotImplemented": NotImplemented,
    "Exception": Exception, "ValueError": ValueError,
    "TypeError": TypeError, "KeyError": KeyError,
    "IndexError": IndexError, "AttributeError": AttributeError,
    "StopIteration": StopIteration, "ZeroDivisionError": ZeroDivisionError,
    "AssertionError": AssertionError, "RuntimeError": RuntimeError,
}

# Safe modules that can be imported
ALLOWED_MODULES = {
    "math", "random", "datetime", "json", "re",
    "string", "collections", "itertools", "functools",
    "copy", "pprint", "textwrap", "hashlib",
    "base64", "struct", "decimal", "fractions",
    "statistics", "operator",
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def run_python(input_data: Dict) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Safe Python code execution with full controls.
    """
    if not isinstance(input_data, dict):
        return {
            "status": "error",
            "message": "Input must be a dictionary with 'code' key."
        }

    code = input_data.get("code")
    if not code:
        return {"status": "error", "message": "Missing 'code' in input."}

    sandbox = PythonSandbox(
        timeout=input_data.get("timeout", MAX_EXECUTION_TIME),
        safe_mode=input_data.get("safe_mode", True),
    )

    return sandbox.execute(code)


# ==================================================
# 🔒 SANDBOX CLASS
# ==================================================

class PythonSandbox:
    """
    Advanced Python Execution Sandbox.
    Provides controlled, safe code execution environment.
    """

    def __init__(
        self,
        timeout: int = MAX_EXECUTION_TIME,
        safe_mode: bool = True,
    ):
        self.timeout = min(timeout, MAX_EXECUTION_TIME)
        self.safe_mode = safe_mode

    def execute(self, code: str) -> Dict:
        """
        Execute Python code safely.

        Returns:
            Dict with status, output, result, and metadata
        """
        start_time = time.time()

        # Safety validation
        if self.safe_mode:
            validation = self._validate_code(code)
            if not validation["safe"]:
                return {
                    "status": "blocked",
                    "message": f"Safety violation: {validation['reason']}",
                    "code": code[:100],
                }

        # Setup execution environment
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        local_scope = {}
        global_scope = self._build_safe_globals()

        # Execute with output capture
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Timeout via alarm (Unix) or threading
            exec_result = self._execute_with_timeout(
                code, global_scope, local_scope
            )

            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()

        except Exception as e:
            output = stdout_capture.getvalue()
            errors = traceback.format_exc()
            exec_result = {"error": str(e)}

        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        duration = round(time.time() - start_time, 4)

        # Truncate output
        if len(output) > MAX_OUTPUT_SIZE:
            output = output[:MAX_OUTPUT_SIZE] + "\n...[output truncated]"

        # Build clean result
        clean_scope = {
            k: repr(v)[:200]
            for k, v in local_scope.items()
            if not k.startswith("_") and k not in global_scope
        }

        success = exec_result.get("status") == "success"

        return {
            "status": "success" if success else "error",
            "output": output.strip() if output else None,
            "stderr": errors.strip() if errors else None,
            "result": clean_scope,
            "variables": clean_scope,
            "execution_time_sec": duration,
            "lines_executed": code.count("\n") + 1,
            "error": exec_result.get("error") if not success else None,
        }

    def _execute_with_timeout(
        self,
        code: str,
        global_scope: Dict,
        local_scope: Dict,
    ) -> Dict:
        """Execute with timeout."""
        import threading

        result = {"status": "error", "error": "Execution failed"}
        exception_holder = []

        def run():
            try:
                exec(compile(code, "<sandbox>", "exec"), global_scope, local_scope)
                result["status"] = "success"
            except TimeoutError:
                exception_holder.append(TimeoutError("Execution timed out"))
            except Exception as e:
                exception_holder.append(e)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            return {"status": "error", "error": f"Execution timed out ({self.timeout}s)"}

        if exception_holder:
            raise exception_holder[0]

        return result

    def _validate_code(self, code: str) -> Dict:
        """Code safety validate karo."""
        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"safe": False, "reason": f"Syntax error: {e}"}

        # Check for forbidden operations
        for node in ast.walk(tree):
            # Import checks
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in FORBIDDEN_IMPORTS:
                        return {"safe": False, "reason": f"Forbidden import: {module}"}
                    if module not in ALLOWED_MODULES and self.safe_mode:
                        return {"safe": False, "reason": f"Module not in allowlist: {module}"}

            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module in FORBIDDEN_IMPORTS:
                    return {"safe": False, "reason": f"Forbidden import: {module}"}

            # Function call checks
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_BUILTINS:
                        return {"safe": False, "reason": f"Forbidden builtin: {node.func.id}"}

            # Attribute access checks (e.g., os.system)
            elif isinstance(node, ast.Attribute):
                if node.attr in ("system", "popen", "spawn", "exec", "eval"):
                    return {"safe": False, "reason": f"Forbidden method: {node.attr}"}

        return {"safe": True, "reason": "Code passed safety checks"}

    def _build_safe_globals(self) -> Dict:
        """Safe global environment build karo."""
        safe_globals = {"__builtins__": SAFE_BUILTINS.copy()}

        # Add allowed modules
        import math
        import random
        import datetime as dt
        import json as json_mod
        import re as re_mod
        import string as string_mod
        import collections

        module_map = {
            "math": math,
            "random": random,
            "datetime": dt,
            "json": json_mod,
            "re": re_mod,
            "string": string_mod,
            "collections": collections,
        }

        for name, mod in module_map.items():
            safe_globals[name] = mod

        return safe_globals


# ==================================================
# 🔧 STANDALONE FUNCTIONS
# ==================================================

def quick_run(code: str, timeout: int = 5) -> str:
    """Quick code run — returns output string."""
    result = run_python({"code": code, "timeout": timeout})
    if result.get("output"):
        return result["output"]
    if result.get("error"):
        return f"Error: {result['error']}"
    return str(result.get("result", "No output"))


def validate_python_code(code: str) -> Dict:
    """Python code validate karo without executing."""
    sandbox = PythonSandbox()
    return sandbox._validate_code(code)
