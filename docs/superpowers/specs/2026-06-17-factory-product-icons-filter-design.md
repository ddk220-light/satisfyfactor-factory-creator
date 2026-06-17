# Design — Product icons + component filter on the factory map

Date: 2026-06-17
Status: approved (design)

## Goal

On the **Map** tab of `factory-map.html`, show which production component(s) each
factory makes (as small colored letter-badges), and let the user filter the map
to a single component via a dropdown, so they can see exactly which factories
produce that component.

## Scope

- **Map tab only.** The Factories (Factory Crazy) tab is unchanged.
- Applies to two factory layers already drawn on the map:
  - `GAP_FACTORIES` (13) — the gap supply-chain plan; each has explicit product
    `targets` in `gap-factory-locations.json`.
  - `FACTORIES` (5) — the original themed factories (Ferrium, Naphtheon,
    Forgeholm, Luxara, Cathera). All are **Heavy Modular Frame** producers
    (Option A, user-chosen) and are tagged as such so the HMF filter shows the
    complete picture.
- Gap mining **towns** (`GAP_TOWNS`, `MINING_TOWNS`) produce raw resources, not
  components — they are **not** badged and are hidden while a component filter
  is active.

## The 11 components

Distinct, non-export products across the gap plan:

| Component | Code | Source |
|---|---|---|
| Aluminum Casing | AC | aldercast, bauxhold, silvashade |
| Cooling System | CS | aldercast |
| Steel Beam | SB | moldmarsh, silvashade |
| Motor | MTR | voltreach, classic_iron_motor |
| Stator | STA | voltreach, moldmarsh |
| Heavy Modular Frame | HMF | ferrium_hmf, naphtheon_hmf, forgeholm_hmf, cathera_hmf + the 5 base FACTORIES |
| Smart Plating | SP | ferrium+ |
| Modular Frame | MF | ferrium+ |
| High-Speed Connector | HSC | cathera+ |
| Copper Powder | CuP | cathera+ |
| Rubber | RUB | naphtheon+ |

`"… (export)"` pseudo-targets (Petroleum Coke export, Rubber export on
naphtheon+) are **dropped** — they are surpluses shipped out, not the factory's
production purpose.

## Data model

### 1. Carry products into `GAP_DATA`

Each gap factory's products live in `gap-factory-locations.json` as
`targets` (e.g. moldmarsh → `{"Steel Beam": 400, "Stator": 159}`) but are not
copied into the map's `GAP_DATA` block.

- Add a `prod` field to the record builder in
  `find_gap_factory_locations.py` (~line 1278): for each factory,
  `prod = [{"item": k, "amt": v} for k, v in (targets or {}).items()
           if not k.endswith("(export)")]`.
- **Regenerate the block from the committed plan, not the DB.** Write a small
  one-off (or reuse the existing writer) that loads `gap-factory-locations.json`
  as `out` and invokes the same `GAP_DATA` writer function. The committed JSON
  already has every key the writer reads (`factory_locations`,
  `gap_mining_towns`, `building_totals`, `sites[].center/nodes`, etc.), so the
  placements are preserved and only the `prod` field is added. **No DB run.**
- Verify: a diff of the regenerated `GAP_DATA` vs the current one shows only the
  added `prod` keys (factory ids, coordinates, node counts, towns unchanged).

### 2. Tag the original 5 factories as HMF

`FACTORIES` records have no product data. Add a constant in the HTML that maps
each of the 5 ids to `["Heavy Modular Frame"]`, or attach a `prod` field at
render time. (Kept HTML-side because `FACTORIES` is hand-maintained in the page,
not generated.)

### 3. `COMPONENT_META` (HTML constant)

```js
const COMPONENT_META = {
  "Aluminum Casing":      { code: "AC",  color: "#8fd3f4" },
  "Cooling System":       { code: "CS",  color: "#4dd0e1" },
  "Steel Beam":           { code: "SB",  color: "#b0bec5" },
  "Motor":                { code: "MTR", color: "#ff8a65" },
  "Stator":               { code: "STA", color: "#ffd54f" },
  "Heavy Modular Frame":  { code: "HMF", color: "#ba68c8" },
  "Smart Plating":        { code: "SP",  color: "#81c784" },
  "Modular Frame":        { code: "MF",  color: "#aed581" },
  "High-Speed Connector": { code: "HSC", color: "#f06292" },
  "Copper Powder":        { code: "CuP", color: "#d4915d" },
  "Rubber":               { code: "RUB", color: "#9e9e9e" }
};
```

Unknown/unmapped items fall back to a neutral grey badge with the first 3 chars
uppercased, so the map never breaks if the plan adds a new product.

## Rendering

### Canvas badges

- A helper `drawProductBadges(screenX, screenY, prodList, activeComponent)`
  draws a horizontal row of rounded-rect pills (component color fill, dark text
  code, Courier font) centered under a factory's primary marker.
- Called from `drawGapCenter` (for `GAP_FACTORIES`, primary site `si === 0`) and
  `drawFactoryCenter` (for the 5 base factories, the HMF badge).
- Gated by the same zoom threshold that already controls label visibility, so
  low zoom stays uncluttered.
- When a component filter is active, the matching badge is drawn at full
  opacity/with an outline; the factory's other badges are dimmed.

### Sidebar legend

A "Products" legend block lists each component as `[badge] Full Name`, using the
same code+color, so the canvas badges are decodable. Rendered once in the
sidebar near the gap-factory list.

## Filter — dropdown

- A `<select id="componentFilter">` in the map controls area:
  `All components` (default) + the 11 components (alphabetical, value = full
  item name; `all` for the default).
- State: `let componentFilter = 'all';` updated via `onchange`, then `draw()`.
- A factory is **eligible** when `componentFilter === 'all'` or its `prod`
  includes the selected component.
- Visibility combines with existing per-factory checkboxes:
  - Gap factory drawn iff `gapVisible[id] && eligible(gf)`.
  - Base factory drawn iff `visible[fid] && eligible(f)`.
- While `componentFilter !== 'all'`, **all gap towns and mining towns are
  hidden** (raw suppliers, not component producers). `all` restores them to
  their checkbox state.
- Connecting lines / search radii follow their factory's visibility (existing
  behavior keyed off the same visibility check).

## Edge cases

- **Fractional amounts:** HMF increments are 16.5/min — badge shows the code
  only; amounts (if shown on hover/tooltip) display as-is.
- **Multi-product factories** (aldercast AC+CS, voltreach MTR+STA, moldmarsh
  SB+STA, silvashade AC+SB, ferrium+ SP+MF): draw one badge per product, all in
  the row; filter highlights the matching one.
- **HMF duplication:** both the relocated `_hmf` gap entries and the 5 base
  factories carry HMF and both appear under the HMF filter — intended.
- **New/unknown product:** neutral grey fallback badge; never throws.

## Files touched

- `find_gap_factory_locations.py` — add `prod` to the `GAP_DATA` record builder.
- `factory-map.html` — `COMPONENT_META`, base-factory HMF tags, regenerated
  `GAP_DATA` block (with `prod`), `drawProductBadges`, calls in
  `drawGapCenter`/`drawFactoryCenter`, sidebar legend, `<select>` + filter
  state + eligibility checks in the draw loop, town hiding under active filter.

## Verification

- `python -c` parse check that the regenerated `GAP_DATA` JSON is valid and each
  record has `prod`; diff confirms placements unchanged.
- Serve `python server.py`, open the Map tab, and confirm: badges render under
  factories; the legend decodes them; the dropdown isolates each component
  (correct factories shown, towns hidden); "All components" restores everything;
  per-factory checkboxes still work in combination.

## Out of scope / future

- Product badges/filter on the Factories (Factory Crazy) tab.
- Real game sprite icons (chosen against — letter-badges instead).
- Showing per-product throughput amounts on the badges (codes only for now;
  amounts available in `prod` if a tooltip is added later).
- Auto-filtering towns to those that supply the visible producing factories
  (towns are simply hidden under an active filter for now).
