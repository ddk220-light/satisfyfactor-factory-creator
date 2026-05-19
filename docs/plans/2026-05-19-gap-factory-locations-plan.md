# Gap Supply-Chain Factory Locations — Implementation Plan

> **For Claude:** Implement task-by-task against the approved design in
> `docs/superpowers/specs/2026-05-19-gap-supply-chain-factories-design.md`
> (referenced below as "the design spec") and the brainstormed siting design
> (Approach A) captured in this plan. Commits per task follow the repo
> convention but are **gated on explicit user approval** — do not commit
> unless asked.

**Goal:** Automatically place the gap supply-chain factories on the map by
proximity to the raw resources each one needs — scarcity-ordered, conflict-free
(no factory double-books a node, the 115 live miners are excluded), multi-site
where one cluster can't meet demand, soft-biased to the top-left (NW) and
bottom-right (SE) quadrants. Re-site / add satellites / relocate the `+`
extensions and the existing 5 HMF factories if their scaled demand can't be met
locally. Display the result on the existing Map tab (no picker — selection is
automatic).

**Architecture:** One new stdlib-only script `find_gap_factory_locations.py`
(reuses scoring helpers patterned on `find_factory_locations.py`), reading
`resource_nodes.json`, `planner-export/occupied-nodes.json`, and
`satisfactory.db`; emitting `gap-factory-locations.json`; then a data-injection
edit into the hand-maintained `factory-map.html` (NOT via `build_map.py`).

**Tech Stack:** Python 3 (stdlib: `json`, `math`, `sqlite3`, `collections`).

**Coordinate convention:** `+x` = east/right, `+y` = south/bottom, units cm
(100 = 1 m). **Top-left = NW = (x<0, y<0); bottom-right = SE = (x>0, y>0).**

**DB path (this checkout):**
`/home/starlight/satisfy/satisfyfactor-factory-creator/satisfactory.db`
(scripts in this repo hardcode an absolute DB path; update if checkout differs).

---

## v2 — Pressure-test amendments (READ FIRST; these OVERRIDE the task steps below where they conflict)

A self-review against the design spec, the node data, `factory-map.html`, and
`satisfactory.db` found the following holes. Each amendment is binding.

**A1 — Resource wells (Nitrogen Gas) must be modeled.**
`resource_nodes.json` has a separate `resource_wells` key. **Aldercast's
Cooling System (150/min) needs Nitrogen Gas**, sourced from wells, and Nitrogen
is in deficit (−120). Task 2 `load_pool()` MUST load BOTH `resource_nodes` and
`resource_wells` (tag `kind: 'node'|'well'`). Occupancy match (Task 2) must
also resolve well records (`occupied-nodes.json` Nitrogen Gas / Geyser
entries). Verified shape: 149 `resource_wells`; 45 `nitrogenGas`, 18 `oil`,
55 `water` satellites. **Wells are grouped by a `core`** (one Resource Well
Pressurizer extracts ALL satellites of a core) — the reservation/non-overlap
unit for wells is the **core**, not the satellite: reserving any satellite
reserves its whole core, and capacity = Σ `WELL_RATE[purity]` over that core's
satellites. Add `WELL_RATE` (Pressurizer per-satellite rate by purity);
nitrogen capacity uses it. **Water = explicitly out of scope for siting**
(extractors work on any water body; the 55 water wells are ignored too) —
documented, not a node draw. **Geyser = power only, excluded.** Nitrogen is
never a signature — a factory needing it (only Aldercast, for Cooling System)
treats it as a piped outpost (core). **`oil` exists in BOTH files** (30 surface
`resource_nodes` + 18 fracking `resource_wells`); keep surface oil nodes as the
oil source (consistent with the HMF method), note well-oil as unused spare
capacity — Naphtheon+ is an extension expected to scale near its existing oil
site.

**A2 — Unified scarcity-ordered job queue (replaces Task 4 Step 1 + Task 5
ordering).** Do NOT process "6 new, then extensions, then HMF." Instead build
ONE list of *siting jobs*:
- the 6 new factories (full demand);
- each extension's *added* production (Naphtheon+, Cathera+, Ferrium+);
- each HMF-scale factory's *incremental* critical-resource need (the +66/5 ≈
  +13.2/factory) — **Luxara's increment is bauxite** and MUST contend in the
  same pass as the 3 new bauxite factories.

For each job compute `raw_demand` (Task 3), then its **pressure key** =
`min over its mined resources of (available_count_of_type / sqrt(demand_of_type))`
(lower = tighter). Sort jobs ascending by pressure key; tie-break by total raw
tonnage descending. Process every job through the same `allocate()`.
Consequence: Cathera+ Copper Powder 1,000 and Luxara-bauxite are prioritized by
real scarcity, not stranded as a residual. The "new first, extensions adapt"
priority from §Task 5 is **removed** — replaced by pure resource-pressure
ordering (extensions can now out-prioritize a new factory if their draw is
scarcer; this is correct).

**A3 — Round-robin among same-pressure-tier signature peers.** For jobs sharing
the same signature resource (the 3 bauxite factories; Luxara-bauxite), do NOT
fully satisfy one before the next. Allocate in rounds: each peer claims its
single best remaining cluster per round, looping until each peer's signature
demand is met or the pool is exhausted. This prevents the first bauxite job
from stranding the others when a spread would have fit all (design §3.5 intent:
"spread 3 ways… multi-site near different nodes").

**A4 — Global cross-job separation (fixes the Task 6 assert contradiction).**
Maintain a global `placed_centers` list. In candidate scoring, any centroid
within `MIN_SEPARATION` of ANY previously placed center (any job's primary or
satellite) is excluded, not just the current job's own satellites. Then Task 6
assert #4 is actually guaranteed instead of being able to false-fail.

**A5 — One node-selection policy (replaces Task 3 Step 4 vs Task 4 Step 3
divergence).** Single policy used for BOTH the feasibility count and the actual
reservation: from a center, take available nodes of the needed type in
ascending distance, accumulating actual `MINER_RATE[purity]` (or `WELL_RATE`)
until ≥ demand. No separate purity-first estimator. The reserved set IS the
counted set → estimate and reservation can never disagree.

**A6 — "(or in-house)" rule.** For any item the design spec writes as
"X (or in-house)" (e.g. Moldmarsh Wire, §3.7), DEFAULT to **in-house**: count
its raw at this factory (conservative — never under-provisions). Override only
if another factory's `exports` explicitly names it as a supplied import. Record
the resolved choice per factory in the output `meta`.

**A7 — Decompose end products end-to-end; never size intermediates from
external targets.** Each factory's raw = Σ over its *final gap products* of a
full to-raw decomposition. Do NOT decompose, e.g., Voltreach Motor 110 and
Stator 130 as if independent and also separately size a Stator line — the Motor
decomposition already pulls its own internal Stator. Internal-consumption
caveat (design §2.2, e.g. Voltreach Rigor Motor eats Crystal Oscillator;
Stator-for-Motor) is thereby captured *within* a factory. Cross-factory
net-positive erosion remains deferred (design §2.2) — note it, don't model it.

**A8 — Recipe-name resolution gate (Task 3).** Each recipe named in
`FACTORIES[*]['recipes']` MUST resolve to exactly one `satisfactory.db` recipe.
On zero/multiple matches, FAIL LOUD printing the candidate recipe names — never
silently fall back to a default recipe (would corrupt the raw estimate).

**A9 — Empty-candidate guard.** If a job has zero available signature nodes
(post-occupancy/post-reservation), emit a clean
`disposition:'infeasible'` record with the shortfall and skip all
centroid/scoring math (no divide-by-zero on an empty node set).

**A10 — Determinism.** Round candidate scores to 3 decimals before sorting;
final tie-break by node `path_name` (stable, unique). Re-runs must be
byte-identical.

**A11 — Outpost clustering defined.** Trained-resource reservations are grouped
by single-linkage at `SEARCH_RADIUS`; each cluster's outpost center = its node
centroid. (Removes the under-specified "contiguous" wording.)

**A12 — Demand sanity anchor (Task 6).** Before allocation, print estimated
total demand vs. available unoccupied capacity for **bauxite and copper**
(the two bottlenecks). If estimated bauxite demand is wildly off the
3-node reality or the design's "3,900 is the heaviest raw" claim, halt for
review — guards against a decomposition bug shipping silently.

**A13 — Existing-center resolution assert (Task 5).** Assert every extension
and HMF-scale factory has a center in `selected-factory-locations.json` before
use; fail loud if missing.

**A14 — Centroid buildability is a KNOWN, ACCEPTED limitation** (inherited from
the HMF method): a node-centroid can land on water/cliff. Out of scope to fix;
state it in output `meta` so it isn't mistaken for a guarantee.

---

### Task 1: Scaffold script + design constants

**Files:**
- Create: `find_gap_factory_locations.py`

**Step 1: Module docstring + paths + tunable constants**

```python
DB_PATH            = '/home/starlight/satisfy/satisfyfactor-factory-creator/satisfactory.db'
RESOURCE_NODES     = 'resource_nodes.json'
OCCUPIED_NODES     = 'planner-export/occupied-nodes.json'
EXISTING_LOCATIONS = 'selected-factory-locations.json'
OUTPUT_PATH        = 'gap-factory-locations.json'

SEARCH_RADIUS   = 40_000     # 400 m, reused from HMF method (tunable)
MIN_SEPARATION  = 25_000     # 250 m between distinct sites/factory centers
PURITY_WEIGHT   = {'impure': 1, 'normal': 2, 'pure': 4}   # = Mk.3 120/240/480
MINER_RATE      = {'impure': 120, 'normal': 240, 'pure': 480}  # Mk.3 assumption
QUADRANT_BONUS  = 1.5        # soft NW/SE multiplier (1.0 elsewhere)
OCC_MATCH_TOL   = 5_000      # 50 m nearest-node occupancy match tolerance
MAX_SITES       = 3          # max satellite sites per factory
```

**Step 2: Locked gap targets (design spec §2.3) as constants**

```python
GAP_TARGETS = {  # items/min, locked
    'Aluminum Casing': 3900, 'Steel Beam': 450, 'Motor': 220,
    'Stator': 289, 'Cooling System': 150, 'Copper Powder': 1000,
    'High-Speed Connector': 115, 'Smart Plating': 150,
    'Modular Frame': 38, 'Rubber': 917, 'Heavy Modular Frame': 66,
}
```

**Step 3: Heuristic flavor splits — `# ESTIMATE`, tunable (design spec §3.5, §5)**

```python
# ESTIMATE — split fractions; Bauxite-stretch-biased per design §3.5
FLAVOR_SPLITS = {
    'Aluminum Casing': {'bauxhold': 1500, 'aldercast': 1400, 'silvashade': 1000},
    'Steel Beam':       {'silvashade': 225, 'moldmarsh': 225},   # Al-Beam / cast
    'Motor':            {'voltreach': 110, 'classic_iron_motor': 110},
    'Stator':           {'moldmarsh': 159, 'voltreach': 130},
}
```

**Step 4: Factory definitions — signature resource, recipe chain, products**

For each of the 6 new factories define: `signature` (the one local/siting
resource), `products` (gap items it makes, resolved via `FLAVOR_SPLITS` or
`GAP_TARGETS`), `recipes` (the **specific** signature recipes named in design
spec §3 — e.g. Aldercast → `Alternate: Sloppy Alumina`, `Alternate: Electrode
Aluminum Scrap`, `Alternate: Pure Aluminum Ingot`, `Alternate: Alclad Casing`,
`Alternate: Heat Exchanger`, `Cooling System`), and `imports` (declared
imported intermediates per design §3.6/§3.7 — e.g. Aldercast imports
`Petroleum Coke`, `Rubber` from Naphtheon+).

```python
FACTORIES = {
  'aldercast':          {'signature':'bauxite',   'products':['Aluminum Casing','Cooling System'], 'recipes':[...], 'imports':['Petroleum Coke','Rubber']},
  'bauxhold':           {'signature':'bauxite',   'products':['Aluminum Casing'],                  'recipes':[...], 'imports':[]},
  'silvashade':         {'signature':'bauxite',   'products':['Aluminum Casing','Steel Beam'],     'recipes':[...], 'imports':[]},
  'voltreach':          {'signature':'caterium',  'products':['Motor','Stator'],                   'recipes':[...], 'imports':[]},
  'moldmarsh':          {'signature':'limestone', 'products':['Steel Beam','Stator'],              'recipes':[...], 'imports':[]},
  'classic_iron_motor': {'signature':'iron',      'products':['Motor'],                            'recipes':[...], 'imports':[]},
}
EXTENSIONS = {  # existing center looked up from selected-factory-locations.json
  'naphtheon': {'signature':'oil',     'added':['Rubber'],                          'exports':['Petroleum Coke','Rubber']},
  'cathera':   {'signature':'caterium','added':['High-Speed Connector','Copper Powder'],'exports':[]},
  'ferrium':   {'signature':'iron',    'added':['Smart Plating','Modular Frame'],   'exports':[]},
}
HMF_SCALE = {'ferrium','naphtheon','forgeholm','luxara','cathera'}  # +66/5 each
```

**Step 5: Commit** (on approval)

```bash
git add find_gap_factory_locations.py docs/plans/2026-05-19-gap-factory-locations-plan.md
git commit -m "feat: scaffold gap factory location finder + plan"
```

---

### Task 2: Node pool + robust occupancy matching

**Files:**
- Modify: `find_gap_factory_locations.py`

**Step 1: `load_pool()`** — read `resource_nodes.json` `resource_nodes`
(459); each node a mutable dict `{type, purity, x, y, reserved_by: None}`.

**Step 2: `mark_occupied(pool)`** — for each record in
`occupied-nodes.json`, take `node_pos` (fallback `miner_pos`), find the nearest
pool node **of the same resource type** within `OCC_MATCH_TOL`; mark
`reserved_by = '__occupied__'`. Map save resource names → node `type`
(`'Iron Ore'→'iron'`, `'Crude Oil'→'oil'`, `'Caterium Ore'→'caterium'`,
`'Raw Quartz'→'quartz'`, `'SAM Ore'→'sam'`, else lowercase first word).

**Step 3: report match coverage** — print `matched / 115`; list unmatched
records (target ≈ 115 vs the 93 from naive exact-coord matching). This is
validation gate #2.

**Step 4: Commit** (on approval) — `feat: node pool + robust occupancy match`

---

### Task 3: Rough demand estimation (DB decomposition)

**Files:**
- Modify: `find_gap_factory_locations.py`

**Step 1: `recipe_io(conn, recipe_name)`** — query `satisfactory.db` per the
`satisfactory-factory-planning` skill: products & ingredients with
`quantity / duration * 60` = per-min; building from `recipe_buildings`. Fluids
(`÷1000` for m³). Recipe names are exact (e.g. `Alternate: Alclad Casing`).

**Step 2: `decompose(conn, factory)`** — for a factory's `products` at their
split/target rate, walk its **specified `recipes`** (NOT DB defaults) backward,
recursing into ingredients, aggregating per item. **Boundary rule — stop
recursion at:** (a) raw mined resources (no non-extraction producer; see skill
Step 3 query), and (b) any item in the factory's `imports` list (declared
imported intermediate — its raw is attributed to the supplying factory, never
re-mined here). In-house Iron/Copper Rotor IS decomposed (design §3.1a). Use
cycle detection (topological aggregation) per the repo's circular-recipe
guardrail.

**Step 3: `raw_demand(factory) -> {resource_type: items_per_min}`** — solid
mined types only (bauxite, iron, copper, coal, caterium, limestone, quartz,
sulfur). Water = sited-anywhere (excluded from siting); oil/nitrogen kept as
node-based only for oil-touching factories.

**Step 4: `nodes_needed(demand, pool_of_type)`** — drives multi-site.
> **SUPERSEDED BY A5:** do NOT implement a separate purity-first estimator.
> Use the single distance-first policy (claim nearest available, accumulate
> actual `MINER_RATE`/`WELL_RATE` until ≥ demand) for both counting and
> reservation, so estimate and reservation are identical by construction.

**Step 5: Commit** (on approval) — `feat: rough raw-demand estimation via DB`

---

### Task 4: Scarcity-ordered greedy allocation

**Files:**
- Modify: `find_gap_factory_locations.py`

**Step 1: ordering.**
> **SUPERSEDED BY A2 + A3:** do NOT order only the 6 new factories by
> signature scarcity. Build the unified job queue (6 new + extensions' added
> + per-HMF increments incl. Luxara-bauxite), order by the A2 pressure key,
> and round-robin same-signature peers per A3. `allocate()` below is applied
> to every job in that queue, not just the 6 new factories.

**Step 2: `score_candidates(factory, pool)`** — every available signature
node is a candidate center. `score = Σ PURITY_WEIGHT[p] × (sig_demand ×
rarity^1.5)` over signature nodes within `SEARCH_RADIUS`, where
`rarity = (max_type_count / sig_type_count) ** 1.5`. Multiply by
`QUADRANT_BONUS` if the centroid is in NW or SE (soft bias). Center = centroid
of nearby signature nodes. Sort desc.

**Step 3: `allocate(factory, pool)`** —
1. Best-scored center; claim nearest available **signature** nodes within
   radius until Σ `MINER_RATE` ≥ signature demand.
2. Shortfall → open a **satellite**: next-best candidate ≥ `MIN_SEPARATION`
   from prior sites; repeat. Cap `MAX_SITES`. Pool exhausted →
   `infeasible=True` + recorded shortfall (Bauxite risk surfaces here).
3. **Trained-in resources** (every non-signature mined type in `raw_demand`,
   incl. nitrogen-via-well per A1): claim nearest available nodes of that type
   anywhere (NW/SE-biased, independent of factory center) until demand met;
   group into **outposts** by A11 (single-linkage @ `SEARCH_RADIUS`). Wells
   reserve by `core` (A1).
4. Set `reserved_by = job_id` on every claimed node (removes from pool →
   structural non-overlap). Append the chosen center(s) to the global
   `placed_centers` list (A4).

> Candidate scoring/centers in Steps 1–2 must apply the **A4** global
> separation (≥ `MIN_SEPARATION` from ANY prior job's center) and the **A9**
> empty-candidate guard.

**Step 4:** loop `factory_order`, calling `allocate`.

**Step 5: Commit** (on approval) — `feat: scarcity-ordered greedy allocation`

---

### Task 5: Extension & HMF feasibility (in place / satellite / relocate)

**Files:**
- Modify: `find_gap_factory_locations.py`

Runs **after** Task 4 (pool already reduced). Existing factories' current
consumption sits on `__occupied__` nodes — only the **incremental** demand is
sited.

**Step 1: `check_extension(ext, pool)`** — added raw demand via Task 3
(including raw for `exports` it ships, e.g. Naphtheon+ → Aldercast's Petroleum
Coke + Rubber). Look up existing center from `selected-factory-locations.json`.
Measure residual available capacity for needed resources within
`SEARCH_RADIUS` of that center. Outcomes:
- **Fits** → `disposition='scaled_in_place'`, reserve nearby nodes.
- **Modest shortfall, satellite within reach** → `disposition='satellite'`,
  one+ satellite near the existing center (Task 4 spill logic).
- **Cannot be met near existing center even with a satellite** →
  `disposition='relocated'`: run the **full Task 4 allocation** for the
  extension's *added* demand as a standalone factory, unconstrained by the old
  center (NW/SE-biased, scarcity-aware). The live base factory keeps its
  occupied nodes; only the expansion moves. Record `decoupled_from`.

> **SUPERSEDED BY A2:** the "new factories claim first; extensions take
> residual" priority is **removed**. Extensions are jobs in the single A2
> queue, ordered by resource pressure — Cathera+ (Copper Powder 1,000) can and
> should out-prioritize a lighter new factory. `check_extension` only decides
> the *disposition* (in-place / satellite / relocated) relative to the
> existing center; it does NOT defer the extension to a trailing pass.

**Step 2: `check_hmf_scale(pool)`** — split `+66` as `~13.2` each across
`HMF_SCALE`. Per factory: check residual availability of its critical resource
near its existing center; emit an explicit `in_place` / `satellite` line — no
silent assumptions.

**Step 3: Commit** (on approval) — `feat: extension/HMF feasibility + relocate`

---

### Task 6: Output JSON + validation asserts + report

**Files:**
- Modify: `find_gap_factory_locations.py`

**Step 1: `build_output()`** — `gap-factory-locations.json` mirroring
`selected-factory-locations.json` shape. Per factory: `factory_name`, `theme`,
`signature_resource`, `disposition`
(`new|scaled_in_place|satellite|relocated|infeasible`), `center{x,y}`,
`sites[]` (`center`, signature `nodes[]`), `outposts[]`
(`resource`,`center`,`nodes[]`), `demand` vs `reserved_capacity` per resource,
`estimate: true`, `reason`. Top-level `pool_balance` per resource
(total / occupied / reserved / remaining) and `meta` (coords, Mk.3 assumption,
radius, flavor-split constants used).

**Step 2: validation (hard asserts + printed report)** — per design §6:
1. assert no node `reserved_by` two factories; assert
   `total == occupied + reserved + free`.
2. occupancy match coverage line (from Task 2).
3. per factory: `reserved_capacity ≥ demand` OR `infeasible` + shortfall.
4. assert all factory/satellite centers ≥ `MIN_SEPARATION` (outposts exempt).
5. quadrant tally: centers in NW/SE vs NE/SW.
6. per-resource pool balance (deficits explicit — Bauxite/Caterium).
7. determinism per **A10** (3-dp score rounding + `path_name` tie-break;
   re-run byte-identical).
8. **A12** demand sanity anchor printed *before* allocation (bauxite + copper
   estimated vs available; halt if wildly off).
9. **A13** assert every extension/HMF existing center resolves.

`build_output()` `meta` also records: A6 resolved "(or in-house)" choices,
the A14 centroid-buildability caveat, and the Mk.3/`WELL_RATE` assumptions.

**Step 3: Commit** (on approval) — `feat: output JSON + validation report`

---

### Task 7: Inject into factory-map.html (display only)

**Files:**
- Modify: `factory-map.html` (hand-edited directly — **do NOT run
  `build_map.py`**, it would wipe the tabs)

Exact touch-points (line numbers approximate — re-grep before editing; the
file is hand-maintained, **never run `build_map.py`**):

**Step 1: data.** Insert a `GAP_FACTORIES` const + `GAP_OUTPOSTS` between a
marked `// <GAP_DATA>` … `// </GAP_DATA>` block placed right after the
`FACTORIES` const (~L362) / `MINING_TOWNS` (~L363). Same record shape as
`FACTORIES` (`name,theme,req,cx,cy,nodes[],resources{}`) plus
`disposition`, `sites[]`, `outposts[]`. The script rewrites only between the
markers (idempotent re-injection).

**Step 2: visibility state.** Extend the visibility-init loop (~L422,
`for (const mt of MINING_TOWNS) townVisible[...]=true`) with a
`gapVisible[fid]=true` map and a `toggleGapVis()` mirroring `toggleVis`
(~L749 pattern) / `toggleTownVis` (~L796).

**Step 3: drawing.** Hook the existing canvas `draw()` path: call new
`drawGapNodes`/`drawGapCenter` modeled on `drawFactoryNodes` (L558) and
`drawFactoryCenter` (L592), honoring the same `ZOOM_SHOW_FACTORY_NODES`
threshold. Distinct color band from the 5 HMF; primary site = solid marker,
satellite = same color outlined, outpost = small diamond (reuse the
mining-town diamond style). `disposition:'infeasible'` → warning color +
shortfall in tooltip.

**Step 4: legend.** Add a **"Gap Factories"** sidebar section beside the
"Mining Towns" header block (~L757) with the same per-factory visibility
checkboxes (`toggleGapVis`) — visibility toggles only, NOT a picker.

**Step 5: export decision (was unspecified).** The JSON export builder
(~L814–853, downloads `selected-factory-locations.json`) **MUST** include the
gap factories under a distinct `"group":"gap"` tag so the export stays the
single locations artifact. Add gap entries to the export object alongside the
factory/mining-town loops; keep the existing filename.

**Step 6:** Stays on the existing **Map** tab; no new tab; the Factories
(Factory Crazy) tab is untouched.

**Step 7: parse-check.** After injection, extract the `// <GAP_DATA>` block and
validate it (`node --check`, or regex-extract the array literal and
`json.loads` after stripping `const X =`/`;`). Headless box — JS validity is
the only automated check; rendered-map verification is the user's.

**Step 8: Commit** (on approval) — `feat: render gap factories on map`

---

### Task 8: Run, validate, finalize

**Files:**
- Run: `find_gap_factory_locations.py`; Verify: `gap-factory-locations.json`,
  `factory-map.html`

**Step 1:** `cd /home/starlight/satisfy/satisfyfactor-factory-creator &&
python3 find_gap_factory_locations.py`. Expect: occupancy match ≈115/115,
all asserts pass, per-resource balance printed, quadrant tally NW/SE-heavy.

**Step 2:** Inspect `gap-factory-locations.json` — every factory has a
`disposition`; no `reserved_by` collisions; Bauxite/Caterium balance lines
sane (infeasible flagged, not silent).

**Step 3:** Parse-check the injected JS (`node --check` or a Python regex
extract + `json.loads` of the `GAP_DATA` block). **Headless box — cannot
visually verify the rendered map / checkbox behavior;** state this explicitly,
user eyeballs the served/deployed map (`python server.py` → :8080).

**Step 4: Commit** (on approval)

```bash
git add find_gap_factory_locations.py gap-factory-locations.json factory-map.html
git commit -m "feat: gap supply-chain factory locations + map overlay"
```

---

## Deferred / explicitly out of scope

- Exact flavor splits & building-count sizing — the design spec's "amounts
  phase" (§5); here only rough estimates flagged `estimate:true`.
- In-browser visual verification (headless box).
- Re-deriving needs — `PLANNING-STATE.md` + the design spec remain canonical.
