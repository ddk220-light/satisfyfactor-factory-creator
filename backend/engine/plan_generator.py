# backend/engine/plan_generator.py
"""Generate comprehensive factory plan: building counts, power, resource sourcing."""
import math
from backend.engine.recipe_graph import RecipeDAG, RecipeNode, RAW_RESOURCES

POWER_EXPONENT = 1.321929


def generate_factory_plan(
    dag: RecipeDAG,
    allocated_rate: float,
    local_resources: dict[str, float],
) -> dict:
    """
    Generate a full production plan for one factory.

    Returns dict with: target_rate, buildings[], total_power_mw,
    total_buildings, train_imports, local_extraction, building_summary.
    """
    buildings = []
    total_power = 0.0
    raw_demands: dict[str, float] = {}
    visited: set[str] = set()

    def _plan_node(node: RecipeNode, needed_rate: float):
        nonlocal total_power
        if node.output_per_min <= 0:
            return
        if node.item in visited:
            return
        visited.add(node.item)

        count_exact = needed_rate / node.output_per_min
        count_ceil = math.ceil(count_exact)
        frac = count_exact - math.floor(count_exact)

        full_buildings = math.floor(count_exact)
        power_full = full_buildings * node.power_mw
        power_partial = node.power_mw * (frac ** POWER_EXPONENT) if frac > 0.001 else 0
        power_total = power_full + power_partial
        total_power += power_total

        buildings.append({
            "item": node.item,
            "recipe": node.recipe_name,
            "building": node.building,
            "count_exact": round(count_exact, 4),
            "count": count_ceil,
            "last_clock_pct": round(frac * 100, 1) if frac > 0.01 else 100.0,
            "power_mw": round(power_total, 1),
        })

        scale = needed_rate / node.output_per_min
        for input_item, qty in node.inputs.items():
            input_rate = (qty / node.duration_s * 60) * scale
            if input_item in RAW_RESOURCES:
                raw_demands[input_item] = raw_demands.get(input_item, 0) + input_rate
            else:
                child = next((c for c in node.children if c.item == input_item), None)
                if child:
                    _plan_node(child, input_rate)

    _plan_node(dag.root, allocated_rate)

    train_imports = {}
    local_extraction = {}
    for resource, demand in raw_demands.items():
        local_cap = local_resources.get(resource, 0.0)
        local_used = min(demand, local_cap)
        train_needed = max(0, demand - local_cap)
        local_extraction[resource] = round(local_used, 2)
        if train_needed > 0.01:
            train_imports[resource] = round(train_needed, 2)

    building_summary: dict[str, int] = {}
    for b in buildings:
        building_summary[b["building"]] = building_summary.get(b["building"], 0) + b["count"]

    return {
        "target_rate": allocated_rate,
        "buildings": buildings,
        "total_buildings": sum(b["count"] for b in buildings),
        "total_power_mw": round(total_power, 1),
        "raw_demands": {k: round(v, 2) for k, v in raw_demands.items()},
        "train_imports": train_imports,
        "local_extraction": local_extraction,
        "building_summary": building_summary,
    }
