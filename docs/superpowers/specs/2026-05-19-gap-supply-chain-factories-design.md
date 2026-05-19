# Gap Supply-Chain Factories — Design Spec

**Date:** 2026-05-19
**Status:** Approved (design phase). Quantities-per-flavor and locations are deferred to the next (planning) phase.

## 1. Purpose

Fill the production gaps for the main **"Special factories"** assembly plant
(`planner-export/simple.sft`) by designing a set of supply-chain–flavored
sub-factories — the same idea as the existing 5 themed HMF factories, extended
to the rest of the feed products. Heavy Modular Frame stays with the existing 5
themed factories (scaled, not redesigned).

## 2. Planning basis (locked)

### 2.1 Goal (the `simple.sft` "Special factories" outputs)

Assembly Director System 30 · Thermal Propulsion Rocket 30 · Magnetic Field
Generator 30 · Nuclear Pasta 5 (per minute).

### 2.2 Methodology

- The `.sft` stores the **problem**, not the solved amounts. Per-input
  quantities are computed on the fly by satisfactorytools.com and are **not**
  in the file (only Heavy Modular Frame carries a real cap: 190).
- The **authoritative input amounts are the website's solved values**
  (captured from the solver UI), using `simple.sft`'s own policy: 107 allowed
  alternate recipes, 4 blocked recipes (standard Computer / Circuit Board /
  Crystal Oscillator / Automated Wiring), and all ores blocked (only Nitrogen
  Gas is an available raw). With every ore blocked, all paths terminate at the
  input products, which forces specific alternates (Supercomputer → OC
  Supercomputer, Automated Wiring → Automated Speed Wiring, EM Control Rod →
  EM Connection Rod) and removes most recipe ambiguity. Plastic resolves to 0.
- Only the 4 SET output targets are immutable. Input amounts follow from the
  website solve and are treated as the locked basis for this design.
- **Internal-consumption caveat:** the new themed factories themselves consume
  some items that are "already covered" net-positive today (Voltreach's Rigor
  Motor eats Crystal Oscillator; Copper Rotor eats Copper Sheet; Stator lines
  eat Wire; High-Speed Connector eats Circuit Board). Sizing the new factories
  may erode those surpluses. This must be re-checked in the amounts phase, not
  assumed away.

### 2.3 Authoritative targets and the gap

"Net now" = make − consume from `planner-export/current-production.txt`.

| Product | Need/min | Net now | Build target |
|---|--:|--:|--:|
| Aluminum Casing | 4,950 | 1,050 | **3,900** (gap) |
| Copper Powder | 1,000 | 0 | **1,000** (gap, new) |
| Rubber | 2,725 | 1,808 | **917** (gap) |
| Stator | 230 | −58 | **289** (gap) |
| Motor | 220 | 0 | **220** (gap) |
| Smart Plating | 150 | 0 | **150** (gap, new) |
| Steel Beam | 450 | 244 | **450** (full, new) |
| Cooling System | 150 | 3 | **150** (full, new) |
| High-Speed Connector | 115 | 30 | **115** (full, new) |
| Modular Frame | 38 | 14 | **38** (full, new) |
| Heavy Modular Frame | 95 | 29 | **+66** (scale existing 5) |

Per user override, Steel Beam / High-Speed Connector / Modular Frame / Cooling
System are built as full new dedicated production (existing output not counted
toward them). The rest are built to the computed gap.

**No new build (already over-covered):** Wire, Circuit Board, Computer, Rotor,
Crystal Oscillator. **Not needed:** Plastic (0 — forced OC Supercomputer path
uses none).

### 2.4 Input coverage check (all 17 simple.sft inputs)

Heavy Modular Frame → existing 5 (scaled) · High-Speed Connector → Cathera+ ·
Cooling System → Aldercast · Motor → Voltreach + Classic Iron · Rubber →
Naphtheon+ · Smart Plating → Ferrium+ · Aluminum Casing → Aldercast / Bauxhold
/ Silvashade · Stator → Moldmarsh + Voltreach · Copper Powder → Cathera+ ·
Steel Beam → Silvashade (Aluminum Beam) + Moldmarsh (cast) · Modular Frame →
Ferrium+ · Wire / Circuit Board / Computer / Rotor / Crystal Oscillator → no
new build · Plastic → not needed.

## 3. Factory-flavor design

Approach: mostly extend the existing themed factories, plus new themed
factories with distinct, intermixed-recipe identities (the same spirit as
Ferrium / Naphtheon / Forgeholm / Luxara / Cathera). Aluminium runs **three
distinct flavors**; Steel Beam and Motor each run **two distinct flavors** —
for variety, resilience, and to spread scarce-resource pressure. Factory names
are placeholders in the existing invented-place style.

### 3.1 New themed factories

The 3,900/min Aluminum Casing load is split across **three distinct aluminium
flavors**, each a different recipe identity and a different scarce-resource
pressure (the split fraction is decided in the amounts phase):

**① Aldercast — Alclad / Copper-fused**
- Chain: Sloppy Alumina → Electrode Aluminum Scrap (Petroleum Coke fed from
  Naphtheon) → Pure Aluminum Ingot → **Alclad Casing** (+ Copper Ingot).
- By-line: **Heat Exchanger** (Aluminum Casing + Rubber → Heat Sink) →
  **Cooling System** (+ Water + Nitrogen).
- Outputs: a share of Aluminum Casing · Cooling System 150.
- Identity: throughput-dense, copper + oil-coke intermix.

**② Bauxhold — Chemical / Sulfuric**
- Chain: **Instant Scrap** (Blender: Bauxite + Coal + Sulfuric Acid + Water →
  30/cyc) → Pure Aluminum Ingot → standard Aluminum Casing.
- Outputs: a share of Aluminum Casing.
- Identity: skips the Alumina/Refinery stages; the most Bauxite-stretching
  route; consumes the Sulfur surplus (+1,060).

**③ Silvashade — Classic Silica Foundry**
- Chain: standard Alumina Solution → Aluminum Scrap (Coal) → Aluminum Ingot
  (Foundry, + Silica) → standard Aluminum Casing.
- By-line: **Aluminum Beam** (3 Aluminum Ingot → 3 Steel Beam) off the same
  ingot output — a Steel Beam with zero iron/coal.
- Outputs: a share of Aluminum Casing · a share of Steel Beam.
- Identity: no copper; uses the Raw Quartz / Silica surplus (+391); the
  "pure aluminium" foundry, the Ferrium of aluminium.

**④ Voltreach — Electric Motion**
- Chain: **Copper Rotor** (Copper Sheet) + **Quickwire Stator** (Caterium
  high-speed wire) → **Rigor Motor** (+ Crystal Oscillator).
- Outputs: a share of Motor (electric) · Quickwire Stator.
- Identity: caterium/copper electrical motor, no iron rods/screws.

**⑤ Moldmarsh — Cast Steel**
- Chain: **Molded Beam** (Steel Ingot + Concrete, Foundry, 9/cyc) + **Molded
  Steel Pipe** → standard **Stator**.
- Outputs: a share of Steel Beam (cast) · a share of Stator.
- Identity: limestone/concrete-heavy Foundry casting works, distinct from
  Forgeholm's plain steel.

**⑥ Classic Iron Motor**
- Chain: standard **Rotor** (Iron Rod + Iron Screw) + standard **Stator** +
  standard **Motor**. May lean on Ferrium's iron for the Rotor leg.
- Outputs: a share of Motor (iron).

### 3.2 Targeted extensions of existing factories

- **Naphtheon+** (oil/polymer identity) → Rubber +917. Also supplies Petroleum
  Coke to Aldercast.
- **Cathera+** (caterium/copper identity) → High-Speed Connector 115 · Copper
  Powder 1,000.
- **Ferrium+** (pure iron plate/rod identity) → Smart Plating 150 · Modular
  Frame 38.

### 3.3 Heavy Modular Frame

Scaled +66/min across the existing 5 themed factories
(Ferrium / Naphtheon / Forgeholm / Luxara / Cathera). No redesign.

### 3.4 Who-makes-what map

| Factory | Flavor / signature recipes | Gap products it outputs |
|---|---|---|
| **Aldercast** (new) | Sloppy Alumina · Electrode Scrap · Pure Al Ingot · Alclad Casing · Heat Exchanger | Aluminum Casing (share) · Cooling System 150 |
| **Bauxhold** (new) | Instant Scrap (Blender) · Pure Al Ingot · std Casing | Aluminum Casing (share) |
| **Silvashade** (new) | std Alumina · Scrap · Foundry Al Ingot (+Silica) · std Casing · Aluminum Beam | Aluminum Casing (share) · Steel Beam (Al) share |
| **Voltreach** (new) | Copper Rotor · Quickwire Stator · Rigor Motor (+Crystal Osc.) | Motor (electric) share · Stator (quickwire) |
| **Moldmarsh** (new) | Molded Beam · Molded Steel Pipe (Foundry cast) | Steel Beam (cast) share · Stator share |
| **Classic Iron Motor** (new) | Std Rotor (Iron Rod+Screw) · Std Stator · std Motor | Motor (iron) share |
| **Naphtheon+** (extend) | existing oil/polymer | Rubber +917 |
| **Cathera+** (extend) | existing caterium/copper | High-Speed Connector 115 · Copper Powder 1,000 |
| **Ferrium+** (extend) | existing pure-iron plate/rod | Smart Plating 150 · Modular Frame 38 |
| **Ferrium/Naphtheon/Forgeholm/Luxara/Cathera** | existing HMF chains | Heavy Modular Frame — scale +66 |

### 3.5 Bauxite constraint (primary feasibility risk)

Bauxite is the scarcest resource — 3 nodes, already in deficit
(`planner-export/PLANNING-STATE.md`). Aluminum Casing at 3,900/min is the
heaviest raw demand in the plan and is Bauxite-bound. Mitigations baked into
the design:
- The 3 aluminium flavors consume Bauxite at different efficiencies; bias the
  split toward the most Bauxite-stretching route (Bauxhold's Instant Scrap,
  Aldercast's Sloppy Alumina).
- Lean on spare resources instead of more Bauxite where possible (Bauxhold →
  Sulfur surplus; Silvashade → Raw Quartz/Silica surplus).
- Aluminium factories are **multi-site**, sited near different Bauxite nodes;
  not one building cluster.

### 3.6 Cross-factory intermediate flows (known at design time)

- Naphtheon → Aldercast: Petroleum Coke (Electrode Scrap) and Rubber (Heat
  Exchanger / Cooling System).
- Copper feed → Aldercast (Alclad) and Voltreach (Copper Rotor / Copper
  Sheet); Caterium feed → Voltreach (Quickwire Stator).
- Wire feed → Stator lines; Rotor feed → Ferrium+ Smart Plating.

## 4. Scope boundaries

- **In scope (this spec):** the set of factory flavors, their signature recipe
  chains, which gap products each produces, and the locked target basis.
- **Deferred to next phase:** the Aluminum Casing 3,900 split across
  Aldercast / Bauxhold / Silvashade; the Motor and Steel Beam splits between
  their flavors; per-factory building counts / module sizing; locations and
  node assignments; Bauxite feasibility resolution; re-checking internal
  consumption (§2.2) against the net-positive items.
- **Unchanged:** the existing 5 themed HMF factories' recipe chains; the
  Factory Crazy 2-stage build methodology; `PLANNING-STATE.md` as the
  canonical planning reference.

## 5. Next steps

1. Decide the Aluminum Casing split across the 3 aluminium flavors, and the
   Motor / Steel Beam splits between their flavors.
2. Size each factory (modules / building counts) under the Factory Crazy
   constraints.
3. Resolve Bauxite siting/feasibility for the multi-site aluminium factories.
4. Assign locations against unoccupied nodes (`occupied-nodes.json`).
5. Re-check internal consumption vs the net-positive items (§2.2).
6. Regenerate `PLANNING-STATE.md` to reflect the new factories.
