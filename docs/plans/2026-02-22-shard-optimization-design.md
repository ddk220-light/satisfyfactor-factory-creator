# Shard Optimization Fix for build_factory_crazy.py

## Bug

`build_factory_crazy.py` blindly inherits `shards_per_building` from the source module (`factory-subunits.json`). The source was optimized for a single-manufacturer scale. After re-scaling steps and dividing by N copies, shard assignments are wrong:
- Some steps get shards they don't need (buildings_exact is already integer)
- Other steps miss opportunities where shards could save buildings

## Fix

### 1. Reset inherited shards to 0

In `trace_module` (line 113) and `process_factory` (line 231), always set `shards_per_building: 0`.

### 2. Add global shard optimization pass

After all factories are processed, run `optimize_shards(factories, budget=200)`:

1. Collect candidates from all Stage 2 modules across all factories
   - For each step where `buildings_exact` has a fractional part and `buildings_ceil > 1`:
     - `new_count = buildings_ceil - 1`
     - `new_clock = (buildings_exact / new_count) * 100`
     - `shards_needed = shards_for_clock(new_clock)` (1 shard for <=150%, 2 for <=200%, 3 for <=250%)
     - `total_shards = shards_needed * new_count * module_copies`
2. Sort by building footprint (largest buildings first), then fewest total shards
3. Greedily allocate from 200-shard budget
4. Apply: reduce `buildings_ceil`, set `shards_per_building`, recalculate `buildings_per_copy` and `building_totals`

### 3. Constants needed

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
    if clock_pct <= 100.0: return 0
    elif clock_pct <= 150.0: return 1
    elif clock_pct <= 200.0: return 2
    elif clock_pct <= 250.0: return 3
    else: return None  # can't overclock that much
```

### 4. Update summary output

Print total shards used per factory and globally.
