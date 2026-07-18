"""
Chhoti Don - Threat Heatmap Generator
Advanced threat intensity mapping with temporal analysis,
asset-based weighting, and visual output generation.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Dict, Generator, List, Mapping
# ==================================================

STAGE_BASE_INTENSITY = {
    # Preserved
    "initial_access": 3,
    "privilege_escalation": 4,
    "credential_access": 5,
    "lateral_movement": 4,
    "persistence": 3,

    # New stages
    "reconnaissance": 1,
    "resource_development": 2,
    "execution": 4,
    "defense_evasion": 3,
    "discovery": 2,
    "collection": 3,
    "command_and_control": 4,
    "exfiltration": 5,
    "impact": 5,
}

# Temporal decay — older events less intense
TEMPORAL_DECAY_FACTOR = 0.95  # Per hour

# Asset criticality multipliers
ASSET_MULTIPLIERS = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 1.2,
    "low": 1.0,
}

# Stage color mapping for visualization
STAGE_COLORS = {
    "reconnaissance": "#3498db",
    "resource_development": "#2980b9",
    "initial_access": "#e74c3c",
    "execution": "#c0392b",
    "persistence": "#8e44ad",
    "privilege_escalation": "#d35400",
    "defense_evasion": "#7f8c8d",
    "credential_access": "#f39c12",
    "discovery": "#27ae60",
    "lateral_movement": "#e74c3c",
    "collection": "#2980b9",
    "command_and_control": "#8e44ad",
    "exfiltration": "#c0392b",
    "impact": "#e74c3c",
}

# Risk level thresholds
RISK_THRESHOLDS = {
    "extreme": 4.5,
    "severe": 3.5,
    "elevated": 2.5,
    "moderate": 1.5,
    "low": 0.5,
}


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def generate_heatmap(
    detected_stages: List[str],
    breach_probability: float,
    asset_criticality: str = "medium",
    temporal_data: Dict = None,
    context: Dict = None,
) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Advanced threat heatmap with multi-factor analysis.
    """
    engine = HeatmapEngine()
    return engine.generate(
        detected_stages,
        breach_probability,
        asset_criticality,
        temporal_data,
        context,
    )


def classify_global_risk(index: float) -> str:
    """
    Original function — preserved.
    Global risk classification.
    """
    if index >= 4.5:
        return "Extreme"
    elif index >= 3.5:
        return "Severe"
    elif index >= 2.5:
        return "Elevated"
    elif index >= 1.5:
        return "Moderate"
    elif index >= 0.5:
        return "Low"
    else:
        return "Minimal"


# ==================================================
# 🧠 HEATMAP ENGINE
# ==================================================

class HeatmapEngine:
    """
    Advanced Threat Heatmap Generation Engine.
    """

    def generate(
        self,
        detected_stages: List[str],
        breach_probability: float,
        asset_criticality: str = "medium",
        temporal_data: Dict = None,
        context: Dict = None,
    ) -> Dict:
        """Generate comprehensive threat heatmap."""
        start_time = time.time()
        context = context or {}
        temporal_data = temporal_data or {}

        heatmap = {}
        total_intensity = 0

        asset_mult = ASSET_MULTIPLIERS.get(asset_criticality, 1.0)

        for stage in detected_stages:
            base = STAGE_BASE_INTENSITY.get(stage, 2)

            # Breach probability scaling (preserved)
            intensity = base * breach_probability

            # Asset criticality scaling (NEW)
            intensity *= asset_mult

            # Temporal decay (NEW)
            if temporal_data and stage in temporal_data:
                hours_ago = temporal_data.get(stage, {}).get("hours_ago", 0)
                decay = TEMPORAL_DECAY_FACTOR ** hours_ago
                intensity *= decay

            # Context modifiers (NEW)
            if context.get("internet_facing"):
                intensity *= 1.2
            if context.get("critical_data"):
                intensity *= 1.3
            if context.get("active_exploitation"):
                intensity *= 1.5

            # Level classification
            if intensity >= 4.5:
                level = "Extreme"
                color = "#8B0000"
            elif intensity >= 3.5:
                level = "Critical"
                color = "#e74c3c"
            elif intensity >= 2.5:
                level = "High"
                color = "#e67e22"
            elif intensity >= 1.5:
                level = "Moderate"
                color = "#f39c12"
            elif intensity >= 0.5:
                level = "Low"
                color = "#27ae60"
            else:
                level = "Minimal"
                color = "#2ecc71"

            # MITRE tactics for this stage
            mitre_tactics = self._get_mitre_tactics(stage)

            heatmap[stage] = {
                "intensity_score": round(intensity, 3),
                "level": level,
                "color": color,
                "base_intensity": base,
                "breach_factor": round(breach_probability, 3),
                "asset_multiplier": asset_mult,
                "description": self._get_stage_description(stage),
                "mitre_tactics": mitre_tactics,
                "stage_color": STAGE_COLORS.get(stage, "#95a5a6"),
                "recommendations": self._get_stage_recommendations(stage, level),
            }

            total_intensity += intensity

        # Overall metrics
        overall_index = total_intensity / len(detected_stages) if detected_stages else 0
        overall_index = round(overall_index, 3)

        # Risk progression
        risk_progression = self._analyze_progression(detected_stages, heatmap)

        # Hotspots — highest intensity stages
        hotspots = sorted(
            [(stage, data["intensity_score"]) for stage, data in heatmap.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Trend
        trend = self._calculate_trend(heatmap)

        return {
            # Backward compat
            "stage_heatmap": heatmap,
            "overall_threat_index": overall_index,
            "global_risk_level": classify_global_risk(overall_index),

            # Enhanced
            "asset_criticality": asset_criticality,
            "breach_probability": breach_probability,
            "hotspots": [{"stage": s, "score": round(sc, 2)} for s, sc in hotspots],
            "risk_progression": risk_progression,
            "trend": trend,
            "total_stages": len(detected_stages),
            "critical_stages": [
                s for s, d in heatmap.items()
                if d["level"] in ["Extreme", "Critical"]
            ],
            "visual_data": self._generate_visual_data(heatmap),
            "analysis_time_sec": round(time.time() - start_time, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _get_mitre_tactics(self, stage: str) -> List[str]:
        """Stage se MITRE tactics lo."""
        tactic_map = {
            "reconnaissance": ["TA0043"],
            "initial_access": ["TA0001"],
            "execution": ["TA0002"],
            "persistence": ["TA0003"],
            "privilege_escalation": ["TA0004"],
            "defense_evasion": ["TA0005"],
            "credential_access": ["TA0006"],
            "discovery": ["TA0007"],
            "lateral_movement": ["TA0008"],
            "collection": ["TA0009"],
            "exfiltration": ["TA0010"],
            "command_and_control": ["TA0011"],
            "impact": ["TA0040"],
        }
        return tactic_map.get(stage, [])

    def _get_stage_description(self, stage: str) -> str:
        """Stage description lo."""
        descriptions = {
            "reconnaissance": "Attacker gathering target information",
            "initial_access": "First foothold established in environment",
            "execution": "Malicious code being executed",
            "persistence": "Maintaining access through restarts",
            "privilege_escalation": "Gaining higher system privileges",
            "defense_evasion": "Avoiding detection mechanisms",
            "credential_access": "Stealing authentication credentials",
            "discovery": "Mapping internal environment",
            "lateral_movement": "Spreading through network",
            "collection": "Gathering target data",
            "command_and_control": "C2 channel active",
            "exfiltration": "Data leaving the environment",
            "impact": "Final destructive/disruptive actions",
        }
        return descriptions.get(stage, "Attack activity detected")

    def _get_stage_recommendations(self, stage: str, level: str) -> List[str]:
        """Stage-specific recommendations generate karo."""
        base_recs = {
            "initial_access": [
                "Patch exploited vulnerabilities immediately",
                "Review web application firewall rules",
            ],
            "lateral_movement": [
                "Segment network — block SMB between workstations",
                "Enable enhanced authentication logging",
                "Force password resets for affected accounts",
            ],
            "credential_access": [
                "Enable MFA on all accounts immediately",
                "Rotate all compromised credentials",
                "Monitor for Pass-the-Hash attacks",
            ],
            "command_and_control": [
                "Block identified C2 domains/IPs at firewall",
                "Isolate affected systems",
                "Analyze network traffic for beacon patterns",
            ],
            "exfiltration": [
                "Block outbound transfers to unknown destinations",
                "Review DLP alerts",
                "Initiate incident response immediately",
            ],
            "impact": [
                "EMERGENCY: Isolate all affected systems NOW",
                "Activate incident response plan",
                "Engage forensics team",
                "Notify stakeholders per breach protocol",
            ],
        }

        recs = base_recs.get(stage, ["Investigate and monitor closely"])

        if level in ["Extreme", "Critical"]:
            recs.insert(0, f"⚠️ URGENT: {stage.replace('_', ' ').title()} at {level} intensity!")

        return recs[:3]

    def _analyze_progression(self, stages: List[str], heatmap: Dict) -> Dict:
        """Attack progression analyze karo."""
        stage_order = list(STAGE_BASE_INTENSITY.keys())

        if not stages:
            return {"phase": "none", "advancement": 0}

        max_stage_idx = max(
            (stage_order.index(s) for s in stages if s in stage_order),
            default=0
        )

        advancement = round((max_stage_idx + 1) / len(stage_order) * 100, 1)

        if advancement >= 80:
            phase = "Final Objectives"
        elif advancement >= 60:
            phase = "Active Intrusion"
        elif advancement >= 40:
            phase = "Establishing Control"
        elif advancement >= 20:
            phase = "Initial Compromise"
        else:
            phase = "Early Reconnaissance"

        return {
            "phase": phase,
            "advancement_percent": advancement,
            "furthest_stage": stages[-1] if stages else "none",
        }

    def _calculate_trend(self, heatmap: Dict) -> str:
        """Threat trend calculate karo."""
        if not heatmap:
            return "stable"

        intensities = [d["intensity_score"] for d in heatmap.values()]
        avg = sum(intensities) / len(intensities)

        if avg >= 3.5:
            return "critical"
        elif avg >= 2.5:
            return "escalating"
        elif avg >= 1.5:
            return "moderate"
        else:
            return "low"

    def _generate_visual_data(self, heatmap: Dict) -> List[Dict]:
        """Chart-friendly visual data generate karo."""
        return [
            {
                "stage": stage,
                "score": data["intensity_score"],
                "level": data["level"],
                "color": data["color"],
                "label": stage.replace("_", " ").title(),
            }
            for stage, data in heatmap.items()
        ]


# ==================================================
# 🔧 HELPER FUNCTIONS
# ==================================================

def get_heatmap_summary(heatmap_result: Dict) -> str:
    """Human-readable heatmap summary."""
    global_risk = heatmap_result.get("global_risk_level", "Unknown")
    overall = heatmap_result.get("overall_threat_index", 0)
    hotspots = heatmap_result.get("hotspots", [])
    critical = heatmap_result.get("critical_stages", [])

    summary = f"Threat Level: {global_risk} (Index: {overall:.2f}). "

    if critical:
        summary += f"Critical stages: {', '.join(critical)}. "

    if hotspots:
        top = hotspots[0]
        summary += f"Hotspot: {top['stage']} (score: {top['score']}). "

    return summary


def compare_heatmaps(heatmap1: Dict, heatmap2: Dict) -> Dict:
    """Two heatmaps compare karo — track changes."""
    stages1 = set(heatmap1.get("stage_heatmap", {}).keys())
    stages2 = set(heatmap2.get("stage_heatmap", {}).keys())

    new_stages = stages2 - stages1
    resolved = stages1 - stages2
    persisting = stages1 & stages2

    index1 = heatmap1.get("overall_threat_index", 0)
    index2 = heatmap2.get("overall_threat_index", 0)

    return {
        "new_stages": list(new_stages),
        "resolved_stages": list(resolved),
        "persisting_stages": list(persisting),
        "threat_index_change": round(index2 - index1, 3),
        "trend": "escalating" if index2 > index1 else "improving" if index2 < index1 else "stable",
    }
