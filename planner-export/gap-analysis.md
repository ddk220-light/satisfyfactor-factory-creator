# Gap Analysis — What's Still Needed for the Space Elevator Goal

## Methodology (important)

**Only the production targets explicitly declared in the `.sft` factory-plan
tabs are determined needs.** Those are the "set" formulas. Every intermediate
the chain *might* consume (Copper Sheet, Circuit Board, Computer, Rotor,
Reinforced Iron Plate, etc.) is **flexible** — its quantity depends on which
alternate recipes get chosen, and those choices are not locked. Do **not**
treat decomposed intermediates as fixed needs; a default-recipe decomposition
(e.g. "3,690 Copper Sheet/min") is **not** a real requirement.

**Sources:** `*.sft` (the plan's set targets), `current-production.txt` (live
factory output), `*.sav` (occupied nodes).

## The only determined needs — set sub-factory production targets

| Item | Target/min | Currently make/min | Gap | Status |
|---|--:|--:|--:|---|
| **Aluminum Casing** | 5,000 | 1,350 | **−3,650** | scale up hugely |
| **Steel Beam** | 900 | 302 | **−598** | scale up |
| **Motor** | 250 | 45 | **−205** | scale up |
| **Smart Plating** | 150 | 0 | **−150** | build new |
| **Stator** | 250 | 120 | **−130** | scale up |
| **Heavy Modular Frame** | 95 | 35 | **−60** | scale up |
| Modular Frame | 75 | 148 | **+74** | ✓ already enough |
| Magnetic Field Generator | 30 | 0 | −30 | build (final assembly) |
| Thermal Propulsion Rocket | 30 | 0 | −30 | build (final assembly) |
| Nuclear Pasta | 5 | 0 | −5 | build (final assembly) |

Note: the MFG / TPR / Nuclear Pasta tabs in the raw `.sft` declare **2× the
main factory's actual need** (a known mistake). The targets above are already
**corrected (halved)**: MFG 60→30, TPR 60→30, Nuclear Pasta 10→5 — matching the
main factory's real consumption. Stator and Aluminum Casing are *not* simple
2× cases (their true need depends on flexible recipes) and are left as declared.

The 5 themed HMF factories in this repo cover the **Heavy Modular Frame 95/min**
line of the Stator sub-factory.

## Main factory end goal (assembled from the above, no raw mining)

Assembly Director System 30 · Thermal Propulsion Rocket 30 · Magnetic Field
Generator 30 · Nuclear Pasta 5 (per min).

## What this means

To still make / scale, in priority order:
1. **Aluminum Casing** — by far the largest gap (−3,650/min vs the 5,000 target)
2. **Steel Beam** — −598/min
3. **Motor** — −205/min
4. **Smart Plating** — −150/min (no production at all yet)
5. **Stator** — −130/min
6. **Heavy Modular Frame** — −60/min (the 5 themed factories' job)
7. Final assembly lines: MFG, TPR, Nuclear Pasta (none built yet)

**Modular Frame is already covered** (148 made vs 75 target).

Everything below these set targets — the intermediate sub-products and their
recipes — is an open optimization, not a fixed requirement, and will be
determined when each flexible sub-plan is actually designed.
