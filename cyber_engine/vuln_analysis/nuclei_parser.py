"""Module Description"""

import json

def parse_nuclei_results(json_lines):
    """Function Description"""

    findings = []

    for line in json_lines.splitlines():
        try:
            data = json.loads(line)

            findings.append({
                "template": data.get("template-id"),
                "severity": data.get("severity"),
                "matched_at": data.get("matched-at")
            })

        except:
            continue

    return {
        "total_findings": len(findings),
        "findings": findings
    }
