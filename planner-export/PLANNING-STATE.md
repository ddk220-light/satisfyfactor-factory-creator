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

## 1. Determined needs — SET sub-factory targets vs current production

Only targets explicitly declared in `.sft` tabs are real needs. Intermediates
(Copper Sheet, Circuit Board, Computer, Rotor, …) are **flexible** — quantity
depends on alternate-recipe choices not yet locked. Never treat them as needs.

| Item | Target/min | Make/min | Gap | Action |
|---|--:|--:|--:|---|
| Aluminum Casing | 5,000 | 1,350 | −3,650 | scale up (biggest gap) |
| Steel Beam | 900 | 302 | −598 | scale up |
| Motor | 250 | 45 | −205 | scale up |
| Smart Plating | 150 | 0 | −150 | build new |
| Stator | 250 | 120 | −130 | scale up |
| Heavy Modular Frame | 95 | 35 | −60 | 5 themed factories' job |
| Modular Frame | 75 | 148 | +74 | ✓ already enough |
| Magnetic Field Generator | 30 | 0 | −30 | final assembly |
| Thermal Propulsion Rocket | 30 | 0 | −30 | final assembly |
| Nuclear Pasta | 5 | 0 | −5 | final assembly |

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

## 3. Occupied resource nodes (already used — unavailable for new factories)

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
Per-node coordinates: `occupied-nodes.json`.

## Planning rules

1. Needs = SET `.sft` targets only (Section 1). Intermediates are flexible.
2. New factories must site on nodes NOT in `occupied-nodes.json`.
3. Compare against `current-production.txt` for what already exists.
4. Update this file when any source file changes; keep it the single reference.
