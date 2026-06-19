# PLANNING STATE — Canonical Reference

**This is the single source of truth for all factory planning. Going forward,
plan ONLY against the data in this file (and the source files it points to).
Do not re-derive needs from default-recipe decomposition.**

Source files (all in `planner-export/`):
- `*.sft` — the plan (set production targets per factory tab)
- `current-production.txt` — live factory output/consumption (raw user export)
- `occupied-nodes.json` — 115 miner→node records from the save
- `occupied-nodes-summary.json` — aggregated occupied nodes by resource/purity
- `gap-analysis.md` — detailed gap write-up + methodology

Additional artifacts (added 2026-05-19, gap supply-chain amounts phase):
- `../gap-factory-locations.json` — auto-placed gap factory plan with sites,
  outposts, building counts, per-node overclock %, shards used, erosion check
- `../docs/superpowers/specs/2026-05-19-gap-supply-chain-factories-design.md` — design
- `../docs/plans/2026-05-19-gap-factory-locations-plan.md` — implementation plan

## 1. Determined needs — SET sub-factory targets vs current production

Only targets explicitly declared in `.sft` tabs are real needs. Intermediates
(Copper Sheet, Circuit Board, Computer, Rotor, …) are **flexible** — quantity
depends on alternate-recipe choices not yet locked. Never treat them as needs.

| Item | Target/min | Make/min | Gap | Action | Plan status |
|---|--:|--:|--:|---|---|
| Aluminum Casing | 5,000 | 1,350 | −3,650 | scale up | **planned** (Aldercast+Bauxhold+Silvashade) |
| Steel Beam | 900 | 302 | −598 | scale up | **planned** (Silvashade Al-Beam + Moldmarsh cast) |
| Motor | 250 | 45 | −205 | scale up | **planned** (Voltreach + iron-copper Bronzereach/Brasshold) |
| Smart Plating | 150 | 0 | −150 | build new | **planned** (iron-copper Bronzereach + Brasshold) |
| Stator | 250 | 120 | −130 | scale up | **planned** (Moldmarsh + Voltreach) |
| Heavy Modular Frame | 95 | 35 | −60 | 5 themed factories' job | **planned** (existing 4 +HMF — Luxara share = 0) |
| **Copper Powder** | **1,000** | **0** | **−1,000** | build new | **planned** (Dustforge) — feeds Nuclear Pasta |
| Modular Frame | 75 | 148 | +74 | ✓ already enough | (live covers it) |
| Magnetic Field Generator | 30 | 0 | −30 | final assembly | (main factory) |
| Thermal Propulsion Rocket | 30 | 0 | −30 | final assembly | (main factory) |
| Nuclear Pasta | 5 | 0 | −5 | final assembly | (main factory) |

NOTE (2026-06-19): **Copper Powder IS a genuine gap — corrected.** It was
previously dropped as a "phantom" because the `.sft` lists CopperDust only as an
`input`. But Nuclear Pasta (a Phase-5 SET production target) consumes 200 Copper
Powder each → **1,000/min for 5 pasta/min**, and live production makes ZERO. So
nothing supplies it; the `.sft` `input` declaration was an unfulfilled
assumption. A standalone factory (**Dustforge**) now builds it (Pure Copper Ingot
route, ~2,400 copper ore/min). High-Speed Connector, Rubber, Cooling System and
Modular Frame remain NON-needs (live production covers them).

MFG/TPR/Nuclear Pasta targets are **corrected (halved)** from the raw `.sft`
(60/60/10 → 30/30/5) to match the main factory's real consumption. Stator and
Aluminum Casing are left as declared (not simple 2× cases).

**Main factory end goal (assembly only, no mining):** Assembly Director System
30 · Thermal Propulsion Rocket 30 · Magnetic Field Generator 30 · Nuclear
Pasta 5 per minute.

## 2. Current raw extraction (consumption base; mining is overclocked)

| Resource | Mined/min | Used/min | Net |
|---|--:|--:|--:|
| Iron Ore | 16,860 | 18,335 | −1,475 |
| Limestone | 5,070 | 6,061 | −991 |
| Caterium Ore | 2,460 | 3,276 | −816 |
| Bauxite | 1,050 | 1,200 | −150 |
| Copper Ore | 6,420 | 6,530 | −110 |
| Coal | 5,100 | 5,190 | −90 |
| Nitrogen Gas | 5,550 m³ | 5,670 m³ | −120 |
| Crude Oil | 3,000 m³ | 3,120 m³ | −120 |
| Sulfur | 3,510 | 2,450 | +1,060 |
| Raw Quartz | 3,060 | 2,669 | +391 |
| SAM | 300 | 300 | 0 |

Negative net = drawing down storage buffers. Crude Oil largely feeds Rocket
Fuel for power. Full item-level table: `current-production.txt`.

## 3. Occupied resource nodes (currently active in the save)

115 miners/extractors placed. Counts by resource (Impure/Normal/Pure):

| Resource | Nodes | I / N / P |
|---|--:|---|
| Iron Ore | 26 | 1 / 6 / **19** |
| Nitrogen Gas | 14 | 2 / 4 / 8 |
| Copper Ore | 14 | 4 / 6 / 4 |
| Limestone | 13 | 2 / 7 / 4 |
| Coal | 12 | 3 / 6 / 3 |
| Sulfur | 7 | 2 / 2 / 3 |
| Crude Oil | 6 | 0 / 2 / 4 |
| Raw Quartz | 6 | 2 / 2 / 2 |
| Geyser | 6 | 1 / 1 / 4 (power) |
| Caterium Ore | 5 | 0 / 3 / 2 |
| Bauxite | 3 | 1 / 1 / 1 (scarcest) |
| SAM Ore | 1 | 1 / 0 / 0 |

Iron is the most-committed (19 Pure nodes taken). Bauxite is the tightest
(only 3 nodes, already at deficit) — a constraint for any aluminum scaling.
Per-node coordinates: `occupied-nodes.json`. 109/109 material nodes are
matched 1-to-1 to `resource_nodes.json`; 6 unmatched Geyser records (geysers
aren't material) and 2 unattached miners are structurally unmatchable.

## 4. Gap factory plan — iron-copper + copper-powder + saturated themes (2026-06-19)

Built by `find_gap_factory_locations.py`. Requirement targets still come from the
`.sft` SET production minus already-supplied input minus live production. Beyond
meeting those, this revision adds three user-directed changes (all independently
re-verified: requirements met, no phantoms, 0 nodes double-booked, no overlapping
markers, every factory on a single site/no scatter, shards 196 ≤ 200):

1. **Iron-copper Smart Plating + Motor** replaces the old pure-iron NE pair
   (ferrium+ "Plateholm" Smart Plating + classic_iron_motor "Coghaven"). Two
   factories, **Bronzereach** (extreme NE) and **Brasshold** (near Cathera), each
   make SP 75 + Motor 51. Theme: **copper Wire (30/min) kills the iron-wire
   bottleneck** + Iron-Alloy Ingot (8 iron + 2 copper → 15). Iron on-site, copper
   from shared towns.
2. **Dustforge** — standalone **Copper Powder 1000/min** for Nuclear Pasta (the
   corrected gap, §1). Pure Copper Ingot keeps copper ore at ~2,400/min.
3. **Saturated themed factories** — voltreach / moldmarsh / silvashade /
   naphtheon_hmf / cathera_hmf maxed to their **on-site signature cluster** (one
   site, belt-capped 780/node, existing outposts allowed to 250% but NOT grown,
   no new outposts). Output beyond the SET target is deliberate surplus
   (`('fixed', amt)` product mode); the requirement is still covered by the
   unchanged split factories.
4. **Heavyhold** (ferrium_hmf) stays **pure iron** (iron + a little limestone).

**Genuine gap targets** (requirement; surplus from maxing sits on top):
Aluminum Casing 3,650 · Steel Beam 598 · Motor 205 · Stator 130 ·
Smart Plating 150 · Heavy Modular Frame 60 · **Copper Powder 1,000**.

**12 factories:**

| Factory | Disp | Produces | Bldgs | Power | Shards |
|---|---|---|--:|--:|--:|
| Bronzereach (iron-copper) | scaled_in_place | Smart Plating 75 + Motor 51 | 321 | 3,027 MW | 2 |
| Brasshold (iron-copper) | scaled_in_place | Smart Plating 75 + Motor 51 | 321 | 3,027 MW | 1 |
| Dustforge | scaled_in_place | Copper Powder 1000 | 180 | 4,880 MW | 3 |
| silvashade *(maxed)* | new | Aluminum Casing 1409 + Steel Beam 91 | 169 | 1,819 MW | 17 |
| aldercast | new | Aluminum Casing 1591 | 148 | 1,379 MW | 9 |
| bauxhold | new | Aluminum Casing 1029 | 92 | 1,356 MW | 7 |
| voltreach *(maxed)* | new | Motor 240 + Stator 137 | 612 | 6,993 MW | 4 |
| moldmarsh *(maxed)* | new | Steel Beam 990 + Stator 133 | 313 | 2,705 MW | 16 |
| naphtheon_hmf *(maxed)* | scaled_in_place | HMF 17 | 300 | 3,349 MW | 6 |
| cathera_hmf *(maxed)* | scaled_in_place | HMF 30 | 257 | 3,100 MW | 2 |
| Heavyhold (ferrium_hmf) | scaled_in_place | HMF 15 | 190 | 1,354 MW | 5 |
| Anvilreach (forgeholm_hmf) | relocated | HMF 15 | 203 | 2,322 MW | 10 |
| **TOTAL** | | | **3,106** | **35,310 MW** | **196** |

Totals delivered (requirement + maxing surplus): Aluminum Casing 4,030 ·
Steel Beam 1,081 · Motor 342 · Stator 270 · Smart Plating 150 · HMF 77 ·
Copper Powder 1,000.

**Saturate ceilings are belt-capped.** A node yields `min(MINER_RATE, 780)`/min,
so a *pure* node = 780 (not its 250%-OC 1,200). Maxing is bounded by the local
signature cluster: dense fields (moldmarsh limestone, voltreach caterium) claim
more local nodes in one site; sparse fields (silvashade 4 bauxite, cathera 1
copper) hit a low ceiling — over-targeting them spilled satellites 100k+ away,
so silvashade was sized to ~1,500 combined and cathera to 30 HMF (one site each).

**Mining towns** (shared iron/copper/limestone/coal): 10 gap towns. Copper towns
at 3/6 (Bronzereach/Brasshold/cathera/voltreach pull copper via towns). Coal and
copper town margins are tight (+141 / +125 /min) but positive — feasible.

**Implementation notes (find_gap_factory_locations.py):**
- `PHANTOM_EXCEPTIONS = {'Copper Powder'}` lets the verified-real Copper Powder
  past the phantom guard without weakening it for true input-only phantoms.
- `('fixed', amt)` product mode = absolute per-factory surplus (decoupled from
  the rescaled splits). `HMF_SATURATE` overrides per-HMF-factory increments.
- `NEW_FACTORY_ANCHORS` pins Bronzereach/Brasshold/Dustforge; anchored `new`
  factories dispatch through `alloc_anchored` (not score_centers auto-placement).

## Planning rules

1. Needs = SET `.sft` targets only (Section 1). Intermediates are flexible.
2. New factories must site on nodes NOT in `occupied-nodes.json`.
3. Compare against `current-production.txt` for what already exists.
4. Update this file when any source file or `gap-factory-locations.json`
   changes; keep it the single reference.
