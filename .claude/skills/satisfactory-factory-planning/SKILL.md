---
name: satisfactory-factory-planning
description: Use when planning Satisfactory production chains, decomposing complex items into raw resources, comparing recipe alternatives, or calculating factory throughput requirements.
---

# Satisfactory Factory Planning

Algorithm-first reference for production chain analysis. **REQUIRED:** Use `satisfactory-db` skill for DB schema and connection. This skill teaches HOW to plan factories.

**Rule:** Never rely on memorized recipe data. Always query `satisfactory.db`.

## Core Formulas

| Formula | Expression |
|---------|------------|
| Production rate | `quantity / duration * 60 = items_per_min` |
| Fluid conversion | DB stores mL; `÷ 1000` for m³/min |
| Power (clocked) | `base_power × (clock_pct / 100)^1.321929` |
| Buildings needed | `desired_rate / recipe_output_per_min` |
| Last building clock | `fractional_part × 100%` |

### Building Power (MW)

| Smelter | Constructor | Foundry | Assembler | Refinery | Manufacturer | Blender |
|---------|-------------|---------|-----------|----------|--------------|---------|
| 4 | 4 | 16 | 15 | 30 | 55 | 75 |

Particle Accelerator: variable per recipe (check `power_used_recipes` JSON field).

### Throughput Limits

- **Belts** (Mk.1→6): 60 / 120 / 270 / 480 / 780 / 1200 items/min
- **Pipes**: 600 m³/min (600,000 mL/min in DB units)

## Production Chain Decomposition

### Algorithm

Given a target item and desired output rate (items/min):

1. **Find recipe** for target item (default or chosen alternate)
2. **Calculate multiplier**: `desired_rate / recipe_output_per_min`
3. **For each ingredient**: `needed_rate = ingredient_per_min × multiplier`
4. **Recurse** on each ingredient until hitting a raw resource
5. **Aggregate** — same item at multiple tree nodes → sum all demands
6. **Calculate buildings**: `ceil(multiplier)` buildings; last at `(frac(multiplier) / 1) × 100%` clock. If frac = 0, all run at 100%
7. **Track by-products**: `by_product_per_min × multiplier`
8. **Track power**: per building `base_power × (clock% / 100)^1.321929`; sum across all buildings

### Step 1: Find Default Recipe

```sql
SELECT r.id, r.name, r.duration, rp.quantity,
       rp.quantity * 1.0 / r.duration * 60 AS output_per_min,
       b.name AS building, b.power_used
FROM recipes r
JOIN recipe_products rp ON rp.recipe_id = r.id
JOIN items i ON i.id = rp.item_id
JOIN recipe_buildings rb ON rb.recipe_id = r.id
JOIN buildings b ON b.id = rb.building_id
WHERE i.name = :item_name AND r.name NOT LIKE 'Alternate%'
```

If multiple rows, prefer the recipe whose name matches the item name. Some items have packaging/unpackaging variants — filter by context.

### Step 2: Get Ingredients

```sql
SELECT i.name, i.id, ri.quantity,
       ri.quantity * 1.0 / r.duration * 60 AS per_min
FROM recipe_ingredients ri
JOIN items i ON i.id = ri.item_id
JOIN recipes r ON r.id = ri.recipe_id
WHERE r.id = :recipe_id
```

### Step 3: Check if Raw Resource (Recursion Terminator)

An item is a raw resource if no non-extraction building produces it:

```sql
SELECT COUNT(*) = 0 AS is_raw
FROM recipe_products rp
JOIN recipe_buildings rb ON rb.recipe_id = rp.recipe_id
JOIN buildings b ON b.id = rb.building_id
WHERE rp.item_id = :item_id
  AND b.name NOT LIKE '%Miner%'
  AND b.name NOT LIKE '%Extractor%'
  AND b.name NOT LIKE '%Well%'
```

Raw resources (extraction only): Iron Ore, Copper Ore, Limestone, Coal, Caterium Ore, Raw Quartz, Sulfur, Bauxite, Uranium, SAM, Water, Crude Oil, Nitrogen Gas.

### Step 4: Aggregate Demand

The same intermediate item often appears in multiple branches. After full tree decomposition, **group by item and sum rates**:

```
Total Copper Ingot/min = (for Wire branch) + (for Copper Sheet branch in Circuit Board)
                       + (for Copper Sheet branch in AI Limiter) + ...
```

Then calculate buildings from aggregated totals, not per-branch.

### Step 5: Calculate Total Raw Resources

After aggregation, the leaf nodes show total raw resource demand. For extraction planning:

```sql
-- Extraction building capacity
SELECT name, extraction_rate_impure, extraction_rate_normal, extraction_rate_pure
FROM buildings WHERE name LIKE '%Miner%' OR name LIKE '%Extractor%'
```

| Miner | Impure | Normal | Pure |
|-------|--------|--------|------|
| Mk.1 | 30 | 60 | 120 |
| Mk.2 | 60 | 120 | 240 |
| Mk.3 | 120 | 240 | 480 |

Oil Extractor: 60/120/240 m³/min (impure/normal/pure). Water Extractor: 120 m³/min (fixed).

## Alternate Recipe Comparison

### Find All Recipes for an Item

```sql
SELECT r.id, r.name, r.duration,
       rp.quantity * 1.0 / r.duration * 60 AS output_per_min,
       b.name AS building, b.power_used,
       GROUP_CONCAT(i_in.name || ' @' ||
         ROUND(ri.quantity * 1.0 / r.duration * 60, 2) || '/min', ', ') AS inputs
FROM recipes r
JOIN recipe_products rp ON rp.recipe_id = r.id
JOIN items i_out ON i_out.id = rp.item_id
JOIN recipe_buildings rb ON rb.recipe_id = r.id
JOIN buildings b ON b.id = rb.building_id
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN items i_in ON i_in.id = ri.item_id
WHERE i_out.name = :item_name
GROUP BY r.id
ORDER BY output_per_min DESC
```

Alternate recipe names start with `Alternate:` in the DB.

### Comparison Dimensions

When evaluating recipe alternatives, compare across these dimensions:

1. **Raw resource footprint** — Trace each recipe's full chain to raw resources. Which ores/fluids does it ultimately consume?
2. **Complexity** — Fewer intermediate steps = fewer buildings = simpler logistics
3. **By-products** — No by-products = simpler. Useful by-products = bonus
4. **Total chain power** — Sum power across the FULL production chain, not just the final building
5. **Total building count** — Across the entire chain
6. **Tier/milestone requirements** — Some buildings or recipes need later-game unlocks

### Example: Supercomputer — 3 Recipes Compared

| Recipe | Output/min | Key Inputs | Trade-off |
|--------|-----------|------------|-----------|
| Supercomputer | 1.875 | Computer, AI Limiter, HSC, Plastic | Complex chain, oil-heavy, no iron needed |
| Alternate: Super-State Computer | 2.4 | Computer, Battery, EM Control Rod, Wire | Needs sulfur (Battery chain), higher throughput |
| Alternate: OC Supercomputer | 3.0 | Cooling System, Radio Control Unit | Highest rate, but very high-tier inputs |

To choose: run full decomposition on each, compare total raw resource demands and building counts.

## By-Product Handling

Every recipe has **at most 2 outputs**. The secondary output is a by-product.

**Critical:** If a by-product output backs up (storage full, no consumer, no sink), the building **STOPS producing entirely**. Always plan by-product routing.

### Find By-Product Recipes

```sql
SELECT r.name, i.name AS product,
       rp.quantity * 1.0 / r.duration * 60 AS per_min
FROM recipes r
JOIN recipe_products rp ON rp.recipe_id = r.id
JOIN items i ON i.id = rp.item_id
WHERE r.id IN (
    SELECT recipe_id FROM recipe_products GROUP BY recipe_id HAVING COUNT(*) > 1
)
ORDER BY r.name, rp.quantity DESC
```

### Handling Strategies

1. **Sink** — Route to AWESOME Sink (simplest, wastes value)
2. **Chain** — Feed into another recipe that consumes the by-product
3. **Alternate recipe** — Choose a variant without by-products
4. **Balance** — Match by-product output rate to a consumer's input rate

**Common chain:** Plastic (Refinery) → Heavy Oil Residue (10 m³/min by-product) → Petroleum Coke (Refinery) or Fuel (Refinery)

When planning a chain with by-products, compute the by-product rate alongside the primary product, then plan its disposal as part of the factory.

## Corrections to Claude's Training Data

| Topic | Claude often says | Actual (verified from DB) |
|-------|------------------|--------------------------|
| Power exponent | 1.6 | **1.321929** (updated in game Update 7) |
| Supercomputer chain | Includes Screws / Iron Ore | **No iron at all** — needs Copper Ore, Caterium Ore, Crude Oil |
| Fluid units in DB | m³ | **mL** (divide by 1000 for m³) |
| Mk.6 conveyor belt | "Uncertain if exists" | **Exists: 1200 items/min** |
| Pipe throughput | Often omitted | **600 m³/min max** |
| Max recipe outputs | "Varies" | **Always ≤ 2** (primary + optional by-product) |
| Recipes without buildings | "A few" | **542** hand-craft / build-gun recipes (no machine) |
| Computer recipe | Includes Screws | **No Screws** — uses Circuit Board, Cable, Plastic (Manufacturer) |

## Worked Example: Supercomputer (Standard Recipes)

```
Supercomputer (Manufacturer, 32s → 1.875/min)
├── Computer ×4 (7.5/min) — Manufacturer, 24s → 2.5/min
│   ├── Circuit Board ×4 (10/min) — Assembler, 8s → 7.5/min
│   │   ├── Copper Sheet ×2 (15/min) — Constructor, 6s → 10/min
│   │   │   └── Copper Ingot ×2 (20/min) — Smelter → [Copper Ore]
│   │   └── Plastic ×4 (30/min) — Refinery, 6s → 20/min
│   │       └── [Crude Oil 30 m³/min] + BY-PRODUCT: Heavy Oil Residue 10 m³/min
│   ├── Cable ×8 (20/min) — Constructor, 2s → 30/min
│   │   └── Wire ×2 (60/min) — Constructor, 4s → 30/min
│   │       └── Copper Ingot ×1 (15/min) — Smelter → [Copper Ore]
│   └── Plastic ×16 (40/min) → [Crude Oil]
│
├── AI Limiter ×2 (3.75/min) — Assembler, 12s → 5/min
│   ├── Copper Sheet ×5 (25/min) → Copper Ingot → [Copper Ore]
│   └── Quickwire ×20 (100/min) — Constructor, 5s → 60/min
│       └── Caterium Ingot ×1 (12/min) — Smelter → [Caterium Ore]
│
├── High-Speed Connector ×3 (5.625/min) — Manufacturer, 16s → 3.75/min
│   ├── Quickwire ×56 (210/min) → Caterium Ingot → [Caterium Ore]
│   ├── Cable ×10 (37.5/min) → Wire → Copper Ingot → [Copper Ore]
│   └── Circuit Board ×1 (3.75/min) → Copper Sheet + Plastic
│
└── Plastic ×28 (52.5/min) → [Crude Oil]

Raw resources needed: Copper Ore, Caterium Ore, Crude Oil
NOT needed: Iron Ore (common misconception)
```

The rates shown (e.g., "7.5/min") are what the Supercomputer recipe DEMANDS from each ingredient at 1.875 Supercomputers/min. To plan the factory, aggregate all demands for each item across branches, then divide by recipe output rates to get building counts.
