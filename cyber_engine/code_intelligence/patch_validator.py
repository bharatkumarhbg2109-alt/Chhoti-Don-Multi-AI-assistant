"""
Chhoti Don EvolveX - Patch Validator
Advanced patch validation with multi-layer checks.
Phase 2.2 - Full Upgrade
"""

import py_compile
import ast
from typing import Dict, Dict


def validate_patch(file_path: str, baseline_error_count: int = None) -> int:
    """
    Validate patch safety — preserved + upgraded.

    Returns:
        error_count or 9999 on catastrophic failure
    """
    # Syntax validation
    try:
        py_compile.compile(file_path, doraise=True)
    except Exception:
        return 9999

    # AST validation (NEW)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
    except SyntaxError:
        return 9999

    # Static analysis re-check
    issues = run_static_analysis([file_path])
    error_count = sum(1 for i in issues if i.get("severity") == "error")

    # Baseline comparison
    if baseline_error_count is not None:
        if error_count > baseline_error_count:
            return 9999  # Patch worsened state

    return error_count


def validate_patch_content(original: str, patched: str, file_path: str = "") -> Dict:
    """
    Content-level patch validation.

    Returns:
        Detailed validation result
    """
    results = {
        "syntax_valid": False,
        "ast_valid": False,
        "no_regression": True,
        "safe": False,
    }

    # Syntax check
    try:
        py_compile.compile(file_path or "<string>", doraise=True) if file_path else None
        compile(patched, file_path or "<string>", "exec")
        results["syntax_valid"] = True
    except SyntaxError as e:
        results["error"] = str(e)
        return results

    # AST check
    try:
        ast.parse(patched)
        results["ast_valid"] = True
    except Exception as e:
        results["error"] = str(e)
        return results

    # Content safety checks
    dangerous_removals = ["def ", "class ", "import ", "return "]
    original_lines = set(original.splitlines())
    patched_lines = set(patched.splitlines())

    removed_lines = original_lines - patched_lines
    dangerous = [l for l in removed_lines if any(d in l for d in dangerous_removals)]

    if len(dangerous) > 3:
        results["no_regression"] = False
        results["warning"] = f"Removed {len(dangerous)} important lines"

    results["safe"] = results["syntax_valid"] and results["ast_valid"] and results["no_regression"]
    return results
