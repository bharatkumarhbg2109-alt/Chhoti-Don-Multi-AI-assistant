"""
Chhoti Don- Attack Graph Engine
Advanced attack path modeling with breach probability,
critical path analysis, and attack simulation.
Phase 2.2 - Full Upgrade
"""
from typing import Dict, List, Optional


# ==================================================
# 🎯 ATTACK STAGE DEFINITIONS
# ==================================================

ATTACK_STAGES = {
    "reconnaissance": {
        "order": 1,
        "description": "Information gathering phase",
        "base_weight": 0.3,
        "indicators": ["port scan", "subdomain enum", "osint", "network scan"],
        "next_stages": ["initial_access", "weaponization"],
        "color": "#3498db"
    },
    "weaponization": {
        "order": 2,
        "description": "Creating attack tools/payloads",
        "base_weight": 0.5,
        "indicators": ["payload creation", "exploit development"],
        "next_stages": ["initial_access"],
        "color": "#e67e22"
    },
    "initial_access": {
        "order": 3,
        "description": "First foothold in target",
        "base_weight": 0.7,
        "indicators": ["exploit", "phishing", "brute force", "credential"],
        "next_stages": ["execution", "persistence"],
        "color": "#e74c3c"
    },
    "execution": {
        "order": 4,
        "description": "Running malicious code",
        "base_weight": 0.75,
        "indicators": ["command execution", "script", "shell", "rce"],
        "next_stages": ["persistence", "privilege_escalation", "defense_evasion"],
        "color": "#c0392b"
    },
    "persistence": {
        "order": 5,
        "description": "Maintaining access",
        "base_weight": 0.6,
        "indicators": ["backdoor", "cron job", "service", "registry"],
        "next_stages": ["privilege_escalation", "lateral_movement"],
        "color": "#8e44ad"
    },
    "privilege_escalation": {
        "order": 6,
        "description": "Gaining higher privileges",
        "base_weight": 0.8,
        "indicators": ["privesc", "sudo", "suid", "kernel exploit"],
        "next_stages": ["credential_access", "lateral_movement", "defense_evasion"],
        "color": "#d35400"
    },
    "defense_evasion": {
        "order": 7,
        "description": "Avoiding detection",
        "base_weight": 0.65,
        "indicators": ["obfuscation", "log deletion", "encoding"],
        "next_stages": ["credential_access", "lateral_movement"],
        "color": "#7f8c8d"
    },
    "credential_access": {
        "order": 8,
        "description": "Stealing credentials",
        "base_weight": 0.85,
        "indicators": ["mimikatz", "hash dump", "credential theft"],
        "next_stages": ["lateral_movement", "exfiltration"],
        "color": "#f39c12"
    },
    "lateral_movement": {
        "order": 9,
        "description": "Moving through network",
        "base_weight": 0.9,
        "indicators": ["smb", "rdp", "ssh lateral", "psexec"],
        "next_stages": ["collection", "exfiltration", "impact"],
        "color": "#e74c3c"
    },
    "collection": {
        "order": 10,
        "description": "Gathering target data",
        "base_weight": 0.7,
        "indicators": ["file access", "data collection", "screenshot"],
        "next_stages": ["exfiltration"],
        "color": "#2980b9"
    },
    "command_and_control": {
        "order": 11,
        "description": "C2 communication established",
        "base_weight": 0.8,
        "indicators": ["c2", "beacon", "reverse shell", "c2 channel"],
        "next_stages": ["collection", "lateral_movement", "exfiltration"],
        "color": "#8e44ad"
    },
    "exfiltration": {
        "order": 12,
        "description": "Data leaving target",
        "base_weight": 0.9,
        "indicators": ["data exfil", "data leak", "upload"],
        "next_stages": ["impact"],
        "color": "#c0392b"
    },
    "impact": {
        "order": 13,
        "description": "Final destructive actions",
        "base_weight": 0.95,
        "indicators": ["ransomware", "destruction", "dos", "wipe"],
        "next_stages": [],
        "color": "#e74c3c"
    },
}

# Stage risk multipliers
STAGE_RISK_MULTIPLIERS = {
    "reconnaissance": 1.0,
    "initial_access": 2.5,
    "execution": 3.0,
    "persistence": 2.0,
    "privilege_escalation": 3.5,
    "credential_access": 4.0,
    "lateral_movement": 4.5,
    "exfiltration": 5.0,
    "impact": 5.0,
}


class AttackGraphEngine:
    """
    Advanced Attack Graph Engine.
    Models attack paths, calculates breach probability,
    and simulates attack progression.
    """

    def __init__(self):
        self.graphs = {}

    # ==================================================
    # 🔧 Build Attack Graph (PRESERVED + UPGRADED)
    # ==================================================
    def build_attack_graph(self, detected_stages: List[str]) -> Dict:
        """
        Build attack graph from detected stages.
        Preserved + upgraded with metadata.
        """
        graph = {}
        stage_details = {}

        for i in range(len(detected_stages) - 1):
            source = detected_stages[i]
            target = detected_stages[i + 1]

            if source not in graph:
                graph[source] = []
            graph[source].append(target)

            # Stage metadata
            if source not in stage_details:
                stage_info = ATTACK_STAGES.get(source, {})
                stage_details[source] = {
                    "order": stage_info.get("order", 0),
                    "description": stage_info.get("description", "Unknown stage"),
                    "base_weight": stage_info.get("base_weight", 0.5),
                }

        # Add last stage
        if detected_stages:
            last = detected_stages[-1]
            if last not in stage_details:
                stage_info = ATTACK_STAGES.get(last, {})
                stage_details[last] = {
                    "order": stage_info.get("order", 0),
                    "description": stage_info.get("description", "Unknown stage"),
                    "base_weight": stage_info.get("base_weight", 0.5),
                }

        return {
            "graph": graph,
            "stage_details": stage_details,
            "total_stages": len(detected_stages),
            "stages": detected_stages,
        }

    # ==================================================
    # 🎯 Calculate Edge Weights (PRESERVED + UPGRADED)
    # ==================================================
    def calculate_edge_weights(self, graph: Dict) -> Dict:
        """
        Calculate weighted edges with stage-based heuristics.
        Preserved + upgraded with dynamic weighting.
        """
        weighted_graph = {}

        for node, edges in graph.items():
            weighted_graph[node] = []
            stage_info = ATTACK_STAGES.get(node, {})
            base_weight = stage_info.get("base_weight", 0.5)
            risk_mult = STAGE_RISK_MULTIPLIERS.get(node, 1.0)

            for edge in edges:
                target_info = ATTACK_STAGES.get(edge, {})
                target_weight = target_info.get("base_weight", 0.5)

                # Combined weight
                edge_weight = (base_weight + target_weight) / 2
                edge_weight = min(edge_weight * (risk_mult / 5), 1.0)

                weighted_graph[node].append({
                    "to": edge,
                    "weight": round(edge_weight, 3),
                    "risk_multiplier": risk_mult,
                    "description": f"{node} → {edge}",
                })

        return weighted_graph

    # ==================================================
    # 📊 Breach Probability (PRESERVED + UPGRADED)
    # ==================================================
    def estimate_breach_probability(self, weighted_graph: Dict) -> Dict:
        """
        Estimate breach probability with detailed analysis.
        Preserved + massively upgraded.
        """
        if not weighted_graph:
            return {
                "breach_probability": 0.1,
                "assessment": "Minimal Threat Surface",
                "confidence": "low",
            }

        total_weight = 0
        edge_count = 0
        max_weight = 0
        critical_paths = []

        for node, edges in weighted_graph.items():
            for edge in edges:
                w = edge["weight"]
                total_weight += w
                edge_count += 1
                if w > max_weight:
                    max_weight = w

                if w >= 0.7:
                    critical_paths.append(f"{node} → {edge['to']} (weight: {w})")

        if edge_count == 0:
            return {
                "breach_probability": 0.1,
                "assessment": "Minimal Threat Surface",
                "confidence": "low",
            }

        avg_weight = total_weight / edge_count

        # Probability calculation
        breach_prob = min((avg_weight * 0.7) + (max_weight * 0.3), 1.0)
        breach_prob = round(breach_prob, 3)

        # Assessment
        if breach_prob >= 0.8:
            assessment = "Critical Breach Probability — Immediate Action Required"
            level = "CRITICAL"
        elif breach_prob >= 0.65:
            assessment = "High Breach Probability — Urgent Remediation Needed"
            level = "HIGH"
        elif breach_prob >= 0.5:
            assessment = "Moderate Breach Probability — Prioritize Remediation"
            level = "MEDIUM"
        elif breach_prob >= 0.3:
            assessment = "Low-Moderate Breach Probability — Monitor Closely"
            level = "LOW"
        else:
            assessment = "Minimal Breach Probability"
            level = "INFO"

        return {
            "breach_probability": breach_prob,
            "breach_percentage": f"{breach_prob * 100:.1f}%",
            "assessment": assessment,
            "level": level,
            "avg_path_weight": round(avg_weight, 3),
            "max_path_weight": round(max_weight, 3),
            "total_attack_paths": edge_count,
            "critical_paths": critical_paths,
            "confidence": "high" if edge_count >= 3 else "medium",
        }

    # ==================================================
    # 🔍 Critical Path Analysis
    # ==================================================
    def find_critical_path(self, weighted_graph: Dict) -> Dict:
        """
        Highest-risk attack path dhundho.
        """
        if not weighted_graph:
            return {"critical_path": [], "total_weight": 0}

        # Find all paths using DFS
        all_paths = []

        def dfs(node, path, weight):
            if node not in weighted_graph or not weighted_graph[node]:
                all_paths.append((path[:], weight))
                return

            for edge in weighted_graph[node]:
                path.append(edge["to"])
                dfs(edge["to"], path, weight + edge["weight"])
                path.pop()

        # Start from all root nodes
        all_nodes = set(weighted_graph.keys())
        target_nodes = set()
        for edges in weighted_graph.values():
            for e in edges:
                target_nodes.add(e["to"])

        root_nodes = all_nodes - target_nodes

        for root in root_nodes or list(weighted_graph.keys())[:1]:
            dfs(root, [root], 0)

        if not all_paths:
            return {"critical_path": [], "total_weight": 0}

        # Highest weight path
        critical = max(all_paths, key=lambda x: x[1])

        return {
            "critical_path": critical[0],
            "total_weight": round(critical[1], 3),
            "path_length": len(critical[0]),
            "all_paths_count": len(all_paths),
        }

    # ==================================================
    # 🚀 Full Analysis Pipeline
    # ==================================================
    def full_analysis(self, detected_stages: List[str], findings: List[Dict] = None) -> Dict:
        """
        Complete attack graph analysis.

        Args:
            detected_stages: List of attack stages detected
            findings: Optional vulnerability findings

        Returns:
            Complete attack graph analysis
        """
        start_time = time.time()

        # Auto-detect stages from findings
        if findings and not detected_stages:
            detected_stages = self._detect_stages_from_findings(findings)

        if not detected_stages:
            detected_stages = ["reconnaissance"]

        # Build graph
        graph_data = self.build_attack_graph(detected_stages)

        # Calculate weights
        weighted_graph = self.calculate_edge_weights(graph_data["graph"])

        # Breach probability
        breach_prob = self.estimate_breach_probability(weighted_graph)

        # Critical path
        critical_path = self.find_critical_path(weighted_graph)

        # Attack progression
        progression = self._analyze_progression(detected_stages)

        return {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "detected_stages": detected_stages,
            "graph": graph_data["graph"],
            "stage_details": graph_data["stage_details"],
            "weighted_graph": weighted_graph,
            "breach_probability": breach_prob,
            "critical_path": critical_path,
            "attack_progression": progression,
            "analysis_time_sec": round(time.time() - start_time, 3),
        }

    def _detect_stages_from_findings(self, findings: List[Dict]) -> List[str]:
        """Findings se attack stages detect karo."""
        stages = []

        for finding in findings:
            finding_text = str(finding).lower()

            for stage, data in ATTACK_STAGES.items():
                for indicator in data["indicators"]:
                    if indicator in finding_text and stage not in stages:
                        stages.append(stage)
                        break

        # Sort by order
        stages.sort(key=lambda s: ATTACK_STAGES.get(s, {}).get("order", 99))
        return stages

    def _analyze_progression(self, stages: List[str]) -> Dict:
        """Attack progression analyze karo."""
        if not stages:
            return {}

        orders = [ATTACK_STAGES.get(s, {}).get("order", 0) for s in stages]
        max_stage = max(orders) if orders else 0

        if max_stage >= 10:
            maturity = "Advanced — Breach likely occurred"
        elif max_stage >= 7:
            maturity = "Intermediate — Active intrusion"
        elif max_stage >= 4:
            maturity = "Early — Initial foothold"
        else:
            maturity = "Reconnaissance — Pre-attack"

        return {
            "current_stage": stages[-1] if stages else "unknown",
            "max_stage_reached": max_stage,
            "attack_maturity": maturity,
            "stages_count": len(stages),
        }


# ==================================================
# 🔧 STANDALONE FUNCTIONS (PRESERVED)
# ==================================================

def build_attack_graph(detected_stages: List[str]) -> Dict:
    """Preserved standalone function."""
    engine = AttackGraphEngine()
    data = engine.build_attack_graph(detected_stages)
    return data["graph"]


def calculate_edge_weights(graph: Dict) -> Dict:
    """Preserved standalone function."""
    engine = AttackGraphEngine()
    return engine.calculate_edge_weights(graph)


def estimate_breach_probability(weighted_graph: Dict) -> Dict:
    """Preserved standalone function."""
    engine = AttackGraphEngine()
    return engine.estimate_breach_probability(weighted_graph)
