# SVG Resource/Product Icons + Component Filter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the Map tab of `factory-map.html`, render hand-authored SVG icons for all 11 produced components and 13 raw resources (replacing the colored node dots), and add a dropdown that filters the map to a single component.

**Architecture:** Icons are inline SVG strings in the HTML (`ICON_SVG`), rasterized to cached `Image` objects via `data:` URLs and drawn on the existing 2D canvas through a `drawIcon()` helper with a graceful colored-dot fallback. Per-factory products come from each gap factory's plan `targets` (injected into the generated `GAP_DATA` block); the 5 base factories are tagged HMF in the HTML. A `<select>` drives a `componentFilter` state used in the draw loop.

**Tech Stack:** Vanilla JS + HTML5 canvas (no framework, no build step); Python 3 stdlib for the data generator. No JS test framework exists — data tasks verify with `python` assertion scripts; rendering tasks verify by serving `python server.py` and inspecting the Map tab in a browser.

---

## File Structure

- `find_gap_factory_locations.py` — generator; `inject_map(out)` writes the `// <GAP_DATA>` block. **Modify** the record builder to add a `prod` field.
- `factory-map.html` — the served page (hand-maintained source of truth). **Modify**: add `ICON_SVG`, `COMPONENT_META`, `BASE_FACTORY_PROD`, `RES_ALIAS` constants; `getIconImage`/`drawIcon` helpers; icon swaps in 5 node-draw paths; `drawProductIcons` + calls in the two center-draw functions; the `<select>` + filter state + eligibility checks in the draw loop; legend sections.
- `gap-factory-locations.json` — committed plan output; **read-only** source for regenerating `GAP_DATA` (no DB run).

Constants/functions defined here and reused across tasks (names are fixed):
`ICON_SVG` (Task 2), `COMPONENT_META` (Task 2), `BASE_FACTORY_PROD` (Task 2), `RES_ALIAS` (Task 2), `ICON_IMG` cache + `getIconImage(name)` + `drawIcon(name,sx,sy,size,alpha)` (Task 3), `drawProductIcons(sx,sy,prodList,r)` (Task 5), `componentFilter` + `setComponentFilter(v)` + `populateComponentFilter()` + `gapEligible(gf)` + `baseEligible(fid)` + `factoryProducts(prod)` (Task 6).

---

## Task 1: Add `prod` to the GAP_DATA generator and regenerate the block

**Files:**
- Modify: `find_gap_factory_locations.py:1278-1297` (the record dict in `inject_map`)
- Modify (generated): `factory-map.html` (the `// <GAP_DATA>` block, rewritten by running `inject_map`)
- Test: `tmp_verify_prod.py` (temporary, deleted at end of task)

- [ ] **Step 1: Add the `prod` field to the record builder**

In `find_gap_factory_locations.py`, the loop at line 1276 appends a dict per factory. Add one key. Change:

```python
        arr.append({
            'id': fid, 'name': f['factory_name'], 'theme': f['theme'],
            'sig': f['signature_resource'], 'disp': f['disposition'],
```

to:

```python
        arr.append({
            'id': fid, 'name': f['factory_name'], 'theme': f['theme'],
            'sig': f['signature_resource'], 'disp': f['disposition'],
            'prod': [{'item': k, 'amt': v}
                     for k, v in (f.get('targets') or {}).items()
                     if not k.endswith('(export)')],
```

Also make the writer UTF-8 explicit (the HTML is UTF-8; default-encoding `open` corrupts the em-dashes on Windows). In the same function, change:

```python
    html = open(MAP_HTML).read()
```

to:

```python
    html = open(MAP_HTML, encoding='utf-8').read()
```

and change:

```python
    open(MAP_HTML, 'w').write(new)
```

to:

```python
    open(MAP_HTML, 'w', encoding='utf-8').write(new)
```

- [ ] **Step 2: Snapshot the current GAP_DATA block (to prove placements don't change)**

Run:

```bash
python -c "import re; h=open('factory-map.html',encoding='utf-8').read(); m=re.search(r'// <GAP_DATA>.*?// </GAP_DATA>',h,re.S); open('tmp_gapdata_before.txt','w',encoding='utf-8').write(m.group(0))"
```

Expected: creates `tmp_gapdata_before.txt` (no output).

- [ ] **Step 3: Regenerate the block from the committed plan JSON (no DB run)**

`inject_map(out)` reads only `out['factory_locations']` / `out['gap_mining_towns']` and rewrites the block in `factory-map.html`. The committed `gap-factory-locations.json` has exactly those keys, so feed it directly. Run:

`inject_map(out)` returns `(n_factories, n_towns)` (the confirmation line is printed by `main()`, not the function), so print the return value. Run:

```bash
python -c "import json, find_gap_factory_locations as G; print('injected', G.inject_map(json.load(open('gap-factory-locations.json',encoding='utf-8'))))"
```

Expected: `injected (13, 13)`. (Internally it parse-checks both injected literals and raises if the GAP_DATA markers are missing.)

- [ ] **Step 4: Write the verification script**

Create `tmp_verify_prod.py`:

```python
import re, json
html = open('factory-map.html', encoding='utf-8').read()
arr = json.loads(re.search(r'const GAP_FACTORIES\s*=\s*(\[.*?\]);', html, re.S).group(1))
src = json.load(open('gap-factory-locations.json', encoding='utf-8'))['factory_locations']

# Every record has prod
for r in arr:
    assert 'prod' in r, f"{r['id']} missing prod"

# prod matches targets minus exports
for r in arr:
    want = {k: v for k, v in (src[r['id']].get('targets') or {}).items()
            if not k.endswith('(export)')}
    got = {p['item']: p['amt'] for p in r['prod']}
    assert got == want, f"{r['id']}: {got} != {want}"

# No (export) leaked in
for r in arr:
    for p in r['prod']:
        assert not p['item'].endswith('(export)'), f"{r['id']} leaked export {p['item']}"

# Placements unchanged: compare every record minus prod against the snapshot
before = json.loads(re.search(r'const GAP_FACTORIES\s*=\s*(\[.*?\]);',
                              open('tmp_gapdata_before.txt', encoding='utf-8').read(), re.S).group(1))
strip = lambda L: [{k: v for k, v in d.items() if k != 'prod'} for d in L]
assert strip(arr) == before, "non-prod fields changed!"

print("OK: %d factories, all have prod, placements unchanged" % len(arr))
print("distinct products:", sorted({p['item'] for r in arr for p in r['prod']}))
```

- [ ] **Step 5: Run the verification script**

Run: `python tmp_verify_prod.py`
Expected: `OK: 13 factories, all have prod, placements unchanged` then a list of 11 products (Aluminum Casing, Cooling System, Copper Powder, Heavy Modular Frame, High-Speed Connector, Modular Frame, Motor, Rubber, Smart Plating, Stator, Steel Beam).

- [ ] **Step 6: Clean up temp files and commit**

```bash
rm tmp_verify_prod.py tmp_gapdata_before.txt
git add find_gap_factory_locations.py factory-map.html
git commit -m "feat(map): carry per-factory products into GAP_DATA

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Add icon + metadata constants to `factory-map.html`

**Files:**
- Modify: `factory-map.html` — insert constants immediately after the `RESOURCE_COLORS` declaration (ends with `};` around line 360, just before `const FACTORIES`).

- [ ] **Step 1: Insert the constants block**

Find this line (the close of `RESOURCE_COLORS`):

```javascript
  water:'#4fc3f7'
};
```

Immediately after it, insert:

```javascript

// === ICONS: 13 raw resources + 11 produced components (viewBox 0 0 24 24) ===
const ICON_SVG = {
  iron:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polygon points="3,15 21,15 18,9 6,9" fill="#e74c3c" stroke="#1a1a2e" stroke-width="1"/></svg>',
  copper:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polygon points="2,16 14,16 12,11 4,11" fill="#e67e22" stroke="#1a1a2e" stroke-width="1"/><polygon points="10,13 22,13 20,8 12,8" fill="#e67e22" stroke="#1a1a2e" stroke-width="1"/></svg>',
  coal:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polygon points="6,17 3,11 8,6 16,7 21,13 16,18" fill="#555" stroke="#1a1a2e" stroke-width="1"/></svg>',
  limestone:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="13" width="8" height="6" fill="#95a5a6" stroke="#1a1a2e"/><rect x="13" y="13" width="8" height="6" fill="#95a5a6" stroke="#1a1a2e"/><rect x="8" y="6" width="8" height="6" fill="#95a5a6" stroke="#1a1a2e"/></svg>',
  oil:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 3 C12 3 5 12 5 16 a7 7 0 0 0 14 0 C19 12 12 3 12 3 Z" fill="#9b59b6"/></svg>',
  caterium:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polygon points="12,3 20,9 12,21 4,9" fill="#f1c40f" stroke="#1a1a2e"/></svg>',
  bauxite:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="9" cy="12" r="5" fill="#e91e63" stroke="#1a1a2e"/><circle cx="16" cy="14" r="4" fill="#e91e63" stroke="#1a1a2e"/></svg>',
  quartz:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polygon points="12,2 16,9 14,22 10,22 8,9" fill="#00bcd4" stroke="#1a1a2e"/></svg>',
  sulfur:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><polygon points="12,4 21,19 3,19" fill="#cddc39" stroke="#1a1a2e"/></svg>',
  sam:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2 L14 10 L22 12 L14 14 L12 22 L10 14 L2 12 L10 10 Z" fill="#2196f3"/></svg>',
  uranium:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9" fill="#4caf50" stroke="#1a1a2e"/><circle cx="12" cy="12" r="2.5" fill="#1a1a2e"/><circle cx="12" cy="5.5" r="1.5" fill="#1a1a2e"/><circle cx="6.4" cy="15" r="1.5" fill="#1a1a2e"/><circle cx="17.6" cy="15" r="1.5" fill="#1a1a2e"/></svg>',
  nitrogen:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="9" cy="13" r="5" fill="#80deea" stroke="#1a1a2e"/><circle cx="16" cy="10" r="4" fill="#80deea" stroke="#1a1a2e"/></svg>',
  water:'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 3 C12 3 5 12 5 16 a7 7 0 0 0 14 0 C19 12 12 3 12 3 Z" fill="#4fc3f7"/></svg>',
  'Aluminum Casing':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="6" y="7" width="13" height="10" rx="1.5" fill="#8fd3f4" stroke="#1a1a2e"/><ellipse cx="6" cy="12" rx="2.5" ry="5" fill="#5fa8d8" stroke="#1a1a2e"/></svg>',
  'Cooling System':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><g stroke="#4dd0e1" stroke-width="2"><line x1="12" y1="3" x2="12" y2="21"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/><line x1="18.5" y1="5.5" x2="5.5" y2="18.5"/></g><circle cx="12" cy="12" r="2" fill="#4dd0e1"/></svg>',
  'Steel Beam':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 5 H19 V8 H14 V16 H19 V19 H5 V16 H10 V8 H5 Z" fill="#b0bec5" stroke="#1a1a2e"/></svg>',
  'Motor':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><g fill="#ff8a65" stroke="#1a1a2e"><rect x="10.5" y="2" width="3" height="4"/><rect x="10.5" y="18" width="3" height="4"/><rect x="2" y="10.5" width="4" height="3"/><rect x="18" y="10.5" width="4" height="3"/></g><circle cx="12" cy="12" r="6" fill="#ff8a65" stroke="#1a1a2e"/><circle cx="12" cy="12" r="2" fill="#1a1a2e"/></svg>',
  'Stator':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="5" width="14" height="14" rx="3" fill="none" stroke="#ffd54f" stroke-width="2"/><line x1="9" y1="7" x2="9" y2="17" stroke="#ffd54f" stroke-width="2"/><line x1="12" y1="7" x2="12" y2="17" stroke="#ffd54f" stroke-width="2"/><line x1="15" y1="7" x2="15" y2="17" stroke="#ffd54f" stroke-width="2"/></svg>',
  'Heavy Modular Frame':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" fill="none" stroke="#ba68c8" stroke-width="2"/><rect x="8" y="8" width="8" height="8" fill="none" stroke="#ba68c8" stroke-width="2"/></svg>',
  'Smart Plating':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="4" y="4" width="16" height="16" rx="2" fill="#81c784" stroke="#1a1a2e"/><circle cx="12" cy="12" r="3.5" fill="#fff"/></svg>',
  'Modular Frame':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="4" y="4" width="16" height="16" fill="none" stroke="#aed581" stroke-width="2"/><line x1="4" y1="12" x2="20" y2="12" stroke="#aed581" stroke-width="2"/><line x1="12" y1="4" x2="12" y2="20" stroke="#aed581" stroke-width="2"/></svg>',
  'High-Speed Connector':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="8" width="10" height="8" rx="1" fill="#f06292" stroke="#1a1a2e"/><line x1="15" y1="10.5" x2="20" y2="10.5" stroke="#f06292" stroke-width="2"/><line x1="15" y1="13.5" x2="20" y2="13.5" stroke="#f06292" stroke-width="2"/></svg>',
  'Copper Powder':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><g fill="#d4915d"><circle cx="8" cy="9" r="2"/><circle cx="14" cy="8" r="2"/><circle cx="11" cy="13" r="2"/><circle cx="16" cy="14" r="2"/><circle cx="9" cy="16" r="2"/></g></svg>',
  'Rubber':'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9" fill="#9e9e9e" stroke="#1a1a2e"/><circle cx="12" cy="12" r="4" fill="#1a1a2e"/></svg>'
};
// Component -> short code (fallback badge text) + accent color (highlight ring)
const COMPONENT_META = {
  'Aluminum Casing':      { code:'AC',  color:'#8fd3f4' },
  'Cooling System':       { code:'CS',  color:'#4dd0e1' },
  'Steel Beam':           { code:'SB',  color:'#b0bec5' },
  'Motor':                { code:'MTR', color:'#ff8a65' },
  'Stator':               { code:'STA', color:'#ffd54f' },
  'Heavy Modular Frame':  { code:'HMF', color:'#ba68c8' },
  'Smart Plating':        { code:'SP',  color:'#81c784' },
  'Modular Frame':        { code:'MF',  color:'#aed581' },
  'High-Speed Connector': { code:'HSC', color:'#f06292' },
  'Copper Powder':        { code:'CuP', color:'#d4915d' },
  'Rubber':               { code:'RUB', color:'#9e9e9e' }
};
// The 5 base themed factories are all HMF producers (Option A)
const BASE_FACTORY_PROD = {
  ferrium:['Heavy Modular Frame'], naphtheon:['Heavy Modular Frame'],
  forgeholm:['Heavy Modular Frame'], luxara:['Heavy Modular Frame'],
  cathera:['Heavy Modular Frame']
};
// Node data uses 'nitrogenGas'; icons/colors key on 'nitrogen'
const RES_ALIAS = { nitrogenGas:'nitrogen' };
```

- [ ] **Step 2: Verify the constants parse and are complete**

Run:

```bash
python -c "
import re, json
h=open('factory-map.html',encoding='utf-8').read()
svg=re.search(r'const ICON_SVG\s*=\s*(\{.*?\});',h,re.S).group(1)
keys=re.findall(r'(?:\'([^\']+)\'|(\w+)):\s*\'<svg',svg)
keys=[a or b for a,b in keys]
raw=['iron','limestone','copper','coal','oil','caterium','bauxite','quartz','sulfur','sam','uranium','nitrogen','water']
comp=['Aluminum Casing','Cooling System','Steel Beam','Motor','Stator','Heavy Modular Frame','Smart Plating','Modular Frame','High-Speed Connector','Copper Powder','Rubber']
miss=[k for k in raw+comp if k not in keys]
assert not miss, 'missing icons: '+str(miss)
assert all('viewBox=\"0 0 24 24\"' in h for _ in [0])
assert h.count('const COMPONENT_META') == 1 and h.count('const BASE_FACTORY_PROD') == 1
print('OK: %d icons (%d raw + %d components)' % (len(keys), len(raw), len(comp)))
"
```

Expected: `OK: 24 icons (13 raw + 11 components)`

- [ ] **Step 3: Commit**

```bash
git add factory-map.html
git commit -m "feat(map): add ICON_SVG, COMPONENT_META, base-factory HMF tags

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Add the icon cache + canvas draw helpers

**Files:**
- Modify: `factory-map.html` — add helpers just before `// === DRAWING ===` (before `function draw()`, ~line 451); add a preload line in `init()` (~line 1302).

- [ ] **Step 1: Add the cache + helpers**

Immediately before the `// === DRAWING ===` comment (line 451), insert:

```javascript
// === ICON RASTER CACHE ===
const ICON_IMG = new Map();   // key -> HTMLImageElement | null
function getIconImage(name) {
  const key = RES_ALIAS[name] || name;
  if (ICON_IMG.has(key)) return ICON_IMG.get(key);
  const svg = ICON_SVG[key];
  if (!svg) { ICON_IMG.set(key, null); return null; }
  const img = new Image();
  img.onload = () => { draw(); };           // repaint once this icon is ready
  img.src = 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
  ICON_IMG.set(key, img);
  return img;
}
// Draw an icon centered at (sx,sy). Returns false if not ready (caller draws fallback).
function drawIcon(name, sx, sy, size, alpha) {
  const img = getIconImage(name);
  if (img && img.complete && img.naturalWidth) {
    ctx.globalAlpha = (alpha == null) ? 1 : alpha;
    ctx.drawImage(img, sx - size / 2, sy - size / 2, size, size);
    ctx.globalAlpha = 1;
    return true;
  }
  return false;
}
```

- [ ] **Step 2: Preload all icons in `init()`**

In `init()` (line 1302), change:

```javascript
function init() {
  resize();
  fitZoom();
  buildLegend();
```

to:

```javascript
function init() {
  resize();
  fitZoom();
  for (const k of Object.keys(ICON_SVG)) getIconImage(k);  // warm the cache
  buildLegend();
```

- [ ] **Step 3: Verify the page loads with no console errors**

Run: `python server.py` (serves http://localhost:8080), open the Map tab in a browser, open DevTools console.
Expected: no errors; `Object.keys(ICON_IMG).length`-style check — paste in console: `ICON_IMG.size` → `24`, and `drawIcon('iron',100,100,20)` returns `true` (an icon is drawn at 100,100). Nothing visually changes yet (helpers not wired into node drawing).

- [ ] **Step 4: Commit**

```bash
git add factory-map.html
git commit -m "feat(map): icon raster cache + drawIcon canvas helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Replace node dots with raw-resource icons

**Files:**
- Modify: `factory-map.html` — `drawBackgroundNodes` (~548), `drawFactoryNodes` (~591), `drawTownNodes` (~785), `drawGapNodes` (~662), `drawGapTown` node loop (~727).

- [ ] **Step 1: `drawBackgroundNodes` — icon with faint fallback dot**

Replace the body of the `for (const n of ALL_NODES)` loop. Change:

```javascript
    const s = g2s(n.x, n.y);
    const r = 2 * PURITY_SCALE[n.p];
    ctx.globalAlpha = 0.15 * PURITY_ALPHA[n.p];
    ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
    ctx.beginPath();
    ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
    ctx.fill();
```

to:

```javascript
    const s = g2s(n.x, n.y);
    if (!drawIcon(n.t, s.x, s.y, 6 * PURITY_SCALE[n.p], 0.4 * PURITY_ALPHA[n.p])) {
      ctx.globalAlpha = 0.15 * PURITY_ALPHA[n.p];
      ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
      ctx.beginPath();
      ctx.arc(s.x, s.y, 2 * PURITY_SCALE[n.p], 0, Math.PI * 2);
      ctx.fill();
    }
```

- [ ] **Step 2: `drawFactoryNodes` — ring + icon, dot fallback**

In `drawFactoryNodes`, replace the "Filled dot in resource color" + "Ring in factory color" blocks (lines 597-610), i.e. change:

```javascript
    // Filled dot in resource color
    ctx.globalAlpha = PURITY_ALPHA[n.p];
    ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2);
    ctx.fill();

    // Ring in factory color
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR + 1.5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
```

to:

```javascript
    // Ring in factory color
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR + 2, 0, Math.PI * 2);
    ctx.stroke();

    // Resource icon (dot fallback until loaded)
    if (!drawIcon(n.t, s.x, s.y, baseR * 2.6, PURITY_ALPHA[n.p])) {
      ctx.globalAlpha = PURITY_ALPHA[n.p];
      ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
      ctx.beginPath();
      ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
```

(The purity/type label block below stays unchanged.)

- [ ] **Step 3: `drawTownNodes` — same treatment with town-color ring**

Replace lines 789-799. Change:

```javascript
    ctx.globalAlpha = PURITY_ALPHA[n.p];
    ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = mt.color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR + 1.5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
```

to:

```javascript
    ctx.strokeStyle = mt.color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(s.x, s.y, baseR + 2, 0, Math.PI * 2);
    ctx.stroke();
    if (!drawIcon(n.t, s.x, s.y, baseR * 2.6, PURITY_ALPHA[n.p])) {
      ctx.globalAlpha = PURITY_ALPHA[n.p];
      ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
      ctx.beginPath();
      ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
```

- [ ] **Step 4: `drawGapNodes` — replace site-node fill, keep dashed satellite outline; iconize outposts**

Replace the entire `drawGapNodes` function (lines 662-694) with:

```javascript
function drawGapNodes(gf) {
  const color = GAP_COLORS[gf.disp] || '#2ecc71';
  (gf.sites || []).forEach((site, si) => {
    for (const n of (site.nodes || [])) {
      const s = g2s(n.x, n.y);
      const baseR = 4 * (PURITY_SCALE[n.p] || 1);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash(si === 0 ? [] : [3, 2]);   // satellites dashed
      ctx.beginPath(); ctx.arc(s.x, s.y, baseR + 2, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      if (!drawIcon(n.t, s.x, s.y, baseR * 2.6, PURITY_ALPHA[n.p] || 0.7)) {
        ctx.globalAlpha = PURITY_ALPHA[n.p] || 0.7;
        ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
        ctx.beginPath(); ctx.arc(s.x, s.y, baseR, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
      }
    }
  });
  // outposts: resource icon with gap-colored outline (was small diamonds)
  for (const o of (gf.outposts || [])) {
    for (const n of (o.nodes || [])) {
      const s = g2s(n.x, n.y);
      const r = 3.5 * (PURITY_SCALE[n.p] || 1);
      ctx.strokeStyle = color; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(s.x, s.y, r + 2, 0, Math.PI * 2); ctx.stroke();
      if (!drawIcon(n.t, s.x, s.y, r * 2.4, 0.7)) {
        ctx.globalAlpha = 0.6;
        ctx.fillStyle = RESOURCE_COLORS[n.t] || '#666';
        ctx.beginPath();
        ctx.moveTo(s.x, s.y - r); ctx.lineTo(s.x + r, s.y);
        ctx.lineTo(s.x, s.y + r); ctx.lineTo(s.x - r, s.y);
        ctx.closePath(); ctx.fill();
        ctx.globalAlpha = 1;
      }
    }
  }
}
```

- [ ] **Step 5: `drawGapTown` — iconize the mining-style nodes**

In `drawGapTown`, replace the node loop body (lines 729-737). Change:

```javascript
      const s = g2s(n.x, n.y);
      const r = 4 * (PURITY_SCALE[n.p] || 1);
      ctx.globalAlpha = PURITY_ALPHA[n.p] || 0.7;
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(s.x, s.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(s.x, s.y, r + 1, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
```

to:

```javascript
      const s = g2s(n.x, n.y);
      const r = 4 * (PURITY_SCALE[n.p] || 1);
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(s.x, s.y, r + 2, 0, Math.PI * 2); ctx.stroke();
      if (!drawIcon(n.t || gt.r, s.x, s.y, r * 2.6, PURITY_ALPHA[n.p] || 0.7)) {
        ctx.globalAlpha = PURITY_ALPHA[n.p] || 0.7;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(s.x, s.y, r, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
      }
```

(Note: gap-town node objects may not carry `t`; `gt.r` is the town's resource type, used as a fallback so the icon still resolves.)

- [ ] **Step 6: Verify in the browser**

Run: `python server.py`, open the Map tab, zoom in past the node threshold.
Expected: resource nodes now show SVG glyphs (iron bar, oil droplet, etc.) instead of flat dots; purer nodes render larger / more opaque; rings (factory/town color) still surround them; no console errors. Zoom out — nodes disappear at the same thresholds as before.

- [ ] **Step 7: Commit**

```bash
git add factory-map.html
git commit -m "feat(map): render raw-resource SVG icons on all node layers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Draw product icons under factory markers

**Files:**
- Modify: `factory-map.html` — add `drawProductIcons` after `drawGapTown` (~757); call it from `drawGapCenter` (~710 block) and `drawFactoryCenter` (~658).

- [ ] **Step 1: Add `drawProductIcons`**

After the `drawGapTown` function (line 757), insert:

```javascript
// Row of component icons under a factory marker. prodList items: string | {item,amt}.
function drawProductIcons(sx, sy, prodList, r) {
  if (!prodList || !prodList.length) return;
  const size = Math.max(13, Math.min(26, Math.round(15 * Math.sqrt(zoom / 0.001))));
  const step = size + 3;
  const totalW = prodList.length * step - 3;
  let x = sx - totalW / 2 + size / 2;
  const y = sy + r + 10 + size / 2;
  const active = componentFilter !== 'all';
  for (const p of prodList) {
    const item = (typeof p === 'string') ? p : p.item;
    const isMatch = item === componentFilter;
    const a = (!active || isMatch) ? 1 : 0.25;
    if (active && isMatch) {
      ctx.strokeStyle = (COMPONENT_META[item] && COMPONENT_META[item].color) || '#fff';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, size / 2 + 3, 0, Math.PI * 2); ctx.stroke();
    }
    if (!drawIcon(item, x, y, size, a)) {
      const meta = COMPONENT_META[item] || { code: item.slice(0, 3).toUpperCase(), color: '#888' };
      ctx.globalAlpha = a;
      ctx.fillStyle = meta.color;
      ctx.fillRect(x - size / 2, y - size / 2, size, size);
      ctx.fillStyle = '#1a1a2e';
      ctx.font = `bold ${Math.round(size * 0.4)}px Courier New`;
      ctx.textAlign = 'center';
      ctx.fillText(meta.code, x, y + size * 0.15);
      ctx.textAlign = 'left';
      ctx.globalAlpha = 1;
    }
    x += step;
  }
}
```

- [ ] **Step 2: Call from `drawGapCenter` (primary site only)**

In `drawGapCenter`, inside the `if (si === 0) { ... }` block, after the existing label lines and before `ctx.textAlign = 'left';`, add the call. Change:

```javascript
      ctx.fillStyle = gf.infeasible ? '#ff6b6b' : '#fff';
      ctx.fillText(tag, s.x, s.y - r - 8);
      ctx.textAlign = 'left';
```

to:

```javascript
      ctx.fillStyle = gf.infeasible ? '#ff6b6b' : '#fff';
      ctx.fillText(tag, s.x, s.y - r - 8);
      ctx.textAlign = 'left';
      drawProductIcons(s.x, s.y, gf.prod, r);
```

- [ ] **Step 3: Call from `drawFactoryCenter` (base factories → HMF)**

At the end of `drawFactoryCenter`, change:

```javascript
  ctx.fillStyle = '#fff';
  ctx.fillText(f.name, s.x, s.y - r - 8);
  ctx.textAlign = 'left';
}
```

to:

```javascript
  ctx.fillStyle = '#fff';
  ctx.fillText(f.name, s.x, s.y - r - 8);
  ctx.textAlign = 'left';
  drawProductIcons(s.x, s.y, BASE_FACTORY_PROD[fid], r);
}
```

- [ ] **Step 4: Verify in the browser**

Run: `python server.py`, open the Map tab.
Expected: a row of component icons sits under each factory marker — e.g. Aldercast shows Aluminum Casing + Cooling System; Moldmarsh shows Steel Beam + Stator; the 5 base factories (Ferrium, Naphtheon, Forgeholm, Luxara, Cathera) each show the HMF icon. No console errors. (Filtering not wired yet — `componentFilter` is still undefined here; **Step 5 guards against that.**)

- [ ] **Step 5: Guard `componentFilter` before Task 6 defines it**

`drawProductIcons` references `componentFilter`, which is declared in Task 6. To keep this task runnable on its own, add the declaration now at the top of the drawing section — immediately after the `ICON_IMG` cache block from Task 3 insert:

```javascript
let componentFilter = 'all';
```

(Task 6 will reuse this same variable; do not redeclare it there.)

- [ ] **Step 6: Commit**

```bash
git add factory-map.html
git commit -m "feat(map): product icons under factory markers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Component dropdown filter

**Files:**
- Modify: `factory-map.html` — `<select>` in `#controls` (~143); filter helpers (after the `componentFilter` declaration from Task 5); draw-loop eligibility (`draw`, ~464-514); `populateComponentFilter()` call in `init` (~1302).

- [ ] **Step 1: Add the `<select>` to the controls**

Change:

```html
      <div id="controls">
        <button id="export-btn">EXPORT SELECTIONS</button>
        <button id="reset-btn">Reset View</button>
      </div>
```

to:

```html
      <div id="controls">
        <label style="display:block;font-size:11px;color:#ccc;margin-bottom:6px">Filter to component:
          <select id="componentFilter" onchange="setComponentFilter(this.value)" style="width:100%;margin-top:3px;background:#16213e;color:#fff;border:1px solid #333;padding:4px;font-family:'Courier New',monospace;font-size:11px">
            <option value="all">All components</option>
          </select>
        </label>
        <button id="export-btn">EXPORT SELECTIONS</button>
        <button id="reset-btn">Reset View</button>
      </div>
```

- [ ] **Step 2: Add filter helpers**

After the `let componentFilter = 'all';` line (added in Task 5 Step 5), insert:

```javascript
function setComponentFilter(v) { componentFilter = v; draw(); }
function populateComponentFilter() {
  const sel = document.getElementById('componentFilter');
  if (!sel) return;
  for (const name of Object.keys(COMPONENT_META).sort()) {
    const o = document.createElement('option');
    o.value = name; o.textContent = name;
    sel.appendChild(o);
  }
}
function factoryProducts(prod) {
  return (prod || []).map(p => (typeof p === 'string') ? p : p.item);
}
function gapEligible(gf) {
  return componentFilter === 'all' || factoryProducts(gf.prod).includes(componentFilter);
}
function baseEligible(fid) {
  return componentFilter === 'all' || (BASE_FACTORY_PROD[fid] || []).includes(componentFilter);
}
```

- [ ] **Step 3: Apply eligibility + town hiding in the draw loop**

In `draw()`, make these changes. First, the base-factory node loop — change:

```javascript
  const fids = Object.keys(FACTORIES);
  for (const fid of fids) {
    if (!visible[fid]) continue;
    const f = FACTORIES[fid];

    if (zoom > ZOOM_SHOW_RADIUS) drawSearchRadius(fid, f);
```

to:

```javascript
  const filterActive = componentFilter !== 'all';
  const fids = Object.keys(FACTORIES);
  for (const fid of fids) {
    if (!visible[fid] || !baseEligible(fid)) continue;
    const f = FACTORIES[fid];

    if (zoom > ZOOM_SHOW_RADIUS) drawSearchRadius(fid, f);
```

The mining-town node loop — change:

```javascript
  // Mining towns
  for (const mt of MINING_TOWNS) {
    if (!townVisible[mt.id]) continue;
```

to:

```javascript
  // Mining towns (hidden while a component filter is active)
  for (const mt of MINING_TOWNS) {
    if (filterActive || !townVisible[mt.id]) continue;
```

The gap-factory node loop — change:

```javascript
  // Gap supply-chain factories
  for (const gf of GAP_FACTORIES) {
    if (!gapVisible[gf.id]) continue;
    if (zoom > ZOOM_SHOW_FACTORY_NODES) drawGapNodes(gf);
  }
```

to:

```javascript
  // Gap supply-chain factories
  for (const gf of GAP_FACTORIES) {
    if (!gapVisible[gf.id] || !gapEligible(gf)) continue;
    if (zoom > ZOOM_SHOW_FACTORY_NODES) drawGapNodes(gf);
  }
```

The base-factory center loop — change:

```javascript
  // Factory centers always on top
  for (const fid of fids) {
    if (!visible[fid]) continue;
    const f = FACTORIES[fid];
    drawFactoryCenter(fid, f);
  }
```

to:

```javascript
  // Factory centers always on top
  for (const fid of fids) {
    if (!visible[fid] || !baseEligible(fid)) continue;
    const f = FACTORIES[fid];
    drawFactoryCenter(fid, f);
  }
```

The mining-town center loop — change:

```javascript
  // Mining town centers on top
  for (const mt of MINING_TOWNS) {
    if (!townVisible[mt.id]) continue;
    drawTownCenter(mt);
  }
```

to:

```javascript
  // Mining town centers on top
  for (const mt of MINING_TOWNS) {
    if (filterActive || !townVisible[mt.id]) continue;
    drawTownCenter(mt);
  }
```

The gap-factory center loop — change:

```javascript
  // Gap factory centers on top
  for (const gf of GAP_FACTORIES) {
    if (!gapVisible[gf.id]) continue;
    drawGapCenter(gf);
  }
```

to:

```javascript
  // Gap factory centers on top
  for (const gf of GAP_FACTORIES) {
    if (!gapVisible[gf.id] || !gapEligible(gf)) continue;
    drawGapCenter(gf);
  }
```

The gap-town loop — change:

```javascript
  // Gap mining towns (diamonds in resource color)
  if (typeof GAP_TOWNS !== 'undefined') {
    for (const gt of GAP_TOWNS) {
      if (!gapTownVisible[gt.id]) continue;
      drawGapTown(gt);
    }
  }
```

to:

```javascript
  // Gap mining towns (hidden while a component filter is active)
  if (typeof GAP_TOWNS !== 'undefined' && !filterActive) {
    for (const gt of GAP_TOWNS) {
      if (!gapTownVisible[gt.id]) continue;
      drawGapTown(gt);
    }
  }
```

- [ ] **Step 4: Populate the dropdown in `init`**

In `init()`, change:

```javascript
  for (const k of Object.keys(ICON_SVG)) getIconImage(k);  // warm the cache
  buildLegend();
```

to:

```javascript
  for (const k of Object.keys(ICON_SVG)) getIconImage(k);  // warm the cache
  populateComponentFilter();
  buildLegend();
```

- [ ] **Step 5: Verify in the browser**

Run: `python server.py`, open the Map tab.
Expected: the sidebar shows a "Filter to component" dropdown with `All components` + 11 components (alphabetical). Selecting **Aluminum Casing** leaves only Aldercast, Bauxhold, Silvashade visible (towns hidden); the AC icon under each is ringed/highlighted and their other icons dimmed. Selecting **Heavy Modular Frame** shows the 4 `_hmf` gap factories **and** the 5 base factories. `All components` restores everything including towns. Unchecking a factory in the list still hides it within the current filter.

- [ ] **Step 6: Commit**

```bash
git add factory-map.html
git commit -m "feat(map): component dropdown filter with town hiding

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Legend sections with SVG icons

**Files:**
- Modify: `factory-map.html` — add a CSS rule (~line 12 in `<style>`); rewrite the resource section of `buildLegend` (~861-865) and add a Products section.

- [ ] **Step 1: Add a CSS rule for inline legend SVGs**

In the `<style>` block (near the top, after the `#legend .row` rule around line 12), add:

```css
#legend .ic{display:inline-flex;width:15px;height:15px;margin-right:6px;vertical-align:middle}
#legend .ic svg{width:15px;height:15px}
```

- [ ] **Step 2: Rewrite the Resource Types section and add Products**

In `buildLegend`, change:

```javascript
  let html = '<div style="font-weight:bold;margin-bottom:4px;color:#fff;font-size:12px">Resource Types</div>';
  const types = ['iron','limestone','copper','coal','oil','caterium','bauxite','quartz','sulfur','sam','uranium'];
  for (const t of types) {
    html += `<div class="row"><span class="dot" style="background:${RESOURCE_COLORS[t]}"></span>${t}</div>`;
  }
```

to:

```javascript
  let html = '<div style="font-weight:bold;margin-bottom:4px;color:#fff;font-size:12px">Products</div>';
  for (const name of Object.keys(COMPONENT_META).sort()) {
    html += `<div class="row"><span class="ic">${ICON_SVG[name] || ''}</span>${name}</div>`;
  }
  html += '<div style="margin-top:6px;font-weight:bold;color:#fff;font-size:12px">Resource Types</div>';
  const types = ['iron','limestone','copper','coal','oil','caterium','bauxite','quartz','sulfur','sam','uranium','nitrogen','water'];
  for (const t of types) {
    html += `<div class="row"><span class="ic">${ICON_SVG[t] || ''}</span>${t}</div>`;
  }
```

- [ ] **Step 3: Verify in the browser**

Run: `python server.py`, open the Map tab.
Expected: the legend now has a "Products" section (11 component icons + names) and a "Resource Types" section showing the SVG glyphs (13 incl. nitrogen, water) instead of flat color dots. Icons in the legend visually match those drawn on the canvas.

- [ ] **Step 4: Commit**

```bash
git add factory-map.html
git commit -m "feat(map): legend shows SVG icons + Products section

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Full regression pass**

Run: `python server.py`, open the Map tab and exercise:
1. Zoom in/out across `ZOOM_SHOW_BG_NODES` and `ZOOM_SHOW_FACTORY_NODES` — icons appear/disappear at the same thresholds as the old dots; no flicker beyond first-load pop.
2. Each dropdown value isolates the correct factories (cross-check against the spec's component→factory table); towns hide under any non-"All" filter; "All components" restores everything.
3. Per-factory checkboxes still toggle visibility within the active filter.
4. The Factories (crazy) tab is unchanged.
5. Browser console: no errors.

- [ ] **Confirm clean git state**

Run: `git status`
Expected: clean (all 7 task commits present; no stray temp files).

---

## Spec coverage notes

- SVG icons for 11 components + 13 raw resources — Task 2 (authoring), Tasks 4/5/7 (rendering).
- Replace node/town dots with raw-resource icons — Task 4 (all 5 node paths).
- Product icons on factory markers (gap + base/HMF) — Task 5.
- `prod` data into `GAP_DATA` without DB run; placements preserved — Task 1.
- Component dropdown filter; combine with checkboxes; hide towns under filter — Task 6.
- Legend with both sets as SVG — Task 7.
- Async load fallback, purity (size+alpha), zoom gates, `nitrogenGas` alias, unknown-item fallback — Tasks 3/4/5.
- Out of scope (unchanged): Factories tab, raw-resource filtering, throughput labels, town auto-filtering.
