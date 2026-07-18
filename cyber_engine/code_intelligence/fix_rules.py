"""Module Description"""

# cyber_engine/code_intelligence/fix_rules.py

import re
import json
import os


# ==============================
# 🛡 GOVERNANCE STATE
# ==============================

GOVERNANCE_MODE = "normal"  # normal | cautious | restricted


def set_governance_mode(mode):
    global GOVERNANCE_MODE
    if mode in ["normal", "cautious", "restricted"]:
        GOVERNANCE_MODE = mode


# ==============================
# SAFE FIXABLE ISSUE TYPES
# ==============================

FIXABLE_SYMBOLS = {
    "unused-import",
    "missing-module-docstring",
    "missing-function-docstring",
    "missing-class-docstring",
    "trailing-whitespace",
    "missing-final-newline",
}


# ==============================
# 🧠 BASE RULE CONFIDENCE
# ==============================

RULE_CONFIDENCE = {
    "unused-import": 0.96,
    "missing-module-docstring": 0.93,
    "missing-function-docstring": 0.92,
    "missing-class-docstring": 0.92,
    "trailing-whitespace": 0.99,
    "missing-final-newline": 0.99,
}

MIN_CONFIDENCE_THRESHOLD = 0.70


# ==============================
# 🧠 ADAPTIVE RULE STATS (C-LAYER)
# ==============================

STATS_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "rule_stats.json"
)

RULE_STATS = {}

# ==============================
# 🛡 GOVERNANCE LAYER
# ==============================

DISABLED_RULES = set()

GOVERNANCE_MIN_ATTEMPTS = 5
GOVERNANCE_STABILITY_THRESHOLD = 0.30


def is_rule_enabled(rule_type):
    """
    Returns True if rule is allowed to execute.
    """
    return rule_type not in DISABLED_RULES


def evaluate_rule_governance():
    """
    Evaluates rule stability and auto-disables unstable rules.
    Auto re-enables if stability recovers.
    """

    for rule, stats in RULE_STATS.items():

        success = stats.get("success", 0.0)
        failure = stats.get("failure", 0.0)

        total = success + failure

        if total < GOVERNANCE_MIN_ATTEMPTS:
            continue

        stability = get_rule_stability(rule)

        if stability < GOVERNANCE_STABILITY_THRESHOLD:
            DISABLED_RULES.add(rule)
        else:
            DISABLED_RULES.discard(rule)


# ==============================
# 🧠 CONFIDENCE CALCULATION
# ==============================


def get_rule_confidence(rule_type):

    base = RULE_CONFIDENCE.get(rule_type, 0.5)

    stats = RULE_STATS.get(rule_type)

    if not stats:
        return base

    success = stats["success"]
    failure = stats["failure"]

    adjustment = (success * 0.01) - (failure * 0.02)

    stability = get_rule_stability(rule_type)

    stability_factor = 0.5 + (stability * 0.5)

    dynamic = base + (adjustment * stability_factor)

    final_confidence = max(0.60, min(0.99, dynamic))

# Governance Override
    if GOVERNANCE_MODE == "cautious":
       final_confidence *= 0.85
    elif GOVERNANCE_MODE == "restricted":
       final_confidence *= 0.65


    return max(0.50, min(0.99, final_confidence))




def get_rule_stability(rule_type):

    stats = RULE_STATS.get(rule_type)

    if not stats:
        return 0.75

    success = stats["success"]
    failure = stats["failure"]

    total = success + failure

    if total <= 0:
        return 0.75

    return success / total


def update_rule_confidence(rule_type, success):

    stats = RULE_STATS.setdefault(
        rule_type,
        {"success": 0.0, "failure": 0.0}
    )

    if success:
        stats["success"] += 1.0
    else:
        stats["failure"] += 1.0


def decay_rule_stats():

    for rule in RULE_STATS:
        RULE_STATS[rule]["success"] *= 0.95
        RULE_STATS[rule]["failure"] *= 0.95


# ==============================
# MAIN FIX ROUTER
# ==============================

def apply_fix(issue, file_content):

    symbol = issue.get("type")
    line_no = issue.get("line")

    if symbol not in FIXABLE_SYMBOLS:
        return file_content

    lines = file_content.split("\n")

    if symbol == "unused-import":
        return fix_unused_import(lines, line_no)

    elif symbol == "missing-module-docstring":
        return fix_module_docstring(lines)

    elif symbol == "missing-function-docstring":
        return fix_function_docstring(lines, line_no)

    elif symbol == "missing-class-docstring":
        return fix_class_docstring(lines, line_no)

    elif symbol == "trailing-whitespace":
        return fix_trailing_whitespace(lines)

    elif symbol == "missing-final-newline":
        return fix_missing_final_newline(file_content)

    return file_content


# ==============================
# FIX IMPLEMENTATIONS
# ==============================

def fix_unused_import(lines, line_no):
    if line_no and 0 < line_no <= len(lines):
        lines.pop(line_no - 1)
    return "\n".join(lines)


def fix_module_docstring(lines):

    if not lines:
        return '"""Module Description"""\n'

    first_non_empty = 0
    while first_non_empty < len(lines) and not lines[first_non_empty].strip():
        first_non_empty += 1

    if first_non_empty < len(lines):
        if not lines[first_non_empty].strip().startswith('"""'):
            lines.insert(first_non_empty, '"""Module Description"""')
            lines.insert(first_non_empty + 1, "")

    return "\n".join(lines)


def fix_function_docstring(lines, line_no):

    if not line_no or line_no > len(lines):
        return "\n".join(lines)

    def_index = line_no - 1

    if def_index < 0 or def_index >= len(lines):
        return "\n".join(lines)

    if def_index + 1 < len(lines):
        if lines[def_index + 1].strip().startswith('"""'):
            return "\n".join(lines)

    indent = get_indent(lines[def_index])
    docstring_line = indent + "    \"\"\"Function Description\"\"\""

    lines.insert(def_index + 1, docstring_line)

    return "\n".join(lines)


def fix_class_docstring(lines, line_no):

    if not line_no or line_no > len(lines):
        return "\n".join(lines)

    class_index = line_no - 1

    if class_index < 0 or class_index >= len(lines):
        return "\n".join(lines)

    if class_index + 1 < len(lines):
        if lines[class_index + 1].strip().startswith('"""'):
            return "\n".join(lines)

    indent = get_indent(lines[class_index])
    docstring_line = indent + "    \"\"\"Class Description\"\"\""

    lines.insert(class_index + 1, docstring_line)

    return "\n".join(lines)


def fix_trailing_whitespace(lines):
    return "\n".join([line.rstrip() for line in lines])


def fix_missing_final_newline(content):
    if not content.endswith("\n"):
        return content + "\n"
    return content


def get_indent(line):
    match = re.match(r"\s*", line)
    return match.group() if match else ""


# ==============================
# 💾 PERSISTENCE
# ==============================

def load_rule_stats():
    global RULE_STATS

    if not os.path.exists(STATS_FILE_PATH):
        return

    try:
        with open(STATS_FILE_PATH, "r", encoding="utf-8") as f:
            RULE_STATS = json.load(f)
    except Exception:
        RULE_STATS = {}


def save_rule_stats():
    try:
        with open(STATS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(RULE_STATS, f, indent=4)
    except Exception:
        pass
