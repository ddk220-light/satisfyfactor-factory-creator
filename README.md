# Satisfactory Factory Planner

Interactive map-based factory location planner for **Satisfactory**. Computes optimal factory layouts for Heavy Modular Frame (HMF) production across five themed factories, each using distinct alternate recipe chains.

## Live App

Deployed on Railway — serves an interactive canvas-based map where you can:

- Pan/zoom across the full game world with resource node overlays
- Toggle visibility of each factory's resource catchment area
- View mining towns with capacity breakdowns
- Export selected factory locations as JSON

## Factories

| Factory | Theme | Strategy |
|---------|-------|----------|
| **Ferrium** | Pure Iron | All-iron recipes, no coal/oil |
| **Naphtheon** | Oil Ecosystem | Oil-based plastics and rubber |
| **Forgeholm** | Steel Spine | Coal-heavy steel production |
| **Luxara** | Aluminum Replacement | Bauxite-based alternate recipes |
| **Cathera** | Copper & Caterium | Copper/caterium wire variants |

## Pipeline Scripts

Factory layouts use a single strategy: **Factory Crazy** (2-stage decomposition). The old stamp-copy "Factories" view has been removed.

| Script | Purpose |
|--------|---------|
| `compute_modules.py` | Per-factory HMF module basis (internal intermediate for the step below) |
| `build_factory_crazy.py` | 2-stage decomposition into building-capped mini-modules — the canonical plan |
| `find_factory_locations.py` | Score map locations by resource proximity |

`factory-map.html` is hand-maintained and served directly. `build_map.py` is a stale map-only generator — do not run it to regenerate the page (it would wipe the tabs).

## Running Locally

```bash
python server.py
# Open http://localhost:8080
```

## Deployment

Configured for Railway with auto-deploy from GitHub. Push to `main` to deploy.
