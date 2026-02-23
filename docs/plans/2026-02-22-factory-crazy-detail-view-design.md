# Factory Crazy Module Detail View Redesign

## Goal

Replace the flow diagram in each Stage 2 module card with a color-banded table showing inputs, intermediate production steps, and output with per-module and total rates plus recipe/building details.

## Current State

Each Stage 2 module card shows:
- Header with name, demand, surplus badge, copies badge, buildings/copy
- Belt load bar
- Input pills (colored dots with rates)
- Building totals list
- Flow diagram (DAG with SVG connectors)

## New Design

### Module Header (simplified)

Only show: module name, copies count, per-copy output rate.

```
Modular Frame Module          x3 copies  ->  18.0/min each
```

### Module Body: Color-Banded Table

Single table per module with three row types distinguished by background color:

| Row Type | Background | Data |
|----------|-----------|------|
| Input (green tint) | `#0d2818` | Item, per-module rate, total rate. Recipe/Building = "---" |
| Intermediate (neutral) | `#1a1a2e` | Item, per-module rate, total rate, recipe, building x count, rate/bldg |
| Output (blue tint) | `#0d1b2a` | Item, per-module rate, total rate, recipe, building x count, rate/bldg |

### Table Columns

- **Item** -- item name
- **/mod** -- items/min for one copy (from `step.outputs[item]` or `mm.inputs[item]`)
- **Total** -- per-mod rate x copies
- **Recipe** -- recipe name from `step.recipe`
- **Building** -- `building x buildings_ceil` with shard indicator if overclocked
- **Rate/bldg** -- base rate per building (outputs / buildings_exact)

### Row Ordering

1. Input rows from `mm.inputs` -- alphabetical
2. Intermediate steps from `mm.steps` (excluding final output) -- dependency order from data
3. Output row -- the step where `step.item === mm.product` -- always last

### Removed Elements

- Flow diagram (`.flow-diagram`, SVG connectors, `renderFlowDiagram`)
- Belt load bar
- Surplus badge
- Raw pill display
- Building totals list
- Synthetic module construction for flow rendering

## Data Source

All data comes from `factory-crazy.json`:
- `mm.inputs` for input rows
- `mm.steps[]` for intermediate and output rows
- `mm.copies` for total calculation
- `mm.product` to identify the output step
- `step.recipe`, `step.building`, `step.buildings_ceil`, `step.outputs`, `step.shards_per_building`
