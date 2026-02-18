#!/usr/bin/env python3
"""Decompose factory modules into self-contained mini-modules per Manufacturer input.

Each mini-module produces exactly one input to the final Manufacturer,
contains all upstream buildings from raw ore, and is constrained by
a single Mk.5 input belt (780 items/min total solid inputs).
"""

import json
import math
from collections import deque

BELT_LIMIT = 780  # items/min on a single Mk.5 belt
FLUIDS = {
    "Water", "Crude Oil", "Heavy Oil Residue", "Alumina Solution",
    "Sulfuric Acid", "Nitrogen Gas", "Nitric Acid"
}


def trace_module(target_item, target_rate, producers, all_steps):
    """Trace backwards from a target item/rate through the DAG.

    Strategy: use the ORIGINAL full-factory rates and scale proportionally.
    The original factory-subunits.json already has correct rates accounting
    for byproduct loops. We just need to figure out what fraction of each
    step belongs to this mini-module.

    For the target product, we know the Manufacturer needs X/min and the
    full step produces Y/min, so our fraction is X/Y. We propagate this
    fraction backwards through the DAG.
    """
    # Build map of which step produces each item (primary output)
    step_for = {}
    for s in all_steps:
        step_for[s["item"]] = s

    # Also map any secondary outputs
    for s in all_steps:
        for out_item in s["outputs"]:
            if out_item not in step_for:
                step_for[out_item] = s

    # Find all steps upstream of target via DFS (using primary item links only)
    needed_items = set()
    def find_upstream(item):
        if item in needed_items or item not in producers:
            return
        needed_items.add(item)
        step = producers[item]
        for inp in step["inputs"]:
            find_upstream(inp)
    find_upstream(target_item)

    # For each needed item, calculate what fraction of its full-factory
    # production this module requires. Start from target and propagate back.
    fraction = {}  # item -> fraction of full step output needed

    # Target: we need target_rate of target_item, full step produces outputs[target_item]
    target_step = producers[target_item]
    fraction[target_item] = target_rate / target_step["outputs"][target_item]

    # BFS backwards, propagating fractions
    visited = set()
    queue = deque([target_item])
    while queue:
        item = queue.popleft()
        if item in visited:
            continue
        visited.add(item)

        if item not in producers:
            continue

        step = producers[item]
        frac = fraction[item]

        for inp, inp_rate in step["inputs"].items():
            # How much of inp does this step need at our fraction?
            inp_needed = inp_rate * frac

            if inp in producers:
                inp_step = producers[inp]
                inp_full_output = inp_step["outputs"][inp]
                inp_frac = inp_needed / inp_full_output
                # Accumulate fractions (multiple steps may need same input)
                fraction[inp] = fraction.get(inp, 0) + inp_frac
                if inp not in visited:
                    queue.append(inp)

    # Build scaled steps and raw inputs
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

        frac = fraction.get(item, 0)
        if frac <= 0:
            continue

        bex = step["buildings_exact"] * frac
        scaled_steps.append({
            "recipe": step["recipe"],
            "item": step["item"],
            "building": step["building"],
            "power_mw": step["power_mw"],
            "shards_per_building": step["shards_per_building"],
            "inputs": {k: round(v * frac, 4) for k, v in step["inputs"].items()},
            "outputs": {k: round(v * frac, 4) for k, v in step["outputs"].items()},
            "buildings_exact": round(bex, 4),
            "buildings_ceil": max(1, math.ceil(bex - 0.001)),
        })

        # Raw inputs = step inputs that have no producer
        for inp, inp_rate in step["inputs"].items():
            if inp not in producers:
                needed = inp_rate * frac
                bucket = raw_fluid if inp in FLUIDS else raw_solid
                bucket[inp] = bucket.get(inp, 0) + needed

    return scaled_steps, raw_solid, raw_fluid


def build_mini_module(name, product, product_rate, scaled_steps, raw_solid, raw_fluid):
    """Build a mini-module dict with belt constraint applied."""
    solid_total = sum(raw_solid.values())
    copies = math.ceil(solid_total / BELT_LIMIT) if solid_total > BELT_LIMIT else 1
    d = copies  # divisor

    final_steps = []
    building_totals = {}
    for step in scaled_steps:
        bex = step["buildings_exact"] / d
        bc = max(1, math.ceil(bex - 0.001))
        final_steps.append({
            "recipe": step["recipe"],
            "item": step["item"],
            "building": step["building"],
            "power_mw": step["power_mw"],
            "shards_per_building": step["shards_per_building"],
            "inputs": {k: round(v / d, 4) for k, v in step["inputs"].items()},
            "outputs": {k: round(v / d, 4) for k, v in step["outputs"].items()},
            "buildings_exact": round(bex, 4),
            "buildings_ceil": bc,
        })
        building_totals[step["building"]] = building_totals.get(step["building"], 0) + bc

    belt_per_copy = round(solid_total / d, 2)
    return {
        "name": name,
        "product": product,
        "product_rate": round(product_rate, 4),
        "product_rate_per_copy": round(product_rate / d, 4),
        "raw_inputs_solid": {k: round(v / d, 4) for k, v in raw_solid.items()},
        "raw_inputs_fluid": {k: round(v / d, 4) for k, v in raw_fluid.items()},
        "belt_items_per_min": belt_per_copy,
        "belt_utilization": round(belt_per_copy / BELT_LIMIT, 4),
        "copies_needed": copies,
        "steps": final_steps,
        "building_totals": building_totals,
        "total_buildings": sum(building_totals.values()),
    }


def process_factory(fid, mod):
    """Process one factory into mini-modules."""
    steps = mod["steps"]
    mfr = next(s for s in steps if s["building"] == "Manufacturer")

    # Producer map excluding the Manufacturer
    producers = {}
    for s in steps:
        if s["building"] != "Manufacturer":
            for item in s["outputs"]:
                producers[item] = s

    non_mfr_steps = [s for s in steps if s["building"] != "Manufacturer"]

    # Phase 1: trace each module to get gross raw inputs
    raw_modules = []
    for inp_item, inp_rate in mfr["inputs"].items():
        scaled, raw_s, raw_f = trace_module(inp_item, inp_rate, producers, non_mfr_steps)
        raw_modules.append((inp_item, inp_rate, scaled, raw_s, raw_f))

    # Phase 2: correct raw inputs using factory's known net totals.
    # The trace over-counts when byproduct recycling reduces net demand
    # (e.g., Water recycled in aluminum chain). Fix by distributing
    # the factory's actual net raw inputs proportionally across modules.
    factory_raw = {}
    for res_name, res_info in mod["raw_inputs"].items():
        factory_raw[res_name] = res_info["per_min"]

    # For each raw resource, sum gross across all modules, then scale each
    # module's share to match the factory total.
    # Also handle "partially raw" items (produced as byproduct AND imported,
    # e.g., Silica/Water in Luxara). These don't appear in module raw inputs
    # because the tracer sees them as having producers. We need to distribute
    # the external import across modules that use the chain containing them.
    gross_totals = {}
    for _, _, _, raw_s, raw_f in raw_modules:
        for r, v in raw_s.items():
            gross_totals[r] = gross_totals.get(r, 0) + v
        for r, v in raw_f.items():
            gross_totals[r] = gross_totals.get(r, 0) + v

    # Find factory raw resources missing from any module's raw inputs
    # (partially raw / byproduct-supplemented resources)
    missing_raws = {}
    for res_name, amount in factory_raw.items():
        if res_name not in gross_totals or gross_totals[res_name] == 0:
            missing_raws[res_name] = amount

    # For missing raws, distribute proportionally to modules that use
    # steps consuming that resource
    module_usage = {}  # res -> [(module_idx, consumption_rate)]
    for i, (_, _, scaled, _, _) in enumerate(raw_modules):
        for step in scaled:
            for inp, rate in step["inputs"].items():
                if inp in missing_raws:
                    if inp not in module_usage:
                        module_usage[inp] = []
                    module_usage[inp].append((i, rate))

    mini_modules = []
    for idx, (inp_item, inp_rate, scaled, raw_s, raw_f) in enumerate(raw_modules):
        # Correct solid raw inputs
        corrected_s = {}
        for r, v in raw_s.items():
            if r in factory_raw and r in gross_totals and gross_totals[r] > 0:
                corrected_s[r] = v / gross_totals[r] * factory_raw[r]
            else:
                corrected_s[r] = v
        # Correct fluid raw inputs
        corrected_f = {}
        for r, v in raw_f.items():
            if r in factory_raw and r in gross_totals and gross_totals[r] > 0:
                corrected_f[r] = v / gross_totals[r] * factory_raw[r]
            else:
                corrected_f[r] = v

        # Add missing raw resources proportionally
        for res, users in module_usage.items():
            total_consumption = sum(rate for _, rate in users)
            for mod_idx, rate in users:
                if mod_idx == idx and total_consumption > 0:
                    share = rate / total_consumption * missing_raws[res]
                    bucket = corrected_f if res in FLUIDS else corrected_s
                    bucket[res] = bucket.get(res, 0) + share

        mm = build_mini_module(f"{inp_item} Module", inp_item, inp_rate, scaled, corrected_s, corrected_f)
        mini_modules.append(mm)

    return {
        "factory": fid,
        "theme": mod["theme"],
        "hmf_recipe": mod["hmf_recipe"],
        "hmf_per_min": mod["hmf_per_min"],
        "target_hmf": mod["target_hmf"],
        "factory_copies": mod["copies_needed_ceil"],
        "manufacturer": {
            "recipe": mfr["recipe"],
            "building": mfr["building"],
            "inputs": {k: round(v, 4) for k, v in mfr["inputs"].items()},
            "output": {k: round(v, 4) for k, v in mfr["outputs"].items()},
            "power_mw": mfr["power_mw"],
        },
        "mini_modules": mini_modules,
    }


def validate(fid, result, mod):
    """Validate decomposition against original factory data."""
    issues = []
    mfr = next(s for s in mod["steps"] if s["building"] == "Manufacturer")

    if len(result["mini_modules"]) != len(mfr["inputs"]):
        issues.append(f"Expected {len(mfr['inputs'])} modules, got {len(result['mini_modules'])}")

    for mm in result["mini_modules"]:
        if mm["belt_utilization"] > 1.0 and mm["copies_needed"] <= 1:
            issues.append(f"{mm['name']}: belt {mm['belt_utilization']:.0%} but copies=1")
        if mm["total_buildings"] == 0:
            issues.append(f"{mm['name']}: 0 buildings")

    # Check raw resource conservation
    for res_name, res_info in mod["raw_inputs"].items():
        expected = res_info["per_min"]
        actual = 0
        for mm in result["mini_modules"]:
            actual += mm["raw_inputs_solid"].get(res_name, 0) * mm["copies_needed"]
            actual += mm["raw_inputs_fluid"].get(res_name, 0) * mm["copies_needed"]
        diff = abs(actual - expected) / expected * 100 if expected > 0 else 0
        if diff > 2.0:
            issues.append(f"{res_name}: modules sum={actual:.2f} vs factory={expected:.2f} ({diff:.1f}% off)")

    return issues


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
            "title": "HMF-95 Factory Crazy Modules",
            "belt_limit": BELT_LIMIT,
            "description": "Self-contained mini-modules per Manufacturer input, belt-constrained to Mk.5 (780/min)",
            "source": "factory-subunits.json",
        },
        "factories": factories,
    }

    with open("factory-crazy.json", "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    print("\n" + "=" * 65)
    print("  HMF-95 Factory Crazy Modules")
    print("=" * 65)
    for fid, fac in factories.items():
        print(f"\n  {fid.upper()} — {fac['theme']}  ({fac['hmf_per_min']} HMF/min x{fac['factory_copies']})")
        for mm in fac["mini_modules"]:
            pct = mm["belt_utilization"] * 100
            cp = f" x{mm['copies_needed']}" if mm["copies_needed"] > 1 else ""
            print(f"    {mm['name']:<35} belt:{pct:5.1f}%  bldgs:{mm['total_buildings']:>2}{cp}")

    print(f"\n{'=' * 65}")
    total_mm = sum(len(f["mini_modules"]) for f in factories.values())
    print(f"  {len(factories)} factories, {total_mm} mini-modules")
    if all_ok:
        print("  All validation checks passed.")
    print(f"\n  Written to factory-crazy.json")


if __name__ == "__main__":
    main()
