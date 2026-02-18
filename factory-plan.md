# Satisfactory HMF Factory Plan

*Generated 2026-02-15*

## Overview

- **Target:** 95 Heavy Modular Frames/min
- **Factories:** 5 themed mini-factories
- **Strategy:** Iron shipped by train (except Ferrium). Local resources mined within 500m.
- **Miners:** Mk.3 @ 250% overclock, capped by Mk.5 belt (780/min)
- **Effort model:** Local extraction = 1x, Train import = 2x, Water = 3x

## Allocation Summary

| Factory | Theme | HMF/min | Buildings | Power (MW) | Self-sufficient? |
|---------|-------|---------|-----------|------------|------------------|
| Ferrium | Pure Iron | 18.9 | 238 | 1703 | Train: Limestone |
| Naphtheon | Oil Ecosystem | 21.3 | 373 | 4175 | Train: Iron Ore |
| Forgeholm | Steel Spine | 17.3 | 232 | 2661 | Yes |
| Luxara | Aluminum Replacement | 8.4 | 194 | 1678 | Train: Iron Ore, Limestone + Water |
| Cathera | Copper & Caterium | 29.1 | 250 | 2994 | Yes |
| **Total** | | **95.0** | **1287** | **13211** | |

---

## Ferrium — Pure Iron (18.9 HMF/min)

**Location:** (279838, -181875)  
**Effort:** 5518  
**Total buildings:** 238  
**Total power:** 1703 MW

> Monolithic. Every intermediate derives from iron. No Foundries, no Refineries. Two raw inputs, one output. The purest HMF factory possible.

### Raw Resources

| Resource | Per HMF | Total/min | Local Cap | Local Used | Train Import | Source |
|----------|---------|-----------|-----------|------------|-------------|--------|
| Iron Ore | 179.0 | 3390 | 8280 | 3390 | 0 | All Local |
| Limestone | 72.0 | 1364 | 600 | 600 | 764 | Mixed |

### Local Resource Nodes (within 500m)

| Resource | Nodes | Pure | Normal | Impure | Capacity |
|----------|-------|------|--------|--------|----------|
| Iron | 15 | 6 | 3 | 6 | 8280/min |
| Limestone | 2 | 0 | 0 | 2 | 600/min |

### Production Chain

| # | Item | Recipe | Building | Count | Clock% | Power (MW) |
|---|------|--------|----------|-------|--------|------------|
| 1 | Heavy Modular Frame | Alternate: Heavy Encased Frame | Manufacturer | 7 | 6×100% + 1×73% | 367 |
| 2 | Modular Frame | Alternate: Steeled Frame | Assembler | 17 | 16×100% + 1×84% | 252 |
| 3 | Reinforced Iron Plate | Alternate: Stitched Iron Plate | Assembler | 6 | 5×100% + 1×99% | 90 |
| 4 | Wire | Alternate: Iron Wire | Constructor | 10 | 9×100% + 1×98% | 40 |
| 5 | Iron Plate | Iron Plate | Constructor | 6 | 5×100% + 1×61% | 22 |
| 6 | Steel Pipe | Alternate: Iron Pipe | Constructor | 31 | 30×100% + 1×98% | 124 |
| 7 | Encased Industrial Beam | Alternate: Encased Industrial Pipe | Assembler | 16 | 15×100% + 1×78% | 236 |
| 8 | Concrete | Concrete | Constructor | 31 | 30×100% + 1×30% | 121 |
| 9 | Iron Ingot | Iron Ingot | Smelter | 114 | 113×100% + 1×1% | 452 |

### Building Summary

| Building | Count |
|----------|-------|
| Assembler | 39 |
| Constructor | 78 |
| Manufacturer | 7 |
| Smelter | 114 |

---

## Naphtheon — Oil Ecosystem (21.3 HMF/min)

**Location:** (53864, -1143)  
**Effort:** 5518  
**Total buildings:** 373  
**Total power:** 4175 MW

> Circular economy. Heavy Oil Residue from Plastic and Rubber becomes Petroleum Coke for steel smelting. Oil pipes run alongside iron belts. Three raw resources, zero waste.

### Raw Resources

| Resource | Per HMF | Total/min | Local Cap | Local Used | Train Import | Source |
|----------|---------|-----------|-----------|------------|-------------|--------|
| Iron Ore | 94.2 | 2008 | 0 | 0 | 2008 | All Train |
| Crude Oil | 50.6 m³ | 1078 m³ | 1200 m³ | 1078 m³ | 0 m³ | All Local |
| Limestone | 20.0 | 426 | 600 | 426 | 0 | All Local |

### Local Resource Nodes (within 500m)

| Resource | Nodes | Pure | Normal | Impure | Capacity |
|----------|-------|------|--------|--------|----------|
| Limestone | 1 | 0 | 1 | 0 | 600/min |
| Oil | 3 | 1 | 2 | 0 | 1200 m³/min |

### Production Chain

| # | Item | Recipe | Building | Count | Clock% | Power (MW) |
|---|------|--------|----------|-------|--------|------------|
| 1 | Heavy Modular Frame | Alternate: Heavy Flexible Frame | Manufacturer | 6 | 5×100% + 1×68% | 308 |
| 2 | Modular Frame | Modular Frame | Assembler | 54 | 53×100% + 1×25% | 797 |
| 3 | Reinforced Iron Plate | Alternate: Adhered Iron Plate | Assembler | 43 | 42×100% + 1×60% | 638 |
| 4 | Iron Plate | Alternate: Coated Iron Plate | Assembler | 7 | 6×100% + 1×39% | 94 |
| 5 | Screw | Screws | Constructor | 56 | 55×100% + 1×38% | 221 |
| 6 | Iron Rod | Iron Rod | Constructor | 80 | 79×100% + 1×52% | 318 |
| 7 | Iron Ingot | Iron Ingot | Smelter | 48 | 47×100% + 1×75% | 191 |
| 8 | Encased Industrial Beam | Encased Industrial Beam | Assembler | 11 | 10×100% + 1×65% | 158 |
| 9 | Steel Beam | Steel Beam | Constructor | 13 | 12×100% + 1×78% | 51 |
| 10 | Steel Ingot | Alternate: Coke Steel Ingot | Foundry | 8 | 7×100% + 1×67% | 121 |
| 11 | Concrete | Alternate: Rubber Concrete | Assembler | 5 | 4×100% + 1×26% | 62 |
| 12 | Rubber | Rubber | Refinery | 34 | 33×100% + 1×55% | 1004 |
| 13 | Plastic | Plastic | Refinery | 3 | 2×100% + 1×40% | 69 |
| 14 | Petroleum Coke | Petroleum Coke | Refinery | 5 | 4×100% + 1×79% | 142 |

### Building Summary

| Building | Count |
|----------|-------|
| Assembler | 120 |
| Constructor | 149 |
| Foundry | 8 |
| Manufacturer | 6 |
| Refinery | 42 |
| Smelter | 48 |

---

## Forgeholm — Steel Spine (17.3 HMF/min)

**Location:** (125551, -24977)  
**Effort:** 5518  
**Total buildings:** 232  
**Total power:** 2661 MW

> Steel mill. Foundries dominate the floor making Steel Ingot. Steel Screws at 260/min are the star — one building does the work of six. Limestone appears only for EIB concrete. Pure iron-and-coal industry.

### Raw Resources

| Resource | Per HMF | Total/min | Local Cap | Local Used | Train Import | Source |
|----------|---------|-----------|-----------|------------|-------------|--------|
| Iron Ore | 125.6 | 2170 | 2340 | 2170 | 0 | All Local |
| Coal | 119.0 | 2055 | 2940 | 2055 | 0 | All Local |
| Limestone | 75.0 | 1295 | 1380 | 1295 | 0 | All Local |

### Local Resource Nodes (within 500m)

| Resource | Nodes | Pure | Normal | Impure | Capacity |
|----------|-------|------|--------|--------|----------|
| Coal | 4 | 3 | 1 | 0 | 2940/min |
| Iron | 3 | 3 | 0 | 0 | 2340/min |
| Limestone | 2 | 1 | 1 | 0 | 1380/min |

### Production Chain

| # | Item | Recipe | Building | Count | Clock% | Power (MW) |
|---|------|--------|----------|-------|--------|------------|
| 1 | Heavy Modular Frame | Heavy Modular Frame | Manufacturer | 9 | 8×100% + 1×64% | 470 |
| 2 | Modular Frame | Alternate: Steeled Frame | Assembler | 29 | 28×100% + 1×78% | 431 |
| 3 | Reinforced Iron Plate | Reinforced Iron Plate | Assembler | 12 | 11×100% + 1×51% | 171 |
| 4 | Screw | Alternate: Steel Screws | Constructor | 11 | 10×100% + 1×63% | 42 |
| 5 | Iron Plate | Alternate: Steel Cast Plate | Foundry | 8 | 7×100% + 1×68% | 122 |
| 6 | Steel Pipe | Steel Pipe | Constructor | 58 | 57×100% + 1×57% | 230 |
| 7 | Steel Beam | Steel Beam | Constructor | 4 | 3×100% + 1×54% | 14 |
| 8 | Encased Industrial Beam | Alternate: Encased Industrial Pipe | Assembler | 22 | 21×100% + 1×59% | 322 |
| 9 | Concrete | Concrete | Constructor | 29 | 28×100% + 1×78% | 115 |
| 10 | Steel Ingot | Steel Ingot | Foundry | 46 | 45×100% + 1×66% | 729 |
| 11 | Iron Ingot | Iron Ingot | Smelter | 4 | 3×100% + 1×84% | 15 |

### Building Summary

| Building | Count |
|----------|-------|
| Assembler | 63 |
| Constructor | 102 |
| Foundry | 54 |
| Manufacturer | 9 |
| Smelter | 4 |

---

## Luxara — Aluminum Replacement (8.4 HMF/min)

**Location:** (198574, 98588)  
**Effort:** 5518  
**Total buildings:** 194  
**Total power:** 1678 MW

> High-tech. The complex Bauxite refining chain (Alumina Solution -> Aluminum Scrap -> Aluminum Ingot) replaces simple iron smelting for rods and beams. Fewer buildings needed per item thanks to 3.5x throughput on Aluminum Rod.

### Raw Resources

| Resource | Per HMF | Total/min | Local Cap | Local Used | Train Import | Source |
|----------|---------|-----------|-----------|------------|-------------|--------|
| Iron Ore | 97.5 | 820 | 780 | 780 | 40 | Mixed |
| Coal | 43.4 | 365 | 2100 | 365 | 0 | All Local |
| Limestone | 90.0 | 757 | 600 | 600 | 157 | Mixed |
| Bauxite | 80.4 | 676 | 900 | 676 | 0 | All Local |
| Water | 107.1 m³ | 901 m³ | ∞ (extractors) | 901 m³ | — | Water (3x effort, 8 extractors) |

### Local Resource Nodes (within 500m)

| Resource | Nodes | Pure | Normal | Impure | Capacity |
|----------|-------|------|--------|--------|----------|
| Bauxite | 2 | 0 | 1 | 1 | 900/min |
| Coal | 6 | 0 | 1 | 5 | 2100/min |
| Iron | 1 | 1 | 0 | 0 | 780/min |
| Limestone | 1 | 0 | 1 | 0 | 600/min |

### Production Chain

| # | Item | Recipe | Building | Count | Clock% | Power (MW) |
|---|------|--------|----------|-------|--------|------------|
| 1 | Heavy Modular Frame | Heavy Modular Frame | Manufacturer | 5 | 4×100% + 1×20% | 227 |
| 2 | Modular Frame | Modular Frame | Assembler | 22 | 21×100% + 1×2% | 315 |
| 3 | Reinforced Iron Plate | Reinforced Iron Plate | Assembler | 13 | 12×100% + 1×62% | 188 |
| 4 | Screw | Screws | Constructor | 45 | 44×100% + 1×15% | 176 |
| 5 | Iron Rod | Alternate: Aluminum Rod | Constructor | 14 | 13×100% + 1×22% | 52 |
| 6 | Iron Plate | Iron Plate | Constructor | 19 | 18×100% + 1×92% | 76 |
| 7 | Steel Pipe | Steel Pipe | Constructor | 9 | 8×100% + 1×41% | 33 |
| 8 | Encased Industrial Beam | Encased Industrial Beam | Assembler | 8 | 7×100% + 1×1% | 105 |
| 9 | Steel Beam | Alternate: Aluminum Beam | Constructor | 6 | 5×100% + 1×61% | 22 |
| 10 | Concrete | Concrete | Constructor | 17 | 16×100% + 1×82% | 67 |
| 11 | Iron Ingot | Iron Ingot | Smelter | 19 | 18×100% + 1×92% | 76 |
| 12 | Steel Ingot | Steel Ingot | Foundry | 6 | 5×100% + 1×61% | 88 |
| 13 | Aluminum Ingot | Aluminum Ingot | Foundry | 4 | 3×100% + 1×76% | 59 |
| 14 | Aluminum Scrap | Aluminum Scrap | Refinery | 1 | 1×94% | 28 |
| 15 | Alumina Solution | Alumina Solution | Refinery | 6 | 5×100% + 1×63% | 166 |

### Building Summary

| Building | Count |
|----------|-------|
| Assembler | 43 |
| Constructor | 110 |
| Foundry | 10 |
| Manufacturer | 5 |
| Refinery | 7 |
| Smelter | 19 |

---

## Cathera — Copper & Caterium (29.1 HMF/min)

**Location:** (75657, -98308)  
**Effort:** 5518  
**Total buildings:** 250  
**Total power:** 2994 MW

> Multi-ore diversity. Three smelting lines (Iron Alloy in Foundries, Copper in Smelters, Caterium in Smelters) feed diverging paths that reconverge at RIP. Copper enters at two levels — alloyed into Iron Ingot AND smelted for Fused Wire. No coal, no oil. Exotic ores as primary inputs.

### Raw Resources

| Resource | Per HMF | Total/min | Local Cap | Local Used | Train Import | Source |
|----------|---------|-----------|-----------|------------|-------------|--------|
| Iron Ore | 92.0 | 2675 | 4680 | 2675 | 0 | All Local |
| Copper Ore | 24.6 | 715 | 780 | 715 | 0 | All Local |
| Caterium Ore | 1.2 | 34 | 600 | 34 | 0 | All Local |
| Limestone | 72.0 | 2094 | 4080 | 2094 | 0 | All Local |

### Local Resource Nodes (within 500m)

| Resource | Nodes | Pure | Normal | Impure | Capacity |
|----------|-------|------|--------|--------|----------|
| Caterium | 1 | 0 | 1 | 0 | 600/min |
| Copper | 1 | 1 | 0 | 0 | 780/min |
| Iron | 6 | 6 | 0 | 0 | 4680/min |
| Limestone | 7 | 1 | 5 | 1 | 4080/min |

### Production Chain

| # | Item | Recipe | Building | Count | Clock% | Power (MW) |
|---|------|--------|----------|-------|--------|------------|
| 1 | Heavy Modular Frame | Alternate: Heavy Encased Frame | Manufacturer | 11 | 10×100% + 1×34% | 563 |
| 2 | Modular Frame | Alternate: Steeled Frame | Assembler | 26 | 25×100% + 1×86% | 387 |
| 3 | Reinforced Iron Plate | Alternate: Stitched Iron Plate | Assembler | 10 | 9×100% + 1×20% | 137 |
| 4 | Wire | Alternate: Fused Wire | Assembler | 4 | 3×100% + 1×83% | 57 |
| 5 | Iron Plate | Iron Plate | Constructor | 9 | 8×100% + 1×62% | 34 |
| 6 | Steel Pipe | Alternate: Iron Pipe | Constructor | 48 | 47×100% + 1×58% | 190 |
| 7 | Encased Industrial Beam | Alternate: Encased Industrial Pipe | Assembler | 25 | 24×100% + 1×24% | 362 |
| 8 | Concrete | Concrete | Constructor | 47 | 46×100% + 1×54% | 186 |
| 9 | Iron Ingot | Alternate: Iron Alloy Ingot | Foundry | 67 | 66×100% + 1×88% | 1070 |
| 10 | Copper Ingot | Copper Ingot | Smelter | 2 | 1×100% + 1×53% | 6 |
| 11 | Caterium Ingot | Caterium Ingot | Smelter | 1 | 1×77% | 3 |

### Building Summary

| Building | Count |
|----------|-------|
| Assembler | 65 |
| Constructor | 104 |
| Foundry | 67 |
| Manufacturer | 11 |
| Smelter | 3 |

---

## Train Network

Resources that must be imported by train:

| Resource | Total Demand/min | Consumers |
|----------|-----------------|-----------|
| Iron Ore | 2048 | Naphtheon, Luxara |
| Limestone | 921 | Ferrium, Luxara |

---

## Resource Extraction Sites

Recommended mining outposts to supply train-imported resources.

### Iron Ore Sites (train demand: 2048/min)

| Site | Location | Nodes | Purity | Capacity | Notes |
|------|----------|-------|--------|----------|-------|
| Iron Hub Alpha | (241941, 3242) | 8 | 3P 5N 0I | 5340/min | Best iron cluster. Near Luxara (1,047m) and Forgeholm (1,198m). |
| Iron Hub Beta | (179893, -118392) | 2 | 2P 0N 0I | 1560/min | Between Cathera, Forgeholm, Ferrium. Strategic for multi-factory. |
| Iron West Gamma | (-218000, -119429) | 7 | 4P 3N 0I | 4920/min | Remote western site. High purity but far from all factories. |

### Limestone Sites (train demand: 921/min)

| Site | Location | Nodes | Purity | Capacity | Notes |
|------|----------|-------|--------|----------|-------|
| Limestone Central | (169486, -45968) | 4 | 1P 3N 0I | 2580/min | Reachable by 4 factories. Near Forgeholm (487m). |
| Limestone South | (168003, -86516) | 3 | 0P 3N 0I | 1800/min | Near Forgeholm and Cathera. Closest unclaimed to Ferrium route. |
| Limestone West | (-195258, -135899) | 6 | 5P 1N 0I | 4500/min | Massive capacity. Remote but highest purity cluster on map. |

### Recommended Extraction Plan

**Iron Ore** (2048/min needed):
- **Iron Hub Alpha** (241941, 3242): 5,340/min from 8 nodes (3P+5N)
  - Supplies Naphtheon via train (~2,007/min)
  - Supplies Luxara via train (~40/min)
  - Excess capacity: 3292/min for future expansion

**Limestone** (921/min needed):
- **Limestone Central** (169486, -45968): 2,580/min from 4 nodes (1P+3N)
  - Near Forgeholm (487m), serves as central distribution hub
  - Supplies Ferrium via train (~764/min)
  - Supplies Luxara via train (~157/min)
  - Excess capacity: 1659/min for future expansion
