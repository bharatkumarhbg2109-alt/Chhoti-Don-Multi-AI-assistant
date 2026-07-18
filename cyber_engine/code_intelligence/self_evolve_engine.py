"""
Chhoti Don EvolveX - Self Evolve Engine
Advanced self-improvement cycle with observation,
fixing, testing, and learning.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Dict, List, List

from.observer import Observer
from .behavior_tracker import get_project_health, get_fix_effectiveness
from .ast_fix_engine import ASTFixEngine


class SelfEvolveEngine:
    """
    Advanced Self-Evolution Engine.
    Observe → Fix → Test → Learn → Repeat
    """

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.observer = Observer(project_path)
        self.tester = TestRunner(project_path)
        self.ast_engine = ASTFixEngine()
        self.cycle_log = []
        self.max_cycles = 3

    # ==================================================
    # 🚀 Main Evolution Cycle
    # ==================================================
    def run_cycle(self, max_cycles: int = None) -> Dict:
        """
        Full self-evolution cycle.

        Returns:
            Evolution report
        """
        cycles = max_cycles or self.max_cycles
        start_time = time.time()
        all_results = []

        print("[SelfEvolve] Starting evolution cycle...")

        for cycle_num in range(1, cycles + 1):
            print(f"\n[SelfEvolve] === Cycle {cycle_num}/{cycles} ===")

            result = self._single_cycle(cycle_num)
            all_results.append(result)
            self.cycle_log.append(result)

            # Stop if system is healthy
            if result.get("system_healthy"):
                print("[SelfEvolve] System healthy — stopping early")
                break

            # Stop if no progress
            if result.get("fixes_applied", 0) == 0 and cycle_num > 1:
                print("[SelfEvolve] No progress — stopping")
                break

        # Final health check
        final_health = get_project_health(self.project_path)
        final_effectiveness = get_fix_effectiveness()

        duration = round(time.time() - start_time, 3)

        return {
            "status": "complete",
            "cycles_run": len(all_results),
            "cycle_results": all_results,
            "final_health": final_health,
            "fix_effectiveness": final_effectiveness,
            "total_duration_sec": duration,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _single_cycle(self, cycle_num: int) -> Dict:
        """Single evolution cycle."""
        cycle_start = time.time()

        # Step 1: Observe
        print(f"[SelfEvolve] Step 1: Observing...")
        issues = self.observer.observe()

        if not issues:
            print("[SelfEvolve] System healthy — no issues found")
            return {
                "cycle": cycle_num,
                "system_healthy": True,
                "issues_found": 0,
                "fixes_applied": 0,
                "tests_passed": None,
            }

        print(f"[SelfEvolve] Found {len(issues)} issue type(s)")

        # Step 2: Fix
        print(f"[SelfEvolve] Step 2: Fixing...")
        fixes_applied = 0

        from .fix_rules import FIXABLE_SYMBOLS
        from .static_analysis import run_static_analysis

        # Get fixable issues from static analysis
        python_files = self._get_python_files()
        if python_files:
            static_issues = run_static_analysis(python_files)
            fixable = [i for i in static_issues if i.get("type") in FIXABLE_SYMBOLS]
            if fixable:
                fixes_applied = run_auto_fix(fixable)
                print(f"[SelfEvolve] Applied {fixes_applied} fixes")

        # Step 3: AST fixes (NEW)
        print(f"[SelfEvolve] Step 3: AST Analysis...")
        ast_issues = 0
        try:
            ast_report = self.ast_engine.analyze_project(self.project_path)
            ast_issues = ast_report.get("total_issues", 0)
        except Exception:
            pass

        # Step 4: Test
        print(f"[SelfEvolve] Step 4: Testing...")
        tests_passed = None
        test_output = ""

        try:
            success, output = self.tester.run_tests()
            tests_passed = success
            test_output = output[:500]
            print(f"[SelfEvolve] Tests: {'✅ PASSED' if success else '❌ FAILED'}")
        except Exception as e:
            print(f"[SelfEvolve] Tests skipped: {e}")

        duration = round(time.time() - cycle_start, 3)

        return {
            "cycle": cycle_num,
            "system_healthy": False,
            "issues_found": len(issues),
            "fixes_applied": fixes_applied,
            "ast_issues": ast_issues,
            "tests_passed": tests_passed,
            "test_output": test_output,
            "duration_sec": duration,
        }

    def _get_python_files(self) -> List[str]:
        """Python files discover karo."""
        import os
        py_files = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if "__pycache__" not in d]
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
        return py_files

    def get_evolution_history(self) -> List[Dict]:
        """Evolution cycle history."""
        return self.cycle_log

    def get_health_trend(self) -> Dict:
        """Health trend from cycle log."""
        if not self.cycle_log:
            return {"trend": "no_data"}

        fix_counts = [c.get("fixes_applied", 0) for c in self.cycle_log]
        if len(fix_counts) >= 2:
            if fix_counts[-1] < fix_counts[0]:
                trend = "improving"
            elif fix_counts[-1] > fix_counts[0]:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "cycles": len(self.cycle_log),
            "total_fixes": sum(fix_counts),
        }
