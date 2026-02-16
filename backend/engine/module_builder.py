# backend/engine/module_builder.py
"""
Decompose a factory plan into smallest repeatable module.

Module = 1 final-product building at 100% clock + all upstream buildings.
Total copies = ceil(target_rate / rate_per_module).
"""
import math
from backend.engine.recipe_graph import RecipeDAG


def compute_modules(dag: RecipeDAG, plan: dict) -> dict:
    """
    Compute the repeatable module for a factory plan.

    Returns: {rate_per_module, copies, buildings_per_module, power_per_module, buildings[]}
    """
    root = dag.root
    rate_per_module = root.output_per_min
    target_rate = plan["target_rate"]

    if rate_per_module <= 0:
        return {"rate_per_module": 0, "copies": 0, "buildings_per_module": 0,
                "power_per_module": 0, "buildings": []}

    copies_exact = target_rate / rate_per_module
    copies = math.ceil(copies_exact)

    module_buildings = []
    total_module_power = 0.0
    for b in plan["buildings"]:
        count_per_module = b["count_exact"] / copies_exact if copies_exact > 0 else 0
        power_per_module = b["power_mw"] / copies_exact if copies_exact > 0 else 0
        module_buildings.append({
            "item": b["item"],
            "recipe": b["recipe"],
            "building": b["building"],
            "count_exact": round(count_per_module, 4),
            "count": math.ceil(count_per_module),
            "power_mw": round(power_per_module, 1),
        })
        total_module_power += power_per_module

    return {
        "rate_per_module": round(rate_per_module, 4),
        "copies": copies,
        "buildings_per_module": sum(b["count"] for b in module_buildings),
        "power_per_module": round(total_module_power, 1),
        "buildings": module_buildings,
    }
