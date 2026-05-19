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

Plus new products in the gap plan: Copper Powder 1,000, High-Speed Connector
115, Rubber 917, Cooling System 150 (Cathera+, Cathera+, Naphtheon+, Aldercast
respectively).

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

## 4. Gap factory plan — placed (2026-05-19 amounts phase)

The gap supply-chain plan from the design spec has been sized, sited, and
build-quantified. Full details in `../gap-factory-locations.json`.

**Locked tunables (this plan):** Aluminum Casing 3,900 split = Aldercast 1,400
/ Bauxhold 1,500 / Silvashade 1,000 → revised to **3,500 / 200 / 200**
(bauxite-optimal shift toward most-efficient Aldercast, minima preserved for
identity). Steel Beam 450 split = **Moldmarsh 400 / Silvashade 50**. Motor 220
split = Voltreach 110 / Classic Iron Motor 110. Stator 289 split = Moldmarsh
159 / Voltreach 130. HMF +66 split = **Ferrium / Naphtheon / Forgeholm /
Cathera 16.5 each; Luxara 0** (Luxara HMF uses bauxite, omitted from
increment). Miner overclock = up to 250% (3 power shards); belt cap 780/min;
nitrogen wells modeled by Pressurizer per-satellite, reserved by `core`.

**Design §2.2 erosion check** (existing surplus vs new consumption):

| Item | Existing net | New consumption | Decision |
|---|--:|--:|---|
| Wire | +5,481 | +5,845 | in-house (existing can't cover) |
| Copper Sheet | −133 | +340 | in-house (already deficit) |
| Crystal Oscillator | +56 | +18 | in-house (below 100/min margin) |
| Circuit Board | +998 | +115 | **import from existing** (Cathera+) |
| Computer | +120 | 0 | (no consumption) |

**Per-factory placement + sizing:**

| Factory | Disp. | Sig nodes | Outposts | Buildings | Power | Shards | Imports |
|---|---|--:|--:|--:|--:|--:|---|
| Aldercast | new | 11 (7 sites) | 8 | 385 | 5,478 MW | 95 | Petroleum Coke, Rubber |
| Bauxhold | new | 1 | 2 | 18 | 263 MW | 0 | — |
| Silvashade | new | 1 | 2 | 30 | 294 MW | 3 | — |
| Voltreach | new | 2 | 5 | 323 | 3,490 MW | 20 | — |
| Moldmarsh | new | 5 (2 sites) | 4 | 218 | 1,841 MW | 30 | — |
| Classic Iron Motor | new | 5 | 3 | 605 | 4,008 MW | 14 | — |
| Naphtheon+ | satellite | 13 (2 sites) | 0 | 146 | 4,349 MW | 32 | — |
| Cathera+ | relocated | 11 (4 sites) | 6 | 600 | 3,953 MW | 41 | Circuit Board |
| Ferrium+ | satellite | 8 (2 sites) | 0 | 658 | 4,520 MW | 16 | — |
| Ferrium (+HMF) | relocated | 5 | 2 | 208 | 1,489 MW | 13 | — |
| Naphtheon (+HMF) | relocated | 3 | 4 | 288 | 3,250 MW | 8 | — |
| Forgeholm (+HMF) | relocated | 3 | 7 | 224 | 2,555 MW | 18 | — |
| Cathera (+HMF) | relocated | 1 | 6 | 143 | 1,705 MW | 13 | — |
| **TOTAL** | | | | **3,846** | **37,195 MW** | **285** | |

**Gap mining towns** (shared outposts for the high-volume trained resources
— matches the existing Siderith / Calcara pattern; each town supplies 3–5
factories over rail/truck rather than each factory mining its own):

| Resource | Towns | Total nodes | Total cap/min | Shards | Supplies |
|---|--:|--:|--:|--:|---|
| Coal | 2 | 6 | 3,600 | 12 | silvashade, bauxhold, voltreach, moldmarsh, classic_iron_motor |
| Copper | 6 | 8 | 5,160 | 22 | aldercast, voltreach, moldmarsh, classic_iron_motor |
| Iron | 5 | 14 | 8,160 | 35 | voltreach, moldmarsh, forgeholm_hmf, naphtheon_hmf, cathera_hmf |
| Limestone | 3 | 7 | 4,080 | 13 | forgeholm_hmf, naphtheon_hmf, ferrium_hmf, cathera_hmf |
| **Total** | **16** | **35** | **21,000/min** | **82** | |

**Projected resource pool after gap factory build:**

| Resource | Total | Currently occupied | Gap-plan reserved | Remaining unoccupied |
|---|--:|--:|--:|--:|
| Bauxite | 17 | 3 | 13 | **1** (very tight) |
| Caterium Ore | 17 | 5 | 9 | 3 |
| Coal | 62 | 12 | 13 | 37 |
| Copper Ore | 55 | 14 | 23 | 18 |
| Iron Ore | 127 | 26 | 34 | 67 |
| Limestone | 94 | 13 | 13 | 68 |
| Nitrogen Gas (wells) | 45 | 14 | 17 | 14 |
| Crude Oil | 48 | 6 | 16 | 26 |
| Raw Quartz | 17 | 6 | 2 | 9 |
| SAM Ore | 19 | 1 | 0 | 18 |
| Sulfur | 16 | 7 | 1 | 8 |
| Uranium | 5 | 0 | 0 | 5 |
| Water | 55 | 0 | 0 | 55 |

Bauxite remains the binding constraint (1 node free post-plan); any further
aluminum scaling would require either reclaiming a current-occupied bauxite
node, accepting Aldercast's 7-site spread, or revisiting the splits.

## Planning rules

1. Needs = SET `.sft` targets only (Section 1). Intermediates are flexible.
2. New factories must site on nodes NOT in `occupied-nodes.json`.
3. Compare against `current-production.txt` for what already exists.
4. Update this file when any source file or `gap-factory-locations.json`
   changes; keep it the single reference.
