# Factory Crazy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decompose each factory into self-contained mini-modules (one per Manufacturer input), belt-constrained to 780/min, rendered in a new "Factory Crazy" tab.

**Architecture:** Python script reads `factory-subunits.json`, traces the DAG backwards from each Manufacturer input to raw resources, scales rates proportionally, applies 780/min belt constraint, outputs `factory-crazy.json`. HTML loads that JSON in a new tab.

**Tech Stack:** Python 3 (stdlib only: json, math), vanilla JS/HTML/CSS in `factory-map.html`

---

### Task 1: Python Script — DAG Decomposition Engine

**Files:**
- Create: `build_factory_crazy.py`
- Read: `factory-subunits.json`
- Output: `factory-crazy.json`

**Step 1: Write `build_factory_crazy.py` with the core algorithm**

```python
#!/usr/bin/env python3
"""Decompose factory modules into self-contained mini-modules per Manufacturer input."""

import json
import math

BELT_LIMIT = 780  # Mk.5 belt max items/min
FLUIDS = {"Water", "Crude Oil", "Heavy Oil Residue", "Alumina Solution", "Sulfuric Acid", "Nitrogen Gas", "Nitric Acid"}

def load_data():
    with open("factory-subunits.json") as f:
        return json.load(f)

def build_producer_map(steps):
    """Map item name -> step that produces it."""
    producers = {}
    for step in steps:
        for out_item in step["outputs"]:
            producers[out_item] = step
    return producers

def trace_module(product, demand_rate, producers, all_steps):
    """Trace backwards from a product at a given demand rate.

    Returns list of scaled steps and dict of raw inputs.
    Each step gets scaled proportionally to how much of its output
    this module needs.
    """
    module_steps = []
    raw_inputs = {}
    queue = [(product, demand_rate)]
    visited = {}  # item -> already-queued demand (to merge duplicate requests)

    while queue:
        item, needed = queue.pop(0)

        if item in visited:
            continue
        visited[item] = needed

        if item not in producers:
            # Raw resource
            raw_inputs[item] = raw_inputs.get(item, 0) + needed
            continue

        step = producers[item]
        step_output_rate = step["outputs"][item]
        scale = needed / step_output_rate

        # Create scaled copy of this step
        scaled_step = {
            "recipe": step["recipe"],
            "item": step["item"],
            "building": step["building"],
            "power_mw": step["power_mw"],
            "shards_per_building": step["shards_per_building"],
            "overclock_detail": step["overclock_detail"],
            "inputs": {k: v * scale for k, v in step["inputs"].items()},
            "outputs": {k: v * scale for k, v in step["outputs"].items()},
        }

        # Recalculate building counts from scaled output rate
        # buildings_exact = scaled_output / per_building_output
        # per_building_output = original_output / original_buildings_exact
        if step["buildings_exact"] > 0:
            per_building = step_output_rate / step["buildings_exact"]
            scaled_step["buildings_exact"] = round(needed / per_building, 4)
            scaled_step["buildings_ceil"] = math.ceil(scaled_step["buildings_exact"])
        else:
            scaled_step["buildings_exact"] = 0
            scaled_step["buildings_ceil"] = 0

        module_steps.append(scaled_step)

        # Queue upstream inputs
        for inp_item, inp_rate in scaled_step["inputs"].items():
            if inp_item not in visited:
                queue.append((inp_item, inp_rate))
            # If already visited as raw, it stays raw

    return module_steps, raw_inputs

def apply_belt_constraint(module_steps, raw_inputs, belt_limit):
    """If solid raw inputs exceed belt_limit, calculate copies needed and scale down."""
    solid_total = sum(rate for item, rate in raw_inputs.items() if item not in FLUIDS)

    if solid_total <= belt_limit:
        return module_steps, raw_inputs, 1, solid_total

    copies = math.ceil(solid_total / belt_limit)
    scale = 1.0 / copies

    scaled_steps = []
    for step in module_steps:
        s = dict(step)
        s["inputs"] = {k: v * scale for k, v in step["inputs"].items()}
        s["outputs"] = {k: v * scale for k, v in step["outputs"].items()}
        s["buildings_exact"] = round(step["buildings_exact"] * scale, 4)
        s["buildings_ceil"] = math.ceil(s["buildings_exact"])
        scaled_steps.append(s)

    scaled_raw = {k: v * scale for k, v in raw_inputs.items()}
    new_solid_total = sum(rate for item, rate in scaled_raw.items() if item not in FLUIDS)

    return scaled_steps, scaled_raw, copies, new_solid_total

def building_totals(steps):
    totals = {}
    for s in steps:
        b = s["building"]
        totals[b] = totals.get(b, 0) + s["buildings_ceil"]
    return totals

def decompose_factory(factory_id, mod):
    """Decompose one factory into mini-modules."""
    steps = mod["steps"]
    producers = build_producer_map(steps)

    # Find manufacturer step (produces HMF)
    mfr_step = None
    for step in steps:
        if step["building"] == "Manufacturer":
            mfr_step = step
            break

    if not mfr_step:
        raise ValueError(f"No Manufacturer step found in {factory_id}")

    # Remove manufacturer from producers so it's not traced into
    hmf_item = mfr_step["item"]
    if hmf_item in producers:
        del producers[hmf_item]

    mini_modules = []
    for input_item, input_rate in mfr_step["inputs"].items():
        module_steps, raw_inputs = trace_module(input_item, input_rate, producers, steps)
        module_steps, raw_inputs, copies, solid_total = apply_belt_constraint(
            module_steps, raw_inputs, BELT_LIMIT
        )

        # Separate solid and fluid raw inputs
        solid_inputs = {k: round(v, 4) for k, v in raw_inputs.items() if k not in FLUIDS}
        fluid_inputs = {k: round(v, 4) for k, v in raw_inputs.items() if k in FLUIDS}

        bt = building_totals(module_steps)
        total_b = sum(bt.values())

        mini_modules.append({
            "name": f"{input_item} Module",
            "product": input_item,
            "product_rate": round(input_rate, 4),
            "product_rate_per_copy": round(input_rate / copies, 4) if copies > 1 else round(input_rate, 4),
            "raw_inputs_solid": solid_inputs,
            "raw_inputs_fluid": fluid_inputs,
            "belt_items_per_min": round(solid_total, 2),
            "belt_utilization": round(solid_total / BELT_LIMIT, 4),
            "copies_needed": copies,
            "steps": module_steps,
            "building_totals": bt,
            "total_buildings": total_b,
        })

    return {
        "factory": factory_id,
        "theme": mod["theme"],
        "hmf_recipe": mod["hmf_recipe"],
        "hmf_per_min": mod["hmf_per_min"],
        "target_hmf": mod["target_hmf"],
        "factory_copies": mod["copies_needed_ceil"],
        "manufacturer": {
            "recipe": mfr_step["recipe"],
            "building": mfr_step["building"],
            "inputs": {k: round(v, 4) for k, v in mfr_step["inputs"].items()},
            "output": {k: round(v, 4) for k, v in mfr_step["outputs"].items()},
            "power_mw": mfr_step["power_mw"],
        },
        "mini_modules": mini_modules,
    }

def main():
    data = load_data()
    result = {
        "meta": {
            "title": "HMF-95 Factory Crazy Modules",
            "belt_limit": BELT_LIMIT,
            "description": "Self-contained mini-modules per Manufacturer input, belt-constrained to Mk.5 (780/min)",
            "source": "factory-subunits.json",
        },
        "factories": {}
    }

    for fid, mod in data["modules"].items():
        result["factories"][fid] = decompose_factory(fid, mod)

    with open("factory-crazy.json", "w") as f:
        json.dump(result, f, indent=2)

    # Print summary
    for fid, fdata in result["factories"].items():
        print(f"\n{'='*60}")
        print(f"{fid.upper()} — {fdata['theme']}")
        print(f"  Manufacturer: {fdata['hmf_recipe']} → {fdata['hmf_per_min']} HMF/min")
        print(f"  Factory copies: {fdata['factory_copies']}")
        for mm in fdata["mini_modules"]:
            belt_pct = mm["belt_utilization"] * 100
            print(f"  [{mm['name']}]")
            print(f"    Output: {mm['product_rate']}/min {mm['product']}")
            print(f"    Belt: {mm['belt_items_per_min']}/780 ({belt_pct:.1f}%)")
            print(f"    Buildings: {mm['total_buildings']} | Copies: {mm['copies_needed']}")
            if mm['raw_inputs_solid']:
                print(f"    Solid: {mm['raw_inputs_solid']}")
            if mm['raw_inputs_fluid']:
                print(f"    Fluid: {mm['raw_inputs_fluid']}")

    print(f"\nWritten to factory-crazy.json")

if __name__ == "__main__":
    main()
```

**Step 2: Run the script and validate output**

Run: `cd /Users/deepak/AI/satisfy && python3 build_factory_crazy.py`

Expected: Script prints summary for all 5 factories, writes `factory-crazy.json`. Verify:
- Each factory has 4 mini-modules (one per Manufacturer input)
- All belt utilizations are <= 100% (or copies_needed > 1)
- Raw input sums across all mini-modules approximately match the factory's total raw inputs
- No mini-module has 0 buildings

**Step 3: Spot-check Ferrium manually**

Ferrium Manufacturer inputs: Concrete 20.625, Modular Frame 7.5, Steel Pipe 33.75, EIB 9.375.

Check that:
- Concrete module raw inputs ≈ Limestone only
- Steel Pipe module raw inputs ≈ Iron Ore only
- Sum of all modules' Iron Ore ≈ 503.52 (Ferrium total)
- Sum of all modules' Limestone ≈ 202.5 (Ferrium total)

**Step 4: Commit**

```bash
git add build_factory_crazy.py factory-crazy.json
git commit -m "feat: add factory-crazy decomposition script"
```

---

### Task 2: Add Factory Crazy Tab to HTML

**Files:**
- Modify: `factory-map.html`

**Step 1: Add CSS for mini-module cards**

Add before `</style>` (line 100):

```css
.mini-module{margin:8px 20px 16px;border:1px solid #333;border-radius:4px;background:#0d1117;overflow:hidden}
.mini-module-header{padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.mini-module-header h4{font-size:12px;color:#e0e0e0;margin:0}
.mini-module-header .copies-badge{font-size:10px;padding:2px 8px;background:#f39c12;color:#111;border-radius:3px;font-weight:bold}
.belt-bar{margin:0 14px 10px;height:14px;background:#1a1a2e;border-radius:3px;position:relative;overflow:hidden}
.belt-bar-fill{height:100%;border-radius:3px;transition:width 0.3s}
.belt-bar-label{position:absolute;top:0;left:0;right:0;height:100%;display:flex;align-items:center;justify-content:center;font-size:9px;color:#ccc;font-weight:bold}
.mini-module-body{padding:0 14px 10px;font-size:10px;color:#aaa}
.mini-module-body .raw-list{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px}
.mini-module-body .buildings-list{display:flex;gap:8px;flex-wrap:wrap}
.mini-module-body .buildings-list span{white-space:nowrap}
.manufacturer-card{margin:8px 20px 4px;padding:12px 14px;border:2px dashed #555;border-radius:4px;background:#1a1a2e}
.manufacturer-card h4{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px}
.manufacturer-card .mfr-inputs{display:flex;gap:6px;flex-wrap:wrap}
.manufacturer-card .mfr-pill{padding:3px 8px;background:#16213e;border:1px solid #333;border-radius:12px;font-size:10px;color:#ccc}
```

**Step 2: Add the tab button and container div**

In the HTML `<div id="tab-bar">` section (~line 103-106), add the new tab button:

```html
<button class="tab-btn" onclick="switchTab('crazy')">Factory Crazy</button>
```

After `<div id="factories-view">...</div>` (~line 122), add:

```html
<div id="crazy-view" style="display:none;flex:1;overflow-y:auto;background:#0d1117;color:#ccc;padding:24px 32px;font-family:'Courier New',monospace">
  <div id="crazy-content" style="max-width:1400px;margin:0 auto;width:100%"></div>
</div>
```

**Step 3: Update `switchTab()` to handle the new tab**

In the `switchTab` function (~line 129-138), add the crazy view toggle:

```javascript
document.getElementById('crazy-view').style.display = tab === 'crazy' ? 'flex' : 'none';
```

And add the lazy-load trigger:

```javascript
if (tab === 'crazy' && !crazyLoaded) { loadCrazy(); }
```

Add above `switchTab`:

```javascript
let crazyLoaded = false;
async function loadCrazy() {
  try {
    const resp = await fetch('factory-crazy.json');
    const data = await resp.json();
    crazyLoaded = true;
    renderCrazyTab(data);
  } catch (e) {
    document.getElementById('crazy-content').innerHTML = '<p style="color:#e74c3c">Failed to load factory-crazy.json: ' + e.message + '</p>';
  }
}
```

**Step 4: Write `renderCrazyTab()` function**

Add after the `loadCrazy` function:

```javascript
function renderCrazyTab(data) {
  var el = document.getElementById('crazy-content');
  var html = '';

  // Meta banner
  html += '<div class="summary-banner">';
  html += '<h2>' + data.meta.title + '</h2>';
  html += '<div class="meta">' + data.meta.description + ' | Belt limit: ' + data.meta.belt_limit + '/min</div>';
  html += '</div>';

  for (var fid in data.factories) {
    if (!data.factories.hasOwnProperty(fid)) continue;
    var fac = data.factories[fid];
    var color = FACTORY_COLORS[fid] || '#666';

    html += '<div id="crazy-' + fid + '" class="factory-card">';

    // Factory header
    html += '<div class="factory-card-header" style="border-left-color:' + color + '">';
    html += '<h3 style="color:' + color + '">' + fid.toUpperCase() + ' — ' + fac.theme + '</h3>';
    html += '<div class="recipe">' + fac.hmf_recipe + '</div>';
    html += '<div class="stats">';
    html += '<span class="stat"><b>' + fac.hmf_per_min + '</b> HMF/min per module</span>';
    html += '<span class="stat">×' + fac.factory_copies + ' factory copies → <b>' + fac.target_hmf + '</b> HMF/min</span>';
    html += '</div>';
    html += '</div>';

    // Manufacturer card
    var mfr = fac.manufacturer;
    html += '<div class="manufacturer-card">';
    html += '<h4>★ Manufacturer — ' + mfr.recipe + ' (' + mfr.power_mw + ' MW)</h4>';
    html += '<div class="mfr-inputs">';
    for (var inp in mfr.inputs) {
      html += '<span class="mfr-pill">' + inp + ' ' + mfr.inputs[inp] + '/min</span>';
    }
    html += '</div>';
    html += '</div>';

    // Mini-modules
    for (var i = 0; i < fac.mini_modules.length; i++) {
      var mm = fac.mini_modules[i];
      var pct = Math.min(mm.belt_utilization * 100, 100);
      var barColor = pct > 90 ? '#e74c3c' : pct > 70 ? '#f39c12' : '#2ecc71';

      html += '<div class="mini-module">';
      html += '<div class="mini-module-header">';
      html += '<h4>' + mm.name + ' → ' + mm.product_rate + '/min</h4>';
      if (mm.copies_needed > 1) {
        html += '<span class="copies-badge">×' + mm.copies_needed + ' copies</span>';
      }
      html += '</div>';

      // Belt utilization bar
      html += '<div class="belt-bar">';
      html += '<div class="belt-bar-fill" style="width:' + pct + '%;background:' + barColor + '"></div>';
      html += '<div class="belt-bar-label">' + mm.belt_items_per_min + ' / 780 items/min (' + pct.toFixed(1) + '%)</div>';
      html += '</div>';

      html += '<div class="mini-module-body">';

      // Raw inputs
      html += '<div class="raw-list">';
      for (var r in mm.raw_inputs_solid) {
        html += '<span class="raw-pill"><span class="dot" style="background:#e74c3c"></span>' + r + ' ' + mm.raw_inputs_solid[r].toFixed(1) + '/min</span>';
      }
      for (var r in mm.raw_inputs_fluid) {
        html += '<span class="raw-pill"><span class="dot" style="background:#4fc3f7"></span>' + r + ' ' + mm.raw_inputs_fluid[r].toFixed(1) + ' m³/min (piped)</span>';
      }
      html += '</div>';

      // Buildings
      html += '<div class="buildings-list">';
      for (var b in mm.building_totals) {
        html += '<span>' + b + ' ×' + mm.building_totals[b] + '</span>';
      }
      html += '<span style="color:#666">| ' + mm.total_buildings + ' total</span>';
      html += '</div>';

      html += '</div>'; // mini-module-body
      html += '</div>'; // mini-module
    }

    html += '</div>'; // factory-card
  }

  el.innerHTML = html;
}
```

**Step 5: Test in browser**

Open `file:///Users/deepak/AI/satisfy/factory-map.html`, click "Factory Crazy" tab. Verify:
- All 5 factory cards render
- Each has a Manufacturer card + 4 mini-modules
- Belt bars show correct utilization
- Copy badges appear where belt > 780
- No JS console errors

**Step 6: Commit**

```bash
git add factory-map.html
git commit -m "feat: add Factory Crazy tab with mini-module decomposition"
```
