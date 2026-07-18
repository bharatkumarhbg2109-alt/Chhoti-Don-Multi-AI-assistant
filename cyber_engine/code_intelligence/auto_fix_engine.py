"""
Chhoti Don EvolveX - Auto Fix Engine
Behavior-aware + Risk-weighted + Adaptive + Persistent + Governance Override
Phase 2.2 - Full Upgrade
"""

import os
import py_compile
import time
import datetime
from .fix_rules import (
    DISABLED_RULES, FIXABLE_SYMBOLS,
    apply_fix, MIN_CONFIDENCE_THRESHOLD, decay_rule_stats, evaluate_rule_governance, get_rule_confidence, is_rule_enabled, load_rule_stats, save_rule_stats, set_governance_mode, update_rule_confidence)
from typing import Dict, List

from .rollback_manager import create_backup, restore_backup, delete_backup
from .patch_validator import validate_patch
from .static_analysis import run_static_analysis
from .behavior_tracker import update_file_behavior, is_file_stable


MAX_FIXES_PER_FILE = 25
MAX_HEALING_ITERATIONS = 5


# ==================================================
# 🎯 RISK MODEL (PRESERVED + UPGRADED)
# ==================================================

HIGH_RISK_PATTERNS = [
    "core/", "manager.py", "brain.py",
    "memory.py", "config.py", "guardian",
    "execution_controller", "brain_router",
]

MEDIUM_RISK_PATTERNS = [
    "engine", "controller", "cyber_engine",
    "scanner", "analyzer",
]

LOW_RISK_PATTERNS = [
    "test_", "tests/", "tools/",
    "utils", "helper",
]


def calculate_file_risk(file_path: str) -> str:
    """File risk level calculate karo."""
    normalized = file_path.replace("\\", "/")

    for pattern in HIGH_RISK_PATTERNS:
        if pattern in normalized:
            return "high"

    for pattern in MEDIUM_RISK_PATTERNS:
        if pattern in normalized:
            return "medium"

    return "low"


def get_dynamic_fix_limit(risk_level: str) -> int:
    """Risk level ke hisaab se max fixes."""
    limits = {"high": 3, "medium": 10, "low": MAX_FIXES_PER_FILE}
    return limits.get(risk_level, MAX_FIXES_PER_FILE)


def get_dynamic_confidence_threshold(risk_level: str) -> float:
    """Risk level ke hisaab se confidence threshold."""
    thresholds = {"high": 0.90, "medium": 0.80, "low": MIN_CONFIDENCE_THRESHOLD}
    return max(thresholds.get(risk_level, MIN_CONFIDENCE_THRESHOLD), MIN_CONFIDENCE_THRESHOLD)


# ==================================================
# 🔧 SINGLE PASS AUTO FIX (PRESERVED + UPGRADED)
# ==================================================

def run_auto_fix(issues: List[Dict]) -> int:
    """
    Run single-pass auto fix on issues.

    Args:
        issues: List of issues from static analysis

    Returns:
        Total fixes applied
    """
    issues_by_file = {}

    for issue in issues:
        file_path = issue.get("file")
        rule_type = issue.get("type")

        if not file_path:
            continue
        if rule_type not in FIXABLE_SYMBOLS:
            continue

        issues_by_file.setdefault(file_path, []).append(issue)

    total_fixes = 0
    fix_summary = {}

    for file_path, file_issues in issues_by_file.items():

        if not os.path.exists(file_path):
            continue

        # File stability check (NEW)
        if not is_file_stable(file_path):
            print(f"[EvolveX] Skipping unstable file: {file_path}")
            continue

        risk_level = calculate_file_risk(file_path)
        dynamic_limit = get_dynamic_fix_limit(risk_level)
        dynamic_threshold = get_dynamic_confidence_threshold(risk_level)

        print(f"[EvolveX] Processing {file_path} | Risk: {risk_level}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except Exception:
            continue

        # Baseline analysis
        baseline_issues = run_static_analysis([file_path])
        baseline_error_count = sum(
            1 for i in baseline_issues if i.get("severity") == "error"
        )

        # Backup
        create_backup(file_path)

        modified_content = original_content
        fixes_applied = 0
        applied_rules = []
        skipped_rules = []

        # Apply fixes
        for issue in file_issues:

            if fixes_applied >= dynamic_limit:
                break

            rule_type = issue.get("type")

            # Governance check
            if not is_rule_enabled(rule_type):
                print(f"[Governance] Rule disabled: {rule_type}")
                skipped_rules.append(rule_type)
                continue

            confidence = get_rule_confidence(rule_type)

            if confidence < dynamic_threshold:
                print(f"[EvolveX] Skipping low-confidence rule: {rule_type}")
                skipped_rules.append(rule_type)
                continue

            try:
                updated_content = apply_fix(issue, modified_content)

                if updated_content != modified_content:
                    modified_content = updated_content
                    fixes_applied += 1
                    total_fixes += 1
                    applied_rules.append(rule_type)

            except Exception:
                continue

        # Write fixed file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)
        except Exception:
            restore_backup(file_path)
            for rule in applied_rules:
                update_rule_confidence(rule, False)
            update_file_behavior(file_path, baseline_error_count, False)
            continue

        # Syntax validation
        try:
            py_compile.compile(file_path, doraise=True)
        except Exception:
            restore_backup(file_path)
            for rule in applied_rules:
                update_rule_confidence(rule, False)
            update_file_behavior(file_path, baseline_error_count, False)
            continue

        # Patch validation
        try:
            error_count = validate_patch(file_path, baseline_error_count)
        except Exception:
            error_count = 9999

        if error_count == 9999:
            restore_backup(file_path)
            for rule in applied_rules:
                update_rule_confidence(rule, False)
            update_file_behavior(file_path, baseline_error_count, False)
        else:
            delete_backup(file_path)
            for rule in applied_rules:
                update_rule_confidence(rule, True)
            update_file_behavior(file_path, error_count, fixes_applied > 0)

        fix_summary[file_path] = {
            "risk": risk_level,
            "fixes": fixes_applied,
            "skipped": skipped_rules,
        }

    return total_fixes


# ==================================================
# 🔁 FULL AUTO SELF-HEAL LOOP (PRESERVED + UPGRADED)
# ==================================================

def run_full_self_heal(project_path: str) -> Dict:
    """
    Full automated self-healing loop.

    Args:
        project_path: Project root path

    Returns:
        Healing report dict
    """
    print("[EvolveX] FULL AUTO SELF-HEAL MODE STARTED")
    start_time = time.time()

    load_rule_stats()

    iteration = 0
    previous_fix_count = None
    total_fixes_all = 0
    iteration_log = []

    while iteration < MAX_HEALING_ITERATIONS:

        print(f"[EvolveX] Healing Iteration {iteration + 1}")

        python_files = get_python_files(project_path)

        if not python_files:
            print("[EvolveX] No Python files found.")
            break

        print("[EvolveX] Running static analysis...")
        issues = run_static_analysis(python_files)

        fixable = [i for i in issues if i.get("type") in FIXABLE_SYMBOLS]

        if not fixable:
            print("[EvolveX] No more fixable issues.")
            break

        fixes_applied = run_auto_fix(fixable)
        total_fixes_all += fixes_applied

        print(f"[EvolveX] Iteration Fixes Applied: {fixes_applied}")

        # Decay historical influence
        decay_rule_stats()

        # Evaluate governance
        evaluate_rule_governance()

        # Governance mode switching
        disabled_count = len(DISABLED_RULES)

        if disabled_count >= 3:
            set_governance_mode("restricted")
            print("[Governance Mode] RESTRICTED")
        elif disabled_count >= 1:
            set_governance_mode("cautious")
            print("[Governance Mode] CAUTIOUS")
        else:
            set_governance_mode("normal")
            print("[Governance Mode] NORMAL")

        iteration_log.append({
            "iteration": iteration + 1,
            "fixes": fixes_applied,
            "fixable_issues": len(fixable),
            "total_issues": len(issues),
        })

        if fixes_applied == 0:
            print("[EvolveX] Nothing changed. Stopping.")
            break

        if previous_fix_count == fixes_applied:
            print("[EvolveX] Fix count stabilized. Stopping.")
            break

        previous_fix_count = fixes_applied
        iteration += 1

    save_rule_stats()

    # AST analysis (NEW)
    try:
        from .ast_fix_engine import ASTFixEngine
        ast_engine = ASTFixEngine()
        ast_report = ast_engine.analyze_project(project_path)
        ast_summary = {
            "files_analyzed": ast_report.get("files_analyzed", 0),
            "ast_issues": ast_report.get("total_issues", 0),
            "high_complexity": len(ast_report.get("high_complexity_functions", [])),
        }
    except Exception:
        ast_summary = {}

    # Telemetry Decision Layer (PRESERVED)
    telemetry_report = {}
    try:
        from cyber_engine.intelligence.telemetry_decision_engine import (
            run_telemetry_decision_engine
        )
        telemetry_report = run_telemetry_decision_engine()

        print("\n[EvolveX Telemetry Report]")
        print(f"System Health: {telemetry_report.get('system_health')}")

        for alert in telemetry_report.get("alerts", []):
            print(f"Alert: {alert}")

    except Exception as e:
        print(f"[Telemetry] Skipped due to error: {e}")

    duration = round(time.time() - start_time, 3)
    print(f"[EvolveX] SELF-HEAL COMPLETE in {duration}s")

    return {
        "status": "complete",
        "project_path": project_path,
        "total_iterations": iteration + 1,
        "total_fixes": total_fixes_all,
        "iteration_log": iteration_log,
        "ast_summary": ast_summary,
        "telemetry": telemetry_report,
        "duration_sec": duration,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


# ==================================================
# 🔍 TARGETED FIX (NEW)
# ==================================================

def fix_single_file(file_path: str) -> Dict:
    """
    Single file ko fix karo — full pipeline.

    Args:
        file_path: Path to Python file

    Returns:
        Fix result
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": "File not found"}

    issues = run_static_analysis([file_path])
    fixable = [i for i in issues if i.get("type") in FIXABLE_SYMBOLS]

    if not fixable:
        return {
            "status": "success",
            "message": "No fixable issues found",
            "file": file_path,
        }

    fixes = run_auto_fix(fixable)

    return {
        "status": "success",
        "file": file_path,
        "fixes_applied": fixes,
        "issues_found": len(issues),
        "fixable_issues": len(fixable),
    }


# ==================================================
# 📂 FILE DISCOVERY (PRESERVED + UPGRADED)
# ==================================================

def get_python_files(project_path: str, exclude_patterns: List[str] = None) -> List[str]:
    """
    Python files discover karo.

    Args:
        project_path: Root path
        exclude_patterns: Patterns to exclude

    Returns:
        List of Python file paths
    """
    default_excludes = ["__pycache__", ".venv", "venv", ".git", "node_modules"]
    excludes = default_excludes + (exclude_patterns or [])

    py_files = []

    for root, dirs, files in os.walk(project_path):
        # Exclude unwanted directories
        dirs[:] = [d for d in dirs if not any(ex in d for ex in excludes)]

        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))

    return py_files


def get_fix_statistics() -> Dict:
    """Current fix engine statistics lo."""
    load_rule_stats()

    from .fix_rules import RULE_STATS, DISABLED_RULES, GOVERNANCE_MODE, get_rule_stability

    stats = {}
    for rule, data in RULE_STATS.items():
        stats[rule] = {
            "success": round(data.get("success", 0), 2),
            "failure": round(data.get("failure", 0), 2),
            "stability": round(get_rule_stability(rule), 3),
            "enabled": rule not in DISABLED_RULES,
        }

    return {
        "governance_mode": GOVERNANCE_MODE,
        "disabled_rules": list(DISABLED_RULES),
        "rule_stats": stats,
        "total_rules": len(FIXABLE_SYMBOLS),
    }
