# Factory Crazy Module Detail View Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the flow diagram in each Factory Crazy Stage 2 module card with a color-banded table showing inputs, intermediates, and output with per-module/total rates and recipe details.

**Architecture:** Single-file change to `factory-map.html`. Add new CSS table styles, replace the Stage 2 module rendering loop (lines 237-291), remove the `renderCrazyFlow` and `drawCrazyConnectors` functions and their call site. The `buildDAG` function is shared with the Factories tab and must be kept.

**Tech Stack:** Vanilla HTML/CSS/JS (no frameworks)

---

### Task 1: Add CSS for module detail table

**Files:**
- Modify: `factory-map.html:82-119` (CSS section — after `.flow-diagram` styles, before `.manufacturer-card`)

**Step 1: Add new CSS rules**

Insert these styles after line 119 (after `.surplus-badge.high`) in the `<style>` block:

```css
.module-detail-table{width:100%;border-collapse:collapse;font-size:11px;font-family:'Courier New',monospace}
.module-detail-table th{text-align:left;color:#666;font-weight:normal;padding:4px 10px;font-size:10px;text-transform:uppercase;border-bottom:1px solid #333}
.module-detail-table td{padding:5px 10px;border-top:1px solid #222}
.module-detail-table .row-input td{background:#0d2818}
.module-detail-table .row-intermediate td{background:#1a1a2e}
.module-detail-table .row-output td{background:#0d1b2a;font-weight:bold}
.module-detail-table .item-col{color:#e0e0e0}
.module-detail-table .rate-col{color:#aaa;text-align:right;white-space:nowrap}
.module-detail-table .recipe-col{color:#888}
.module-detail-table .building-col{color:#aaa;white-space:nowrap}
.module-detail-table .shard-indicator{color:#f39c12;margin-left:4px}
.module-detail-table .dash{color:#444}
```

**Step 2: Verify CSS loads**

Open browser, go to Factory Crazy tab, confirm no visual regressions (new CSS is additive only).

**Step 3: Commit**

```bash
git add factory-map.html
git commit -m "style: add CSS for module detail table in Factory Crazy tab"
```

---

### Task 2: Replace Stage 2 module rendering with detail table

**Files:**
- Modify: `factory-map.html:237-291` (the `for` loop over `fac.stage2_modules`)

**Step 1: Replace the module rendering loop**

Replace lines 237-291 (from `for (var i = 0; i < fac.stage2_modules.length; i++) {` through the closing `html += '</div>'; // end mini-module` and the next `}`) with:

```javascript
    for (var i = 0; i < fac.stage2_modules.length; i++) {
      var mm = fac.stage2_modules[i];

      html += '<div class="mini-module">';

      // Simplified header: name, copies, output rate
      html += '<div class="mini-module-header">';
      html += '<h4>' + mm.name + '</h4>';
      html += '<div style="display:flex;align-items:center;gap:8px">';
      if (mm.copies > 1) {
        html += '<span class="copies-badge">\u00d7' + mm.copies + ' copies</span>';
      }
      html += '<span style="font-size:10px;color:#aaa">\u2192 ' + mm.output_per_copy.toFixed(1) + '/min each</span>';
      html += '</div>';
      html += '</div>';

      // Detail table
      html += '<div style="padding:0 14px 10px">';
      html += '<table class="module-detail-table">';
      html += '<thead><tr><th>Item</th><th style="text-align:right">/mod</th><th style="text-align:right">Total</th><th>Recipe</th><th>Building</th><th style="text-align:right">Rate/bldg</th></tr></thead>';
      html += '<tbody>';

      // 1. Input rows (sorted alphabetically)
      var inputKeys = Object.keys(mm.inputs).sort();
      for (var j = 0; j < inputKeys.length; j++) {
        var inp = inputKeys[j];
        var perMod = mm.inputs[inp];
        var total = perMod * mm.copies;
        html += '<tr class="row-input">';
        html += '<td class="item-col">' + inp + '</td>';
        html += '<td class="rate-col">' + perMod.toFixed(1) + '/m</td>';
        html += '<td class="rate-col">' + total.toFixed(1) + '/m</td>';
        html += '<td class="dash">\u2014</td>';
        html += '<td class="dash">\u2014</td>';
        html += '<td class="dash">\u2014</td>';
        html += '</tr>';
      }

      // 2. Separate output step from intermediate steps
      var outputStep = null;
      var intermediateSteps = [];
      for (var s = 0; s < mm.steps.length; s++) {
        if (mm.steps[s].item === mm.product) {
          outputStep = mm.steps[s];
        } else {
          intermediateSteps.push(mm.steps[s]);
        }
      }

      // Intermediate step rows (dependency order from data)
      for (var s = 0; s < intermediateSteps.length; s++) {
        var step = intermediateSteps[s];
        var outRate = step.outputs[step.item] || Object.values(step.outputs)[0];
        var ratePerBldg = outRate / step.buildings_exact;
        var shardHtml = step.shards_per_building > 0 ? '<span class="shard-indicator">\u26a1' + step.shards_per_building + '</span>' : '';
        html += '<tr class="row-intermediate">';
        html += '<td class="item-col">' + step.item + '</td>';
        html += '<td class="rate-col">' + outRate.toFixed(1) + '/m</td>';
        html += '<td class="rate-col">' + (outRate * mm.copies).toFixed(1) + '/m</td>';
        html += '<td class="recipe-col">' + step.recipe + '</td>';
        html += '<td class="building-col">' + step.building + ' \u00d7' + step.buildings_ceil + shardHtml + '</td>';
        html += '<td class="rate-col">' + ratePerBldg.toFixed(1) + '/m</td>';
        html += '</tr>';
      }

      // 3. Output row (always last)
      if (outputStep) {
        var outRate = outputStep.outputs[outputStep.item] || Object.values(outputStep.outputs)[0];
        var ratePerBldg = outRate / outputStep.buildings_exact;
        var shardHtml = outputStep.shards_per_building > 0 ? '<span class="shard-indicator">\u26a1' + outputStep.shards_per_building + '</span>' : '';
        html += '<tr class="row-output">';
        html += '<td class="item-col">' + outputStep.item + '</td>';
        html += '<td class="rate-col">' + outRate.toFixed(1) + '/m</td>';
        html += '<td class="rate-col">' + (outRate * mm.copies).toFixed(1) + '/m</td>';
        html += '<td class="recipe-col">' + outputStep.recipe + '</td>';
        html += '<td class="building-col">' + outputStep.building + ' \u00d7' + outputStep.buildings_ceil + shardHtml + '</td>';
        html += '<td class="rate-col">' + ratePerBldg.toFixed(1) + '/m</td>';
        html += '</tr>';
      }

      html += '</tbody></table>';
      html += '</div>';
      html += '</div>'; // end mini-module
    }
```

**Step 2: Verify in browser**

Open Factory Crazy tab. Each Stage 2 module card should now show:
- Simplified header with module name, copies badge, output rate
- Color-banded table: green inputs → neutral intermediates → blue output
- No flow diagram (it will be orphaned but harmless at this point)

**Step 3: Commit**

```bash
git add factory-map.html
git commit -m "feat: replace flow diagram with detail table in Factory Crazy modules"
```

---

### Task 3: Remove flow diagram rendering and dead CSS

**Files:**
- Modify: `factory-map.html:204` (remove `flowContainers` declaration)
- Modify: `factory-map.html:334-345` (remove `requestAnimationFrame` block that renders flow diagrams)
- Modify: `factory-map.html:348-462` (remove `renderCrazyFlow` and `drawCrazyConnectors` functions)
- Modify: `factory-map.html:82-99` (remove flow-diagram CSS that's only used by Factory Crazy — verify Factories tab doesn't use these classes first)

**Step 1: Remove the `flowContainers` variable and its rendering block**

In `renderFactoryCrazyTab`, remove:
- Line 204: `var flowContainers = [];`
- Lines 334-345: The `requestAnimationFrame` block that iterates `flowContainers`

**Step 2: Remove `renderCrazyFlow` and `drawCrazyConnectors` functions**

Delete the two functions (lines 348-462). These are only called from the `flowContainers` rendering block removed in step 1.

**Step 3: Check if flow-diagram CSS is shared with Factories tab**

Search for `flow-diagram`, `flow-columns`, `flow-node`, `flow-svg` usage in the Factories tab rendering (`renderFactoriesTab` function and `renderFlowDiagram` function). If these classes ARE used by the Factories tab, keep the CSS. If not, remove it.

Note: The Factories tab has its own `renderFlowDiagram` function (line 692) which uses `flow-columns`, `flow-node`, `flow-svg`, etc. — so ALL flow CSS must be kept. Only remove CSS specific to Factory Crazy that no longer applies:
- `.belt-bar`, `.belt-bar-fill`, `.belt-bar-label` (lines 104-106) — check if used elsewhere. If only in Factory Crazy, remove.
- `.surplus-badge` styles (lines 116-119) — check if used elsewhere. If only in Factory Crazy, remove.

**Step 4: Remove dead CSS for belt-bar and surplus-badge if unused elsewhere**

Search the entire file for `belt-bar` and `surplus-badge` usage outside Factory Crazy. If only used in the code that was already removed, delete those CSS rules.

**Step 5: Verify in browser**

- Factory Crazy tab: Detail tables render correctly, no JS errors in console
- Factories tab: Flow diagrams still render correctly (no regression)

**Step 6: Commit**

```bash
git add factory-map.html
git commit -m "refactor: remove dead flow diagram code and unused CSS from Factory Crazy"
```

---

### Task 4: Final visual polish and verification

**Files:**
- Modify: `factory-map.html` (CSS tweaks if needed)

**Step 1: Visual review**

Open browser, check all factories in Factory Crazy tab:
- All modules show correct input/intermediate/output rows
- Color banding is visible and distinguishable
- Shard indicators appear on overclocked steps
- Numbers are correct (spot-check one module against `factory-crazy.json`)
- Responsive at different window widths (table should scroll horizontally if needed)

**Step 2: Check edge cases**

- Module with only 1 copy (no copies badge should show)
- Module with no intermediate steps (only input + output rows)
- Steps with multiple outputs (byproducts)
- Steps with `shards_per_building: 0` (no shard indicator)

**Step 3: Commit if any fixes needed**

```bash
git add factory-map.html
git commit -m "fix: visual polish for Factory Crazy detail tables"
```
