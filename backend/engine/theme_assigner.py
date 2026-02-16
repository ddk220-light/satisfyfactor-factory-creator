# backend/engine/theme_assigner.py
"""
Assign recipe DAG nodes to resource-based factory themes.

Algorithm:
1. For each recipe node, determine which raw resources its subtree consumes
2. Map raw resources to themes via themes.json primary_resources
3. Assign each recipe to the theme of its rarest raw resource
4. Merge trivial themes (<5% of total demand) into nearest related theme
5. Cap at max_factories
"""
import json
import os
from backend.engine.recipe_graph import RecipeDAG, RecipeNode, RAW_RESOURCES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

RESOURCE_NODE_COUNTS = {
    "Iron Ore": 163, "Limestone": 72, "Copper Ore": 50, "Coal": 43,
    "Caterium Ore": 16, "Raw Quartz": 17, "Sulfur": 15, "Bauxite": 14,
    "Crude Oil": 18, "Uranium": 5, "Nitrogen Gas": 13, "SAM": 25,
    "Water": 999,
}


def load_themes() -> list[dict]:
    with open(os.path.join(DATA_DIR, "themes.json")) as f:
        return json.load(f)


def _resource_to_theme(resource: str, themes: list[dict]) -> dict | None:
    for theme in themes:
        if resource in theme["primary_resources"]:
            return theme
    return None


def _subtree_raw_demands(node: RecipeNode, visited: set | None = None) -> dict[str, float]:
    if visited is None:
        visited = set()
    if node.item in visited:
        return {}
    visited.add(node.item)

    demands: dict[str, float] = {}
    scale = 1.0 / node.output_per_min if node.output_per_min > 0 else 0

    for input_item, qty in node.inputs.items():
        rate = (qty / node.duration_s * 60) * scale
        if input_item in RAW_RESOURCES:
            demands[input_item] = demands.get(input_item, 0) + rate
        else:
            child = next((c for c in node.children if c.item == input_item), None)
            if child:
                child_demands = _subtree_raw_demands(child, visited)
                for res, child_rate in child_demands.items():
                    child_output = child.output_per_min
                    child_scale = rate / child_output if child_output > 0 else 0
                    demands[res] = demands.get(res, 0) + child_rate * child_scale
    return demands


def assign_themes(dag: RecipeDAG, themes: list[dict], max_factories: int) -> list[dict]:
    """
    Assign DAG nodes to themes. Returns list of theme assignments:
    [{"theme": theme_dict, "recipes": [node, ...], "raw_demands": {...}}, ...]
    """
    node_theme_map: dict[str, dict] = {}
    node_demands: dict[str, dict[str, float]] = {}

    for node in dag.nodes:
        demands = _subtree_raw_demands(node)
        node_demands[node.item] = demands

        rarest_resource = None
        min_nodes = float("inf")
        for resource in demands:
            if resource == "Water":
                continue
            count = RESOURCE_NODE_COUNTS.get(resource, 999)
            if count < min_nodes:
                min_nodes = count
                rarest_resource = resource

        if rarest_resource:
            theme = _resource_to_theme(rarest_resource, themes)
            if theme:
                node_theme_map[node.item] = theme

    iron_theme = next((t for t in themes if t["id"] == "iron-works"), themes[0])
    for node in dag.nodes:
        if node.item not in node_theme_map:
            node_theme_map[node.item] = iron_theme

    theme_groups: dict[str, dict] = {}
    for node in dag.nodes:
        theme = node_theme_map[node.item]
        tid = theme["id"]
        if tid not in theme_groups:
            theme_groups[tid] = {"theme": theme, "recipes": [], "raw_demands": {}}
        theme_groups[tid]["recipes"].append(node)

    root_demands = node_demands.get(dag.root.item, {})
    total_demand = sum(root_demands.values())

    for tid, group in theme_groups.items():
        resources_owned = set(group["theme"]["primary_resources"])
        for res, demand in root_demands.items():
            owner_theme = _resource_to_theme(res, themes)
            if owner_theme and owner_theme["id"] == tid:
                group["raw_demands"][res] = demand

    if total_demand > 0:
        to_merge = []
        for tid, group in theme_groups.items():
            theme_demand = sum(group["raw_demands"].values())
            if theme_demand / total_demand < 0.05 and len(theme_groups) > 1:
                to_merge.append(tid)

        for tid in to_merge:
            remaining = {k: v for k, v in theme_groups.items() if k not in to_merge}
            if remaining:
                largest = max(remaining, key=lambda k: sum(remaining[k]["raw_demands"].values()))
                theme_groups[largest]["recipes"].extend(theme_groups[tid]["recipes"])
                for res, demand in theme_groups[tid]["raw_demands"].items():
                    theme_groups[largest]["raw_demands"][res] = \
                        theme_groups[largest]["raw_demands"].get(res, 0) + demand
                del theme_groups[tid]

    assignments = sorted(theme_groups.values(),
                         key=lambda g: sum(g["raw_demands"].values()), reverse=True)
    if len(assignments) > max_factories:
        kept = assignments[:max_factories]
        for excess in assignments[max_factories:]:
            kept[-1]["recipes"].extend(excess["recipes"])
            for res, demand in excess["raw_demands"].items():
                kept[-1]["raw_demands"][res] = kept[-1]["raw_demands"].get(res, 0) + demand
        assignments = kept

    return assignments
