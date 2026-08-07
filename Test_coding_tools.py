"""
Chhoti Don - Coding Tools Test Suite
Advanced test runner for all coding tools.
Tests: code_generator, code_executor, code_debugger
Run: python Test_coding_tools.py
Phase 2.2 - Full Upgrade
"""

import sys
import os
import time
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.code_generator import generate_code
from tools.code_executor import execute_code
from tools.code_debugger import debug_code, explain_code


# ==================================================
# 🎨 CONSOLE HELPERS
# ==================================================

class Colors:
    """Class Description"""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(title: str, num: int = None) -> None:
    num_str = f"[TEST {num:02d}] " if num else ""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 58}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🧪 {num_str}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 58}{Colors.RESET}")


def print_result(result: dict, show_full: bool = False) -> None:
    status = result.get("status", "unknown")
    icon = "✅" if status == "success" else "❌"
    color = Colors.GREEN if status == "success" else Colors.RED

    print(f"\n  {icon} {color}Status  : {status.upper()}{Colors.RESET}")

    for key, value in result.items():
        if key == "status":
            continue
        if value is None:
            continue

        if isinstance(value, str):
            if not show_full and len(value) > 400:
                value = value[:400] + f"\n  {Colors.YELLOW}...[truncated]{Colors.RESET}"
        elif isinstance(value, (list, dict)):
            value = str(value)[:300]

        print(f"  {Colors.BLUE}📌 {key:<20}{Colors.RESET}: {value}")


def print_section(title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}  ▶ {title}{Colors.RESET}")


# ==================================================
# 📊 TEST TRACKER
# ==================================================

    """Class Description"""
class TestTracker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
        self.start_time = time.time()

    def record(self, name: str, result: dict) -> None:
        status = result.get("status", "unknown")
        success = status == "success"
        if success:
            self.passed += 1
        else:
            self.failed += 1

        self.results.append({
            "name": name,
            "status": status,
            "success": success,
        })

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        self.results.append({
            "name": name,
            "status": "skipped",
            "reason": reason,
        })

    def summary(self) -> None:
        duration = round(time.time() - self.start_time, 2)
        total = self.passed + self.failed + self.skipped

        print(f"\n{Colors.BOLD}{'=' * 58}{Colors.RESET}")
        print(f"{Colors.BOLD}  📊 TEST SUMMARY{Colors.RESET}")
        print(f"{'=' * 58}")
        print(f"  {Colors.GREEN}✅ Passed  : {self.passed}/{total}{Colors.RESET}")
        print(f"  {Colors.RED}❌ Failed  : {self.failed}/{total}{Colors.RESET}")
        if self.skipped:
            print(f"  {Colors.YELLOW}⏭️  Skipped : {self.skipped}/{total}{Colors.RESET}")
        print(f"  ⏱️  Duration: {duration}s")
        print(f"  🕐 Time    : {datetime.datetime.now().strftime('%H:%M:%S')}")

        if self.failed == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! Coding Engine Ready!{Colors.RESET}")
        else:
            print(f"\n  {Colors.YELLOW}⚠️  {self.failed} test(s) failed — check output above{Colors.RESET}")
            print(f"\n  Failed tests:")
            for r in self.results:
                if not r.get("success") and r.get("status") != "skipped":
                    print(f"    ❌ {r['name']}")

        print(f"{'=' * 58}\n")


tracker = TestTracker()


# ==================================================
# 🧪 CODE GENERATOR TESTS
# ==================================================

print_section("CODE GENERATOR TESTS")

# Test 1 — Python
print_header("GENERATE CODE — Python Calculator", 1)
result = generate_code({
    "prompt": "ek simple calculator banao jo add, subtract, multiply aur divide kare",
    "language": "python"
})
print_result(result)
tracker.record("Generate Python", result)

# Test 2 — JavaScript
print_header("GENERATE CODE — JavaScript Array Sum", 2)
result = generate_code({
    "prompt": "array of numbers ka sum nikalo using reduce",
    "language": "javascript"
})
print_result(result)
tracker.record("Generate JavaScript", result)

# Test 3 — Auto-detect Bash
print_header("GENERATE CODE — Auto Detect Bash", 3)
result = generate_code({
    "prompt": "write a bash script to list all .py files recursively"
})
print_result(result)
tracker.record("Generate Bash (auto-detect)", result)

# Test 4 — SQL
print_header("GENERATE CODE — SQL Query", 4)
result = generate_code({
    "prompt": "write SQL to find top 5 employees by salary with their department",
    "language": "sql"
})
print_result(result)
tracker.record("Generate SQL", result)

# Test 5 — Python Class
print_header("GENERATE CODE — Python Class", 5)
result = generate_code({
    "prompt": "create a Student class with name, age, marks attributes and a method to calculate grade",
    "language": "python"
})
print_result(result)
tracker.record("Generate Python Class", result)


# ==================================================
# 🚀 CODE EXECUTOR TESTS
# ==================================================

print_section("CODE EXECUTOR TESTS")

# Test 6 — Python Basic
print_header("EXECUTE CODE — Python Basic", 6)
result = execute_code({
    "code": """
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
total = sum(numbers)
avg = total / len(numbers)
evens = [n for n in numbers if n % 2 == 0]
print(f"Sum: {total}")
print(f"Average: {avg}")
print(f"Even numbers: {evens}")
""",
    "language": "python"
})
print_result(result)
tracker.record("Execute Python Basic", result)

# Test 7 — Python Math
print_header("EXECUTE CODE — Python Fibonacci", 7)
result = execute_code({
    "code": """
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        print(a, end=" ")
        a, b = b, a + b
    print()

fibonacci(10)
print("Fibonacci sequence complete!")
""",
    "language": "python"
})
print_result(result)
tracker.record("Execute Python Fibonacci", result)

# Test 8 — Python Error Handling
print_header("EXECUTE CODE — Python Error (Expected Fail)", 8)
result = execute_code({
    "code": """
x = 10
y = 0
result = x / y  # ZeroDivisionError expected
print(result)
""",
    "language": "python"
})
print_result(result)
# execute_code SHOULD detect and report the runtime error — correctly
# reporting it (status="error", non-zero return code) is the pass condition.
error_detected = (
    isinstance(result, dict)
    and result.get("status") == "error"
    and result.get("return_code") not in (0, None)
)
tracker.record(
    "Execute Python Error (expected)",
    {"status": "success" if error_detected else "error"},
)

# Test 9 — SQL
print_header("EXECUTE CODE — SQL SQLite", 9)
result = execute_code({
    "code": """
CREATE TABLE students (id INTEGER, name TEXT, marks INTEGER, grade TEXT);
INSERT INTO students VALUES (1, 'Bharat', 95, 'A');
INSERT INTO students VALUES (2, 'Rahul', 88, 'B');
INSERT INTO students VALUES (3, 'Priya', 92, 'A');
INSERT INTO students VALUES (4, 'Amit', 75, 'C');
SELECT name, marks FROM students WHERE marks > 85 ORDER BY marks DESC;
""",
    "language": "sql"
})
print_result(result)
tracker.record("Execute SQL", result)

# Test 10 — Bash
print_header("EXECUTE CODE — Bash Script", 10)
result = execute_code({
    "code": """#!/bin/bash
echo "=== Chhoti Don Coding Engine ==="
echo "Date: $(date)"
echo "Python: $(python --version 2>&1 || python3 --version 2>&1)"
echo "Working Dir: $(pwd)"
echo "================================="
""",
    "language": "bash"
})
print_result(result)
tracker.record("Execute Bash", result)


# ==================================================
# 🐛 DEBUG CODE TESTS
# ==================================================

print_section("CODE DEBUGGER TESTS")

# Test 11 — NameError
print_header("DEBUG CODE — NameError Fix", 11)
result = debug_code({
    "code": """
def greet(name):
    message = "Hello " + nme  # typo: nme instead of name
    return message

print(greet("Bharat"))
""",
    "error": "NameError: name 'nme' is not defined",
    "language": "python"
})
print_result(result)
tracker.record("Debug NameError", result)

# Test 12 — ZeroDivisionError
print_header("DEBUG CODE — ZeroDivisionError Fix", 12)
result = debug_code({
    "code": """
def calculate_average(numbers):
    return sum(numbers) / len(numbers)

print(calculate_average([]))  # Empty list causes ZeroDivisionError
""",
    "error": "ZeroDivisionError: division by zero",
    "language": "python"
})
print_result(result)
tracker.record("Debug ZeroDivisionError", result)

# Test 13 — Logic Bug
print_header("DEBUG CODE — Logic Bug Fix", 13)
result = debug_code({
    "code": """
def is_palindrome(s):
    return s == s.reverse()  # Bug: strings don't have .reverse()

print(is_palindrome("racecar"))
""",
    "error": "AttributeError: 'str' object has no attribute 'reverse'",
    "language": "python"
})
print_result(result)
tracker.record("Debug AttributeError", result)


# ==================================================
# 📖 EXPLAIN CODE TESTS
# ==================================================

print_section("CODE EXPLAINER TESTS")

# Test 14 — Python Recursion
print_header("EXPLAIN CODE — Python Fibonacci Recursion", 14)
result = explain_code({
    "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(fibonacci(i), end=" ")
""",
    "language": "python",
    "detail_level": "simple"
})
print_result(result)
tracker.record("Explain Python Recursion", result)

# Test 15 — SQL Complex Query
print_header("EXPLAIN CODE — SQL Complex Query", 15)
result = explain_code({
    "code": """
SELECT department, 
       COUNT(*) as emp_count,
       AVG(salary) as avg_salary,
       MAX(salary) as max_salary
FROM employees
WHERE hire_date > '2020-01-01'
GROUP BY department
HAVING AVG(salary) > 50000
ORDER BY avg_salary DESC
LIMIT 5;
""",
    "language": "sql",
    "detail_level": "detailed"
})
print_result(result)
tracker.record("Explain SQL Query", result)

# Test 16 — Python OOP
print_header("EXPLAIN CODE — Python OOP", 16)
result = explain_code({
    "code": """
class Stack:
    def __init__(self):
        self.items = []
    
    def push(self, item):
        self.items.append(item)
    
    def pop(self):
        if not self.is_empty():
            return self.items.pop()
        raise IndexError("Stack is empty")
    
    def is_empty(self):
        return len(self.items) == 0
    
    def peek(self):
        return self.items[-1] if self.items else None
""",
    "language": "python",
    "detail_level": "detailed"
})
print_result(result)
tracker.record("Explain Python OOP", result)


# ==================================================
# 📊 FINAL SUMMARY
# ==================================================

tracker.summary()
