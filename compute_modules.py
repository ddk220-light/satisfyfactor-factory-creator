#!/usr/bin/env python3
"""Compute smallest repeatable HMF module for each factory.
Module = 1 HMF Manufacturer at 100% clock, with all upstream buildings.
Supports shard-based overclock optimization to reduce building counts."""

import sqlite3
import json
import math

db = sqlite3.connect('/Users/deepak/AI/satisfy/satisfactory.db')
db.row_factory = sqlite3.Row

def get_recipe_rates(recipe_name):
    """Get per-building-per-minute rates for a recipe."""
    row = db.execute("SELECT id, duration FROM recipes WHERE name = ?", (recipe_name,)).fetchone()
    if not row:
        raise ValueError(f"Recipe not found: {recipe_name}")
    recipe_id, duration = row['id'], row['duration']

    brow = db.execute("""
        SELECT b.name, b.power_used FROM recipe_buildings rb
        JOIN buildings b ON b.id = rb.building_id
        WHERE rb.recipe_id = ?
    """, (recipe_id,)).fetchone()
    building = brow['name'] if brow else "Unknown"
    power = float(brow['power_used']) if brow and brow['power_used'] else 0

    inputs = {}
    for r in db.execute("""
        SELECT i.name, ri.quantity FROM recipe_ingredients ri
        JOIN items i ON i.id = ri.item_id WHERE ri.recipe_id = ?
    """, (recipe_id,)):
        rate = float(r['quantity']) / duration * 60
        if r['quantity'] >= 1000 and is_fluid(r['name']):
            inputs[r['name']] = rate / 1000
        else:
            inputs[r['name']] = rate

    outputs = {}
    for r in db.execute("""
        SELECT i.name, rp.quantity FROM recipe_products rp
        JOIN items i ON i.id = rp.item_id WHERE rp.recipe_id = ?
    """, (recipe_id,)):
        rate = float(r['quantity']) / duration * 60
        if r['quantity'] >= 1000 and is_fluid(r['name']):
            outputs[r['name']] = rate / 1000
        else:
            outputs[r['name']] = rate

    return {
        "building": building, "power": power,
        "inputs": inputs, "outputs": outputs
    }

FLUID_ITEMS = {"Water", "Crude Oil", "Heavy Oil Residue", "Alumina Solution",
               "Sulfuric Acid", "Nitric Acid", "Fuel", "Turbofuel", "Nitrogen Gas"}

def is_fluid(name):
    return name in FLUID_ITEMS

RAW_RESOURCES = {"Iron Ore", "Copper Ore", "Limestone", "Coal", "Caterium Ore",
                 "Bauxite", "Water", "Crude Oil", "Raw Quartz", "Sulfur",
                 "Nitrogen Gas", "Uranium", "SAM"}

RECIPE_CACHE = {}

def cached_recipe(name):
    if name not in RECIPE_CACHE:
        RECIPE_CACHE[name] = get_recipe_rates(name)
    return RECIPE_CACHE[name]

def short_building(name):
    mapping = {
        "Smelter": "Smelter",
        "Constructor": "Constructor",
        "Assembler": "Assembler",
        "Manufacturer": "Manufacturer",
        "Foundry": "Foundry",
        "Refinery": "Refinery",
        "Blender": "Blender",
    }
    for key, val in mapping.items():
        if key in name:
            return val
    return name

def shards_for_clock(clock_pct):
    """Return number of power shards needed for a given clock speed."""
    if clock_pct <= 100.0:
        return 0
    elif clock_pct <= 150.0:
        return 1
    elif clock_pct <= 200.0:
        return 2
    elif clock_pct <= 250.0:
        return 3
    else:
        raise ValueError(f"Clock {clock_pct}% exceeds max 250%")

# Building footprint (width × length) — larger = higher priority for shard use
BUILDING_FOOTPRINT = {
    "Manufacturer": 440,  # 20×22
    "Blender": 304,       # 19×16
    "Refinery": 200,      # 10×20
    "Assembler": 150,     # 10×15
    "Constructor": 80,    # 8×10
    "Foundry": 72,        # 8×9
    "Smelter": 54,        # 6×9
}

def power_at_clock(base_power, clock_pct):
    """Power consumption at a given clock speed."""
    return base_power * (clock_pct / 100) ** 1.321929


FACTORIES = {
    "ferrium": {
        "theme": "Pure Iron",
        "target_hmf": 18.94,
        "recipe_map": {
            "Heavy Modular Frame": "Alternate: Heavy Encased Frame",
            "Modular Frame": "Alternate: Steeled Frame",
            "Reinforced Iron Plate": "Alternate: Stitched Iron Plate",
            "Encased Industrial Beam": "Alternate: Encased Industrial Pipe",
            "Wire": "Alternate: Iron Wire",
            "Steel Pipe": "Alternate: Iron Pipe",
            "Iron Plate": "Iron Plate",
            "Concrete": "Concrete",
            "Iron Ingot": "Iron Ingot",
        },
        "process_order": [
            "Heavy Modular Frame", "Modular Frame", "Reinforced Iron Plate",
            "Encased Industrial Beam", "Wire", "Iron Plate", "Steel Pipe",
            "Concrete", "Iron Ingot"
        ]
    },
    "naphtheon": {
        "theme": "Oil Ecosystem",
        "target_hmf": 21.3,
        "recipe_map": {
            "Heavy Modular Frame": "Alternate: Heavy Flexible Frame",
            "Modular Frame": "Modular Frame",
            "Reinforced Iron Plate": "Alternate: Adhered Iron Plate",
            "Encased Industrial Beam": "Encased Industrial Beam",
            "Iron Plate": "Alternate: Coated Iron Plate",
            "Screws": "Screws",
            "Iron Rod": "Iron Rod",
            "Steel Beam": "Steel Beam",
            "Concrete": "Alternate: Rubber Concrete",
            "Rubber": "Rubber",
            "Plastic": "Plastic",
            "Steel Ingot": "Alternate: Coke Steel Ingot",
            "Petroleum Coke": "Petroleum Coke",
            "Iron Ingot": "Iron Ingot",
        },
        "process_order": [
            "Heavy Modular Frame", "Modular Frame", "Reinforced Iron Plate",
            "Encased Industrial Beam", "Iron Plate", "Screws", "Iron Rod",
            "Steel Beam", "Concrete",
            "Rubber", "Plastic", "Steel Ingot", "Petroleum Coke",
            "Iron Ingot"
        ]
    },
    "forgeholm": {
        "theme": "Steel Spine",
        "target_hmf": 17.27,
        "recipe_map": {
            "Heavy Modular Frame": "Heavy Modular Frame",
            "Modular Frame": "Alternate: Steeled Frame",
            "Reinforced Iron Plate": "Reinforced Iron Plate",
            "Encased Industrial Beam": "Alternate: Encased Industrial Pipe",
            "Screws": "Alternate: Steel Screws",
            "Iron Plate": "Alternate: Steel Cast Plate",
            "Steel Pipe": "Steel Pipe",
            "Steel Beam": "Steel Beam",
            "Concrete": "Concrete",
            "Steel Ingot": "Steel Ingot",
            "Iron Ingot": "Iron Ingot",
        },
        "process_order": [
            "Heavy Modular Frame", "Modular Frame", "Reinforced Iron Plate",
            "Encased Industrial Beam", "Screws", "Iron Plate", "Steel Pipe",
            "Steel Beam", "Concrete", "Steel Ingot", "Iron Ingot"
        ]
    },
    "luxara": {
        "theme": "Aluminum Replacement",
        "target_hmf": 8.41,
        "recipe_map": {
            "Heavy Modular Frame": "Heavy Modular Frame",
            "Modular Frame": "Modular Frame",
            "Reinforced Iron Plate": "Reinforced Iron Plate",
            "Encased Industrial Beam": "Encased Industrial Beam",
            "Screws": "Screws",
            "Iron Rod": "Alternate: Aluminum Rod",
            "Steel Beam": "Alternate: Aluminum Beam",
            "Iron Plate": "Iron Plate",
            "Steel Pipe": "Steel Pipe",
            "Concrete": "Concrete",
            "Aluminum Ingot": "Aluminum Ingot",
            "Aluminum Scrap": "Aluminum Scrap",
            "Alumina Solution": "Alumina Solution",
            "Steel Ingot": "Steel Ingot",
            "Iron Ingot": "Iron Ingot",
        },
        "process_order": [
            "Heavy Modular Frame", "Modular Frame", "Reinforced Iron Plate",
            "Encased Industrial Beam", "Screws", "Iron Rod", "Iron Plate",
            "Steel Beam", "Steel Pipe", "Concrete",
            "Aluminum Ingot", "Aluminum Scrap", "Alumina Solution",
            "Steel Ingot", "Iron Ingot"
        ]
    },
    "cathera": {
        "theme": "Copper & Caterium",
        "target_hmf": 29.09,
        "recipe_map": {
            "Heavy Modular Frame": "Alternate: Heavy Encased Frame",
            "Modular Frame": "Alternate: Steeled Frame",
            "Reinforced Iron Plate": "Alternate: Stitched Iron Plate",
            "Encased Industrial Beam": "Alternate: Encased Industrial Pipe",
            "Wire": "Alternate: Fused Wire",
            "Steel Pipe": "Alternate: Iron Pipe",
            "Iron Plate": "Iron Plate",
            "Concrete": "Concrete",
            "Iron Ingot": "Alternate: Iron Alloy Ingot",
            "Copper Ingot": "Copper Ingot",
            "Caterium Ingot": "Caterium Ingot",
        },
        "process_order": [
            "Heavy Modular Frame", "Modular Frame", "Reinforced Iron Plate",
            "Encased Industrial Beam", "Wire", "Iron Plate", "Steel Pipe",
            "Concrete", "Iron Ingot", "Copper Ingot", "Caterium Ingot"
        ]
    },
}


def compute_module(factory_key, factory_def, shard_budget=None):
    """Compute module with optional shard optimization.

    shard_budget: max shards available for this factory's modules (all copies).
                  None = no optimization (original behavior).
    """
    recipe_map = factory_def["recipe_map"]

    # Demand and supply pools
    demand = {}
    supply = {}
    steps = []

    # Start: 1 HMF Manufacturer
    hmf_recipe_name = recipe_map["Heavy Modular Frame"]
    hmf_recipe = cached_recipe(hmf_recipe_name)
    hmf_rate = hmf_recipe["outputs"]["Heavy Modular Frame"]

    for item, rate in hmf_recipe["inputs"].items():
        demand[item] = demand.get(item, 0) + rate

    steps.append({
        "recipe": hmf_recipe_name,
        "item": "Heavy Modular Frame",
        "building": short_building(hmf_recipe["building"]),
        "power_mw": hmf_recipe["power"],
        "buildings_exact": 1.0,
        "buildings_ceil": 1,
        "last_clock_pct": 100.0,
        "inputs": {k: round(v, 4) for k, v in hmf_recipe["inputs"].items()},
        "outputs": {"Heavy Modular Frame": round(hmf_rate, 4)},
        "shards_per_building": 0,
        "overclock_detail": "1x at 100%",
    })

    # Process each intermediate item
    for item in factory_def["process_order"][1:]:
        total_demand = demand.get(item, 0)
        if total_demand <= 0.0001:
            continue
        if item not in recipe_map:
            continue

        available = supply.get(item, 0)
        net_needed = total_demand - available
        if net_needed <= 0.0001:
            continue

        recipe_name = recipe_map[item]
        recipe = cached_recipe(recipe_name)
        output_rate = recipe["outputs"][item]
        buildings_exact = net_needed / output_rate
        buildings_ceil = math.ceil(buildings_exact - 0.001)

        frac = buildings_exact - int(buildings_exact)
        if frac < 0.001 or frac > 0.999:
            last_clock = 100.0
        else:
            last_clock = round(frac * 100, 1)

        # Add inputs to demand pool
        step_inputs = {}
        for inp_item, inp_rate in recipe["inputs"].items():
            inp_total = buildings_exact * inp_rate
            step_inputs[inp_item] = round(inp_total, 4)
            demand[inp_item] = demand.get(inp_item, 0) + inp_total

        # Record outputs including by-products
        step_outputs = {}
        for out_item, out_rate in recipe["outputs"].items():
            amount = buildings_exact * out_rate
            step_outputs[out_item] = round(amount, 4)
            if out_item != item:
                supply[out_item] = supply.get(out_item, 0) + amount

        steps.append({
            "recipe": recipe_name,
            "item": item,
            "building": short_building(recipe["building"]),
            "power_mw": recipe["power"],
            "buildings_exact": round(buildings_exact, 4),
            "buildings_ceil": buildings_ceil,
            "last_clock_pct": last_clock,
            "inputs": step_inputs,
            "outputs": step_outputs,
            "shards_per_building": 0,
            "overclock_detail": None,  # computed below
        })

    # --- Shard Optimization ---
    # For each step with a fractional building, check if we can overclock
    # N-1 buildings to absorb the fractional work, saving 1 building.
    #
    # Strategy: if buildings_exact = N + f (where 0 < f < 1),
    #   Without optimization: N+1 buildings (N at 100%, 1 at f*100%)
    #   With 1-shard optimization (f <= 0.5):
    #     The fractional output (f * output_rate) must be distributed among N buildings.
    #     Each building needs to run at (N+f)/N * 100% = (1 + f/N) * 100%
    #     This must be <= 150% (1 shard limit)
    #   With 2-shard optimization (f > 0.5):
    #     Same formula, but overclock must be <= 200%

    copies = math.ceil(factory_def["target_hmf"] / hmf_rate - 0.001)

    # Collect optimization candidates
    candidates = []
    for i, step in enumerate(steps):
        be = step["buildings_exact"]
        bc = step["buildings_ceil"]
        if bc <= 1:
            continue  # Can't save a building from a 1-building step

        frac = be - int(be)
        if frac < 0.001 or frac > 0.999:
            continue  # Already exact, no savings

        # New building count = bc - 1
        new_count = bc - 1
        # Each building must run at this clock to produce the same output
        new_clock = (be / new_count) * 100
        shards_needed = shards_for_clock(new_clock)

        if new_clock > 250:
            continue  # Can't overclock that much

        # Total shards = shards_per_building * new_count * copies
        total_shards = shards_needed * new_count * copies

        candidates.append({
            "step_idx": i,
            "building": step["building"],
            "old_count": bc,
            "new_count": new_count,
            "new_clock": round(new_clock, 1),
            "shards_per_building": shards_needed,
            "total_shards": total_shards,
            "buildings_saved_per_copy": 1,
            "buildings_saved_total": copies,
        })

    # Sort: largest buildings first (most space saved), then fewest shards
    candidates.sort(key=lambda c: (-BUILDING_FOOTPRINT.get(c["building"], 0), c["total_shards"]))

    # Allocate shards greedily
    shards_used = 0
    applied = []
    if shard_budget is not None:
        for c in candidates:
            if shards_used + c["total_shards"] <= shard_budget:
                shards_used += c["total_shards"]
                applied.append(c)

    # Apply optimizations
    for opt in applied:
        step = steps[opt["step_idx"]]
        step["buildings_ceil"] = opt["new_count"]
        step["last_clock_pct"] = opt["new_clock"]
        step["shards_per_building"] = opt["shards_per_building"]

    # Generate overclock_detail for all steps
    for step in steps:
        bc = step["buildings_ceil"]
        lc = step["last_clock_pct"]
        shards = step["shards_per_building"]

        if shards > 0:
            # All buildings at the same overclocked speed
            step["overclock_detail"] = f"{bc}x at {lc}% ({shards} shard{'s' if shards > 1 else ''} each)"
        elif lc == 100.0:
            if bc == 1:
                step["overclock_detail"] = "1x at 100%"
            else:
                step["overclock_detail"] = f"{bc}x at 100%"
        else:
            full = bc - 1
            if full == 0:
                step["overclock_detail"] = f"1x at {lc}%"
            else:
                step["overclock_detail"] = f"{full}x at 100% + 1x at {lc}%"

    # Compute raw inputs
    raw_inputs = {}
    for item, total_demand in sorted(demand.items()):
        total_supply = supply.get(item, 0)
        net = total_demand - total_supply
        if net > 0.001:
            if item in RAW_RESOURCES or item not in recipe_map:
                is_fl = is_fluid(item)
                raw_inputs[item] = {
                    "per_min": round(net, 2),
                    "is_fluid": is_fl,
                    "note": "m³/min" if is_fl else "items/min"
                }

    # Compute surplus by-products
    surplus = {}
    for item, total_supply in sorted(supply.items()):
        total_demand_for = demand.get(item, 0)
        net = total_supply - total_demand_for
        if net > 0.001:
            surplus[item] = round(net, 2)

    # Building totals and power
    building_counts = {}
    total_buildings = 0
    total_power = 0
    total_shards_module = 0
    for step in steps:
        b = step["building"]
        building_counts[b] = building_counts.get(b, 0) + step["buildings_ceil"]
        total_buildings += step["buildings_ceil"]

        base = step["power_mw"]
        n = step["buildings_ceil"]
        lc = step["last_clock_pct"]
        shards = step["shards_per_building"]
        total_shards_module += shards * n

        if n == 0:
            continue
        if shards > 0:
            # All buildings at same overclocked speed
            total_power += n * power_at_clock(base, lc)
        elif lc == 100.0:
            total_power += n * base
        else:
            total_power += (n - 1) * base + power_at_clock(base, lc)

    copies_exact = factory_def["target_hmf"] / hmf_rate

    # Reverse steps for display (raw → final)
    display_steps = list(reversed(steps))

    module = {
        "factory": factory_key,
        "theme": factory_def["theme"],
        "module_basis": "1 Manufacturer at 100%",
        "hmf_recipe": hmf_recipe_name,
        "hmf_per_min": round(hmf_rate, 4),
        "raw_inputs": raw_inputs,
        "steps": display_steps,
        "building_totals": building_counts,
        "total_buildings": total_buildings,
        "total_power_mw": round(total_power, 1),
        "shards_per_module": total_shards_module,
        "target_hmf": factory_def["target_hmf"],
        "copies_needed_exact": round(copies_exact, 4),
        "copies_needed_ceil": math.ceil(copies_exact - 0.001),
        "total_shards_all_copies": total_shards_module * math.ceil(copies_exact - 0.001),
    }

    if surplus:
        module["byproduct_surplus"] = surplus

    if applied:
        module["optimizations_applied"] = [{
            "item": steps[a["step_idx"]]["item"],
            "old_buildings": a["old_count"],
            "new_buildings": a["new_count"],
            "new_clock_pct": a["new_clock"],
            "shards_per_building": a["shards_per_building"],
        } for a in applied]

    return module


def format_modules_text(result):
    """Generate human-readable text output."""
    lines = []
    lines.append("HMF-95 FACTORY MODULES (Shard-Optimized)")
    lines.append("=" * 72)
    lines.append("Each module = 1 HMF Manufacturer at 100% + all upstream buildings.")
    lines.append("Shard optimization: buildings overclocked to reduce count.")
    lines.append("Stamp-copy the module to reach target output.")
    lines.append("")

    total_shards_all = 0

    for key in ["ferrium", "naphtheon", "forgeholm", "luxara", "cathera"]:
        mod = result["modules"][key]
        total_shards_all += mod["total_shards_all_copies"]

        lines.append("=" * 72)
        name = key.upper()
        lines.append(f" {name} — {mod['theme']}")
        lines.append(f" {mod['hmf_recipe']} → {mod['hmf_per_min']} HMF/min")
        lines.append(f" {mod['total_buildings']} buildings | {mod['total_power_mw']} MW | "
                     f"{mod['shards_per_module']} shards/module | "
                     f"x{mod['copies_needed_ceil']} copies → {mod['target_hmf']} HMF target")
        lines.append(f" Total shards for all copies: {mod['total_shards_all_copies']}")
        lines.append("=" * 72)
        lines.append("")

        # Raw inputs
        lines.append("  RAW INPUTS:")
        for item, info in sorted(mod["raw_inputs"].items()):
            unit = "m³/min" if info["is_fluid"] else "/min"
            lines.append(f"       {info['per_min']:>8.1f} {unit:<12s} {item}")
        lines.append("")

        # Surplus
        if "byproduct_surplus" in mod:
            lines.append("  SURPLUS (needs sink):")
            for item, rate in mod["byproduct_surplus"].items():
                is_fl = is_fluid(item)
                unit = "m³/min" if is_fl else "/min"
                lines.append(f"       {rate:>8.1f} {unit:<12s} {item}")
            lines.append("")

        # Production chain grouped by stage
        stages = {
            "Smelting & Refining": ["Smelter", "Foundry", "Refinery"],
            "Parts": ["Constructor", "Assembler"],
            "Components": ["Assembler"],
            "Assembly": ["Assembler"],
            "Final": ["Manufacturer"],
        }

        # Categorize steps by tier
        step_list = mod["steps"]  # already reversed: raw→final

        # Simple categorization by item type
        smelting_items = {"Iron Ingot", "Copper Ingot", "Caterium Ingot", "Steel Ingot",
                          "Aluminum Ingot", "Aluminum Scrap", "Alumina Solution",
                          "Petroleum Coke", "Rubber", "Plastic", "Iron Plate"}
        parts_items = {"Concrete", "Steel Pipe", "Steel Beam", "Iron Plate", "Iron Rod",
                       "Screws", "Wire"}
        component_items = {"Encased Industrial Beam", "Reinforced Iron Plate"}
        assembly_items = {"Modular Frame"}
        final_items = {"Heavy Modular Frame"}

        def categorize(step):
            item = step["item"]
            building = step["building"]
            if item in final_items:
                return "Final"
            if item in assembly_items:
                return "Assembly"
            if item in component_items:
                return "Components"
            if building in ("Smelter", "Foundry", "Refinery"):
                return "Smelting & Refining"
            if item in parts_items:
                return "Parts"
            # Assembler making parts (like Rubber Concrete, Coated Iron Plate, etc)
            if building == "Assembler" and item in ("Concrete", "Iron Plate"):
                return "Parts"
            return "Parts"

        # Group steps
        stage_order = ["Smelting & Refining", "Parts", "Components", "Assembly", "Final"]
        grouped = {s: [] for s in stage_order}
        for step in step_list:
            cat = categorize(step)
            grouped[cat].append(step)

        lines.append("  PRODUCTION CHAIN:")
        lines.append("")

        for stage_name in stage_order:
            stage_steps = grouped[stage_name]
            if not stage_steps:
                continue

            lines.append(f"  ── {stage_name} " + "─" * (56 - len(stage_name)))

            for step in stage_steps:
                detail = step["overclock_detail"]
                shard_note = ""
                if step["shards_per_building"] > 0:
                    shard_note = " ⚡"

                lines.append(f"    {step['building']:<14s}{detail:<38s}[{step['recipe']}]{shard_note}")

                # Inputs
                inp_parts = []
                for inp_item, inp_rate in step["inputs"].items():
                    inp_parts.append(f"{inp_rate:.1f} {inp_item}")
                lines.append(f"                 {' + '.join(inp_parts)}")

                # Outputs
                out_parts = []
                for out_item, out_rate in step["outputs"].items():
                    out_parts.append(f"{out_rate:.1f} {out_item}")
                lines.append(f"                 → {' + '.join(out_parts)}")
                lines.append("")

        # Summary
        lines.append("  ── Summary " + "─" * 58)
        for btype, count in sorted(mod["building_totals"].items(), key=lambda x: -x[1]):
            lines.append(f"    {btype:<14s}x{count}")
        lines.append(f"    {'─' * 15}")
        lines.append(f"    TOTAL         x{mod['total_buildings']}  ({mod['total_power_mw']} MW, "
                     f"{mod['shards_per_module']} shards)")
        lines.append("")

        # Optimizations applied
        if "optimizations_applied" in mod:
            lines.append("  ── Shard Optimizations " + "─" * 47)
            for opt in mod["optimizations_applied"]:
                lines.append(f"    {opt['item']}: {opt['old_buildings']}→{opt['new_buildings']} buildings "
                            f"@ {opt['new_clock_pct']}% ({opt['shards_per_building']} shard each)")
            lines.append("")

        lines.append("")

    # Grand summary
    lines.append("=" * 72)
    lines.append(" GRAND SUMMARY")
    lines.append("=" * 72)
    lines.append("")

    grand_buildings = 0
    grand_power = 0
    grand_shards = 0

    lines.append(f"  {'Factory':<12s} {'HMF/mod':>8s} {'Bldg/mod':>9s} {'Shards/mod':>11s} "
                 f"{'Copies':>7s} {'Tot Bldg':>9s} {'Tot Shards':>11s}")
    lines.append(f"  {'─' * 70}")

    for entry in result["summary"]:
        mod = result["modules"][entry["factory"]]
        tot_bldg = mod["total_buildings"] * mod["copies_needed_ceil"]
        grand_buildings += tot_bldg
        grand_power += mod["total_power_mw"] * mod["copies_needed_ceil"]
        grand_shards += mod["total_shards_all_copies"]

        lines.append(f"  {entry['factory']:<12s} {mod['hmf_per_min']:>8.2f} {mod['total_buildings']:>9d} "
                     f"{mod['shards_per_module']:>11d} {mod['copies_needed_ceil']:>7d} "
                     f"{tot_bldg:>9d} {mod['total_shards_all_copies']:>11d}")

    lines.append(f"  {'─' * 70}")
    lines.append(f"  {'TOTAL':<12s} {'':>8s} {'':>9s} {'':>11s} {'':>7s} "
                 f"{grand_buildings:>9d} {grand_shards:>11d}")
    lines.append("")
    lines.append(f"  Total power (all copies): {grand_power:.1f} MW")
    lines.append(f"  Total shards used: {grand_shards} / 200")
    lines.append("")

    return "\n".join(lines)


# Main
TOTAL_SHARD_BUDGET = 200

# First pass: compute without optimization to get copy counts and identify candidates
# Then allocate shards globally across all factories

# Step 1: Compute base modules to get copy counts
base_modules = {}
for key in ["ferrium", "naphtheon", "forgeholm", "luxara", "cathera"]:
    base_modules[key] = compute_module(key, FACTORIES[key], shard_budget=None)

# Step 2: Collect ALL optimization candidates globally with copy counts
all_candidates = []
for key in ["ferrium", "naphtheon", "forgeholm", "luxara", "cathera"]:
    mod = base_modules[key]
    copies = mod["copies_needed_ceil"]

    for step in mod["steps"]:
        be = step["buildings_exact"]
        bc = step["buildings_ceil"]
        if bc <= 1:
            continue
        frac = be - int(be)
        if frac < 0.001 or frac > 0.999:
            continue

        new_count = bc - 1
        new_clock = (be / new_count) * 100
        if new_clock > 250:
            continue

        shards_needed = shards_for_clock(new_clock)
        total_shards = shards_needed * new_count * copies

        all_candidates.append({
            "factory": key,
            "item": step["item"],
            "building": step["building"],
            "old_count": bc,
            "new_count": new_count,
            "new_clock": round(new_clock, 1),
            "shards_per_building": shards_needed,
            "shards_per_module": shards_needed * new_count,
            "total_shards": total_shards,
            "copies": copies,
        })

# Step 3: Greedy allocation - largest buildings first (most space saved), then fewest shards
all_candidates.sort(key=lambda c: (-BUILDING_FOOTPRINT.get(c["building"], 0), c["total_shards"]))

shard_budget_remaining = TOTAL_SHARD_BUDGET
# Track total shards per factory (across ALL copies)
factory_total_shards = {k: 0 for k in ["ferrium", "naphtheon", "forgeholm", "luxara", "cathera"]}
selected = []

for c in all_candidates:
    if shard_budget_remaining >= c["total_shards"]:
        shard_budget_remaining -= c["total_shards"]
        factory_total_shards[c["factory"]] += c["total_shards"]
        selected.append(c)

# Step 4: Recompute modules with exact per-factory shard budgets
result = {
    "meta": {
        "title": "HMF-95 Factory Modules (v3 — Shard-Optimized)",
        "description": "Smallest repeatable module per factory: 1 HMF Manufacturer at 100% with all upstream buildings. Overclocked where beneficial to reduce building count. Stamp-copy each module to reach target output.",
        "module_basis": "1 Manufacturer (100% clock)",
        "shard_budget": TOTAL_SHARD_BUDGET,
        "shards_used": TOTAL_SHARD_BUDGET - shard_budget_remaining,
        "date": "2026-02-15",
        "source_plan": "factory-plan.json"
    },
    "modules": {},
    "summary": []
}

# Pass exact total shard budget per factory (compute_module compares against total_shards
# which is shards_per_building * new_count * copies)
for key in ["ferrium", "naphtheon", "forgeholm", "luxara", "cathera"]:
    budget = factory_total_shards[key]  # exact allocation from global selection
    module = compute_module(key, FACTORIES[key], shard_budget=budget)
    result["modules"][key] = module
    result["summary"].append({
        "factory": key,
        "theme": module["theme"],
        "hmf_per_module": module["hmf_per_min"],
        "buildings_per_module": module["total_buildings"],
        "shards_per_module": module["shards_per_module"],
        "copies_needed": module["copies_needed_ceil"],
        "total_buildings_all_copies": module["total_buildings"] * module["copies_needed_ceil"],
        "total_shards_all_copies": module["total_shards_all_copies"],
        "target_hmf": module["target_hmf"]
    })

# Write JSON
with open('/Users/deepak/AI/satisfy/factory-subunits.json', 'w') as f:
    json.dump(result, f, indent=2)

# Write text
text_output = format_modules_text(result)
with open('/Users/deepak/AI/satisfy/factory-modules.txt', 'w') as f:
    f.write(text_output)

print(text_output)
print("\n--- Files written: factory-subunits.json, factory-modules.txt ---")
