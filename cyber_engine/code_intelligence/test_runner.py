"""
Chhoti Don EvolveX - Test Runner
Advanced test execution with pytest integration,
coverage tracking, and result analysis.
Phase 2.2 - Full Upgrade
"""

import subprocess
import os
import time
import datetime
from typing import Dict, List, Tuple, Tuple

class TestRunner:
    """
    Advanced Test Runner with full pytest integration.
    """

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.run_history = []

    def run_tests(
        self,
        test_path: str = None,
        verbose: bool = False,
        coverage: bool = False,
        timeout: int = 120,
    ) -> Tuple[bool, str]:
        """
        Run pytest and return result.
        Preserved + upgraded.

        Returns:
            (success: bool, output: str)
        """
        cmd = ["pytest"]

        if test_path:
            cmd.append(test_path)
        else:
            cmd.append(self.project_path)

        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        cmd.extend(["--tb=short", "--no-header"])

        if coverage:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=timeout,
            )

            output = result.stdout + result.stderr
            success = result.returncode == 0

            # Log result
            self.run_history.append({
                "success": success,
                "timestamp": time.time(),
                "returncode": result.returncode,
            })

            return success, output

        except subprocess.TimeoutExpired:
            return False, f"Tests timed out after {timeout}s"
        except FileNotFoundError:
            return False, "pytest not found. Install: pip install pytest"
        except Exception as e:
            return False, str(e)

    def run_single_test(self, test_file: str, test_name: str = None) -> Dict:
        """Single test file ya specific test run karo."""
        cmd = ["pytest", test_file]
        if test_name:
            cmd.extend(["-k", test_name])
        cmd.extend(["-v", "--tb=long"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout + result.stderr,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"success": False, "output": str(e)}

    def parse_test_results(self, output: str) -> Dict:
        """Test output parse karo."""
        import re

        passed = len(re.findall(r"\d+ passed", output))
        failed = len(re.findall(r"\d+ failed", output))
        errors = len(re.findall(r"\d+ error", output))
        warnings = len(re.findall(r"\d+ warning", output))

        # Extract counts
        pass_match = re.search(r"(\d+) passed", output)
        fail_match = re.search(r"(\d+) failed", output)
        error_match = re.search(r"(\d+) error", output)

        return {
            "passed": int(pass_match.group(1)) if pass_match else 0,
            "failed": int(fail_match.group(1)) if fail_match else 0,
            "errors": int(error_match.group(1)) if error_match else 0,
            "warnings": warnings,
            "overall": "passed" if failed == 0 and errors == 0 else "failed",
        }

    def get_test_files(self) -> List[str]:
        """Test files discover karo."""
        test_files = []
        for root, _, files in os.walk(self.project_path):
            for f in files:
                if f.startswith("test_") and f.endswith(".py"):
                    test_files.append(os.path.join(root, f))
        return test_files

    def run_with_report(self) -> Dict:
        """Full test run with detailed report."""
        start_time = time.time()
        test_files = self.get_test_files()

        success, output = self.run_tests(verbose=True)
        parsed = self.parse_test_results(output)

        return {
            "success": success,
            "output": output[:3000],
            "parsed_results": parsed,
            "test_files_found": len(test_files),
            "duration_sec": round(time.time() - start_time, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def get_run_history(self) -> List[Dict]:
        """Test run history."""
        return self.run_history

    def get_pass_rate(self) -> float:
        """Overall pass rate calculate karo."""
        if not self.run_history:
            return 0.0
        passed = sum(1 for r in self.run_history if r.get("success"))
        return round(passed / len(self.run_history) * 100, 1)
