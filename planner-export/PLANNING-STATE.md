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
| Motor | 250 | 45 | −205 | scale up | **planned** (Voltreach + Classic Iron Motor) |
| Smart Plating | 150 | 0 | −150 | build new | **planned** (Ferrium+) |
| Stator | 250 | 120 | −130 | scale up | **planned** (Moldmarsh + Voltreach) |
| Heavy Modular Frame | 95 | 35 | −60 | 5 themed factories' job | **planned** (existing 4 +HMF — Luxara share = 0) |
| Modular Frame | 75 | 148 | +74 | ✓ already enough | (Ferrium+ also produces 38 for plan) |
| Magnetic Field Generator | 30 | 0 | −30 | final assembly | (main factory) |
| Thermal Propulsion Rocket | 30 | 0 | −30 | final assembly | (main factory) |
| Nuclear Pasta | 5 | 0 | −5 | final assembly | (main factory) |

NOTE (2026-06-18): the gap plan was re-derived from the `.sft`. Copper Powder,
High-Speed Connector, Rubber, Cooling System and Modular Frame are NOT gap needs
— the `.sft` declares them as already-supplied `input` (and/or live production
already covers them), so no gap factory builds them. See §4.

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

## 4. Gap factory plan — REBUILT from .sft constraints (2026-06-18)

The gap supply-chain was **re-derived from scratch** by
`find_gap_factory_locations.py`. Targets are no longer hand-authored: they come
from the `.sft` `production` SET targets **minus** items the `.sft` declares as
already-supplied `input` **minus** live production (`current-production.txt`).
Two independent derivations + a phantom-hunt + a code audit (multi-agent) agreed,
and the result was independently re-verified: no phantom outputs, all 6 targets
sum exact, no node double-booked, no overlapping factory markers. Full data in
`../gap-factory-locations.json`.

**Phantoms removed** (the old plan built these; the `.sft` already supplies them):

| Old line | per/min | Why dropped |
|---|--:|---|
| High-Speed Connector | 115 | `.sft input`=99999 (supplied) + live net **+30** |
| Copper Powder | 1,000 | `.sft input`=9999/999999 (supplied) |
| Cooling System | 150 | `.sft input`-only, not a SET target; live +3 |
| Rubber (export) | 917 | `.sft input`-only; live surplus **+1,808** |
| Modular Frame | 38 | live makes **148.5** ≥ 75 target — already covered |

The entire **cathera+** copper factory (its only outputs were the two phantoms)
and its 7 far caterium outposts were deleted.

**Genuine gap targets** (SET `.sft` target − live produced):

| Product | SET | live | gap built |
|---|--:|--:|--:|
| Aluminum Casing | 5,000 | 1,350 | **3,650** |
| Steel Beam | 900 | 302 | **598** |
| Motor | 250 | 45 | **205** |
| Stator | 250 | 120 | **130** |
| Smart Plating | 150 | 0 | **150** |
| Heavy Modular Frame | 95 | 35 | **60** |

**11 factories:**

| Factory | Disp | Quad | Produces | Bldgs | Power | Shards |
|---|---|---|---|--:|--:|--:|
| aldercast | new | SE | Aluminum Casing 1591 | 148 | 1,379 MW | 7 |
| bauxhold | new | SE | Aluminum Casing 1029 | 92 | 1,356 MW | 10 |
| silvashade | new | SW | Aluminum Casing 1029 + Steel Beam 66 | 123 | 1,329 MW | 4 |
| moldmarsh | new | NW | Steel Beam 532 + Stator 71 | 141 | 1,339 MW | 4 |
| voltreach | new | SW | Motor 102 + Stator 58 | 242 | 2,891 MW | 2 |
| classic_iron_motor | new | NE | Motor 102 | 484 | 3,406 MW | 4 |
| ferrium+ | scaled_in_place | NE | Smart Plating 150 | 587 | 3,908 MW | 17 |
| ferrium_hmf | satellite | NE | HMF 15 | 190 | 1,354 MW | 16 |
| naphtheon_hmf | scaled_in_place | NE | HMF 15 | 262 | 2,955 MW | 4 |
| cathera_hmf | scaled_in_place | NE | HMF 15 | 131 | 1,550 MW | 0 |
| Anvilreach (forgeholm_hmf) | relocated | SE | HMF 15 | 203 | 2,322 MW | 10 |
| **TOTAL** | | | | **2,603** | **23,787 MW** | **136** |

HMF +60 = ferrium / naphtheon / cathera / Anvilreach 15 each; luxara 0.
**Anvilreach** is the +HMF increment as a DISTINCT factory from the built base
Forgeholm — no longer pinned on top of the base; it relocated to its own 5-node
coal cluster (≈173 k from the base) so the two markers no longer overlap.

**Mining towns** (shared bulk resources): coal 2 towns (7 nodes), copper 1 (3),
iron 1 (11) + existing Siderith/Calcara, limestone 1 (5).

**Pure-node policy:** there are NO "saturation" factories. An earlier attempt to
force-consume every NE pure node by building sink factories was removed — only
factories that make the 6 useful products exist. Instead a SOFT preference
(`PURE_PREF_BUCKET` ≈ 120 m band) makes real factories favour PURE nodes when
claiming ore, so pure nodes get more chance of being used for genuine demand
without overbuilding. Some pure nodes may remain free — expected and acceptable.

**Key tunables:** `SEARCH_RADIUS` 70 k (wide local capture), `MIN_SEPARATION`
25 k, locality penalty (`LOCAL_RADIUS` ≈ 47 k, exp 1.6), pocket-match scoring (a
factory centre must sit inside a pocket of its own signature ore, not a
foreign-ore field), `PURE_PREF_BUCKET` 12 k, `QUADRANT_WEIGHT` NW 1.5 / NE 1.4 /
SE 1.4 / SW 1.0 (soft). Occupancy: 58/115 live nodes matched; user-released nodes
from `../reuse-nodes.json` returned to the pool.

## Planning rules

1. Needs = SET `.sft` targets only (Section 1). Intermediates are flexible.
2. New factories must site on nodes NOT in `occupied-nodes.json`.
3. Compare against `current-production.txt` for what already exists.
4. Update this file when any source file or `gap-factory-locations.json`
   changes; keep it the single reference.
