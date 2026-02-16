# Satisfactory Factory Planner App — Design Document

**Date:** 2026-02-16
**Goal:** Web app that takes a user from "I want X items/min" to a complete multi-factory plan with locations, allocations, building counts, and modular blueprints.

## Overview

A FastAPI + React monolith deployed to Railway. The existing Python calculation scripts become backend engine modules. A wizard guides users through preferences, recipe selection, and map-based location picking, then presents a dashboard with the full plan.

## Architecture

Single deployable container:

```
┌─────────────────────────────────────┐
│           Railway Container          │
│  ┌──────────┐    ┌────────────────┐ │
│  │  FastAPI  │    │  React SPA     │ │
│  │  /api/*   │◄───│  (static)      │ │
│  │           │    │  Leaflet maps  │ │
│  └────┬─────┘    └────────────────┘ │
│       │                              │
│  ┌────▼─────┐                        │
│  │ SQLite   │                        │
│  │ (read-only, bundled)              │
│  └──────────┘                        │
└─────────────────────────────────────┘
```

- **Backend:** FastAPI serving API endpoints + static React build
- **Database:** SQLite bundled in container (read-only game data)
- **Frontend:** React + Vite + Leaflet maps
- **Deployment:** Multi-stage Dockerfile, single Railway service

## Data Layer

### Existing Tables (unchanged)

`buildings`, `items`, `recipes`, `recipe_ingredients`, `recipe_products`, `recipe_buildings`, `schematics` — full Satisfactory game data.

### New Data

**`resource_nodes` table** — migrated from JSON for spatial queries:

| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| type | TEXT |
| purity | TEXT (pure/normal/impure) |
| x | REAL |
| y | REAL |
| z | REAL |

**`themes.json`** — universal resource-based factory themes:

Pre-built themes: Iron Works, Oil Refinery, Coal Forge, Copper Electronics, Bauxite Refinery, Sulfur Works, Quartz Processing, Uranium Complex. Each defined by primary raw resources and allowed building types.

**`plans` table** (stretch) — saved user plans with UUID, timestamps, preferences JSON, result JSON.

## API Endpoints

### Setup
- `GET /api/items/targets` — viable target items (complex production chains)
- `GET /api/recipes?item_id=X` — all recipes producing item X, including alternates
- `GET /api/themes` — available resource themes

### Computation Pipeline
- `POST /api/plan/analyze` — decompose production chain for target item + recipe selection, determine applicable themes
- `POST /api/plan/locations` — find top N candidate locations per theme, scored by resource proximity
- `POST /api/plan/allocate` — effort-balanced allocation across factories (binary search)
- `POST /api/plan/generate` — full plan: building counts, power, modules, train network

### Map
- `GET /api/map/nodes` — all resource nodes for Leaflet overlay

All computation endpoints are stateless — full inputs in request body.

## User Preferences

Captured at wizard start:

| Preference | Input Type | Default |
|-----------|-----------|---------|
| Target item | Searchable dropdown | — |
| Target rate (items/min) | Slider + manual input | — |
| Number of factories | Slider 1-8 or "auto" | Auto |
| Optimization | Radio: Balanced / Min Buildings / Min Power | Balanced |
| Train penalty | Slider 2x-10x | 2x |
| Max local resource radius | Slider 200m-1000m | 500m |
| Quadrant exclusions | Click minimap regions | None |
| Recipe include/exclude | Toggle per alternate recipe | All defaults |

## Wizard Flow

### Stage 1: Preferences
Set all preferences above. Searchable item picker, sliders, minimap for quadrant exclusion.

### Stage 2: Recipe Selection
- Call `/api/plan/analyze` with target item + rate + recipe list
- Display recipe tree as interactive DAG
- Click recipe nodes to toggle default/alternate/exclude
- Sidebar shows which resource themes activate based on selections
- Re-analyze updates theme assignments live

### Stage 3: Location Selection (map-based)
- Full-screen Leaflet map with resource nodes
- Call `/api/plan/locations` — candidates shown as colored circles per theme
- Click to select one location per theme
- Overlap warnings if factories share resource nodes
- Score breakdown in sidebar
- "Auto-select best" button picks optimal non-overlapping set

### After Stage 3 → compute allocation + full plan → Dashboard

## Dashboard

Non-linear exploration of the completed plan.

**Global Summary Banner:** Total buildings, power, train imports, factory count.

**Tabs:**
- **Factories** — cards with DAG flow diagrams, click into per-factory details (buildings, power, resources)
- **Map** — interactive map with factory locations, mining towns, train routes, resource nodes
- **Modules** — per-factory stamp-copy breakdown, building counts per module, shard allocation
- **Export** — download as JSON or Markdown

## Recipe-to-Theme Assignment Algorithm

Core new logic for arbitrary target items:

1. **Build recipe DAG** — trace from target item through all recipes (respecting include/exclude) to raw resources
2. **Aggregate raw resource demands** per unit of target item
3. **Assign recipes to themes by dominant resource:**
   - Recipe with inputs from one theme → that theme
   - Recipe spanning multiple themes → theme of the rarest resource
   - Intermediate recipes → theme of their most complex input
4. **No cross-factory intermediate sharing** — each factory produces its own intermediates (self-contained)
5. **All resources are trainable** — effort model handles preference via penalty multiplier:
   - Local: 1x effort
   - Train import: user's penalty (2x-10x)
   - Rarer resources naturally drive location selection (fewer nodes on map)
6. **Collapse unnecessary themes** — if a theme has trivial demand (<5%), merge into nearest related theme. Cap at user's requested factory count.

## Effort Model

```
effort = Σ(local_demand × 1.0) + Σ(train_demand × train_penalty) + Σ(water_demand × 3.0)
```

Allocation uses binary search to find the balanced effort level where total output = target rate.

## Project Structure

```
satisfy/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── db.py                      # SQLite helpers
│   ├── models.py                  # Pydantic models
│   ├── routers/
│   │   ├── items.py               # /api/items/*, /api/recipes
│   │   ├── themes.py              # /api/themes
│   │   ├── plan.py                # /api/plan/*
│   │   └── map.py                 # /api/map/*
│   ├── engine/
│   │   ├── recipe_graph.py        # DAG builder, chain decomposition
│   │   ├── theme_assigner.py      # Recipe-to-theme partitioning
│   │   ├── location_finder.py     # Spatial scoring
│   │   ├── allocator.py           # Effort-balanced allocation
│   │   ├── plan_generator.py      # Building counts, power
│   │   └── module_builder.py      # Stamp-copy decomposition
│   ├── data/
│   │   ├── satisfactory.db        # Game database
│   │   ├── resource_nodes.json    # Map resource data
│   │   └── themes.json            # Theme definitions
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── wizard/            # PreferencesStep, RecipeStep, LocationStep
│   │   │   ├── dashboard/         # SummaryBanner, FactoriesTab, MapTab, ModulesTab, ExportTab
│   │   │   ├── map/               # GameMap, ResourceNodes, FactoryMarkers
│   │   │   └── recipes/           # RecipeDAG
│   │   ├── hooks/usePlanAPI.ts
│   │   └── types/plan.ts
│   ├── package.json
│   └── vite.config.ts
├── Dockerfile                      # Multi-stage: build React → serve via FastAPI
└── railway.toml
```

## Deployment

- Multi-stage Dockerfile: Stage 1 builds React (Node), Stage 2 runs FastAPI (Python) serving the built static files
- Single Railway service, `PORT` env var, health check at `/api/health`
- SQLite is read-only game data baked into the image — no volume needed
