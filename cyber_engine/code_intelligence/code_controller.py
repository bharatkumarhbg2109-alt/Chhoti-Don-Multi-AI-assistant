"""
Chhoti Don EvolveX - Code Controller
Central orchestrator for all code intelligence operations.
Phase 2.2 - Full Upgrade
"""

import os
import time
import datetime
from .static_analysis import run_static_analysis
from .context_graph import build_dependency_graph, analyze_dependencies
from .report_builder import generate_report, generate_detailed_report
from .behavior_tracker import get_project_health, get_most_problematic_files, get_fix_effectiveness
from typing import Dict, List, List


class CodeController:
    """
    Central Code Intelligence Controller.
    Orchestrates all EvolveX operations.
    """

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.ast_engine = ASTFixEngine()
        self._session_log = []

    # ==================================================
    # 🚀 Main Pipeline
    # ==================================================
    def run_intelligence(self, project_path: str = None) -> Dict:
        """
        Full code intelligence pipeline.

        Args:
            project_path: Project root (uses self.project_path if None)

        Returns:
            Complete intelligence report
        """
        path = project_path or self.project_path
        return run_code_intelligence(path)

    def run_self_heal(self, project_path: str = None) -> Dict:
        """Run full self-healing loop."""
        path = project_path or self.project_path
        return run_full_self_heal(path)

    def fix_file(self, file_path: str) -> Dict:
        """Fix single file."""
        return fix_single_file(file_path)

    # ==================================================
    # 📊 Analysis
    # ==================================================
    def analyze_project(self) -> Dict:
        """Full project AST analysis."""
        return self.ast_engine.analyze_project(self.project_path)

    def get_health_report(self) -> Dict:
        """Project health report."""
        return get_project_health(self.project_path)

    def get_problematic_files(self, top_n: int = 5) -> List[Dict]:
        """Most problematic files."""
        return get_most_problematic_files(top_n)

    def get_statistics(self) -> Dict:
        """Full statistics."""
        return {
            "fix_stats": get_fix_statistics(),
            "health": get_project_health(self.project_path),
            "effectiveness": get_fix_effectiveness(),
            "problematic_files": get_most_problematic_files(3),
        }

    # ==================================================
    # 🔧 Backward Compat Methods
    # ==================================================
    def auto_fix(self, issues: List[Dict]) -> int:
        """Backward compatibility."""
        return run_auto_fix(issues)

    def full_self_heal(self, project_path: str = None) -> Dict:
        """Backward compatibility."""
        return self.run_self_heal(project_path)


# ==================================================
# 🔧 STANDALONE FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def run_code_intelligence(project_path: str) -> Dict:
    """
    Main code intelligence function.
    Preserved + upgraded with full pipeline.
    """
    print(f"[EvolveX] Starting Code Intelligence on: {project_path}")
    start_time = time.time()

    if not os.path.exists(project_path):
        print("[EvolveX] Invalid project path.")
        return {"status": "error", "message": "Invalid project path"}

    # Step 1: Discover Python files
    python_files = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if "__pycache__" not in d and ".git" not in d]
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    if not python_files:
        print("[EvolveX] No Python files found.")
        return {"status": "error", "message": "No Python files found"}

    print(f"[EvolveX] Found {len(python_files)} Python files")

    # Step 2: Static analysis
    print("[EvolveX] Running static analysis...")
    issues = run_static_analysis(python_files)

    # Step 3: AST analysis (NEW)
    print("[EvolveX] Running AST analysis...")
    ast_engine = ASTFixEngine()
    ast_report = ast_engine.analyze_project(project_path)

    # Step 4: Dependency graph
    print("[EvolveX] Building dependency graph...")
    dependency_graph = build_dependency_graph(python_files)
    dep_analysis = analyze_dependencies(dependency_graph)

    # Step 5: Health report
    health = get_project_health(project_path)

    # Step 6: Generate report
    generate_report(issues, dependency_graph)

    duration = round(time.time() - start_time, 3)

    return {
        "status": "success",
        "project_path": project_path,
        "files_analyzed": len(python_files),
        "issues_found": len(issues),
        "ast_issues": ast_report.get("total_issues", 0),
        "dependency_analysis": dep_analysis,
        "health": health,
        "duration_sec": duration,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
