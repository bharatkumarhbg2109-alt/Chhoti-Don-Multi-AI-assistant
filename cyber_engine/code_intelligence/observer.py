"""
Chhoti Don EvolveX - Observer
Advanced system observer with static analysis,
test monitoring, and health tracking.
Phase 2.2 - Full Upgrade
"""

import subprocess
import os
import time
from typing import Dict, List, Tuple, Tuple


class Observer:
    """
    Advanced System Observer.
    Monitors static analysis, tests, and system health.
    """

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.observation_log = []

    def observe_static(self) -> str:
        """Run static analysis and return output."""
        try:
            result = subprocess.run(
                ["python", "-m", "cyber_engine.code_intelligence.static_analysis"],
                capture_output=True, text=True, timeout=60
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "static_analysis_timeout"
        except Exception as e:
            return str(e)

    def observe_tests(self) -> str:
        """Run pytest and capture output."""
        try:
            result = subprocess.run(
                ["pytest", "-q", "--tb=short"],
                capture_output=True, text=True,
                cwd=self.project_path, timeout=120
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "pytest_timeout"
        except Exception as e:
            return str(e)

    def observe_syntax(self) -> List[Dict]:
        """Check syntax errors in all Python files."""
        import py_compile
        errors = []

        for root, _, files in os.walk(self.project_path):
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        py_compile.compile(file_path, doraise=True)
                    except py_compile.PyCompileError as e:
                        errors.append({
                            "file": file_path,
                            "error": str(e),
                            "type": "syntax_error",
                        })

        return errors

    def observe(self) -> List[Tuple]:
        """Full observation cycle."""
        issues = []
        timestamp = time.time()

        # Static analysis
        static_result = self.observe_static()
        if static_result and "error" in static_result.lower():
            issues.append(("static_analysis", static_result))

        # Test results
        test_result = self.observe_tests()
        if test_result and "failed" in test_result.lower():
            issues.append(("test_failure", test_result))

        # Syntax errors
        syntax_errors = self.observe_syntax()
        if syntax_errors:
            issues.append(("syntax_errors", syntax_errors))

        # Log observation
        self.observation_log.append({
            "timestamp": timestamp,
            "issues_found": len(issues),
            "types": [i[0] for i in issues],
        })

        return issues

    def get_observation_summary(self) -> Dict:
        """Observation history summary."""
        if not self.observation_log:
            return {"total_observations": 0}

        total = len(self.observation_log)
        with_issues = sum(1 for o in self.observation_log if o["issues_found"] > 0)

        return {
            "total_observations": total,
            "observations_with_issues": with_issues,
            "clean_rate": round((total - with_issues) / max(total, 1) * 100, 1),
            "last_observation": self.observation_log[-1],
        }
