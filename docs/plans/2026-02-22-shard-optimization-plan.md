# Shard Optimization Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the shard inheritance bug in `build_factory_crazy.py` and add proper global shard optimization that identifies where power shards can reduce building counts in Stage 2 modules.

**Architecture:** Three changes to `build_factory_crazy.py`: (1) add constants and helper function, (2) reset inherited shards to 0 in two places, (3) add `optimize_shards()` function called from `main()` after all factories are processed. Then regenerate `factory-crazy.json`.

**Tech Stack:** Python 3, json, math

---

### Task 1: Add shard constants and helper function

**Files:**
- Modify: `build_factory_crazy.py:16-17` (after existing constants)

**Step 1: Add constants and helper after line 17 (`MAX_SURPLUS_PCT = 5.0`)**

Insert after line 17:

```python
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
```

**Step 2: Commit**

```bash
git add build_factory_crazy.py
git commit -m "feat: add shard constants and helper to build_factory_crazy.py"
```

---

### Task 2: Reset inherited shards to 0

**Files:**
- Modify: `build_factory_crazy.py` — two locations

**Step 1: In `trace_module`, change the `shards_per_building` in the scaled step dict**

Find this line inside `trace_module` (currently line 113):
```python
            "shards_per_building": step["shards_per_building"],
```

Replace with:
```python
            "shards_per_building": 0,
```

**Step 2: Verify the same field in `process_factory` per-copy step construction**

Find this line inside `process_factory` (currently line 231):
```python
                    "shards_per_building": step["shards_per_building"],
```

Replace with:
```python
                    "shards_per_building": 0,
```

**Step 3: Commit**

```bash
git add build_factory_crazy.py
git commit -m "fix: reset inherited shard assignments to 0 in build_factory_crazy"
```

---

### Task 3: Add optimize_shards function

**Files:**
- Modify: `build_factory_crazy.py` — add function before `main()`

**Step 1: Add the `optimize_shards` function**

Insert before the `def main():` function:

```python
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
```

**Step 2: Commit**

```bash
git add build_factory_crazy.py
git commit -m "feat: add global shard optimization for Stage 2 modules"
```

---

### Task 4: Call optimize_shards from main and update summary

**Files:**
- Modify: `build_factory_crazy.py` — in `main()` function

**Step 1: Call optimize_shards after building all factories**

In `main()`, find these lines (after the factory processing loop, before writing JSON):

```python
    output = {
        "meta": {
```

Insert before them:

```python
    # Global shard optimization
    applied_opts, total_shards = optimize_shards(factories)
    if applied_opts:
        print(f"\nShard optimization: {len(applied_opts)} steps optimized, {total_shards}/{SHARD_BUDGET} shards used")
        for opt in applied_opts:
            print(f"  {opt['fid']}: {opt['item']} — {opt['building']} {opt['old_count']}→{opt['new_count']} @ {opt['new_clock']}% ({opt['shards_per_building']} shard × {opt['new_count']} bldgs × {opt['copies']} copies = {opt['total_shards']} shards)")

```

**Step 2: Add shard info to the meta block in output**

Find:
```python
            "source": "factory-subunits.json",
```

Change to:
```python
            "source": "factory-subunits.json",
            "shard_budget": SHARD_BUDGET,
            "shards_used": total_shards,
```

**Step 3: Commit**

```bash
git add build_factory_crazy.py
git commit -m "feat: wire up shard optimization in main() with summary output"
```

---

### Task 5: Regenerate factory-crazy.json and verify

**Files:**
- Run: `build_factory_crazy.py`
- Verify: `factory-crazy.json`

**Step 1: Run the build script**

```bash
cd /Users/deepak/AI/satisfy && python build_factory_crazy.py
```

Expected: Script completes with shard optimization summary showing which steps were optimized.

**Step 2: Verify forgeholm Modular Frame module no longer has spurious shards**

Search `factory-crazy.json` for the forgeholm Modular Frame Module. Verify:
- `Reinforced Iron Plate` step: `shards_per_building` should be `0` (buildings_exact ~3.0, no fractional part)
- `Modular Frame` step: check if shard optimization correctly identified this as a candidate or not based on the new per-copy `buildings_exact`

**Step 3: Verify no regression — all factories still have valid Stage 2 modules**

Check that the script reports "All validation checks passed."

**Step 4: Commit**

```bash
git add build_factory_crazy.py factory-crazy.json
git commit -m "fix: regenerate factory-crazy.json with correct shard optimization"
```
