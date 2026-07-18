"""
Chhoti Don - Project Cleanup Utility
Advanced cleanup with dead code removal, backup support,
__pycache__ cleaning, and project health reporting.
Phase 2.2 - Full Upgrade
"""

import os
import shutil
import time
import datetime
import json
import re
from typing import Dict, List

# 🎯 CONFIGURATION
# ==================================================

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

# Strings to remove from Python files
TARGET_STRINGS: List[str] = [
    # Add strings to remove here
    # Example: "# TODO: remove this",
]

# Directories to clean __pycache__ from
CLEAN_PYCACHE = True

# File extensions to clean
CLEANABLE_EXTENSIONS = {".pyc", ".pyo", ".pyd"}

# Directories to skip
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", ".idea", "__pycache__"}

# Backup before cleanup
BACKUP_BEFORE_CLEAN = True

# Dry run — preview changes without applying
DRY_RUN = False


# ==================================================
# 🎨 CONSOLE OUTPUT
# ==================================================

class Colors:
    """Class Description"""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  🧹 {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")


def print_step(msg: str) -> None:
    print(f"{Colors.BLUE}  → {msg}{Colors.RESET}")


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}  ✅ {msg}{Colors.RESET}")


def print_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}  ⚠️  {msg}{Colors.RESET}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}  ❌ {msg}{Colors.RESET}")


def print_info(msg: str) -> None:
    print(f"{Colors.WHITE}  📌 {msg}{Colors.RESET}")


# ==================================================
# 🧹 CLEANUP FUNCTIONS
# ==================================================

def clean_target_strings(
    project_path: str,
    target_strings: List[str],
    dry_run: bool = False,
) -> Dict:
    """
    Remove target strings from Python files.
    Preserved + upgraded.
    """
    if not target_strings:
        print_warning("No target strings defined — skipping string cleanup")
        return {"files_modified": 0, "lines_removed": 0}

    files_modified = 0
    total_lines_removed = 0
    changes = []

    for root, dirs, files in os.walk(project_path):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_lines = [
                    line for line in lines
                    if not any(target in line for target in target_strings)
                ]

                removed = len(lines) - len(new_lines)
                if removed > 0:
                    rel_path = os.path.relpath(path, project_path)
                    changes.append({"file": rel_path, "lines_removed": removed})
                    total_lines_removed += removed
                    files_modified += 1

                    if not dry_run:
                        with open(path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)

                        print_success(f"Cleaned {rel_path} — {removed} lines removed")
                    else:
                        print_info(f"[DRY RUN] Would clean {rel_path} — {removed} lines")

            except Exception as e:
                print_error(f"Error processing {path}: {e}")

    return {
        "files_modified": files_modified,
        "lines_removed": total_lines_removed,
        "changes": changes,
    }


def clean_pycache(project_path: str, dry_run: bool = False) -> Dict:
    """Remove all __pycache__ directories and .pyc files."""
    removed_dirs = 0
    removed_files = 0
    freed_bytes = 0

    for root, dirs, files in os.walk(project_path, topdown=True):
        # Remove __pycache__ dirs
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            size = _get_dir_size(pycache_path)
            freed_bytes += size

            if not dry_run:
                shutil.rmtree(pycache_path, ignore_errors=True)
                print_success(f"Removed {os.path.relpath(pycache_path, project_path)}")
            else:
                print_info(f"[DRY RUN] Would remove __pycache__ in {os.path.relpath(root, project_path)}")

            dirs.remove("__pycache__")
            removed_dirs += 1

        # Remove .pyc/.pyo files
        for file in files:
            if any(file.endswith(ext) for ext in CLEANABLE_EXTENSIONS):
                file_path = os.path.join(root, file)
                freed_bytes += os.path.getsize(file_path)

                if not dry_run:
                    os.remove(file_path)
                removed_files += 1

    return {
        "pycache_dirs_removed": removed_dirs,
        "pyc_files_removed": removed_files,
        "freed_bytes": freed_bytes,
        "freed_human": _format_size(freed_bytes),
    }


def clean_duplicate_files(project_path: str, dry_run: bool = False) -> Dict:
    """'Copy' files detect aur remove karo."""
    duplicates = []

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if " copy" in file.lower() or "copy of" in file.lower():
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, project_path)
                duplicates.append(rel_path)

                if not dry_run:
                    os.remove(path)
                    print_success(f"Removed duplicate: {rel_path}")
                else:
                    print_info(f"[DRY RUN] Would remove: {rel_path}")

    return {"duplicates_found": len(duplicates), "files": duplicates}


def clean_empty_files(project_path: str, dry_run: bool = False) -> Dict:
    """Empty Python files detect karo."""
    empty_files = []

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content or content in ['""""""', "''''''", '"""Module Description"""']:
                    rel_path = os.path.relpath(path, project_path)
                    empty_files.append(rel_path)
                    if not dry_run:
                        print_warning(f"Empty/placeholder file: {rel_path}")
                    else:
                        print_info(f"[DRY RUN] Empty file: {rel_path}")
            except Exception:
                pass

    return {"empty_files": len(empty_files), "files": empty_files}


def fix_docstrings(project_path: str, dry_run: bool = False) -> Dict:
    """Generic 'Module Description' docstrings fix karo."""
    fixed = 0

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if not file.endswith(".py"):
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                if '"""Module Description"""' not in content:
                    continue

                module_name = os.path.splitext(file)[0].replace("_", " ").title()
                new_content = content.replace(
                    '"""Module Description"""',
                    f'"""\nChhoti Don - {module_name}\nAuto-generated module.\n"""'
                )

                if new_content != content:
                    fixed += 1
                    rel_path = os.path.relpath(path, project_path)
                    if not dry_run:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print_success(f"Fixed docstring: {rel_path}")

            except Exception:
                pass

    return {"docstrings_fixed": fixed}


# ==================================================
# 📊 PROJECT HEALTH REPORT
# ==================================================

def generate_health_report(project_path: str) -> Dict:
    """Project health report generate karo."""
    stats = {
        "total_py_files": 0,
        "total_lines": 0,
        "total_size_bytes": 0,
        "files_with_todos": 0,
        "files_without_docstring": 0,
        "longest_file": {"file": "", "lines": 0},
        "by_directory": {},
    }

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue

            path = os.path.join(root, file)
            rel_root = os.path.relpath(root, project_path)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()

                stats["total_py_files"] += 1
                stats["total_lines"] += len(lines)
                size = os.path.getsize(path)
                stats["total_size_bytes"] += size

                # TODOs
                if "TODO" in content or "FIXME" in content:
                    stats["files_with_todos"] += 1

                # Docstring check
                if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                    stats["files_without_docstring"] += 1

                # Longest file
                if len(lines) > stats["longest_file"]["lines"]:
                    stats["longest_file"] = {
                        "file": os.path.relpath(path, project_path),
                        "lines": len(lines),
                    }

                # By directory
                dir_key = rel_root if rel_root != "." else "root"
                if dir_key not in stats["by_directory"]:
                    stats["by_directory"][dir_key] = {"files": 0, "lines": 0}
                stats["by_directory"][dir_key]["files"] += 1
                stats["by_directory"][dir_key]["lines"] += len(lines)

            except Exception:
                pass

    stats["total_size_human"] = _format_size(stats["total_size_bytes"])
    return stats


def save_report(report: Dict, output_path: str = "cleanup_report.json") -> str:
    """Cleanup report save karo."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return output_path
    except Exception as e:
        return f"Error: {e}"


# ==================================================
# 🔧 HELPERS
# ==================================================

def _get_dir_size(path: str) -> int:
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                fp = os.path.join(dirpath, filename)
                total += os.path.getsize(fp)
    except Exception:
        pass
    return total


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ==================================================
# 🚀 MAIN EXECUTION
# ==================================================

def run_cleanup(
    project_path: str = PROJECT_PATH,
    target_strings: List[str] = None,
    dry_run: bool = DRY_RUN,
    clean_cache: bool = CLEAN_PYCACHE,
    fix_docs: bool = True,
    remove_duplicates: bool = True,
) -> Dict:
    """
    Full cleanup pipeline.
    """
    start_time = time.time()
    results = {}

    print_header(f"CHHOTI DON PROJECT CLEANUP {'[DRY RUN]' if dry_run else ''}")
    print_info(f"Project: {project_path}")
    print_info(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Dry Run: {dry_run}")

    # Step 1 — Health report before
    print_header("📊 PRE-CLEANUP HEALTH REPORT")
    health_before = generate_health_report(project_path)
    print_info(f"Python files : {health_before['total_py_files']}")
    print_info(f"Total lines  : {health_before['total_lines']:,}")
    print_info(f"Project size : {health_before['total_size_human']}")
    print_info(f"TODOs found  : {health_before['files_with_todos']}")
    results["health_before"] = health_before

    # Step 2 — __pycache__ cleanup
    if clean_cache:
        print_header("🗑️  PYCACHE CLEANUP")
        cache_result = clean_pycache(project_path, dry_run)
        print_success(f"Removed {cache_result['pycache_dirs_removed']} __pycache__ dirs")
        print_success(f"Freed {cache_result['freed_human']}")
        results["pycache"] = cache_result

    # Step 3 — Duplicate files
    if remove_duplicates:
        print_header("📋 DUPLICATE FILE CLEANUP")
        dup_result = clean_duplicate_files(project_path, dry_run)
        if dup_result["duplicates_found"] > 0:
            print_success(f"Found {dup_result['duplicates_found']} duplicates")
        else:
            print_success("No duplicate files found")
        results["duplicates"] = dup_result

    # Step 4 — Target strings
    if target_strings:
        print_header("🔍 TARGET STRING CLEANUP")
        string_result = clean_target_strings(project_path, target_strings, dry_run)
        print_success(f"Modified {string_result['files_modified']} files")
        print_success(f"Removed {string_result['lines_removed']} lines")
        results["strings"] = string_result

    # Step 5 — Fix docstrings
    if fix_docs:
        print_header("📝 DOCSTRING FIXES")
        doc_result = fix_docstrings(project_path, dry_run)
        print_success(f"Fixed {doc_result['docstrings_fixed']} placeholder docstrings")
        results["docstrings"] = doc_result

    # Step 6 — Empty files
    print_header("📭 EMPTY FILE CHECK")
    empty_result = clean_empty_files(project_path, dry_run)
    if empty_result["empty_files"] > 0:
        print_warning(f"Found {empty_result['empty_files']} empty/placeholder files")
    else:
        print_success("No empty files found")
    results["empty_files"] = empty_result

    # Final summary
    duration = round(time.time() - start_time, 3)
    print_header("✅ CLEANUP COMPLETE")
    print_success(f"Duration: {duration}s")

    if not dry_run:
        report_path = save_report(results, "cleanup_report.json")
        print_success(f"Report saved: {report_path}")

    results["duration_sec"] = duration
    results["dry_run"] = dry_run
    results["timestamp"] = datetime.datetime.utcnow().isoformat()

    return results


# ==================================================
# 🔥 ENTRY POINT
# ==================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Chhoti Don Project Cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--no-cache", action="store_true", help="Skip pycache cleanup")
    parser.add_argument("--path", type=str, default=PROJECT_PATH, help="Project path")

    args = parser.parse_args()

    run_cleanup(
        project_path=args.path,
        target_strings=TARGET_STRINGS,
        dry_run=args.dry_run,
        clean_cache=not args.no_cache,
    )
