"""
Chhoti Don - AST Fix Engine
Advanced Abstract Syntax Tree based code analysis and fixing.
Handles complex code transformations using Python's AST module.
Phase 2.2 - Full Implementation
"""

import ast
import os
import re
import time
import datetime
from typing import Dict, List, Optional, Tuple, Any
# 🎯 AST TRANSFORMATION RULES
# ==================================================

AST_FIXABLE_ISSUES = {
    "undefined-variable",
    "unused-variable",
    "redundant-return",
    "bare-except",
    "comparison-to-none",
    "comparison-to-true",
    "unnecessary-pass",
    "empty-function-body",
    "missing-return-type",
    "duplicate-code",
    "long-line",
    "complex-function",
}


class ASTAnalyzer(ast.NodeVisitor):
    """
    Advanced AST analyzer — walks the tree and collects issues.
    """

    def __init__(self, source: str, file_path: str = "unknown"):
        self.source = source
        self.file_path = file_path
        self.issues = []
        self.functions = []
        self.classes = []
        self.imports = []
        self.variables = {}
        self.undefined_vars = []
        self.complexity_map = {}

    def analyze(self) -> Dict:
        """Full AST analysis."""
        try:
            tree = ast.parse(self.source)
            self.visit(tree)

            return {
                "status": "success",
                "file": self.file_path,
                "issues": self.issues,
                "functions": self.functions,
                "classes": self.classes,
                "imports": self.imports,
                "complexity": self.complexity_map,
                "total_issues": len(self.issues),
            }
        except SyntaxError as e:
            return {
                "status": "syntax_error",
                "file": self.file_path,
                "error": str(e),
                "line": e.lineno,
            }
        except Exception as e:
            return {
                "status": "error",
                "file": self.file_path,
                "error": str(e),
            }

    # --------------------------------------------------
    # 🔍 Visitor Methods
    # --------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analyze function definitions."""
        complexity = self._calculate_complexity(node)
        self.complexity_map[node.name] = complexity

        func_info = {
            "name": node.name,
            "line": node.lineno,
            "args": [arg.arg for arg in node.args.args],
            "complexity": complexity,
            "has_docstring": ast.get_docstring(node) is not None,
            "has_return": any(isinstance(n, ast.Return) for n in ast.walk(node)),
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
        }
        self.functions.append(func_info)

        # High complexity warning
        if complexity > 10:
            self.issues.append({
                "type": "complex-function",
                "file": self.file_path,
                "line": node.lineno,
                "message": f"Function '{node.name}' has high complexity ({complexity})",
                "severity": "warning",
                "fixable": False,
            })

        # Missing docstring
        if not func_info["has_docstring"]:
            self.issues.append({
                "type": "missing-function-docstring",
                "file": self.file_path,
                "line": node.lineno,
                "message": f"Function '{node.name}' missing docstring",
                "severity": "convention",
                "fixable": True,
            })

        # Empty function body (only pass)
        body_nodes = [n for n in node.body if not isinstance(n, ast.Expr)]
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.issues.append({
                "type": "empty-function-body",
                "file": self.file_path,
                "line": node.lineno,
                "message": f"Function '{node.name}' has empty body",
                "severity": "warning",
                "fixable": True,
            })

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Analyze async function definitions."""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Analyze class definitions."""
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "bases": [self._get_name(b) for b in node.bases],
            "has_docstring": ast.get_docstring(node) is not None,
            "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
        })

        if not ast.get_docstring(node):
            self.issues.append({
                "type": "missing-class-docstring",
                "file": self.file_path,
                "line": node.lineno,
                "message": f"Class '{node.name}' missing docstring",
                "severity": "convention",
                "fixable": True,
            })

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Track imports."""
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "type": "import",
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        self.imports.append({
            "module": node.module,
            "names": [alias.name for alias in node.names],
            "line": node.lineno,
            "type": "from_import",
        })
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        """Detect bare except clauses."""
        for handler in node.handlers:
            if handler.type is None:
                self.issues.append({
                    "type": "bare-except",
                    "file": self.file_path,
                    "line": handler.lineno,
                    "message": "Bare except clause — catches all exceptions",
                    "severity": "warning",
                    "fixable": True,
                })
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        """Detect comparison anti-patterns."""
        for op, comparator in zip(node.ops, node.comparators):
            # comparison to None with == instead of is
            if isinstance(comparator, ast.Constant) and comparator.value is None:
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    self.issues.append({
                        "type": "comparison-to-none",
                        "file": self.file_path,
                        "line": node.lineno,
                        "message": "Use 'is None' or 'is not None' instead of == None",
                        "severity": "convention",
                        "fixable": True,
                    })

            # comparison to True/False
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, bool):
                if isinstance(op, ast.Eq):
                    self.issues.append({
                        "type": "comparison-to-true",
                        "file": self.file_path,
                        "line": node.lineno,
                        "message": "Don't compare to True/False explicitly",
                        "severity": "convention",
                        "fixable": True,
                    })

        self.generic_visit(node)

    # --------------------------------------------------
    # 🔧 Helpers
    # --------------------------------------------------
    def _calculate_complexity(self, node) -> int:
        """Cyclomatic complexity calculate karo."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                  ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _get_name(self, node) -> str:
        """AST node se name extract karo."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "unknown"

    def _get_decorator_name(self, node) -> str:
        """Decorator name extract karo."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return "unknown"


# ==================================================
# 🔧 AST FIX ENGINE
# ==================================================

class ASTFixEngine:
    """
    Advanced AST-based code fix engine.
    Applies safe, syntax-aware transformations.
    """

    def __init__(self):
        self.fixes_applied = 0
        self.fix_log = []

    # --------------------------------------------------
    # 🚀 Main Fix Function
    # --------------------------------------------------
    def fix_file(self, file_path: str, issues: List[Dict] = None) -> Dict:
        """
        Apply AST-based fixes to a file.

        Args:
            file_path: Path to Python file
            issues: Optional pre-analyzed issues list

        Returns:
            Fix result dict
        """
        start_time = time.time()

        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except Exception as e:
            return {"status": "error", "message": str(e)}

        # Analyze if issues not provided
        if issues is None:
            analyzer = ASTAnalyzer(original_content, file_path)
            analysis = analyzer.analyze()
            if analysis["status"] != "success":
                return analysis
            issues = analysis["issues"]

        # Apply fixes
        modified_content = original_content
        fixes = []

        for issue in issues:
            if not issue.get("fixable"):
                continue

            issue_type = issue.get("type")
            line_no = issue.get("line", 0)

            try:
                new_content = self._apply_ast_fix(
                    modified_content, issue_type, line_no, issue
                )
                if new_content != modified_content:
                    modified_content = new_content
                    fixes.append({
                        "type": issue_type,
                        "line": line_no,
                        "status": "applied",
                    })
            except Exception as e:
                fixes.append({
                    "type": issue_type,
                    "line": line_no,
                    "status": "failed",
                    "error": str(e),
                })

        # Validate syntax before writing
        if modified_content != original_content:
            try:
                ast.parse(modified_content)
            except SyntaxError as e:
                return {
                    "status": "error",
                    "message": f"AST fix introduced syntax error: {e}",
                    "file": file_path,
                }

            # Write fixed content
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)
            except Exception as e:
                return {"status": "error", "message": str(e)}

        return {
            "status": "success",
            "file": file_path,
            "fixes_applied": len([f for f in fixes if f["status"] == "applied"]),
            "fixes_failed": len([f for f in fixes if f["status"] == "failed"]),
            "fix_log": fixes,
            "modified": modified_content != original_content,
            "analysis_time_sec": round(time.time() - start_time, 3),
        }

    # --------------------------------------------------
    # 🔧 Fix Router
    # --------------------------------------------------
    def _apply_ast_fix(self, content: str, issue_type: str, line_no: int, issue: Dict) -> str:
        """Fix type ke hisaab se appropriate fix apply karo."""
        fixers = {
            "bare-except": self._fix_bare_except,
            "comparison-to-none": self._fix_comparison_to_none,
            "comparison-to-true": self._fix_comparison_to_true,
            "empty-function-body": self._fix_empty_function,
            "missing-function-docstring": self._fix_missing_docstring,
            "missing-class-docstring": self._fix_missing_class_docstring,
            "unnecessary-pass": self._fix_unnecessary_pass,
        }

        fixer = fixers.get(issue_type)
        if fixer:
            return fixer(content, line_no, issue)

        return content

    # --------------------------------------------------
    # 🔧 Individual Fixers
    # --------------------------------------------------
    def _fix_bare_except(self, content: str, line_no: int, issue: Dict) -> str:
        """Bare except → except Exception karo."""
        lines = content.splitlines()
        if line_no and 0 < line_no <= len(lines):
            line = lines[line_no - 1]
            if re.match(r"\s*except\s*:", line):
                lines[line_no - 1] = line.replace("except:", "except Exception:")
        return "\n".join(lines)

    def _fix_comparison_to_none(self, content: str, line_no: int, issue: Dict) -> str:
        """== None → is None, != None → is not None."""
        lines = content.splitlines()
        if line_no and 0 < line_no <= len(lines):
            line = lines[line_no - 1]
            line = re.sub(r"==\s*None", "is None", line)
            line = re.sub(r"!=\s*None", "is not None", line)
            lines[line_no - 1] = line
        return "\n".join(lines)

    def _fix_comparison_to_true(self, content: str, line_no: int, issue: Dict) -> str:
        """== True → (truthy check), == False → not."""
        lines = content.splitlines()
        if line_no and 0 < line_no <= len(lines):
            line = lines[line_no - 1]
            line = re.sub(r"==\s*True\b", "is True", line)
            line = re.sub(r"==\s*False\b", "is False", line)
            lines[line_no - 1] = line
        return "\n".join(lines)

    def _fix_empty_function(self, content: str, line_no: int, issue: Dict) -> str:
        """Empty function body mein TODO comment add karo."""
        lines = content.splitlines()
        if line_no and 0 < line_no <= len(lines):
            # Find the pass statement after function def
            for i in range(line_no - 1, min(line_no + 5, len(lines))):
                if lines[i].strip() == "pass":
                    indent = re.match(r"\s*", lines[i]).group()
                    lines[i] = f"{indent}# TODO: Implement this function\n{indent}pass"
                    break
        return "\n".join(lines)

    def _fix_missing_docstring(self, content: str, line_no: int, issue: Dict) -> str:
        """Function ke baad docstring add karo."""
        lines = content.splitlines()
        if not line_no or line_no > len(lines):
            return content

        def_line = line_no - 1
        if def_line >= len(lines):
            return content

        # Find next line after def
        insert_at = def_line + 1
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1

        # Check if docstring already exists
        if insert_at < len(lines) and lines[insert_at].strip().startswith('"""'):
            return content

        # Get indentation
        indent = re.match(r"\s*", lines[def_line]).group() + "    "

        # Extract function name for better docstring
        func_match = re.search(r"def\s+(\w+)\s*\(", lines[def_line])
        func_name = func_match.group(1) if func_match else "function"

        docstring = f'{indent}"""{func_name.replace("_", " ").title()} function."""'
        lines.insert(insert_at, docstring)

        return "\n".join(lines)

    def _fix_missing_class_docstring(self, content: str, line_no: int, issue: Dict) -> str:
        """Class ke baad docstring add karo."""
        lines = content.splitlines()
        if not line_no or line_no > len(lines):
            return content

        class_line = line_no - 1
        insert_at = class_line + 1

        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1

        if insert_at < len(lines) and lines[insert_at].strip().startswith('"""'):
            return content

        indent = re.match(r"\s*", lines[class_line]).group() + "    "

        class_match = re.search(r"class\s+(\w+)", lines[class_line])
        class_name = class_match.group(1) if class_match else "class"

        docstring = f'{indent}"""{class_name} class."""'
        lines.insert(insert_at, docstring)

        return "\n".join(lines)

    def _fix_unnecessary_pass(self, content: str, line_no: int, issue: Dict) -> str:
        """Unnecessary pass statements remove karo."""
        lines = content.splitlines()
        if line_no and 0 < line_no <= len(lines):
            line = lines[line_no - 1]
            if line.strip() == "pass":
                # Check if it's the only statement
                prev_line = lines[line_no - 2].strip() if line_no > 1 else ""
                next_line = lines[line_no].strip() if line_no < len(lines) else ""
                if prev_line.endswith(":") and (not next_line or next_line.startswith("#")):
                    return content  # Keep pass — function/class needs it
                lines.pop(line_no - 1)
        return "\n".join(lines)

    # --------------------------------------------------
    # 📊 Analysis Functions
    # --------------------------------------------------
    def analyze_file(self, file_path: str) -> Dict:
        """File analyze karo without fixing."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            analyzer = ASTAnalyzer(content, file_path)
            return analyzer.analyze()

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def analyze_project(self, project_path: str) -> Dict:
        """Full project AST analysis."""
        results = []
        total_issues = 0
        total_functions = 0
        high_complexity = []

        for root, _, files in os.walk(project_path):
            if "__pycache__" in root:
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue

                file_path = os.path.join(root, file)
                result = self.analyze_file(file_path)

                if result.get("status") == "success":
                    total_issues += result.get("total_issues", 0)
                    total_functions += len(result.get("functions", []))

                    for func_name, complexity in result.get("complexity", {}).items():
                        if complexity > 10:
                            high_complexity.append({
                                "file": file_path,
                                "function": func_name,
                                "complexity": complexity,
                            })

                    results.append(result)

        return {
            "status": "success",
            "files_analyzed": len(results),
            "total_issues": total_issues,
            "total_functions": total_functions,
            "high_complexity_functions": high_complexity,
            "results": results,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def get_code_metrics(self, file_path: str) -> Dict:
        """Code quality metrics calculate karo."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            tree = ast.parse(content)

            total_lines = len(lines)
            blank_lines = sum(1 for l in lines if not l.strip())
            comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
            code_lines = total_lines - blank_lines - comment_lines

            functions = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
            classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            imports = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)))

            avg_func_length = code_lines / max(functions, 1)

            return {
                "file": file_path,
                "total_lines": total_lines,
                "code_lines": code_lines,
                "blank_lines": blank_lines,
                "comment_lines": comment_lines,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "avg_function_length": round(avg_func_length, 1),
                "maintainability": self._calculate_maintainability(
                    code_lines, functions, blank_lines
                ),
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _calculate_maintainability(self, code_lines: int, functions: int, blank_lines: int) -> str:
        """Maintainability index calculate karo."""
        if code_lines == 0:
            return "N/A"

        blank_ratio = blank_lines / max(code_lines, 1)
        avg_size = code_lines / max(functions, 1)

        if blank_ratio >= 0.2 and avg_size <= 30:
            return "Excellent"
        elif blank_ratio >= 0.1 and avg_size <= 50:
            return "Good"
        elif avg_size <= 100:
            return "Fair"
        else:
            return "Poor"


# ==================================================
# 🔧 STANDALONE FUNCTIONS
# ==================================================

def analyze_ast(file_path: str) -> Dict:
    """Standalone AST analysis function."""
    engine = ASTFixEngine()
    return engine.analyze_file(file_path)


def fix_ast_issues(file_path: str) -> Dict:
    """Standalone AST fix function."""
    engine = ASTFixEngine()
    return engine.fix_file(file_path)


def get_code_metrics(file_path: str) -> Dict:
    """Standalone code metrics function."""
    engine = ASTFixEngine()
    return engine.get_code_metrics(file_path)
