# backend/engine/location_finder.py
"""
Find optimal factory locations based on proximity to resource nodes.

Scoring: For each candidate point (every resource node center), score by
sum of purity_weight * (demand * rarity^1.5) for all critical resources
within the search radius.
"""
import math

PURITY_WEIGHT = {"impure": 1, "normal": 2, "pure": 4}
MIN_SEPARATION = 25000  # game units (250m) between distinct locations


def _distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _quadrant(x, y) -> str:
    ns = "N" if y < 0 else "S"
    ew = "W" if x < 0 else "E"
    return ns + ew


def _count_by_type(nodes: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in nodes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    return counts


def find_locations(
    nodes: list[dict],
    critical_resources: dict[str, float],
    search_radius_m: float,
    n_results: int,
    excluded_quadrants: list[str],
) -> list[dict]:
    """
    Find top N factory locations scored by proximity to critical resources.

    Args:
        nodes: list of resource node dicts with type, purity, x, y
        critical_resources: {resource_type -> demand_per_min}
        search_radius_m: search radius in meters (converted to game units * 100)
        n_results: max number of locations to return
        excluded_quadrants: list of quadrant strings to exclude (NE, NW, SE, SW)

    Returns list of dicts with: center (x, y), score, resources breakdown, nearby_nodes.
    """
    radius = search_radius_m * 100  # meters to game units
    node_counts = _count_by_type(nodes)
    max_count = max(node_counts.values()) if node_counts else 1

    # Map resource names to node types (e.g. "Iron Ore" -> "iron")
    # The nodes use lowercase type names, but critical_resources uses item names
    resource_type_map = {
        "Iron Ore": "iron", "Copper Ore": "copper", "Limestone": "limestone",
        "Coal": "coal", "Caterium Ore": "caterium", "Raw Quartz": "quartz",
        "Sulfur": "sulfur", "Bauxite": "bauxite", "Uranium": "uranium",
        "Crude Oil": "oil", "Water": "water", "Nitrogen Gas": "nitrogen-gas",
        "SAM": "sam",
    }
    # Build reverse map too
    type_to_resource = {v: k for k, v in resource_type_map.items()}

    # Convert critical_resources keys to node types
    critical_types: dict[str, float] = {}
    for res_name, demand in critical_resources.items():
        node_type = resource_type_map.get(res_name, res_name.lower())
        critical_types[node_type] = demand

    importance = {}
    for ntype, demand in critical_types.items():
        count = node_counts.get(ntype, 1)
        rarity = (max_count / count) ** 1.5
        importance[ntype] = demand * rarity

    scored = []
    resource_types = set(critical_types.keys())

    for center_node in nodes:
        if center_node["type"] not in resource_types:
            continue
        cx, cy = center_node["x"], center_node["y"]

        if _quadrant(cx, cy) in excluded_quadrants:
            continue

        nearby: dict[str, list[dict]] = {t: [] for t in resource_types}
        for n in nodes:
            if n["type"] not in resource_types:
                continue
            d = _distance(cx, cy, n["x"], n["y"])
            if d <= radius:
                nearby[n["type"]].append({**n, "distance": d})

        if not all(nearby.get(t) for t in resource_types):
            continue

        score = 0
        resources_detail = {}
        for rtype in resource_types:
            type_score = sum(
                PURITY_WEIGHT.get(n["purity"], 1) * importance.get(rtype, 1)
                for n in nearby[rtype]
            )
            score += type_score
            purity_breakdown = {}
            for n in nearby[rtype]:
                purity_breakdown[n["purity"]] = purity_breakdown.get(n["purity"], 0) + 1
            res_name = type_to_resource.get(rtype, rtype)
            resources_detail[res_name] = {
                "node_count": len(nearby[rtype]),
                "purity_breakdown": purity_breakdown,
                "score": type_score,
            }

        all_nearby = [n for ns in nearby.values() for n in ns]
        centroid_x = sum(n["x"] for n in all_nearby) / len(all_nearby)
        centroid_y = sum(n["y"] for n in all_nearby) / len(all_nearby)

        scored.append({
            "center": {"x": centroid_x, "y": centroid_y},
            "score": score,
            "resources": resources_detail,
            "nearby_nodes": all_nearby,
        })

    scored.sort(key=lambda s: s["score"], reverse=True)

    results = []
    for loc in scored:
        too_close = any(
            _distance(loc["center"]["x"], loc["center"]["y"],
                      r["center"]["x"], r["center"]["y"]) < MIN_SEPARATION
            for r in results
        )
        if not too_close:
            results.append(loc)
        if len(results) >= n_results:
            break

    return results
