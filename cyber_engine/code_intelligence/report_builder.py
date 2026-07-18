"""
Chhoti Don EvolveX - Report Builder
Advanced code intelligence report generation.
Phase 2.2 - Full Upgrade
"""

from typing import Dict, List, List


def generate_report(issues: List[Dict], dependency_graph: Dict) -> None:
    """
    Generate and print code intelligence report.
    Preserved + upgraded.
    """
    print("\n====== EvolveX Code Intelligence Report ======\n")
    print(f"Timestamp : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Issues Found: {len(issues)}\n")

    # Severity breakdown
    severity_count = {}
    type_count = {}

    for issue in issues:
        sev = issue.get("severity", "unknown")
        typ = issue.get("type", "unknown")
        severity_count[sev] = severity_count.get(sev, 0) + 1
        type_count[typ] = type_count.get(typ, 0) + 1

    print("Severity Breakdown:")
    for sev, count in sorted(severity_count.items()):
        icon = "🔴" if sev == "error" else "🟡" if sev == "warning" else "🔵"
        print(f"  {icon} {sev}: {count}")

    print("\nTop Issue Types:")
    sorted_types = sorted(type_count.items(), key=lambda x: x[1], reverse=True)
    for typ, count in sorted_types[:5]:
        print(f"  → {typ}: {count}")

    print(f"\nDependency Graph Summary:")
    print(f"  Total files: {len(dependency_graph)}")
    total_deps = sum(len(v) for v in dependency_graph.values())
    print(f"  Total dependencies: {total_deps}")

    print("\n==============================================\n")


def generate_detailed_report(
    issues: List[Dict],
    dependency_graph: Dict,
    ast_report: Dict = None,
    health_report: Dict = None,
) -> Dict:
    """
    Detailed structured report generate karo.
    """
    timestamp = datetime.datetime.utcnow().isoformat()

    # Issue analysis
    severity_count = {}
    type_count = {}
    file_issue_count = {}

    for issue in issues:
        sev = issue.get("severity", "unknown")
        typ = issue.get("type", "unknown")
        file = issue.get("file", "unknown")

        severity_count[sev] = severity_count.get(sev, 0) + 1
        type_count[typ] = type_count.get(typ, 0) + 1
        file_issue_count[file] = file_issue_count.get(file, 0) + 1

    # Most problematic files
    top_files = sorted(file_issue_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # Dependency analysis
    total_deps = sum(len(v) for v in dependency_graph.values())
    avg_deps = total_deps / max(len(dependency_graph), 1)

    report = {
        "timestamp": timestamp,
        "summary": {
            "total_issues": len(issues),
            "total_files": len(dependency_graph),
            "total_dependencies": total_deps,
            "avg_dependencies_per_file": round(avg_deps, 2),
        },
        "severity_breakdown": severity_count,
        "issue_type_breakdown": dict(sorted(type_count.items(), key=lambda x: x[1], reverse=True)[:10]),
        "most_problematic_files": [{"file": f, "issues": c} for f, c in top_files],
    }

    if ast_report:
        report["ast_analysis"] = {
            "files_analyzed": ast_report.get("files_analyzed", 0),
            "total_functions": ast_report.get("total_functions", 0),
            "high_complexity_count": len(ast_report.get("high_complexity_functions", [])),
        }

    if health_report:
        report["health"] = {
            "overall_health": health_report.get("overall_health", "unknown"),
            "avg_stability": health_report.get("avg_stability", 0),
        }

    return report


def save_report_to_file(report: Dict, output_path: str = "evolveX_report.json") -> str:
    """Report file mein save karo."""
    import json
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return output_path
    except Exception as e:
        return f"Error: {e}"
