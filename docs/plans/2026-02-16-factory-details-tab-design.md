# Factory Details Tab — Design Document

**Date:** 2026-02-16
**Goal:** Add a "Factories" tab to factory-map.html showing detailed module info for each factory in the 95 HMF plan, with production chain flow diagrams and module anchor callouts.

## Overview

Add a tab bar to the existing factory-map.html page. The "Map" tab shows the current canvas-based map. The new "Factories" tab shows a scrollable page with detailed factory module information loaded from `factory-subunits.json`.

## Architecture Decisions

- **Vanilla JS/CSS/HTML** — no frameworks, matching existing codebase
- **CSS/HTML flow diagram** with SVG arrow connectors (not Canvas)
- **Data via fetch()** — load factory-subunits.json at runtime
- **Tab switching** via JS state variable (no URL routing)

## Tab Bar & Page Structure

Top-level tab bar with two tabs: **Map** | **Factories**.

- "Map" active: existing sidebar + canvas layout renders as-is
- "Factories" active: full-width scrollable `<div>` replaces sidebar + canvas
- Tab bar styled to match existing dark theme: `#0d1117` bg, `#ccc` text, `Courier New` font

## Factories Tab Layout

### Global Summary Banner

At the top, before individual factory cards:

- Title from meta: "HMF-95 Factory Modules (v3 — Shard-Optimized)"
- Module basis and shard budget (196/200)
- Summary table: one row per factory showing target HMF, copies needed, shards, building count
- Totals row at bottom
- Each row clickable → scrolls to that factory's card
- Left accent colored with factory theme color

### Factory Cards (×5, scrolling)

Quick anchor nav at top: `[Ferrium] [Naphtheon] [Forgeholm] [Luxara] [Cathera]`

Each factory card has three vertical sections:

#### A. Header Banner

- Factory name + theme (e.g., "FERRIUM — Pure Iron")
- Left border in factory color (`ferrium: #e74c3c`, `naphtheon: #9b59b6`, `forgeholm: #3498db`, `luxara: #f1c40f`, `cathera: #1abc9c`)
- HMF recipe name
- Output rate: `X HMF/min per module × N copies → Y HMF/min`
- Stats: buildings, power (MW), shards per module
- Raw inputs as small pills with rates

#### B. Production Chain Flow Diagram

Left-to-right DAG layout:

- **Layout:** Topological sort assigns columns (layers). Raw inputs on left, Manufacturer on right. Items at same depth stack vertically.
- **Standard nodes:** Item name (bold), building count + type, output rate
- **Manufacturer node (MODULE ANCHOR):** Double border in factory color, starred, "MODULE ANCHOR" label, scaling info (copies × rate = target)
- **Overclocked nodes:** Highlighted border + shard icon (`⚡ N shards`)
- **Connectors:** SVG arrows between nodes showing item flow. Arrow labels show flow rate.
- **Hover tooltips:** Full details — recipe name, exact building count, clock %, overclock detail, all I/O rates, power

#### C. Building Summary

Compact horizontal grid: `Smelter ×17 | Constructor ×12 | Assembler ×5 | Manufacturer ×1`

## Flow Diagram Technical Details

### DAG Construction

For each factory module, build a dependency graph from the `steps` array:

1. Each step produces one primary item (`step.item`)
2. Each step consumes items from `step.inputs`
3. If an input matches another step's output → that's an edge
4. If an input doesn't match any step's output → it's a raw input

### Topological Layer Assignment

- Raw inputs: layer 0
- Each subsequent item: max(layer of all inputs) + 1
- Manufacturer (HMF output): rightmost layer

### Rendering

- CSS Grid container with columns = number of layers
- Each layer is a vertical flex column of nodes
- SVG overlay (absolute positioned) draws connector arrows between nodes
- Arrow routing: simple horizontal+vertical paths (no curve needed)

### Responsive Behavior

- Flow diagram scrolls horizontally on narrow screens
- Cards are full-width with max-width constraint for readability

## Data Source

`factory-subunits.json` loaded via `fetch()`. Key fields used:

- `meta.*` — global title, shard budget
- `modules[id].theme`, `.hmf_recipe`, `.hmf_per_min` — header info
- `modules[id].raw_inputs` — raw input pills
- `modules[id].steps[]` — production chain nodes
- `modules[id].building_totals` — building summary
- `modules[id].total_buildings`, `.total_power_mw`, `.shards_per_module` — stats
- `modules[id].target_hmf`, `.copies_needed_ceil` — scaling info
- `summary[]` — global summary table
