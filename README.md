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

| Script | Purpose |
|--------|---------|
| `compute_modules.py` | Compute smallest repeatable HMF module per factory |
| `build_factory_crazy.py` | 2-stage decomposition into building-capped mini-modules |
| `find_factory_locations.py` | Score map locations by resource proximity |
| `build_map.py` | Generate the interactive HTML map |

## Running Locally

```bash
python server.py
# Open http://localhost:8080
```

## Deployment

Configured for Railway with auto-deploy from GitHub. Push to `main` to deploy.
