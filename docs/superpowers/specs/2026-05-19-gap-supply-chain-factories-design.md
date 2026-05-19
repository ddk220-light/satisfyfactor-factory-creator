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

## 3. Factory-flavor design

Approach: mostly extend the existing themed factories, plus a small number of
new themed factories with distinct, intermixed-recipe identities (the same
spirit as Ferrium / Naphtheon / Forgeholm / Luxara / Cathera). Steel Beam and
Motor each run **two distinct flavors** for variety and resilience. Factory
names are placeholders in the existing invented-place style.

### 3.1 New themed factories

**① Aldercast — Alclad Aluminum (multi-site)**
- Signature chain: Sloppy Alumina → Electrode Aluminum Scrap (Petroleum Coke
  fed from Naphtheon) → Pure Aluminum Ingot → **Alclad Casing** (+ Copper
  Ingot).
- By-lines off the same aluminum ingots: **Aluminum Beam** (→ Steel Beam, zero
  iron/coal) and **Heat Exchanger** (Aluminum Casing + Rubber → Heat Sink) →
  **Cooling System** (+ Water + Nitrogen).
- Outputs: Aluminum Casing 3,900 · Cooling System 150 · a share of Steel Beam.
- **Binding constraint:** Bauxite is the scarcest resource (3 nodes, already
  in deficit — `planner-export/PLANNING-STATE.md`). Aluminum Casing at
  3,900/min is the heaviest raw demand in the plan and is Bauxite-bound.
  Design consequences: use the most Bauxite-efficient sub-chain (Sloppy
  Alumina; evaluate Instant Scrap via Blender to stretch Bauxite); treat
  Aldercast as **2+ sited factories near different Bauxite nodes** from the
  start. This is the plan's primary feasibility risk.

**② Voltreach — Electric Motion**
- Signature chain: **Copper Rotor** (Copper Sheet) + **Quickwire Stator**
  (Caterium high-speed wire) → **Rigor Motor** (+ Crystal Oscillator).
- Identity: a caterium/copper electrical motor with no iron rods/screws.
- Outputs: a share of Motor (electric) · Quickwire Stator.

**③ Moldmarsh — Cast Steel**
- Signature chain: **Molded Beam** (Steel Ingot + Concrete, Foundry, 9/cycle)
  + **Molded Steel Pipe** → standard **Stator**.
- Identity: limestone/concrete-heavy Foundry casting works, distinct from
  Forgeholm's plain steel.
- Outputs: a share of Steel Beam (cast) · a share of Stator.

**④ Classic Iron Motor**
- Signature chain: standard **Rotor** (Iron Rod + Iron Screw) + standard
  **Stator** + standard **Motor**. May lean on Ferrium's iron output for the
  Rotor leg.
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

### 3.4 Cross-factory intermediate flows (known at design time)

- Naphtheon → Aldercast: Petroleum Coke (for Electrode Aluminum Scrap).
- Naphtheon → Aldercast: Rubber (for Heat Exchanger / Cooling System).
- Copper feed → Aldercast (Alclad Casing) and Voltreach (Copper Rotor / Copper
  Sheet); Caterium feed → Voltreach (Quickwire Stator).
- Wire feed → Stator lines (Wire is already net-positive).

## 4. Scope boundaries

- **In scope (this spec):** the set of factory flavors, their signature recipe
  chains, which gap products each produces, and the locked target basis.
- **Deferred to next phase:** the quantity split of Motor and Steel Beam
  between their two flavors; per-factory building counts / module sizing;
  factory locations and node assignments; Bauxite feasibility resolution for
  Aldercast.
- **Unchanged:** the existing 5 themed HMF factories' recipe chains; the
  Factory Crazy 2-stage build methodology; `PLANNING-STATE.md` as the
  canonical planning reference.

## 5. Next steps

1. Decide Motor and Steel Beam quantity splits between flavors.
2. Size each factory (modules / building counts) under the Factory Crazy
   constraints.
3. Resolve Bauxite siting/feasibility for Aldercast (multi-site).
4. Assign locations against unoccupied nodes (`occupied-nodes.json`).
5. Regenerate `PLANNING-STATE.md` to reflect the new factories.
