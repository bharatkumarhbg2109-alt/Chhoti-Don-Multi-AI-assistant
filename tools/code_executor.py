"""
Chhoti Don - Code Executor Tool
Safely executes code in Python, JavaScript, C/C++, SQL, and Bash.
"""

import subprocess
import sys
import os
import tempfile
import time

# Execution time limit (seconds)
TIMEOUT = 15

# Safe isolated temporary execution directory
EXEC_TEMP_DIR = tempfile.mkdtemp(prefix="chhoti_exec_")

SUPPORTED_EXEC_LANGUAGES = ["python", "javascript", "cpp", "c", "bash", "sql"]


def execute_code(input_data: dict) -> dict:
    """
    Execute code and return output.

    input_data keys:
        - code (str): Code to execute
        - language (str): Language of the code
        - stdin (str, optional): Standard input for the program
    """
    code = input_data.get("code", "")
    language = input_data.get("language", "python").lower()
    stdin_input = input_data.get("stdin", "")

    if not code:
        return {
            "status": "error",
            "success": False,
            "message": "No code provided to execute.",
            "error": "No code provided to execute.",
            "output": None,
            "stderr": None
        }

    if language not in SUPPORTED_EXEC_LANGUAGES:
        return {
            "status": "error",
            "success": False,
            "message": f"Language '{language}' execution not supported. Supported: {SUPPORTED_EXEC_LANGUAGES}",
            "error": f"Language '{language}' execution not supported.",
            "output": None
        }

    # Route to correct executor
    executors = {
        "python": _execute_python,
        "javascript": _execute_javascript,
        "cpp": _execute_cpp,
        "c": _execute_c,
        "bash": _execute_bash,
        "sql": _execute_sql,
    }

    start_time = time.time()
    result = executors[language](code, stdin_input)
    elapsed = round(time.time() - start_time, 3)

    result["execution_time"] = f"{elapsed}s"
    result["language"] = language
    return result


# ==================================================
# 🐍 Python Executor
# ==================================================
def _execute_python(code: str, stdin_input: str = "") -> dict:
    tmp_path = None
    try:
        os.makedirs(EXEC_TEMP_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', dir=EXEC_TEMP_DIR, delete=False) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=EXEC_TEMP_DIR
        )
        return _build_result(result)
    except subprocess.TimeoutExpired:
        return _timeout_result()
    except Exception as e:
        return _error_result(str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ==================================================
# 🌐 JavaScript Executor (Node.js)
# ==================================================
def _execute_javascript(code: str, stdin_input: str = "") -> dict:
    tmp_path = None
    try:
        node_path = _find_executable(["node", "nodejs"])
        if not node_path:
            return {
                "status": "error",
                "success": False,
                "message": "Node.js not found. Please install Node.js to run JavaScript.",
                "error": "Node.js not found.",
                "output": None
            }

        os.makedirs(EXEC_TEMP_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', dir=EXEC_TEMP_DIR, delete=False) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            [node_path, tmp_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=EXEC_TEMP_DIR
        )
        return _build_result(result)
    except subprocess.TimeoutExpired:
        return _timeout_result()
    except Exception as e:
        return _error_result(str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ==================================================
# ⚙️ C++ Executor
# ==================================================
def _execute_cpp(code: str, stdin_input: str = "") -> dict:
    return _compile_and_run(code, stdin_input, suffix=".cpp", compiler="g++")


# ==================================================
# ⚙️ C Executor
# ==================================================
def _execute_c(code: str, stdin_input: str = "") -> dict:
    return _compile_and_run(code, stdin_input, suffix=".c", compiler="gcc")


def _compile_and_run(code: str, stdin_input: str, suffix: str, compiler: str) -> dict:
    src_path = None
    out_path = None
    try:
        compiler_path = _find_executable([compiler])
        if not compiler_path:
            return {
                "status": "error",
                "success": False,
                "message": f"{compiler} not found. Please install GCC/G++ to compile {suffix} files.",
                "error": f"{compiler} not found.",
                "output": None
            }

        os.makedirs(EXEC_TEMP_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, dir=EXEC_TEMP_DIR, delete=False) as f:
            f.write(code)
            src_path = f.name

        out_path = src_path.replace(suffix, ".exe" if os.name == "nt" else ".out")

        # Compile
        compile_result = subprocess.run(
            [compiler_path, src_path, "-o", out_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=EXEC_TEMP_DIR
        )

        if compile_result.returncode != 0:
            return {
                "status": "error",
                "success": False,
                "message": "Compilation failed",
                "error": "Compilation failed",
                "output": None,
                "stderr": compile_result.stderr,
                "compile_errors": compile_result.stderr,
                "return_code": compile_result.returncode
            }

        # Run
        run_result = subprocess.run(
            [out_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=EXEC_TEMP_DIR
        )

        return _build_result(run_result)

    except subprocess.TimeoutExpired:
        return _timeout_result()
    except Exception as e:
        return _error_result(str(e))
    finally:
        if src_path and os.path.exists(src_path):
            try:
                os.unlink(src_path)
            except Exception:
                pass
        if out_path and os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except Exception:
                pass


# ==================================================
# 🐚 Bash Executor (Windows + Linux compatible)
# ==================================================
def _execute_bash(code: str, stdin_input: str = "") -> dict:
    tmp_path = None
    try:
        bash_path = _find_bash_windows() or _find_executable(["bash", "sh"])

        if not bash_path:
            # Fallback: PowerShell pe convert karke chalao
            return _execute_bash_via_powershell(code, stdin_input)

        os.makedirs(EXEC_TEMP_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', dir=EXEC_TEMP_DIR, delete=False, newline='\n') as f:
            f.write(code)
            tmp_path = f.name

        try:
            os.chmod(tmp_path, 0o755)
        except Exception:
            pass  # Windows pe chmod fail ho sakta hai — ignore

        result = subprocess.run(
            [bash_path, tmp_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=EXEC_TEMP_DIR
        )
        return _build_result(result)

    except subprocess.TimeoutExpired:
        return _timeout_result()
    except Exception as e:
        return _error_result(str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def _find_bash_windows() -> str | None:
    """Windows pe Git Bash ya WSL bash dhundho."""
    if os.name != 'nt':
        return None

    common_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        r"C:\Git\bin\bash.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Git\bin\bash.exe"),
    ]

    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


def _execute_bash_via_powershell(code: str, stdin_input: str = "") -> dict:
    """Bash commands ko PowerShell se run karo as fallback."""
    try:
        ps_path = _find_executable(["powershell", "pwsh"])
        if not ps_path:
            return {
                "status": "error",
                "success": False,
                "message": "Bash aur PowerShell dono nahi mile. Git Bash install karo: https://git-scm.com",
                "error": "Bash aur PowerShell dono nahi mile.",
                "output": None
            }

        # Basic bash commands ko PS equivalents mein convert karo
        ps_code = code
        ps_code = ps_code.replace("echo", "Write-Output")
        ps_code = ps_code.replace("ls", "Get-ChildItem")
        ps_code = ps_code.replace("pwd", "Get-Location")
        ps_code = ps_code.replace("#!/bin/bash", "")
        ps_code = ps_code.replace("#!/bin/sh", "")

        os.makedirs(EXEC_TEMP_DIR, exist_ok=True)
        result = subprocess.run(
            [ps_path, "-Command", ps_code],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=EXEC_TEMP_DIR
        )
        r = _build_result(result)
        r["note"] = "⚠️ Bash nahi mila — PowerShell fallback use hua. Git Bash install karo for full support."
        return r

    except subprocess.TimeoutExpired:
        return _timeout_result()
    except Exception as e:
        return _error_result(str(e))


# ==================================================
# 🗄️ SQL Executor (SQLite in-memory)
# ==================================================
def _execute_sql(code: str, stdin_input: str = "") -> dict:
    try:
        import sqlite3
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        output_lines = []
        statements = [s.strip() for s in code.split(";") if s.strip()]

        for stmt in statements:
            try:
                cursor.execute(stmt)
                rows = cursor.fetchall()
                if rows:
                    for row in rows:
                        output_lines.append(str(row))
                else:
                    output_lines.append(f"[OK] {stmt[:50]}...")
            except sqlite3.Error as e:
                output_lines.append(f"[SQL Error] {str(e)}")

        conn.close()
        output = "\n".join(output_lines) if output_lines else "[No output]"

        return {
            "status": "success",
            "success": True,
            "output": output,
            "stderr": None,
            "return_code": 0
        }

    except Exception as e:
        return _error_result(str(e))


# ==================================================
# 🔧 Helpers
# ==================================================
def _find_executable(names: list) -> str | None:
    """Find executable path from list of possible names."""
    for name in names:
        path = _which(name)
        if path:
            return path
    return None


def _which(name: str) -> str | None:
    """Cross-platform which."""
    try:
        result = subprocess.run(
            ["where" if os.name == "nt" else "which", name],
            capture_output=True, text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None


def _build_result(result) -> dict:
    success = result.returncode == 0
    return {
        "status": "success" if success else "error",
        "success": success,
        "output": result.stdout.strip() if result.stdout else "[No output]",
        "stderr": result.stderr.strip() if result.stderr else None,
        "return_code": result.returncode
    }


def _timeout_result() -> dict:
    return {
        "status": "error",
        "success": False,
        "message": f"Execution timed out after {TIMEOUT} seconds.",
        "error": f"Execution timed out after {TIMEOUT} seconds.",
        "output": None,
        "stderr": None,
        "return_code": -1
    }


def _error_result(msg: str) -> dict:
    return {
        "status": "error",
        "success": False,
        "message": msg,
        "error": msg,
        "output": None,
        "stderr": None,
        "return_code": -1
    }
