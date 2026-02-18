# Factory Crazy: Self-Contained Mini-Module Decomposition

**Date:** 2026-02-17
**Status:** Design

## Goal

Decompose each factory's production chain into self-contained mini-modules, one per Manufacturer input. Each mini-module produces exactly one product that feeds the final Manufacturer, contains all upstream buildings from raw ore, and is constrained by a single Mk.5 input belt (780 items/min total across all raw inputs).

## Definitions

- **Mini-module**: A self-contained production unit that takes raw resources on a single mixed belt and outputs one intermediate product for the Manufacturer.
- **Belt constraint**: The sum of all raw resource inputs to a mini-module must not exceed 780 items/min. If it does, the module is stamp-copied.
- **Manufacturer**: Sits outside all mini-modules. Receives outputs from each mini-module.

## Data Flow

```
factory-subunits.json  -->  build_factory_crazy.py  -->  factory-crazy.json  -->  factory-map.html (new tab)
```

## Algorithm: build_factory_crazy.py

For each factory in `factory-subunits.json`:

1. Identify the Manufacturer step (last step, produces HMF).
2. For each input to the Manufacturer (e.g., Concrete, Modular Frame, Steel Pipe, EIB):
   a. Trace backwards through the DAG to collect all upstream steps needed to produce that input.
   b. Since modules are self-contained, each mini-module gets its own copy of shared upstream steps (e.g., Iron Ingot smelting appears in multiple modules independently).
   c. Scale each upstream step's rates proportionally to this mini-module's demand (not the full factory demand).
3. For each mini-module, sum raw resource input rates. If sum > 780, calculate copies_needed = ceil(sum / 780) and divide rates by copies_needed.
4. Recalculate building counts per mini-module based on scaled rates.
5. Output structured JSON.

### Handling Shared Intermediates

When Iron Ingot feeds both Steel Pipe (460/min) and Iron Plate (25/min), those are in different mini-modules. Each module independently includes its own Iron Ingot smelting at the rate it needs. No sharing between modules.

### Rate Scaling

Given the Manufacturer needs X/min of product P, and the full factory produces Y/min of P, the mini-module's scale factor is X/Y. All upstream step rates for that module are multiplied by this factor.

Actually simpler: just trace backwards from the Manufacturer's specific input demand. The steps in factory-subunits.json already have rates for 1 Manufacturer at 100%. We partition those rates by tracing which portion of each step feeds which Manufacturer input.

## Output: factory-crazy.json

```json
{
  "meta": {
    "title": "HMF-95 Factory Crazy Modules",
    "belt_limit": 780,
    "description": "Self-contained mini-modules per Manufacturer input, belt-constrained to 780/min"
  },
  "factories": {
    "ferrium": {
      "factory": "ferrium",
      "theme": "Pure Iron",
      "hmf_recipe": "Alternate: Heavy Encased Frame",
      "hmf_per_min": 2.8125,
      "target_hmf": 18.94,
      "factory_copies": 7,
      "manufacturer": {
        "recipe": "Alternate: Heavy Encased Frame",
        "building": "Manufacturer",
        "inputs": {
          "Concrete": 20.625,
          "Modular Frame": 7.5,
          "Steel Pipe": 33.75,
          "Encased Industrial Beam": 9.375
        },
        "output": { "Heavy Modular Frame": 2.8125 }
      },
      "mini_modules": [
        {
          "name": "Concrete Module",
          "product": "Concrete",
          "product_rate": 20.625,
          "raw_inputs": { "Limestone": 92.8 },
          "raw_input_total": 92.8,
          "belt_utilization": 0.119,
          "copies_needed": 1,
          "steps": [ ... ],
          "building_totals": { "Constructor": 2 },
          "total_buildings": 2
        }
      ]
    }
  }
}
```

## UI: New "Factory Crazy" Tab

Add a third tab to factory-map.html: Map | Factories | Factory Crazy

Each factory card shows:
- Factory header (name, theme, HMF recipe, target rate)
- Manufacturer card (standalone, showing 4 input demands)
- Per mini-module section:
  - Module name and product
  - Belt utilization bar: "93 / 780 items/min" with visual progress bar
  - Raw inputs list
  - Building counts
  - Copy count (if > 1, shown prominently)
  - Compact step list (building x count for each step)

## Constraints

- Fluids (Water, Oil) don't go on belts. Exclude fluid inputs from the 780/min belt sum. Show them separately as "piped" inputs.
- The Manufacturer's own inputs come on 4 separate belts (one from each module), not subject to the 780 constraint.
- Each mini-module's copy count is independent of the factory's overall copy count (factory_copies). The total copies of a mini-module = module_copies * factory_copies.
