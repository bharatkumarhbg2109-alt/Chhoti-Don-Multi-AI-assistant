"""
Chhoti Don EvolveX - Static Analysis
Advanced static analysis with pylint integration
and fallback AST-based analysis.
Phase 2.2 - Full Upgrade
"""

import os
import json
import ast
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, List, List

def run_static_analysis(files: List[str]) -> List[Dict]:
    """
    Run static analysis on Python files.
    Preserved + upgraded with AST fallback.
    """
    print("[EvolveX] Running static analysis...")
    issues = []

    for file in files:
        if not os.path.exists(file):
            continue

        # Try pylint first
        pylint_issues = _run_pylint(file)
        if pylint_issues is not None:
            issues.extend(pylint_issues)
        else:
            # Fallback to AST analysis
            ast_issues = _run_ast_analysis(file)
            issues.extend(ast_issues)

    return issues


def _run_pylint(file: str) -> List[Dict]:
    """Run pylint on a file — multi-version compatible."""
    try:
        # pylint 4.x compatible import
        Run = None
        for lint_path in [
            ("pylint.lint", "Run"),
            ("pylint", "run"),
            ("pylint.lint.run", "Run"),
        ]:
            try:
                import importlib
                mod = importlib.import_module(lint_path[0])
                Run = getattr(mod, lint_path[1], None)
                if Run:
                    break
            except (ImportError, AttributeError):
                continue

        if not Run:
            return None  # pylint not available

        # Stdout capture — works for all versions
        out_buf = StringIO()
        with redirect_stdout(out_buf):
            try:
                Run([file, "--output-format=json", "--score=no", "--exit-zero"])
            except SystemExit:
                pass
            except TypeError:
                try:
                    Run([file, "--output-format=json"])
                except SystemExit:
                    pass
            except Exception:
                pass

        pylint_output = out_buf.getvalue()

        if not pylint_output.strip():
            return []

        try:
            data = json.loads(pylint_output)
            result = []
            for entry in data:
                result.append({
                    "file": entry.get("path") or file,
                    "line": entry.get("line"),
                    "column": entry.get("column"),
                    "type": entry.get("symbol"),
                    "message": entry.get("message"),
                    "severity": _map_pylint_severity(entry.get("type", "")),
                    "source": "pylint",
                })
            return result
        except (json.JSONDecodeError, TypeError):
            return []

    except ImportError:
        return None  # pylint not available
    except Exception:
        return []


def _run_ast_analysis(file: str) -> List[Dict]:
    """AST-based fallback analysis."""
    issues = []

    try:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

        tree = ast.parse(content, filename=file)

        # Check for missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not ast.get_docstring(node):
                    issues.append({
                        "file": file,
                        "line": node.lineno,
                        "type": "missing-function-docstring",
                        "message": f"Function '{node.name}' missing docstring",
                        "severity": "convention",
                        "source": "ast",
                    })
            elif isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    issues.append({
                        "file": file,
                        "line": node.lineno,
                        "type": "missing-class-docstring",
                        "message": f"Class '{node.name}' missing docstring",
                        "severity": "convention",
                        "source": "ast",
                    })

        # Check trailing whitespace
        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                issues.append({
                    "file": file,
                    "line": i,
                    "type": "trailing-whitespace",
                    "message": "Trailing whitespace",
                    "severity": "convention",
                    "source": "ast",
                })

        # Check missing final newline
        if content and not content.endswith("\n"):
            issues.append({
                "file": file,
                "line": len(lines),
                "type": "missing-final-newline",
                "message": "Missing final newline",
                "severity": "convention",
                "source": "ast",
            })

    except SyntaxError as e:
        issues.append({
            "file": file,
            "line": e.lineno,
            "type": "syntax-error",
            "message": str(e),
            "severity": "error",
            "source": "ast",
        })
    except Exception:
        pass

    return issues


def _map_pylint_severity(pylint_type: str) -> str:
    """Pylint type → severity map karo."""
    mapping = {
        "E": "error",
        "W": "warning",
        "C": "convention",
        "R": "refactor",
        "I": "info",
    }
    return mapping.get(pylint_type[:1].upper(), "info")


def analyze_single_file(file_path: str) -> Dict:
    """Single file analysis with summary."""
    issues = run_static_analysis([file_path])

    severity_count = {}
    for issue in issues:
        sev = issue.get("severity", "unknown")
        severity_count[sev] = severity_count.get(sev, 0) + 1

    return {
        "file": file_path,
        "total_issues": len(issues),
        "severity_breakdown": severity_count,
        "issues": issues,
        "has_errors": severity_count.get("error", 0) > 0,
    }
