#!/usr/bin/env python3
"""2-Stage Factory Crazy: decompose HMF production into Stage 1 (raw→intermediates)
and Stage 2 (intermediates→manufacturer inputs) with building-capped modules.

Constraints (priority order):
  1. Max 20 buildings per module copy
  2. Max 5% surplus (soft — prefer, but don't block on it)
  3. Maximize belt utilization (up to 780 items/min)
"""

import json
import math
from collections import deque

BELT_LIMIT = 780
MAX_BUILDINGS = 20
MAX_SURPLUS_PCT = 5.0
SHARD_BUDGET = 200

BUILDING_FOOTPRINT = {
    "Manufacturer": 440,
    "Blender": 304,
    "Refinery": 200,
    "Assembler": 150,
    "Constructor": 80,
    "Foundry": 72,
    "Smelter": 54,
}


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
    return None  # can't overclock that much


FLUIDS = {
    "Water", "Crude Oil", "Heavy Oil Residue", "Alumina Solution",
    "Sulfuric Acid", "Nitrogen Gas", "Nitric Acid",
}

STAGE1_PRODUCTS = {
    "Steel Ingot", "Iron Ingot", "Concrete", "Copper Ingot",
    "Caterium Ingot", "Plastic", "Rubber", "Aluminum Ingot",
}


def trace_module(target_item, target_rate, producers, all_steps, stop_at_stage1=False):
    """Trace backwards from target_item at target_rate through the production DAG.

    If stop_at_stage1=True, treat Stage 1 products (and byproducts of Stage 1
    steps) as external inputs rather than tracing through them.
    """

    def is_boundary(item):
        if not stop_at_stage1 or item == target_item:
            return False
        if item in STAGE1_PRODUCTS:
            return True
        if item in producers and producers[item]["item"] in STAGE1_PRODUCTS:
            return True  # byproduct of a Stage 1 step
        return False

    # DFS: find all items/steps in the module
    needed_items = set()

    def find_upstream(item):
        if item in needed_items or item not in producers:
            return
        if is_boundary(item):
            return
        needed_items.add(item)
        step = producers[item]
        for inp in step["inputs"]:
            find_upstream(inp)

    find_upstream(target_item)

    # BFS: propagate fractional demand backwards
    target_step = producers[target_item]
    fraction = {target_item: target_rate / target_step["outputs"][target_item]}

    visited = set()
    queue = deque([target_item])
    while queue:
        item = queue.popleft()
        if item in visited:
            continue
        visited.add(item)
        if item not in producers or is_boundary(item):
            continue

        step = producers[item]
        frac = fraction[item]

        for inp, inp_rate in step["inputs"].items():
            inp_needed = inp_rate * frac
            if inp in producers and not is_boundary(inp):
                inp_step = producers[inp]
                inp_full_output = inp_step["outputs"][inp]
                inp_frac = inp_needed / inp_full_output
                fraction[inp] = fraction.get(inp, 0) + inp_frac
                if inp not in visited:
                    queue.append(inp)

    # Build scaled steps and collect external inputs
    raw_solid = {}
    raw_fluid = {}
    scaled_steps = []
    seen_recipes = set()

    for item in needed_items:
        if item not in producers:
            continue
        step = producers[item]
        if step["recipe"] in seen_recipes:
            continue
        seen_recipes.add(step["recipe"])

        # Use the PRIMARY item's fraction (handles multi-output steps correctly)
        primary_frac = fraction.get(step["item"], 0)
        if primary_frac <= 0:
            continue

        bex = step["buildings_exact"] * primary_frac
        scaled_steps.append({
            "recipe": step["recipe"],
            "item": step["item"],
            "building": step["building"],
            "power_mw": step["power_mw"],
            "shards_per_building": 0,
            "inputs": {k: round(v * primary_frac, 4) for k, v in step["inputs"].items()},
            "outputs": {k: round(v * primary_frac, 4) for k, v in step["outputs"].items()},
            "buildings_exact": round(bex, 4),
        })

        # Collect external inputs (raw resources or Stage 1 boundaries)
        for inp, inp_rate in step["inputs"].items():
            if inp not in producers or is_boundary(inp):
                needed = inp_rate * primary_frac
                bucket = raw_fluid if inp in FLUIDS else raw_solid
                bucket[inp] = bucket.get(inp, 0) + needed

    return scaled_steps, raw_solid, raw_fluid


def optimize_copies(steps, product, demand, solid_input_total):
    """Find minimum N copies where buildings_per_copy <= MAX_BUILDINGS and belt <= 780.

    Picks the minimum N (= maximum belt utilization) that satisfies both hard
    constraints.  Surplus is reported but not used as a hard filter — it's a
    design goal, not a blocker.

    Returns (copies, buildings_per_copy, output_per_copy, surplus_pct).
    """
    product_step = next(s for s in steps if s["item"] == product)
    output_per_bldg = product_step["outputs"][product] / product_step["buildings_exact"]

    for n in range(1, MAX_BUILDINGS + 1):
        total_bldgs = sum(
            max(1, math.ceil(s["buildings_exact"] / n - 0.02))
            for s in steps
        )
        if total_bldgs > MAX_BUILDINGS:
            continue

        belt = solid_input_total / n
        if belt > BELT_LIMIT:
            continue

        prod_bc = max(1, math.ceil(product_step["buildings_exact"] / n - 0.02))
        out_per_copy = prod_bc * output_per_bldg
        demand_per_copy = demand / n
        surplus = (out_per_copy - demand_per_copy) / demand_per_copy * 100

        return (n, total_bldgs, out_per_copy, surplus)

    # Fallback: just satisfy buildings constraint, ignore belt
    for n in range(1, 100):
        total_bldgs = sum(
            max(1, math.ceil(s["buildings_exact"] / n - 0.02))
            for s in steps
        )
        if total_bldgs <= MAX_BUILDINGS:
            prod_bc = max(1, math.ceil(product_step["buildings_exact"] / n - 0.02))
            out_per_copy = prod_bc * output_per_bldg
            surplus = (out_per_copy - demand / n) / (demand / n) * 100
            return (n, total_bldgs, out_per_copy, surplus)

    return (MAX_BUILDINGS, MAX_BUILDINGS, demand / MAX_BUILDINGS, 0)


def process_factory(fid, mod):
    """Process one factory into 2-stage architecture."""
    steps = mod["steps"]
    mfr = next(s for s in steps if s["building"] == "Manufacturer")
    factory_copies = mod["copies_needed_ceil"]

    # Build producers map (excluding Manufacturer)
    producers = {}
    for s in steps:
        if s["building"] != "Manufacturer":
            for item in s["outputs"]:
                producers[item] = s

    non_mfr_steps = [s for s in steps if s["building"] != "Manufacturer"]

    # Classify manufacturer inputs into Stage 1 (direct) vs Stage 2 (modules)
    stage2_modules = []
    stage1_demand = {}  # product -> total demand across all factory copies

    for inp_item, inp_rate in mfr["inputs"].items():
        total_demand = inp_rate * factory_copies

        if inp_item in STAGE1_PRODUCTS:
            # Direct manufacturer input that IS a Stage 1 product
            stage1_demand[inp_item] = stage1_demand.get(inp_item, 0) + total_demand
        else:
            # Stage 2 module needed
            scaled_steps, inputs_solid, inputs_fluid = trace_module(
                inp_item, total_demand, producers, non_mfr_steps, stop_at_stage1=True,
            )

            # Accumulate Stage 1 demands from this module's inputs
            for s1_item, s1_rate in inputs_solid.items():
                if s1_item in STAGE1_PRODUCTS or s1_item in producers and producers[s1_item]["item"] in STAGE1_PRODUCTS:
                    stage1_demand[s1_item] = stage1_demand.get(s1_item, 0) + s1_rate
            for s1_item, s1_rate in inputs_fluid.items():
                if s1_item in STAGE1_PRODUCTS or s1_item in producers and producers[s1_item]["item"] in STAGE1_PRODUCTS:
                    stage1_demand[s1_item] = stage1_demand.get(s1_item, 0) + s1_rate

            # Optimize copies
            solid_input_total = sum(inputs_solid.values())
            n, bldgs_per_copy, output_per_copy, surplus_pct = optimize_copies(
                scaled_steps, inp_item, total_demand, solid_input_total,
            )

            # Build per-copy step data
            final_steps = []
            building_totals = {}
            for step in scaled_steps:
                bex = step["buildings_exact"] / n
                bc = max(1, math.ceil(bex - 0.02))
                final_steps.append({
                    "recipe": step["recipe"],
                    "item": step["item"],
                    "building": step["building"],
                    "power_mw": step["power_mw"],
                    "shards_per_building": 0,
                    "inputs": {k: round(v / n, 4) for k, v in step["inputs"].items()},
                    "outputs": {k: round(v / n, 4) for k, v in step["outputs"].items()},
                    "buildings_exact": round(bex, 4),
                    "buildings_ceil": bc,
                })
                building_totals[step["building"]] = (
                    building_totals.get(step["building"], 0) + bc
                )

            belt_load = round(sum(v / n for v in inputs_solid.values()), 1)

            stage2_modules.append({
                "name": f"{inp_item} Module",
                "product": inp_item,
                "demand": round(total_demand, 2),
                "copies": n,
                "buildings_per_copy": bldgs_per_copy,
                "output_per_copy": round(output_per_copy, 2),
                "total_output": round(output_per_copy * n, 2),
                "surplus_pct": round(surplus_pct, 1),
                "belt_load": belt_load,
                "inputs": {k: round(v / n, 4) for k, v in inputs_solid.items()},
                "steps": final_steps,
                "building_totals": building_totals,
            })

    # Build Stage 1
    stage1 = build_stage1(stage1_demand, producers, non_mfr_steps, mod)

    return {
        "factory": fid,
        "theme": mod["theme"],
        "hmf_recipe": mod["hmf_recipe"],
        "hmf_per_min": mod["hmf_per_min"],
        "target_hmf": mod["target_hmf"],
        "num_manufacturers": factory_copies,
        "manufacturer": {
            "recipe": mfr["recipe"],
            "building": mfr["building"],
            "inputs": {k: round(v, 4) for k, v in mfr["inputs"].items()},
            "output": {k: round(v, 4) for k, v in mfr["outputs"].items()},
            "power_mw": mfr["power_mw"],
        },
        "stage2_modules": stage2_modules,
        "stage1": stage1,
    }


def build_stage1(stage1_demand_external, producers, all_steps, mod):
    """Build Stage 1: aggregate demand, resolve inter-Stage1 deps, compute buildings.

    Stage 1 products may depend on other Stage 1 products (e.g., Concrete needs
    Rubber in Naphtheon). Resolve these dependencies iteratively.
    """
    factory_copies = mod["copies_needed_ceil"]

    # Trace each Stage 1 product's chain (stopping at other Stage 1 products)
    s1_chains = {}
    for product in STAGE1_PRODUCTS:
        if product not in producers:
            continue
        unit_output = producers[product]["outputs"][product]
        chain_steps, raw_s, raw_f = trace_module(
            product, unit_output, producers, all_steps, stop_at_stage1=True,
        )

        # Separate Stage 1 inputs from pure raw inputs (per unit of product output)
        s1_inputs = {}
        pure_raw = {}
        for k, v in {**raw_s, **raw_f}.items():
            per_unit = v / unit_output
            if k in STAGE1_PRODUCTS:
                s1_inputs[k] = per_unit
            else:
                pure_raw[k] = per_unit

        s1_chains[product] = {
            "steps": chain_steps,
            "s1_inputs": s1_inputs,
            "pure_raw_per_unit": pure_raw,
            "unit_output": unit_output,
        }

    # Resolve inter-Stage1 dependencies iteratively
    total_demand = dict(stage1_demand_external)
    for _ in range(10):
        internal = {}
        for product, demand in total_demand.items():
            if product not in s1_chains:
                continue
            for dep, rate_per_unit in s1_chains[product]["s1_inputs"].items():
                internal[dep] = internal.get(dep, 0) + demand * rate_per_unit
        changed = False
        for dep, need in internal.items():
            new_total = stage1_demand_external.get(dep, 0) + need
            if abs(new_total - total_demand.get(dep, 0)) > 0.01:
                total_demand[dep] = new_total
                changed = True
        if not changed:
            break

    # Build Stage 1 module entries
    modules = []
    total_buildings = 0

    for product in sorted(total_demand.keys()):
        demand = total_demand[product]
        if demand <= 0 or product not in s1_chains:
            continue

        chain = s1_chains[product]
        scale = demand / chain["unit_output"]

        step_details = []
        prod_buildings = 0
        for step in chain["steps"]:
            bex = step["buildings_exact"] * scale
            bc = max(1, math.ceil(bex - 0.02))
            step_details.append({
                "recipe": step["recipe"],
                "item": step["item"],
                "building": step["building"],
                "buildings_exact": round(bex, 2),
                "buildings_ceil": bc,
            })
            prod_buildings += bc

        raw_inputs = {}
        for k, v_per_unit in chain["pure_raw_per_unit"].items():
            raw_inputs[k] = round(v_per_unit * demand, 2)

        modules.append({
            "product": product,
            "demand": round(demand, 2),
            "steps": step_details,
            "raw_inputs": raw_inputs,
            "total_buildings": prod_buildings,
        })
        total_buildings += prod_buildings

    # Use factory's known raw_inputs for accurate raw resource totals
    raw_resources = {}
    for res_name, res_info in mod["raw_inputs"].items():
        raw_resources[res_name] = round(res_info["per_min"] * factory_copies, 2)

    return {
        "modules": modules,
        "total_buildings": total_buildings,
        "raw_resources": raw_resources,
    }


def validate(fid, result, mod):
    """Validate the 2-stage decomposition."""
    issues = []
    mfr = next(s for s in mod["steps"] if s["building"] == "Manufacturer")
    factory_copies = mod["copies_needed_ceil"]

    # Check Stage 2 modules exist for each non-Stage1 manufacturer input
    expected_s2 = [inp for inp in mfr["inputs"] if inp not in STAGE1_PRODUCTS]
    actual_s2 = [m["product"] for m in result["stage2_modules"]]
    if set(expected_s2) != set(actual_s2):
        issues.append(f"Stage 2 mismatch: expected {expected_s2}, got {actual_s2}")

    # Check building constraints
    for m in result["stage2_modules"]:
        if m["buildings_per_copy"] > MAX_BUILDINGS:
            issues.append(f"{m['name']}: {m['buildings_per_copy']} buildings > {MAX_BUILDINGS}")
        if m["surplus_pct"] > 15:  # surplus is soft; only flag extreme cases
            issues.append(f"{m['name']}: surplus {m['surplus_pct']:.1f}% very high")

    # Check Stage 1 has entries
    if not result["stage1"]["modules"]:
        issues.append("Stage 1 has no modules")

    return issues


def optimize_shards(factories, budget=SHARD_BUDGET):
    """Global shard optimization across all Stage 2 modules.

    For each step with fractional buildings, check if we can overclock
    fewer buildings to save one building per copy. Allocate shards greedily
    from a global budget, prioritizing larger buildings (more space saved).
    """
    candidates = []

    for fid, fac in factories.items():
        for mi, mm in enumerate(fac["stage2_modules"]):
            copies = mm["copies"]
            for si, step in enumerate(mm["steps"]):
                be = step["buildings_exact"]
                bc = step["buildings_ceil"]
                if bc <= 1:
                    continue  # can't save a building from a 1-building step

                frac = be - int(be)
                if frac < 0.001 or frac > 0.999:
                    continue  # already effectively integer

                new_count = bc - 1
                new_clock = (be / new_count) * 100
                if new_clock > 250:
                    continue

                shards_needed = shards_for_clock(new_clock)
                if shards_needed is None or shards_needed == 0:
                    continue

                total_shards = shards_needed * new_count * copies

                candidates.append({
                    "fid": fid,
                    "module_idx": mi,
                    "step_idx": si,
                    "building": step["building"],
                    "item": step["item"],
                    "old_count": bc,
                    "new_count": new_count,
                    "new_clock": round(new_clock, 1),
                    "shards_per_building": shards_needed,
                    "total_shards": total_shards,
                    "copies": copies,
                })

    # Sort: largest buildings first (most space saved), then fewest total shards
    candidates.sort(
        key=lambda c: (-BUILDING_FOOTPRINT.get(c["building"], 0), c["total_shards"])
    )

    # Greedily allocate from budget
    shards_used = 0
    applied = []
    for c in candidates:
        if shards_used + c["total_shards"] <= budget:
            shards_used += c["total_shards"]
            applied.append(c)

    # Apply optimizations
    for opt in applied:
        fac = factories[opt["fid"]]
        mm = fac["stage2_modules"][opt["module_idx"]]
        step = mm["steps"][opt["step_idx"]]
        step["buildings_ceil"] = opt["new_count"]
        step["shards_per_building"] = opt["shards_per_building"]

        # Recalculate module totals
        mm["buildings_per_copy"] = sum(s["buildings_ceil"] for s in mm["steps"])
        mm["building_totals"] = {}
        for s in mm["steps"]:
            mm["building_totals"][s["building"]] = (
                mm["building_totals"].get(s["building"], 0) + s["buildings_ceil"]
            )

    return applied, shards_used


def main():
    with open("factory-subunits.json") as f:
        data = json.load(f)

    factories = {}
    all_ok = True

    for fid, mod in data["modules"].items():
        result = process_factory(fid, mod)
        factories[fid] = result

        issues = validate(fid, result, mod)
        if issues:
            all_ok = False
            print(f"\n[{fid}] VALIDATION ISSUES:")
            for i in issues:
                print(f"  - {i}")

    output = {
        "meta": {
            "title": "HMF-95 Factory Crazy — 2-Stage Modules",
            "belt_limit": BELT_LIMIT,
            "max_buildings": MAX_BUILDINGS,
            "max_surplus_pct": MAX_SURPLUS_PCT,
            "description": "Stage 1: raw→intermediates, Stage 2: intermediates→mfr inputs (building-capped modules)",
            "source": "factory-subunits.json",
        },
        "factories": factories,
    }

    with open("factory-crazy.json", "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    print("\n" + "=" * 72)
    print("  HMF-95 Factory Crazy — 2-Stage Modules")
    print("=" * 72)

    grand_s2_bldgs = 0
    grand_s1_bldgs = 0

    for fid, fac in factories.items():
        print(f"\n  {fid.upper()} — {fac['theme']}  ({fac['hmf_per_min']} HMF/min × {fac['num_manufacturers']} mfrs)")

        # Stage 2
        fac_s2_bldgs = 0
        for m in fac["stage2_modules"]:
            cp = f" ×{m['copies']}" if m["copies"] > 1 else ""
            total_b = m["buildings_per_copy"] * m["copies"]
            fac_s2_bldgs += total_b
            pct = m["belt_load"] / BELT_LIMIT * 100
            print(
                f"    S2 {m['name']:<30} {m['copies']:>2} copies  "
                f"{m['buildings_per_copy']:>2} bldgs/copy  "
                f"belt:{pct:5.1f}%  surplus:{m['surplus_pct']:4.1f}%"
            )
        grand_s2_bldgs += fac_s2_bldgs

        # Stage 1
        s1 = fac["stage1"]
        for pm in s1["modules"]:
            print(f"    S1 {pm['product']:<30} {pm['total_buildings']:>3} bldgs  demand:{pm['demand']:.0f}/min")
        grand_s1_bldgs += s1["total_buildings"]

        total = fac_s2_bldgs + s1["total_buildings"]
        print(f"    {'─' * 55}")
        print(f"    Total: S2={fac_s2_bldgs}  S1={s1['total_buildings']}  Grand={total}")

    print(f"\n{'=' * 72}")
    print(f"  Grand Total: S2={grand_s2_bldgs}  S1={grand_s1_bldgs}  All={grand_s2_bldgs + grand_s1_bldgs}")
    total_mm = sum(len(f["stage2_modules"]) for f in factories.values())
    print(f"  {len(factories)} factories, {total_mm} Stage 2 modules")
    if all_ok:
        print("  All validation checks passed.")
    print(f"\n  Written to factory-crazy.json")


if __name__ == "__main__":
    main()
