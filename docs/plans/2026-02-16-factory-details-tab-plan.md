# Factory Details Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Factories" tab to factory-map.html showing production chain flow diagrams, module anchor callouts, and factory stats from factory-subunits.json.

**Architecture:** Single-file vanilla JS/CSS/HTML modification. Tab bar at top toggles between existing map view and new factories view. Flow diagrams built as HTML/CSS nodes with SVG arrow connectors. Data loaded via fetch() from factory-subunits.json.

**Tech Stack:** Vanilla HTML/CSS/JS (no frameworks). CSS Grid for layout. Inline SVG for connectors.

**Design doc:** `docs/plans/2026-02-16-factory-details-tab-design.md`

**Key file:** `factory-map.html` (~670 lines, monolithic single-page app)

**Data file:** `factory-subunits.json` (5 factories, each with steps[], building_totals, raw_inputs, etc.)

**Factory colors (already in codebase):** ferrium:`#e74c3c`, naphtheon:`#9b59b6`, forgeholm:`#3498db`, luxara:`#f1c40f`, cathera:`#1abc9c`

---

### Task 1: Add Tab Bar and Content Wrappers

Wrap existing body content into a tab structure. The Map tab contains the existing sidebar+canvas. A new empty Factories tab container is added.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add tab bar CSS**

Add to the `<style>` block (before `</style>` on line 40):

```css
/* Tab bar */
#tab-bar{display:flex;background:#16213e;border-bottom:2px solid #333;flex-shrink:0}
.tab-btn{padding:10px 24px;font-family:'Courier New',monospace;font-size:13px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;color:#7f8fa6;background:transparent;border:none;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px}
.tab-btn:hover{color:#ccc}
.tab-btn.active{color:#e0e0e0;border-bottom-color:#e0e0e0}
#tab-content{display:flex;flex:1;overflow:hidden}
#map-view{display:flex;flex:1;overflow:hidden}
#factories-view{display:none;flex:1;overflow-y:auto;background:#0d1117;color:#ccc;padding:24px 32px;font-family:'Courier New',monospace}
```

**Step 2: Restructure HTML body**

Replace the current `<body>` content (lines 42-53) with:

```html
<body>
<div id="tab-bar">
  <button class="tab-btn active" onclick="switchTab('map')">Map</button>
  <button class="tab-btn" onclick="switchTab('factories')">Factories</button>
</div>
<div id="tab-content">
  <div id="map-view">
    <div id="sidebar">
      <h1>Factory Location Planner</h1>
      <div id="legend"></div>
      <div id="factory-list"></div>
      <div id="controls">
        <button id="export-btn">EXPORT SELECTIONS</button>
        <button id="reset-btn">Reset View</button>
      </div>
    </div>
    <canvas id="map"></canvas>
  </div>
  <div id="factories-view">
    <div id="factories-content"></div>
  </div>
</div>
<div id="tooltip"></div>
```

**Step 3: Update body CSS**

Change body style (line 8) from:
```css
body{font-family:'Courier New',monospace;display:flex;height:100vh;overflow:hidden;background:#111}
```
to:
```css
body{font-family:'Courier New',monospace;display:flex;flex-direction:column;height:100vh;overflow:hidden;background:#111}
```

**Step 4: Add switchTab function**

Add at the top of the `<script>` block (after line 55 `// === DATA ===`), before the data constants:

```javascript
// === TAB SWITCHING ===
let currentTab = 'map';
function switchTab(tab) {
  currentTab = tab;
  document.getElementById('map-view').style.display = tab === 'map' ? 'flex' : 'none';
  document.getElementById('factories-view').style.display = tab === 'factories' ? 'flex' : 'none';
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.trim().toLowerCase() === tab);
  });
  if (tab === 'map') { resize(); draw(); }
  if (tab === 'factories' && !factoriesLoaded) { loadFactories(); }
}
let factoriesLoaded = false;
async function loadFactories() {
  try {
    const resp = await fetch('factory-subunits.json');
    const data = await resp.json();
    factoriesLoaded = true;
    renderFactoriesTab(data);
  } catch (e) {
    document.getElementById('factories-content').innerHTML = '<p style="color:#e74c3c">Failed to load factory-subunits.json: ' + e.message + '</p>';
  }
}
function renderFactoriesTab(data) {
  document.getElementById('factories-content').innerHTML = '<p style="color:#888">Loading...</p>';
}
```

**Step 5: Open in browser and verify**

Open `factory-map.html` in a browser. Verify:
- Tab bar appears at top with "MAP" and "FACTORIES" tabs
- Map tab is active by default and shows existing sidebar+canvas
- Clicking "FACTORIES" shows empty content area
- Clicking "MAP" returns to the map view
- Map canvas still resizes correctly

**Step 6: Commit**

```bash
git add factory-map.html
git commit -m "feat: add tab bar with Map and Factories tab switching"
```

---

### Task 2: Render Global Summary Banner

Load data and render the summary table at the top of the Factories tab.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add CSS for summary banner and factory cards**

Add to `<style>` block:

```css
/* Factories tab styles */
#factories-content{max-width:1400px;margin:0 auto;width:100%}
.summary-banner{background:#1a1a2e;border:1px solid #333;border-radius:6px;padding:20px 24px;margin-bottom:24px}
.summary-banner h2{font-size:16px;color:#e0e0e0;margin-bottom:4px;letter-spacing:1px}
.summary-banner .meta{font-size:11px;color:#888;margin-bottom:16px}
.summary-table{width:100%;border-collapse:collapse;font-size:12px}
.summary-table th{text-align:left;color:#888;font-weight:normal;padding:4px 12px 4px 0;border-bottom:1px solid #333;font-size:11px;text-transform:uppercase;letter-spacing:0.5px}
.summary-table td{padding:6px 12px 6px 0;border-bottom:1px solid #222}
.summary-table tr:last-child td{border-bottom:none;font-weight:bold;border-top:1px solid #555;color:#fff}
.summary-table .factory-accent{width:4px;padding:0 8px 0 0}
.summary-table .factory-accent span{display:inline-block;width:4px;height:16px;border-radius:2px}
.summary-table tr.clickable{cursor:pointer}
.summary-table tr.clickable:hover td{color:#fff}
.factory-nav{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap}
.factory-nav a{padding:6px 14px;background:#1a1a2e;border:1px solid #333;border-radius:4px;color:#ccc;text-decoration:none;font-size:12px;font-family:'Courier New',monospace}
.factory-nav a:hover{background:#16213e;color:#fff}
```

**Step 2: Implement renderFactoriesTab with summary banner**

Replace the placeholder `renderFactoriesTab` function:

```javascript
function renderFactoriesTab(data) {
  const el = document.getElementById('factories-content');
  let html = '';

  // Global summary banner
  html += '<div class="summary-banner">';
  html += `<h2>${data.meta.title}</h2>`;
  html += `<div class="meta">Module basis: ${data.meta.module_basis} &nbsp;|&nbsp; Shard budget: ${data.meta.shards_used} / ${data.meta.shard_budget} used</div>`;
  html += '<table class="summary-table"><thead><tr>';
  html += '<th class="factory-accent"></th><th>Factory</th><th>Target HMF</th><th>Copies</th><th>Shards</th><th>Buildings</th>';
  html += '</tr></thead><tbody>';

  let totalHmf = 0, totalCopies = 0, totalShards = 0, totalBuildings = 0;
  for (const s of data.summary) {
    const color = FACTORY_COLORS[s.factory] || '#666';
    totalHmf += s.target_hmf;
    totalCopies += s.copies_needed;
    totalShards += s.total_shards_all_copies;
    totalBuildings += s.total_buildings_all_copies;
    html += `<tr class="clickable" onclick="document.getElementById('factory-${s.factory}').scrollIntoView({behavior:'smooth'})">`;
    html += `<td class="factory-accent"><span style="background:${color}"></span></td>`;
    html += `<td style="color:${color};font-weight:bold">${s.factory.charAt(0).toUpperCase() + s.factory.slice(1)}</td>`;
    html += `<td>${s.target_hmf.toFixed(2)}/min</td>`;
    html += `<td>${s.copies_needed} modules</td>`;
    html += `<td>${s.total_shards_all_copies}</td>`;
    html += `<td>${s.total_buildings_all_copies}</td>`;
    html += '</tr>';
  }
  html += `<tr><td></td><td>Total</td><td>${totalHmf.toFixed(2)}/min</td><td>${totalCopies} modules</td><td>${totalShards}</td><td>${totalBuildings}</td></tr>`;
  html += '</tbody></table></div>';

  // Factory anchor nav
  html += '<div class="factory-nav">';
  for (const fid of Object.keys(data.modules)) {
    const color = FACTORY_COLORS[fid] || '#666';
    html += `<a href="#factory-${fid}" style="border-left:3px solid ${color}" onclick="event.preventDefault();document.getElementById('factory-${fid}').scrollIntoView({behavior:'smooth'})">${fid.charAt(0).toUpperCase() + fid.slice(1)}</a>`;
  }
  html += '</div>';

  // Factory cards (placeholder for now)
  for (const [fid, mod] of Object.entries(data.modules)) {
    html += `<div id="factory-${fid}" class="factory-card-placeholder" style="padding:20px;margin-bottom:16px;border:1px solid #333;border-radius:6px;background:#1a1a2e;border-left:4px solid ${FACTORY_COLORS[fid] || '#666'}">`;
    html += `<h3 style="color:${FACTORY_COLORS[fid] || '#fff'};margin-bottom:4px">${fid.toUpperCase()} — ${mod.theme}</h3>`;
    html += `<p style="font-size:11px;color:#888">${mod.hmf_recipe} | ${mod.hmf_per_min} HMF/min per module</p>`;
    html += '</div>';
  }

  el.innerHTML = html;
}
```

**Step 3: Open in browser and verify**

Switch to Factories tab. Verify:
- Summary banner shows title, shard budget
- Table shows all 5 factories with correct numbers
- Totals row at bottom sums correctly (~95 HMF)
- Clicking a factory row scrolls to its placeholder card
- Factory nav buttons appear and scroll correctly

**Step 4: Commit**

```bash
git add factory-map.html
git commit -m "feat: render global summary banner and factory nav on Factories tab"
```

---

### Task 3: Render Factory Card Headers

Replace placeholder factory cards with proper header banners showing all stats.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add CSS for factory cards**

Add to `<style>` block:

```css
.factory-card{margin-bottom:32px;border-radius:6px;background:#1a1a2e;border:1px solid #333;overflow:hidden}
.factory-card-header{padding:16px 20px;border-left:4px solid #666}
.factory-card-header h3{font-size:15px;margin-bottom:2px}
.factory-card-header .recipe{font-size:11px;color:#888;margin-bottom:8px}
.factory-card-header .stats{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;margin-bottom:8px}
.factory-card-header .stats .stat{color:#aaa}
.factory-card-header .stats .stat b{color:#e0e0e0}
.raw-inputs{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.raw-pill{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:#16213e;border:1px solid #333;border-radius:12px;font-size:10px;color:#ccc}
.raw-pill .dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.building-summary{padding:12px 20px;border-top:1px solid #333;font-size:11px;color:#aaa;display:flex;gap:12px;flex-wrap:wrap}
.building-summary span{white-space:nowrap}
```

**Step 2: Update factory card rendering in renderFactoriesTab**

Replace the factory cards section (the `for (const [fid, mod]...` loop) with:

```javascript
  // Factory cards
  for (const [fid, mod] of Object.entries(data.modules)) {
    const color = FACTORY_COLORS[fid] || '#666';
    html += `<div id="factory-${fid}" class="factory-card">`;

    // Header banner
    html += `<div class="factory-card-header" style="border-left-color:${color}">`;
    html += `<h3 style="color:${color}">${fid.toUpperCase()} — ${mod.theme}</h3>`;
    html += `<div class="recipe">${mod.hmf_recipe}</div>`;
    html += '<div class="stats">';
    html += `<span class="stat"><b>${mod.hmf_per_min}</b> HMF/min per module</span>`;
    html += `<span class="stat">&times;${mod.copies_needed_ceil} copies &rarr; <b>${mod.target_hmf}</b> HMF/min</span>`;
    html += `<span class="stat"><b>${mod.total_buildings}</b> buildings</span>`;
    html += `<span class="stat"><b>${mod.total_power_mw}</b> MW</span>`;
    html += `<span class="stat"><b>${mod.shards_per_module}</b> shards/module</span>`;
    html += '</div>';

    // Raw input pills
    const RESOURCE_COLORS_MAP = {
      'Iron Ore': '#e74c3c', 'Limestone': '#95a5a6', 'Copper Ore': '#e67e22',
      'Coal': '#555', 'Crude Oil': '#9b59b6', 'Caterium Ore': '#f1c40f',
      'Bauxite': '#e91e63', 'Water': '#4fc3f7', 'Silica': '#00bcd4'
    };
    html += '<div class="raw-inputs">';
    for (const [name, info] of Object.entries(mod.raw_inputs)) {
      const rc = RESOURCE_COLORS_MAP[name] || '#888';
      html += `<span class="raw-pill"><span class="dot" style="background:${rc}"></span>${name} ${info.per_min}${info.is_fluid ? ' m³' : ''}/min</span>`;
    }
    html += '</div>';
    html += '</div>'; // end header

    // Flow diagram placeholder
    html += `<div class="flow-diagram" id="flow-${fid}" style="padding:20px;min-height:120px;position:relative;overflow-x:auto"></div>`;

    // Building summary
    html += '<div class="building-summary">';
    for (const [btype, count] of Object.entries(mod.building_totals)) {
      html += `<span>${btype} &times;${count}</span>`;
    }
    html += '</div>';

    html += '</div>'; // end factory card
  }
```

**Step 3: Remove the old placeholder CSS class reference**

Delete the `.factory-card-placeholder` style if it was added (it was inline so no CSS to remove).

**Step 4: Open in browser and verify**

Verify each factory card shows:
- Factory name + theme in correct color
- HMF recipe name
- Stats line with per-module rate, copies, target rate, buildings, power, shards
- Colored raw input pills
- Empty flow diagram area
- Building summary at bottom

**Step 5: Commit**

```bash
git add factory-map.html
git commit -m "feat: render factory card headers with stats and raw input pills"
```

---

### Task 4: Build DAG Layout Algorithm

Implement the topological sort and layer assignment for the production chain. This is pure logic — no rendering yet.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add buildDAG function**

Add this function in the script section (after the `renderFactoriesTab` function):

```javascript
// === DAG LAYOUT ===
function buildDAG(steps) {
  // Map: item name -> step that produces it
  const producerOf = {};
  for (const step of steps) {
    producerOf[step.item] = step;
  }

  // Identify raw inputs (inputs not produced by any step)
  const rawInputs = new Set();
  for (const step of steps) {
    for (const inputName of Object.keys(step.inputs)) {
      if (!producerOf[inputName]) {
        rawInputs.add(inputName);
      }
    }
  }

  // Assign layers via BFS from raw inputs
  // layer[item] = max depth from any raw input
  const layer = {};
  for (const r of rawInputs) { layer[r] = 0; }

  // Process steps in dependency order
  let changed = true;
  while (changed) {
    changed = false;
    for (const step of steps) {
      let maxInputLayer = -1;
      let allResolved = true;
      for (const inputName of Object.keys(step.inputs)) {
        if (layer[inputName] === undefined) { allResolved = false; break; }
        maxInputLayer = Math.max(maxInputLayer, layer[inputName]);
      }
      if (allResolved && (layer[step.item] === undefined || layer[step.item] < maxInputLayer + 1)) {
        layer[step.item] = maxInputLayer + 1;
        changed = true;
      }
    }
  }

  // Group by layer
  const maxLayer = Math.max(...Object.values(layer));
  const columns = [];
  for (let i = 0; i <= maxLayer; i++) { columns.push([]); }

  // Add raw inputs to column 0
  for (const r of rawInputs) {
    columns[0].push({ type: 'raw', item: r, layer: 0 });
  }

  // Add steps to their layers
  for (const step of steps) {
    const l = layer[step.item];
    columns[l].push({ type: 'step', step, item: step.item, layer: l });
  }

  // Build edges: for each step, connect each input to this step
  const edges = [];
  for (const step of steps) {
    for (const [inputName, rate] of Object.entries(step.inputs)) {
      edges.push({ from: inputName, to: step.item, rate });
    }
  }

  return { columns, edges, rawInputs, layer, maxLayer };
}
```

**Step 2: Verify by logging**

Temporarily add to `renderFactoriesTab`, inside the factory card loop after defining `mod`:

```javascript
    const dag = buildDAG(mod.steps);
    console.log(fid, 'layers:', dag.maxLayer, 'columns:', dag.columns.map(c => c.map(n => n.item)));
```

**Step 3: Open browser console, switch to Factories tab**

Verify console output shows reasonable layer assignments:
- Ferrium: raw inputs (Iron Ore, Limestone) at layer 0, HMF at the highest layer
- Each intermediate item at increasing layers
- No undefined layers or missing items

**Step 4: Remove the console.log**

Remove the temporary logging added in Step 2.

**Step 5: Commit**

```bash
git add factory-map.html
git commit -m "feat: implement DAG topological sort and layer assignment for production chains"
```

---

### Task 5: Render Flow Diagram Nodes

Render the DAG as HTML nodes arranged in columns using CSS Grid.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add CSS for flow diagram**

Add to `<style>` block:

```css
.flow-diagram{padding:20px;min-height:120px;position:relative;overflow-x:auto}
.flow-columns{display:flex;gap:0;align-items:stretch;min-width:max-content}
.flow-column{display:flex;flex-direction:column;justify-content:center;gap:12px;padding:0 24px;min-width:140px}
.flow-node{background:#16213e;border:1px solid #333;border-radius:4px;padding:8px 10px;font-size:11px;min-width:120px;position:relative}
.flow-node .item-name{font-weight:bold;color:#e0e0e0;font-size:12px;margin-bottom:3px}
.flow-node .building-info{color:#888}
.flow-node .output-rate{color:#aaa;font-size:10px;margin-top:2px}
.flow-node.raw-input{background:#0d1117;border-style:dashed;border-color:#555}
.flow-node.raw-input .item-name{color:#aaa}
.flow-node.anchor{border:2px solid #666;background:#1f2940;position:relative}
.flow-node.anchor .anchor-label{display:block;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:#888;margin-bottom:4px}
.flow-node.anchor .scaling{font-size:10px;color:#aaa;margin-top:6px;padding-top:6px;border-top:1px solid #333}
.flow-node.overclocked{border-color:#f39c12;box-shadow:0 0 6px rgba(243,156,18,0.2)}
.flow-node .shard-badge{display:inline-block;font-size:9px;color:#f39c12;margin-left:4px}
```

**Step 2: Add renderFlowDiagram function**

Add after `buildDAG`:

```javascript
function renderFlowDiagram(fid, mod) {
  const dag = buildDAG(mod.steps);
  const color = FACTORY_COLORS[fid] || '#666';
  const el = document.getElementById('flow-' + fid);

  // Build output rate lookup
  const outputRates = {};
  for (const step of mod.steps) {
    for (const [item, rate] of Object.entries(step.outputs)) {
      outputRates[item] = rate;
    }
  }

  let html = '<div class="flow-columns">';
  for (let col = 0; col <= dag.maxLayer; col++) {
    html += '<div class="flow-column">';
    for (const node of dag.columns[col]) {
      if (node.type === 'raw') {
        // Raw input node
        const rawInfo = mod.raw_inputs[node.item];
        const rate = rawInfo ? rawInfo.per_min : '';
        const unit = rawInfo && rawInfo.is_fluid ? ' m³/min' : '/min';
        html += `<div class="flow-node raw-input" data-item="${node.item}">`;
        html += `<div class="item-name">${node.item}</div>`;
        html += `<div class="output-rate">${rate}${unit}</div>`;
        html += '</div>';
      } else {
        // Step node
        const step = node.step;
        const isAnchor = step.building === 'Manufacturer';
        const isOC = step.shards_per_building > 0;
        let cls = 'flow-node';
        if (isAnchor) cls += ' anchor';
        if (isOC && !isAnchor) cls += ' overclocked';

        html += `<div class="${cls}" data-item="${step.item}" style="${isAnchor ? 'border-color:' + color : ''}">`;
        if (isAnchor) {
          html += `<span class="anchor-label" style="color:${color}">&#9733; Module Anchor</span>`;
        }
        html += `<div class="item-name">${step.item}</div>`;
        html += `<div class="building-info">${step.buildings_ceil}&times; ${step.building}`;
        if (isOC) html += `<span class="shard-badge">&#9889; ${step.shards_per_building}</span>`;
        html += '</div>';
        const outRate = Object.values(step.outputs)[0];
        html += `<div class="output-rate">${outRate.toFixed(1)}/min out</div>`;
        if (isAnchor) {
          html += `<div class="scaling">&times;${mod.copies_needed_ceil} copies &rarr; ${mod.target_hmf} HMF/min</div>`;
        }
        html += '</div>';
      }
    }
    html += '</div>';
  }
  html += '</div>';

  el.innerHTML = html;
}
```

**Step 3: Call renderFlowDiagram from renderFactoriesTab**

In `renderFactoriesTab`, after the `el.innerHTML = html;` line at the end, add:

```javascript
  // Render flow diagrams after DOM is populated
  for (const fid of Object.keys(data.modules)) {
    renderFlowDiagram(fid, data.modules[fid]);
  }
```

**Step 4: Open in browser and verify**

Verify each factory card shows:
- Leftmost column: raw input nodes (dashed border, faded style)
- Middle columns: intermediate items with building counts
- Rightmost column: Manufacturer node with star, "MODULE ANCHOR" label, colored double border, scaling info
- Overclocked nodes have orange border glow and shard badge
- Columns are evenly spaced, nodes vertically centered

**Step 5: Commit**

```bash
git add factory-map.html
git commit -m "feat: render production chain flow diagram nodes in columns"
```

---

### Task 6: Draw SVG Connector Arrows

Add an SVG overlay to each flow diagram that draws arrows between connected nodes.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add CSS for SVG overlay and arrows**

Add to `<style>` block:

```css
.flow-diagram{position:relative}
.flow-svg{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:visible}
.flow-svg line{stroke:#555;stroke-width:1.5}
.flow-svg polygon{fill:#555}
.flow-svg text{fill:#666;font-size:9px;font-family:'Courier New',monospace}
```

**Step 2: Add drawConnectors function**

Add after `renderFlowDiagram`:

```javascript
function drawConnectors(fid, mod) {
  const dag = buildDAG(mod.steps);
  const container = document.getElementById('flow-' + fid);
  const containerRect = container.getBoundingClientRect();

  // Get positions of all nodes by data-item attribute
  const nodeEls = container.querySelectorAll('.flow-node');
  const nodeRects = {};
  for (const el of nodeEls) {
    const item = el.getAttribute('data-item');
    const rect = el.getBoundingClientRect();
    nodeRects[item] = {
      left: rect.left - containerRect.left,
      right: rect.right - containerRect.left,
      top: rect.top - containerRect.top,
      bottom: rect.bottom - containerRect.top,
      cx: (rect.left + rect.right) / 2 - containerRect.left,
      cy: (rect.top + rect.bottom) / 2 - containerRect.top,
    };
  }

  // Create SVG
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.classList.add('flow-svg');
  svg.setAttribute('width', container.scrollWidth);
  svg.setAttribute('height', container.scrollHeight);

  // Arrow marker definition
  const defs = document.createElementNS(svgNS, 'defs');
  const marker = document.createElementNS(svgNS, 'marker');
  marker.setAttribute('id', 'arrow-' + fid);
  marker.setAttribute('viewBox', '0 0 10 10');
  marker.setAttribute('refX', '10');
  marker.setAttribute('refY', '5');
  marker.setAttribute('markerWidth', '6');
  marker.setAttribute('markerHeight', '6');
  marker.setAttribute('orient', 'auto');
  const path = document.createElementNS(svgNS, 'path');
  path.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
  path.setAttribute('fill', '#555');
  marker.appendChild(path);
  defs.appendChild(marker);
  svg.appendChild(defs);

  // Draw edges
  for (const edge of dag.edges) {
    const fromRect = nodeRects[edge.from];
    const toRect = nodeRects[edge.to];
    if (!fromRect || !toRect) continue;

    const x1 = fromRect.right;
    const y1 = fromRect.cy;
    const x2 = toRect.left;
    const y2 = toRect.cy;

    // Draw L-shaped or straight line
    const line = document.createElementNS(svgNS, 'path');
    if (Math.abs(y1 - y2) < 2) {
      // Straight horizontal
      line.setAttribute('d', `M ${x1} ${y1} L ${x2} ${y2}`);
    } else {
      // L-shaped: go right to midpoint, then vertical, then right to target
      const midX = (x1 + x2) / 2;
      line.setAttribute('d', `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`);
    }
    line.setAttribute('fill', 'none');
    line.setAttribute('stroke', '#555');
    line.setAttribute('stroke-width', '1.5');
    line.setAttribute('marker-end', `url(#arrow-${fid})`);
    svg.appendChild(line);
  }

  // Insert SVG at the start of container (behind nodes)
  container.insertBefore(svg, container.firstChild);
}
```

**Step 3: Call drawConnectors after rendering**

In `renderFactoriesTab`, update the post-render loop:

```javascript
  // Render flow diagrams and connectors after DOM is populated
  requestAnimationFrame(() => {
    for (const fid of Object.keys(data.modules)) {
      renderFlowDiagram(fid, data.modules[fid]);
    }
    // Draw connectors after flow nodes are laid out
    requestAnimationFrame(() => {
      for (const fid of Object.keys(data.modules)) {
        drawConnectors(fid, data.modules[fid]);
      }
    });
  });
```

**Step 4: Open in browser and verify**

Verify:
- Arrows connect from right edge of source nodes to left edge of target nodes
- Arrows form L-shaped paths when nodes are at different vertical positions
- Arrowheads point right (toward the target)
- Arrows don't overlap nodes badly
- All 5 factories show connected diagrams

**Step 5: Commit**

```bash
git add factory-map.html
git commit -m "feat: draw SVG connector arrows between flow diagram nodes"
```

---

### Task 7: Add Hover Tooltips for Flow Nodes

Add hover tooltips showing full details for each production step.

**Files:**
- Modify: `factory-map.html`

**Step 1: Add CSS for flow tooltips**

Add to `<style>` block:

```css
.flow-node{cursor:default}
.flow-tooltip{position:absolute;background:rgba(20,20,40,0.97);color:#ddd;padding:10px 14px;border-radius:4px;font-size:11px;font-family:'Courier New',monospace;pointer-events:none;display:none;border:1px solid #555;max-width:300px;z-index:200;white-space:pre-line;line-height:1.5}
```

**Step 2: Add tooltip logic to renderFlowDiagram**

At the end of `renderFlowDiagram`, after setting `el.innerHTML`, add:

```javascript
  // Tooltip setup
  const tooltipEl = document.createElement('div');
  tooltipEl.className = 'flow-tooltip';
  el.appendChild(tooltipEl);

  el.addEventListener('mousemove', (e) => {
    const node = e.target.closest('.flow-node');
    if (!node) { tooltipEl.style.display = 'none'; return; }
    const item = node.getAttribute('data-item');

    if (node.classList.contains('raw-input')) {
      const rawInfo = mod.raw_inputs[item];
      if (!rawInfo) { tooltipEl.style.display = 'none'; return; }
      tooltipEl.innerHTML = `<b>${item}</b> (Raw Input)\n${rawInfo.per_min} ${rawInfo.note}`;
    } else {
      const step = mod.steps.find(s => s.item === item);
      if (!step) { tooltipEl.style.display = 'none'; return; }
      let tt = `<b>${step.item}</b>\n`;
      tt += `Recipe: ${step.recipe}\n`;
      tt += `Building: ${step.building}\n`;
      tt += `Count: ${step.buildings_exact.toFixed(2)} → ${step.buildings_ceil} (ceil)\n`;
      tt += `Clock: ${step.overclock_detail}\n`;
      tt += `Power: ${step.power_mw} MW each\n`;
      if (step.shards_per_building > 0) tt += `Shards: ${step.shards_per_building} per building\n`;
      tt += `\nInputs:`;
      for (const [inp, rate] of Object.entries(step.inputs)) {
        tt += `\n  ${inp}: ${rate.toFixed(2)}/min`;
      }
      tt += `\nOutputs:`;
      for (const [out, rate] of Object.entries(step.outputs)) {
        tt += `\n  ${out}: ${rate.toFixed(2)}/min`;
      }
      tooltipEl.innerHTML = tt;
    }

    const elRect = el.getBoundingClientRect();
    tooltipEl.style.display = 'block';
    tooltipEl.style.left = (e.clientX - elRect.left + 12) + 'px';
    tooltipEl.style.top = (e.clientY - elRect.top + 12) + 'px';
  });

  el.addEventListener('mouseleave', () => { tooltipEl.style.display = 'none'; });
```

**Step 3: Open in browser and verify**

Hover over nodes. Verify tooltips show:
- Raw inputs: name, rate, unit
- Steps: recipe name, building type, exact count, clock detail, power, shards, all I/O rates

**Step 4: Commit**

```bash
git add factory-map.html
git commit -m "feat: add hover tooltips to flow diagram nodes"
```

---

### Task 8: Polish and Final Visual Adjustments

Fix any layout issues, ensure arrow routing works for all 5 factories, and handle edge cases.

**Files:**
- Modify: `factory-map.html`

**Step 1: Handle duplicate items in columns**

Some factories may produce the same intermediate item from multiple steps (e.g., Naphtheon has multiple outputs from Rubber and Plastic refineries that feed later steps). The DAG builder uses `step.item` as the key, but if two steps produce different items that map to the same name, we need to handle it.

Check: In the data, each step has a unique `step.item`. Naphtheon's Rubber and Plastic are separate steps with separate items. The Petroleum Coke → Steel Ingot path is separate from the Plastic path. No duplicates expected, but add a guard:

In `buildDAG`, after the `producerOf` loop, add:

```javascript
  // Handle case where multiple steps produce same item (shouldn't happen but defensive)
  // Already handled since last assignment wins in producerOf
```

Actually, review the data: every step.item is unique within a factory. No changes needed.

**Step 2: Improve column spacing for readability**

Update `.flow-column` CSS to have slightly wider minimum:

```css
.flow-column{display:flex;flex-direction:column;justify-content:center;gap:12px;padding:0 28px;min-width:130px}
```

**Step 3: Add arrow rate labels**

In `drawConnectors`, after drawing each edge line, add a text label:

Update the edge drawing loop. After `svg.appendChild(line);`, add:

```javascript
    // Rate label at midpoint
    const midX = (x1 + x2) / 2;
    const midY = Math.abs(y1 - y2) < 2 ? y1 - 8 : (y1 + y2) / 2 - 8;
    const text = document.createElementNS(svgNS, 'text');
    text.setAttribute('x', midX);
    text.setAttribute('y', midY);
    text.setAttribute('text-anchor', 'middle');
    text.textContent = edge.rate.toFixed(0) + '/m';
    svg.appendChild(text);
```

**Step 4: Open in browser and test all 5 factories**

Verify across all factories:
- Ferrium (9 steps): Clean branching from Iron Ingot to multiple outputs
- Naphtheon (14 steps): Oil chain + iron chain converging. Most complex diagram
- Forgeholm (12 steps): Steel + coal path
- Luxara (15 steps): Aluminum processing path (longest chain)
- Cathera (11 steps): Copper + Caterium merge

Check for:
- No overlapping arrows that make the diagram unreadable
- All arrows connect to correct nodes
- Rate labels readable
- Anchor node clearly stands out in each factory
- Horizontal scroll works if diagram is wider than viewport

**Step 5: Commit**

```bash
git add factory-map.html
git commit -m "feat: polish flow diagrams with rate labels and spacing"
```

---

### Task 9: Final Integration Testing and Commit

End-to-end verification that everything works together.

**Files:**
- Modify: `factory-map.html` (if fixes needed)

**Step 1: Full test pass**

Open `factory-map.html` in browser. Test:

1. **Map tab:** Loads by default, sidebar + canvas work as before, zoom/pan/tooltips work
2. **Tab switching:** Click Factories → shows summary + cards. Click Map → returns to map. Click Factories again → still rendered (no re-fetch).
3. **Summary banner:** Title, shard budget, table with 5 rows + totals. Click row scrolls to card.
4. **Factory nav:** All 5 buttons scroll to correct cards.
5. **Factory headers:** All 5 show correct name, theme, recipe, stats, raw input pills.
6. **Flow diagrams:** All 5 show connected DAG with proper layering, arrows, rate labels.
7. **Module anchors:** Each factory's Manufacturer node is highlighted with star + colored border + scaling info.
8. **Overclocked nodes:** Visible with orange glow + shard badge.
9. **Tooltips:** Hover shows full detail on every node in every factory.
10. **Building summary:** Bottom of each card shows correct building type/count breakdown.
11. **Keyboard shortcuts:** `r`, `e`, `1-5` still work on Map tab.

**Step 2: Fix any issues found**

Address anything broken during testing.

**Step 3: Final commit**

```bash
git add factory-map.html
git commit -m "feat: complete factory details tab with production chain diagrams"
```

---

## Summary of Tasks

| # | Task | Est. Complexity |
|---|------|----------------|
| 1 | Tab bar + content wrappers | Low |
| 2 | Global summary banner | Low |
| 3 | Factory card headers | Low |
| 4 | DAG layout algorithm | Medium |
| 5 | Flow diagram nodes | Medium |
| 6 | SVG connector arrows | Medium |
| 7 | Hover tooltips | Low |
| 8 | Polish + rate labels | Low |
| 9 | Integration testing | Low |
