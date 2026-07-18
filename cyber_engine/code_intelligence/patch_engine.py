"""
Chhoti Don EvolveX - Patch Engine
Advanced patch application with validation,
rollback support, and diff generation.
Phase 2.2 - Full Upgrade
"""

import py_compile
import os
from typing import Dict, List, Optional, Optional
def safe_write_patch(file_path: str, content: str) -> bool:
    """
    Preserved + upgraded.
    """
    try:
        # Write to temp first
        temp_path = file_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Validate syntax
        try:
            py_compile.compile(temp_path, doraise=True)
        except Exception:
            os.remove(temp_path)
            return False

        # Replace original
        os.replace(temp_path, file_path)
        return True

    except Exception:
        if os.path.exists(file_path + ".tmp"):
            os.remove(file_path + ".tmp")
        return False


def apply_auto_fix(issue: Dict) -> Dict:
    """
    Advanced patch system.
    Preserved + upgraded with full pipeline.
    """
    file_path = issue.get("file")
    if not file_path or not os.path.exists(file_path):
        return {"status": "error", "message": "File not found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original = f.read()

        # Import fix engine
        from .fix_rules import apply_fix, FIXABLE_SYMBOLS
        issue_type = issue.get("type")

        if issue_type not in FIXABLE_SYMBOLS:
            return {"status": "skipped", "reason": "Not fixable"}

        fixed = apply_fix(issue, original)

        if fixed == original:
            return {"status": "no_change"}

        # Generate diff
        diff = generate_diff(original, fixed, file_path)

        success = safe_write_patch(file_path, fixed)

        return {
            "status": "success" if success else "error",
            "file": file_path,
            "issue_type": issue_type,
            "diff": diff,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def apply_patch_batch(file_path: str, patches: List[Dict]) -> Dict:
    """
    Multiple patches ek saath apply karo.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": "File not found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        applied = 0
        failed = 0

        from .fix_rules import apply_fix, FIXABLE_SYMBOLS

        for patch in patches:
            if patch.get("type") not in FIXABLE_SYMBOLS:
                continue
            try:
                new_content = apply_fix(patch, content)
                if new_content != content:
                    content = new_content
                    applied += 1
            except Exception:
                failed += 1

        if content == original:
            return {"status": "no_change", "applied": 0}

        diff = generate_diff(original, content, file_path)
        success = safe_write_patch(file_path, content)

        return {
            "status": "success" if success else "error",
            "file": file_path,
            "patches_applied": applied,
            "patches_failed": failed,
            "diff_lines": len(diff.splitlines()),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def generate_diff(original: str, modified: str, file_path: str = "") -> str:
    """Unified diff generate karo."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{os.path.basename(file_path)}",
        tofile=f"b/{os.path.basename(file_path)}",
        lineterm="",
    )

    return "".join(diff)


def verify_patch_safety(file_path: str, original: str, patched: str) -> Dict:
    """Patch safety verify karo."""
    try:
        # Syntax check
        compile(patched, file_path, "exec")

        # Line count change check
        orig_lines = original.count("\n")
        patch_lines = patched.count("\n")
        line_delta = abs(patch_lines - orig_lines)

        if line_delta > 50:
            return {
                "safe": False,
                "reason": f"Too many line changes: {line_delta}",
            }

        return {"safe": True, "line_delta": line_delta}

    except SyntaxError as e:
        return {"safe": False, "reason": f"Syntax error: {e}"}
    except Exception as e:
        return {"safe": False, "reason": str(e)}
