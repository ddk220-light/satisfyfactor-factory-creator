# Design — SVG resource/product icons + component filter on the factory map

Date: 2026-06-17
Status: design (revised — SVG icons, components + raw resources)

## Goal

On the **Map** tab of `factory-map.html`:
1. Create an SVG icon for every resource in play — both **produced components**
   (what each factory makes) and **raw resources** (what nodes/mining towns
   mine) — and render them on the canvas in place of the current colored dots
   and (previously proposed) letter-badges.
2. Let the user filter the map to a single **component** via a dropdown, so they
   can see exactly which factories produce it.

## Scope

- **Map tab only.** The Factories (Factory Crazy) tab is unchanged.
- Factory layers that get **product (component) icons**:
  - `GAP_FACTORIES` (13) — products from each factory's plan `targets`.
  - `FACTORIES` (5) — the base themed factories; all tagged **Heavy Modular
    Frame** (Option A) so the HMF filter shows the complete picture.
- Node/town layers that get **raw-resource icons** (replace colored dots):
  - `ALL_NODES` (459 background nodes, zoom-gated by `ZOOM_SHOW_BG_NODES`).
  - Factory site/outpost nodes (`drawFactoryNodes`, `drawGapNodes`).
  - Mining-town nodes (`drawTownNodes`, `drawGapTown`).
- Component filter (dropdown) targets **components only**. Raw-resource
  filtering is out of scope.

## Icon set — 24 SVG icons

**11 components:** Aluminum Casing, Cooling System, Steel Beam, Motor, Stator,
Heavy Modular Frame, Smart Plating, Modular Frame, High-Speed Connector,
Copper Powder, Rubber.

**13 raw resources:** iron, limestone, copper, coal, oil, caterium, bauxite,
quartz, sulfur, sam, uranium, nitrogen, water.

`"… (export)"` pseudo-targets (Petroleum Coke export, Rubber export on
naphtheon+) are dropped — surpluses shipped out, not the factory's purpose.

### Per-factory component sources (from `targets`)

| Component | Factories |
|---|---|
| Aluminum Casing | aldercast, bauxhold, silvashade |
| Cooling System | aldercast |
| Steel Beam | moldmarsh, silvashade |
| Motor | voltreach, classic_iron_motor |
| Stator | voltreach, moldmarsh |
| Heavy Modular Frame | ferrium_hmf, naphtheon_hmf, forgeholm_hmf, cathera_hmf + the 5 base FACTORIES |
| Smart Plating | ferrium+ |
| Modular Frame | ferrium+ |
| High-Speed Connector | cathera+ |
| Copper Powder | cathera+ |
| Rubber | naphtheon+ |

## Icon authoring & storage

- Each icon is hand-authored SVG on a consistent **`0 0 24 24` viewBox**, simple
  2-tone recognizable glyphs (e.g. iron = ingot bar, oil = droplet, coal = lump,
  HMF = layered frame, Stator = coil, Rubber = tire). Raw-resource icons use
  their `RESOURCE_COLORS` value as the accent; component icons use a
  `COMPONENT_META` color.
- Stored **inline in `factory-map.html`** as a single JS map
  `const ICON_SVG = { "iron": '<svg …>…</svg>', "Aluminum Casing": '…', … }`
  (keys = resource type strings for raw, full item names for components). Keeps
  the page self-contained, matching the project's single-file convention.
- `COMPONENT_META` maps each component → `{ code, color }` (code retained as the
  alt/tooltip text and as a fallback). Unknown items → neutral fallback icon, so
  the map never breaks if the plan adds a product.
- Handle the `nitrogenGas` ↔ `nitrogen` key mismatch (data uses `nitrogenGas`;
  `RESOURCE_COLORS`/`ICON_SVG` use `nitrogen`) with a small alias lookup.

## Canvas rendering of SVG

Canvas cannot draw raw SVG markup directly, so:

- `getIconImage(name)` lazily builds an `Image` from a
  `data:image/svg+xml;utf8,<encoded svg>` URL, rasterized at a base size
  (e.g. 64px) and cached in a `Map`. On first load it sets `img.onload` to call
  `draw()` once, so icons appear as soon as decoded.
- A draw helper `drawIcon(name, sx, sy, size, alpha)` does
  `ctx.drawImage(img, sx - size/2, sy - size/2, size, size)` when the cached
  image is `complete`; otherwise it falls back to the **current colored dot**
  for that position (graceful, no blank frame).

### Raw-resource nodes (replace dots)

- In `drawFactoryNodes` / `drawGapNodes` / `drawTownNodes` / `drawGapTown` and
  the `ALL_NODES` loop, swap the `ctx.arc` dot for
  `drawIcon(resType, s.x, s.y, baseSize * PURITY_SCALE[p], PURITY_ALPHA[p])`.
- **Purity preserved** exactly as today: size via `PURITY_SCALE`, opacity via
  `PURITY_ALPHA`. Keep the existing thin resource-colored / white outline ring
  behind the icon for node-vs-background legibility.
- All existing **zoom gates unchanged** (`ZOOM_SHOW_BG_NODES`,
  `ZOOM_SHOW_FACTORY_NODES`), so density/perf at low zoom is the same.

### Factory markers (product icons)

- `drawProductIcons(sx, sy, prodList, activeComponent)` draws a centered row of
  component icons just under a factory's primary marker, called from
  `drawGapCenter` (primary site `si === 0`) and `drawFactoryCenter` (the HMF
  icon for base factories). Gated by the same zoom as the factory label.
- When a component filter is active, the matching icon draws full-size/opaque
  with a highlight ring; the factory's other product icons are dimmed.

## Sidebar legend

A two-section legend ("Products" and "Resources"), each row `[inline SVG] Name`,
reusing `ICON_SVG` markup directly via `innerHTML`, so on-canvas icons are
decodable. Replaces/augments the existing color-dot resource legend.

## Filter — dropdown

- `<select id="componentFilter">` in the map controls: `All components`
  (default) + the 11 components (alphabetical; value = item name, `all` default).
- State `let componentFilter = 'all';` → `onchange` updates and calls `draw()`.
- Eligibility: `componentFilter === 'all'` OR the factory's `prod` includes the
  selected component.
- Combined with existing per-factory checkboxes:
  - gap factory drawn iff `gapVisible[id] && eligible(gf)`
  - base factory drawn iff `visible[fid] && eligible(f)`
- While a component is selected, **gap towns and mining towns are hidden** (raw
  suppliers, not component producers); `all` restores them to checkbox state.
- Connecting lines / search radii follow their factory's visibility (existing).

## Data model

- `find_gap_factory_locations.py` (~line 1278): add a `prod` field to the
  `GAP_DATA` record builder:
  `prod = [{"item": k, "amt": v} for k, v in (targets or {}).items()
           if not k.endswith("(export)")]`.
- Regenerate the `GAP_DATA` block **from the committed
  `gap-factory-locations.json`** (load it as `out`, call the existing writer) —
  **no DB run**, placements preserved, only `prod` added. Verify via diff.
- Base factories: a small HTML constant mapping the 5 ids →
  `["Heavy Modular Frame"]`.
- Raw-resource icons need **no data change** — nodes already carry `t`.

## Edge cases

- **Async icons:** dot fallback until each SVG image decodes; one `draw()` on
  load. No blank markers.
- **Fractional amounts:** HMF 16.5/min — icon only; amount available in `prod`
  for a future tooltip.
- **Multi-product factories** (aldercast AC+CS, voltreach MTR+STA, moldmarsh
  SB+STA, silvashade AC+SB, ferrium+ SP+MF): one icon per product in the row.
- **HMF duplication:** relocated `_hmf` gap entries and the 5 base factories both
  carry HMF and both appear under the HMF filter — intended.
- **Key alias:** `nitrogenGas` → `nitrogen` for color/icon lookup.
- **Unknown resource/product:** neutral fallback icon; never throws.

## Files touched

- `find_gap_factory_locations.py` — add `prod` to the `GAP_DATA` record builder.
- `factory-map.html` — `ICON_SVG` (24 inline SVGs), `COMPONENT_META`, base-factory
  HMF tags, regenerated `GAP_DATA` (with `prod`), `getIconImage`/`drawIcon`
  helpers, icon swaps in the four node-draw paths + `ALL_NODES` loop,
  `drawProductIcons` in `drawGapCenter`/`drawFactoryCenter`, legend sections,
  `<select>` + filter state + eligibility checks + town hiding.

## Verification

- `python -c` parse check that regenerated `GAP_DATA` is valid JSON and every
  record has `prod`; diff confirms placements unchanged.
- Serve `python server.py`, open the Map tab; confirm: raw-resource icons render
  on nodes/towns with purity size/alpha intact; product icons render under
  factories; legend decodes both sets; the dropdown isolates each component
  (correct factories shown, towns hidden); `All components` restores everything;
  per-factory checkboxes still combine correctly; zoom in/out behaves.

## Out of scope / future

- Product icons/filter on the Factories (Factory Crazy) tab.
- Filtering the map by **raw resource** (icons only for now).
- Per-product throughput labels on icons (amounts available in `prod` for a
  later hover tooltip).
- Auto-filtering towns to those supplying the visible producing factories (towns
  are simply hidden under an active component filter for now).
