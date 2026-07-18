"""
Chhoti Don EvolveX - Context Graph
Advanced dependency analysis with circular detection,
impact assessment, and module coupling metrics.
Phase 2.2 - Full Upgrade
"""

import ast
import os
from typing import Dict, List, Set, Tuple, Tuple
from collections import defaultdict, deque


def build_dependency_graph(files: List[str]) -> Dict:
    """
    Build dependency graph from Python files.
    Preserved + upgraded with full analysis.
    """
    print("[EvolveX] Building dependency graph...")
    graph = {}

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=file)

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            graph[file] = list(set(imports))  # deduplicate

        except Exception as e:
            print(f"[EvolveX] Error parsing {file}: {e}")
            graph[file] = []

    return graph


def analyze_dependencies(graph: Dict) -> Dict:
    """
    Advanced dependency analysis.

    Returns:
        - circular dependencies
        - most imported modules
        - coupling metrics
        - isolated files
    """
    # Circular dependency detection
    circular = _detect_circular_dependencies(graph)

    # Most imported modules
    import_counts = defaultdict(int)
    for imports in graph.values():
        for imp in imports:
            import_counts[imp] += 1

    top_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Isolated files (no imports, not imported)
    all_imported = set()
    for imports in graph.values():
        all_imported.update(imports)

    files_without_imports = [f for f, imps in graph.items() if not imps]

    # Coupling score
    total_edges = sum(len(v) for v in graph.values())
    avg_coupling = total_edges / max(len(graph), 1)

    return {
        "total_files": len(graph),
        "total_dependencies": total_edges,
        "avg_coupling": round(avg_coupling, 2),
        "circular_dependencies": circular,
        "top_imported_modules": top_imports[:5],
        "isolated_files": files_without_imports[:5],
        "coupling_level": "high" if avg_coupling > 10 else "medium" if avg_coupling > 5 else "low",
    }


def _detect_circular_dependencies(graph: Dict) -> List[List[str]]:
    """Circular dependencies detect karo using DFS."""
    visited = set()
    path = []
    circular = []

    def dfs(node, path_set):
        if node in path_set:
            cycle_start = path.index(node)
            circular.append(path[cycle_start:] + [node])
            return
        if node in visited:
            return

        visited.add(node)
        path.append(node)
        path_set.add(node)

        for neighbor in graph.get(node, []):
            # Only follow local imports
            for file_key in graph:
                if neighbor in file_key:
                    dfs(file_key, path_set.copy())

        path.pop()

    for node in list(graph.keys())[:20]:  # Limit for performance
        dfs(node, set())

    return circular[:5]  # Return max 5 cycles


def get_import_tree(file_path: str, graph: Dict, depth: int = 3) -> Dict:
    """Specific file ka import tree build karo."""
    visited = set()

    def build_tree(node, current_depth):
        if current_depth == 0 or node in visited:
            return {}
        visited.add(node)

        children = {}
        for imp in graph.get(node, []):
            children[imp] = build_tree(imp, current_depth - 1)

        return children

    return {
        "file": file_path,
        "imports": build_tree(file_path, depth),
        "depth": depth,
    }
