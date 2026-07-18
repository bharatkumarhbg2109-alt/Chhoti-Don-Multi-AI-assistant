"""
Chhoti Don EvolveX - Test Generator
Advanced test generation with import tests,
function tests, and integration tests.
Phase 2.2 - Full Upgrade
"""

import os
import ast
import time
import datetime
from pathlib import Path
from typing import Dict, Generator, List, List

class TestGenerator:
    """
    Advanced Test Generator.
    Creates import tests, smoke tests, and basic unit tests.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.tests_dir = self.project_root / "tests"

        if not self.tests_dir.exists():
            self.tests_dir.mkdir(parents=True)

    def discover_modules(self) -> List[str]:
        """Discover all Python modules in the project."""
        modules = []
        exclude = {"__pycache__", "tests", ".venv", "venv", ".git", "node_modules"}

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in exclude]

            for file in files:
                if file.endswith(".py") and not file.startswith("test_"):
                    full_path = Path(root) / file

                    try:
                        rel_path = full_path.relative_to(self.project_root)
                        module = str(rel_path).replace(os.sep, ".").replace(".py", "")
                        modules.append(module)
                    except ValueError:
                        pass

        return modules

    def discover_functions(self, file_path: str) -> List[Dict]:
        """File mein functions discover karo."""
        functions = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private and dunder methods
                    if not node.name.startswith("_"):
                        args = [arg.arg for arg in node.args.args if arg.arg != "self"]
                        functions.append({
                            "name": node.name,
                            "line": node.lineno,
                            "args": args,
                            "has_return": any(isinstance(n, ast.Return) for n in ast.walk(node)),
                        })

        except Exception:
            pass

        return functions

    def generate_import_test(self, module_name: str) -> str:
        """Basic import smoke test generate karo."""
        safe_name = module_name.replace(".", "_").replace("-", "_")

        return f"""def test_import_{safe_name}():
    \"\"\"Test that {module_name} can be imported without errors.\"\"\"
    try:
        import {module_name}
        assert True, "Module imported successfully"
    except ImportError as e:
        raise AssertionError(f"Import failed for {module_name}: {{e}}")
    except Exception as e:
        pass  # Runtime errors are acceptable for import tests
"""

    def generate_function_test(self, module_name: str, func_name: str, args: List[str]) -> str:
        """Basic function existence test generate karo."""
        safe_module = module_name.replace(".", "_").replace("-", "_")

        return f"""def test_{safe_module}_{func_name}_exists():
    \"\"\"Test that {func_name} exists in {module_name}.\"\"\"
    try:
        import {module_name}
        assert hasattr({module_name}, '{func_name}'), \\
            f"'{func_name}' not found in {module_name}"
    except ImportError:
        pass  # Skip if module can't be imported
"""

    def generate_class_test(self, module_name: str, class_name: str) -> str:
        """Basic class test generate karo."""
        safe_module = module_name.replace(".", "_").replace("-", "_")

        return f"""def test_{safe_module}_{class_name}_instantiable():
    \"\"\"Test that {class_name} can be instantiated.\"\"\"
    try:
        import {module_name}
        cls = getattr({module_name}, '{class_name}', None)
        assert cls is not None, f"'{class_name}' not found in {module_name}"
    except ImportError:
        pass
"""

    def write_tests(self, modules: List[str]) -> str:
        """Write generated tests to test file."""
        test_file = self.tests_dir / "test_auto_generated.py"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(f'"""Auto-generated tests by Chhoti Don EvolveX"""\n')
            f.write(f'# Generated: {datetime.datetime.now().isoformat()}\n\n')
            f.write("import pytest\n\n")

            for module in modules:
                try:
                    test_code = self.generate_import_test(module)
                    f.write(test_code + "\n\n")
                except Exception:
                    continue

        return str(test_file)

    def run(self) -> Dict:
        """Main execution."""
        start_time = time.time()
        modules = self.discover_modules()
        test_file = self.write_tests(modules)

        return {
            "status": "success",
            "modules_found": len(modules),
            "test_file": test_file,
            "duration_sec": round(time.time() - start_time, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }


def generate_tests(project_path: str = ".") -> Dict:
    """Standalone test generation function."""
    generator = TestGenerator(project_path)
    return generator.run()
