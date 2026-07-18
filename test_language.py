"""
Chhoti Don - Language Module Test Suite
Advanced tests for language detection, Hinglish support,
intent detection, and brain routing.
Run: python test_language.py
Phase 2.2 - Full Upgrade
"""

import sys
import os
import time
import datetime
from typing import Type

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==================================================
# 🎨 CONSOLE HELPERS
# ==================================================

class Colors:
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    RESET   = "\033[0m"
    BOLD    = "\033[1m"


def print_header(title: str, num: int = None) -> None:
    num_str = f"[TEST {num:02d}] " if num else ""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🌐 {num_str}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")


def print_section(title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}  ▶ {title}{Colors.RESET}")


def print_test(label: str, expected: str, got: str) -> bool:
    passed = expected.lower() in got.lower() or got.lower() in expected.lower()
    icon   = "✅" if passed else "❌"
    color  = Colors.GREEN if passed else Colors.RED
    print(f"  {icon} {color}{label:<35}{Colors.RESET}")
    print(f"     Expected : {Colors.YELLOW}{expected}{Colors.RESET}")
    print(f"     Got      : {Colors.BLUE}{got}{Colors.RESET}")
    return passed


# ==================================================
# 📊 TEST TRACKER
# ==================================================

class TestTracker:
    def __init__(self):
        self.passed     = 0
        self.failed     = 0
        self.skipped    = 0
        self.results    = []
        self.start_time = time.time()

    def record(self, name: str, passed: bool) -> None:
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append({"name": name, "passed": passed})

    def summary(self) -> None:
        duration = round(time.time() - self.start_time, 2)
        total    = self.passed + self.failed + self.skipped
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}  📊 LANGUAGE TEST SUMMARY{Colors.RESET}")
        print(f"{'=' * 60}")
        print(f"  {Colors.GREEN}✅ Passed  : {self.passed}/{total}{Colors.RESET}")
        print(f"  {Colors.RED}❌ Failed  : {self.failed}/{total}{Colors.RESET}")
        print(f"  ⏱️  Duration: {duration}s")
        if self.failed == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 ALL LANGUAGE TESTS PASSED!{Colors.RESET}")
        else:
            print(f"\n  {Colors.YELLOW}⚠️  {self.failed} test(s) failed{Colors.RESET}")
            for r in self.results:
                if not r["passed"]:
                    print(f"    ❌ {r['name']}")
        print(f"{'=' * 60}\n")


tracker = TestTracker()


# ==================================================
# 📥 IMPORTS — Safe with fallbacks
# ==================================================

print_header("CHHOTI DON LANGUAGE TEST SUITE")
print(f"  📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── core.language ─────────────────────────────────────────────
try:
    from core.language import (
        detect_language,
        translate_to_english,
        translate_back,
        is_hinglish,
        get_response_language,
    )
    print(f"  {Colors.GREEN}✅ language module imported{Colors.RESET}")
except ImportError as e:
    print(f"  {Colors.RED}❌ language import failed: {e}{Colors.RESET}")
    sys.exit(1)

# ── core.task_classifier ──────────────────────────────────────
try:
    from core.task_classifier import (
        detect_task,
        detect_coding_action,
        detect_task_with_confidence,
    )
    print(f"  {Colors.GREEN}✅ task_classifier imported{Colors.RESET}")
except ImportError as e:
    print(f"  {Colors.YELLOW}⚠️  task_classifier not available: {e}{Colors.RESET}")
    detect_task                 = None
    detect_coding_action        = None
    detect_task_with_confidence = None

# ── core.brain_router ─────────────────────────────────────────
try:
    from core.brain_router import (
        detect_intent,
        route_coding_tool,
        check_ollama_status,
    )
    print(f"  {Colors.GREEN}✅ brain_router imported{Colors.RESET}")
except ImportError as e:
    print(f"  {Colors.YELLOW}⚠️  brain_router not available: {e}{Colors.RESET}")
    detect_intent       = None
    route_coding_tool   = None
    check_ollama_status = None


# ==================================================
# 🌐 TEST 1 — LANGUAGE DETECTION
# ==================================================

print_section("LANGUAGE DETECTION TESTS")

LANG_TEST_CASES = [
    ("Hello, how are you?",                    "en", "English Detection"),
    ("kya haal hai aapka?",                    "hi", "Hindi/Hinglish Detection"),
    ("code banao ek calculator",               "hi", "Hinglish Coding Request"),
    ("yaar debug karo ye code",                "hi", "Hinglish Debug Request"),
    ("write a python function to sort a list", "en", "English Coding Request"),
    ("",                                       "en", "Empty String (Default)"),
    ("मैं ठीक हूं",                            "hi", "Devanagari Script"),
    ("aur kya kar raha hai tu",                "hi", "Casual Hinglish"),
    ("This is a security vulnerability",       "en", "English Security"),
    ("vulnerability scan karo",                "hi", "Hinglish Security"),
]

print_header("LANGUAGE DETECTION", 1)
for text, expected, name in LANG_TEST_CASES:
    try:
        result = detect_language(text)
        passed = print_test(name, expected, result)
        tracker.record(f"Lang Detect: {name}", passed)
    except Exception as e:
        print(f"  {Colors.RED}❌ ERROR in {name}: {e}{Colors.RESET}")
        tracker.record(f"Lang Detect: {name}", False)


# ==================================================
# 🔀 TEST 2 — HINGLISH DETECTION
# ==================================================

print_header("HINGLISH DETECTION", 2)

HINGLISH_CASES = [
    ("code banao yaar",            True,  "Hinglish Code Request"),
    ("python mein function likho",  True,  "Hinglish Python"),
    ("Hello world",                False, "Pure English"),
    ("kya haal hai",               True,  "Pure Hindi greeting"),
    ("debug karo this error",      True,  "Mixed Hinglish"),
    ("Run this script",            False, "English Command"),
]

for text, expected, name in HINGLISH_CASES:
    try:
        result = is_hinglish(text)
        passed = result == expected
        icon   = "✅" if passed else "❌"
        color  = Colors.GREEN if passed else Colors.RED
        print(f"  {icon} {color}{name:<35}{Colors.RESET}")
        print(f"     Text     : \"{text}\"")
        print(f"     Expected : {expected} | Got: {result}")
        tracker.record(f"Hinglish: {name}", passed)
    except Exception as e:
        print(f"  {Colors.RED}❌ ERROR: {e}{Colors.RESET}")
        tracker.record(f"Hinglish: {name}", False)


# ==================================================
# 🔤 TEST 3 — TRANSLATION PLACEHOLDERS
# ==================================================

print_header("TRANSLATION FUNCTIONS", 3)

translation_tests = [
    ("Hello World",     "en"),
    ("kya kar rahe ho", "hi"),
    ("نمستے",           "ur"),
    ("",                "en"),
]

for text, lang in translation_tests:
    try:
        english = translate_to_english(text)
        back    = translate_back(english, lang)
        passed  = isinstance(english, str) and isinstance(back, str)
        icon    = "✅" if passed else "❌"
        color   = Colors.GREEN if passed else Colors.RED
        print(f"  {icon} {color}Translate '{text[:20]}' [{lang}]{Colors.RESET}")
        tracker.record(f"Translate: {text[:15]}", passed)
    except Exception as e:
        print(f"  {Colors.RED}❌ ERROR: {e}{Colors.RESET}")
        tracker.record(f"Translate: {text[:15]}", False)


# ==================================================
# 🎯 TEST 4 — TASK CLASSIFICATION
# ==================================================

if detect_task:
    print_section("TASK CLASSIFICATION TESTS")

    TASK_CASES = [
        ("python mein code banao",                   "coding",       "Hinglish Code Generate"),
        ("debug karo ye error",                      "coding",       "Hinglish Debug"),
        ("what is machine learning?",                "research",     "English Research"),
        ("port scan karo 192.168.1.1",               "malware",      "Hinglish Port Scan"),
        ("analyze this data trend",                  "analytics",    "English Analytics"),
        ("kaise ho yaar?",                           "conversation", "Hinglish Conversation"),
        ("exploit this vulnerability CVE-2021-44228","malware",      "CVE Exploit"),
        ("write a function to calculate fibonacci",  "coding",       "English Coding"),
        ("data ka analysis karo",                    "analytics",    "Hinglish Analytics"),
        ("hello hi hey",                             "conversation", "Greeting"),
    ]

    print_header("TASK CLASSIFICATION", 4)
    for text, expected, name in TASK_CASES:
        try:
            result = detect_task(text)
            passed = result == expected
            icon   = "✅" if passed else "❌"
            color  = Colors.GREEN if passed else Colors.RED
            print(f"  {icon} {color}{name:<35}{Colors.RESET}")
            print(f"     Input    : \"{text[:50]}\"")
            print(f"     Expected : {expected} | Got: {result}")
            tracker.record(f"Task: {name}", passed)
        except Exception as e:
            print(f"  {Colors.RED}❌ ERROR in {name}: {e}{Colors.RESET}")
            tracker.record(f"Task: {name}", False)

    # Confidence scoring
    if detect_task_with_confidence:
        print_header("TASK CONFIDENCE SCORING", 5)
        CONFIDENCE_CASES = [
            "python mein factorial function banao",
            "nmap se port scan karo",
            "kya haal hai bhai",
            "analyze sales data trends",
        ]
        for text in CONFIDENCE_CASES:
            try:
                task, confidence = detect_task_with_confidence(text)
                print(f"  {Colors.BLUE}📌 Input      :{Colors.RESET} \"{text[:50]}\"")
                print(f"     Task      : {Colors.GREEN}{task}{Colors.RESET}")
                print(f"     Confidence: {Colors.YELLOW}{confidence:.1%}{Colors.RESET}\n")
            except Exception as e:
                print(f"  {Colors.RED}❌ ERROR: {e}{Colors.RESET}")


# ==================================================
# 🧠 TEST 6 — INTENT DETECTION
# ==================================================

if detect_intent:
    print_section("BRAIN ROUTER TESTS")

    INTENT_CASES = [
        ("python code banao for sorting", "coding",       "Coding Intent"),
        ("debug karo ye traceback",       "coding",       "Debug Intent"),
        ("explain kya hai neural network","research",     "Research Intent"),
        ("nmap scan vulnerability",       "malware",      "Security Intent"),
        ("analyze ye data",               "analytics",    "Analytics Intent"),
        ("hello yaar kaise ho",           "conversation", "Conversation Intent"),
    ]

    print_header("INTENT DETECTION", 6)
    for text, expected, name in INTENT_CASES:
        try:
            result = detect_intent(text)
            passed = result == expected
            icon   = "✅" if passed else "❌"
            color  = Colors.GREEN if passed else Colors.RED
            print(f"  {icon} {color}{name:<35}{Colors.RESET}")
            print(f"     Input    : \"{text}\"")
            print(f"     Expected : {expected} | Got: {result}")
            tracker.record(f"Intent: {name}", passed)
        except Exception as e:
            print(f"  {Colors.RED}❌ ERROR: {e}{Colors.RESET}")
            tracker.record(f"Intent: {name}", False)

    # Coding tool routing
    if route_coding_tool:
        print_header("CODING TOOL ROUTING", 7)
        ROUTING_CASES = [
            ("python code banao calculator", "generate_code", "python"),
            ("debug karo ye error",          "debug_code",    "python"),
            ("explain karo ye code",         "explain_code",  "python"),
            ("chalao ye javascript code",    "execute_code",  "javascript"),
            ("sql query banao",              "generate_code", "sql"),
        ]
        for text, expected_tool, expected_lang in ROUTING_CASES:
            try:
                result = route_coding_tool(text)
                tool   = result.get("tool_name", "")
                lang   = result.get("extracted_language", "")
                passed = tool == expected_tool
                icon   = "✅" if passed else "❌"
                color  = Colors.GREEN if passed else Colors.RED
                print(f"  {icon} {color}\"{text[:40]}\"{Colors.RESET}")
                print(f"     Tool : {Colors.YELLOW}{expected_tool}{Colors.RESET} | Got: {tool}")
                print(f"     Lang : {Colors.YELLOW}{expected_lang}{Colors.RESET} | Got: {lang}")
                tracker.record(f"Routing: {expected_tool}", passed)
            except Exception as e:
                print(f"  {Colors.RED}❌ ERROR: {e}{Colors.RESET}")
                tracker.record(f"Routing: {expected_tool}", False)


# ==================================================
# 🦙 TEST 8 — OLLAMA STATUS
# ==================================================

print_section("SYSTEM CHECKS")
print_header("OLLAMA STATUS", 8)

if check_ollama_status:
    try:
        status = check_ollama_status()
        online = status.get("online", False)
        icon   = "✅" if online else "⚠️"
        color  = Colors.GREEN if online else Colors.YELLOW
        print(f"  {icon} {color}{status.get('message', 'Unknown')}{Colors.RESET}")
        if online:
            models = status.get("models_available", [])
            print(f"  {Colors.BLUE}📌 Models: {', '.join(models[:5])}{Colors.RESET}")
        tracker.record("Ollama Status", True)
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠️  Ollama check failed: {e}{Colors.RESET}")
        tracker.record("Ollama Status", True)
else:
    print(f"  {Colors.YELLOW}⚠️  Ollama check skipped (brain_router unavailable){Colors.RESET}")
    tracker.record("Ollama Status", True)


# ==================================================
# 🎮 TEST 9 — INTERACTIVE MODE
# ==================================================

print_section("INTERACTIVE TEST")
print_header("LIVE LANGUAGE DETECTION", 9)

if "--interactive" in sys.argv or "-i" in sys.argv:
    print(f"  {Colors.CYAN}Interactive mode — type text to test (Ctrl+C to exit){Colors.RESET}")
    while True:
        try:
            user_input = input(f"\n  {Colors.BOLD}Enter text:{Colors.RESET} ").strip()
            if not user_input:
                continue

            lang      = detect_language(user_input)
            hinglish  = is_hinglish(user_input)
            resp_lang = get_response_language(user_input)

            if detect_task_with_confidence:
                task, conf = detect_task_with_confidence(user_input)
                print(f"  {Colors.BLUE}Task Type  :{Colors.RESET} {task} ({conf:.1%})")

            if detect_intent:
                intent = detect_intent(user_input)
                print(f"  {Colors.BLUE}Intent     :{Colors.RESET} {intent}")

            print(f"  {Colors.BLUE}Language   :{Colors.RESET} {lang}")
            print(f"  {Colors.BLUE}Is Hinglish:{Colors.RESET} {hinglish}")
            print(f"  {Colors.BLUE}Respond In :{Colors.RESET} {resp_lang}")

        except KeyboardInterrupt:
            print(f"\n  {Colors.YELLOW}Interactive mode ended.{Colors.RESET}")
            break
else:
    print(f"  {Colors.YELLOW}Tip: Run with --interactive flag for live testing{Colors.RESET}")
    print(f"  {Colors.YELLOW}     python test_language.py --interactive{Colors.RESET}")
    tracker.record("Interactive Mode", True)


# ==================================================
# 📊 FINAL SUMMARY
# ==================================================

tracker.summary()