# Factory Planner App — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI + React web app that guides users from "I want X items/min" to a complete multi-factory production plan with locations, allocations, building counts, and modular blueprints.

**Architecture:** Single-container monolith. FastAPI backend wraps existing Python calculation scripts as engine modules behind `/api/*` endpoints. React + Vite frontend with Leaflet maps served as static files. SQLite game database bundled read-only.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, SQLite, React 18, TypeScript, Vite, Leaflet, react-leaflet

**Design Doc:** `docs/plans/2026-02-16-factory-planner-app-design.md`

**Existing Code Reference:** The scripts `calc_resources.py`, `find_factory_locations.py`, `allocate_hmf.py`, `generate_factory_plan.py`, `compute_modules.py`, and `build_map.py` in the project root contain the proven algorithms. The engine modules adapt these into parameterized, testable functions.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `backend/requirements.txt`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

**Step 1: Create backend skeleton**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Satisfactory Factory Planner")

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Serve React build in production
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        file_path = os.path.join(frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))
```

```
# backend/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
```

**Step 2: Create frontend skeleton**

```json
// frontend/package.json
{
  "name": "satisfy-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@types/leaflet": "^1.9.14",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^6.0.0"
  }
}
```

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

```tsx
// frontend/src/App.tsx
export default function App() {
  return <div>Satisfactory Factory Planner</div>
}
```

**Step 3: Verify both servers start**

Run backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
Expected: Server starts, `GET /api/health` returns `{"status": "ok"}`

Run frontend: `cd frontend && npm install && npm run dev`
Expected: Vite dev server starts on port 5173, shows placeholder text

**Step 4: Commit**

```bash
git add backend/ frontend/
git commit -m "feat: scaffold FastAPI backend and React frontend"
```

---

## Task 2: Database Layer & Data Migration

**Files:**
- Create: `backend/db.py`
- Copy: `satisfactory.db` → `backend/data/satisfactory.db`
- Copy: `resource_nodes.json` → `backend/data/resource_nodes.json`
- Create: `backend/data/themes.json`
- Create: `backend/engine/__init__.py`
- Create: `tests/test_db.py`

**Step 1: Write test for DB connection and resource_nodes table**

```python
# tests/test_db.py
import pytest
from backend.db import get_db, init_resource_nodes, get_resource_nodes

def test_resource_nodes_loaded():
    db = get_db()
    init_resource_nodes(db)
    nodes = get_resource_nodes(db)
    assert len(nodes) > 500  # game has 700+ resource nodes
    node = nodes[0]
    assert "type" in node
    assert "purity" in node
    assert "x" in node and "y" in node

def test_items_table_exists():
    db = get_db()
    cursor = db.execute("SELECT COUNT(*) FROM items")
    count = cursor.fetchone()[0]
    assert count > 100  # game has hundreds of items
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — `backend.db` module doesn't exist

**Step 3: Implement db.py**

```python
# backend/db.py
import sqlite3
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "satisfactory.db")
NODES_PATH = os.path.join(DATA_DIR, "resource_nodes.json")

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_resource_nodes(db: sqlite3.Connection):
    """Create and populate resource_nodes table from JSON if not exists."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS resource_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            purity TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            z REAL NOT NULL
        )
    """)
    cursor = db.execute("SELECT COUNT(*) FROM resource_nodes")
    if cursor.fetchone()[0] > 0:
        return
    with open(NODES_PATH) as f:
        data = json.load(f)
    nodes = data.get("resource_nodes", data) if isinstance(data, dict) else data
    db.executemany(
        "INSERT INTO resource_nodes (type, purity, x, y, z) VALUES (?, ?, ?, ?, ?)",
        [(n["type"], n["purity"], n["x"], n["y"], n["z"]) for n in nodes]
    )
    db.commit()

def get_resource_nodes(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT type, purity, x, y, z FROM resource_nodes").fetchall()
    return [dict(r) for r in rows]
```

Copy data files:
```bash
mkdir -p backend/data
cp satisfactory.db backend/data/
cp resource_nodes.json backend/data/
```

**Step 4: Create themes.json**

```json
// backend/data/themes.json
[
  {
    "id": "iron-works",
    "name": "Iron Works",
    "primary_resources": ["Iron Ore", "Limestone"],
    "description": "Smelting and constructing from iron and limestone. The backbone of any factory."
  },
  {
    "id": "oil-refinery",
    "name": "Oil Refinery",
    "primary_resources": ["Crude Oil"],
    "description": "Crude oil processing into plastics, rubber, and petroleum coke."
  },
  {
    "id": "coal-forge",
    "name": "Coal Forge",
    "primary_resources": ["Coal"],
    "description": "Steel production through coal and iron foundry work."
  },
  {
    "id": "copper-electronics",
    "name": "Copper Electronics",
    "primary_resources": ["Copper Ore", "Caterium Ore"],
    "description": "Wire, cable, and circuit board production from copper and caterium."
  },
  {
    "id": "bauxite-refinery",
    "name": "Bauxite Refinery",
    "primary_resources": ["Bauxite"],
    "description": "Aluminum processing with water-intensive refining chains."
  },
  {
    "id": "sulfur-works",
    "name": "Sulfur Works",
    "primary_resources": ["Sulfur"],
    "description": "Explosives and acid production from sulfur deposits."
  },
  {
    "id": "quartz-processing",
    "name": "Quartz Processing",
    "primary_resources": ["Raw Quartz"],
    "description": "Crystal oscillators and silica from raw quartz."
  },
  {
    "id": "uranium-complex",
    "name": "Uranium Complex",
    "primary_resources": ["Uranium"],
    "description": "Nuclear fuel rod production and waste processing."
  }
]
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/db.py backend/data/ backend/engine/__init__.py tests/test_db.py
git commit -m "feat: add database layer with resource_nodes migration and themes"
```

---

## Task 3: Recipe Graph Engine

**Files:**
- Create: `backend/engine/recipe_graph.py`
- Create: `tests/test_recipe_graph.py`

**Reference:** `calc_resources.py` lines 1-123 (recursive chain decomposition), `compute_modules.py` `get_recipe_rates()` function.

This is the core engine: given a target item and a set of allowed/excluded recipes, build the full production DAG and calculate raw resource demands.

**Step 1: Write failing tests**

```python
# tests/test_recipe_graph.py
import pytest
from backend.db import get_db, init_resource_nodes
from backend.engine.recipe_graph import build_recipe_dag, get_raw_demands

@pytest.fixture
def db():
    conn = get_db()
    init_resource_nodes(conn)
    return conn

def test_build_dag_for_iron_plate(db):
    """Iron Plate has a simple chain: Iron Ore → Iron Ingot → Iron Plate."""
    dag = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=[])
    assert len(dag.nodes) >= 2  # at least Iron Ingot and Iron Plate steps
    # Root node produces Iron Plate
    assert dag.root.item == "Iron Plate"
    # Leaves should be raw resources
    leaves = [n.item for n in dag.leaves()]
    assert "Iron Ore" in leaves

def test_raw_demands_for_iron_plate(db):
    """1/min of Iron Plate should require 1/min Iron Ore (default recipe)."""
    dag = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=[])
    demands = get_raw_demands(dag, rate=1.0)
    assert "Iron Ore" in demands
    assert demands["Iron Ore"] > 0

def test_excluded_recipe_uses_default(db):
    """Excluding an alternate recipe should fall back to the default."""
    dag_default = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=[])
    dag_excluded = build_recipe_dag(db, target_item="Iron Plate",
                                     excluded_recipes=["Alternate: Pure Iron Ingot"])
    # Both should produce valid DAGs
    assert dag_default.root.item == "Iron Plate"
    assert dag_excluded.root.item == "Iron Plate"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_recipe_graph.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Implement recipe_graph.py**

Key logic adapted from `calc_resources.py` and `compute_modules.py`:

```python
# backend/engine/recipe_graph.py
"""
Build a production DAG for any target item by tracing recipes from the DB.

A DAG node represents one recipe step: item produced, recipe used, building,
power, input/output rates. Edges connect inputs to the recipes that produce them.
Leaves are raw resources (items with no producing recipe).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from backend.db import get_db

# Items that are raw resources (no recipe produces them from scratch)
RAW_RESOURCES = {
    "Iron Ore", "Copper Ore", "Limestone", "Coal", "Caterium Ore",
    "Raw Quartz", "Sulfur", "Bauxite", "Uranium", "Crude Oil",
    "Water", "Nitrogen Gas", "SAM"
}

FLUID_ITEMS = {
    "Water", "Crude Oil", "Heavy Oil Residue", "Fuel", "Turbofuel",
    "Alumina Solution", "Sulfuric Acid", "Nitric Acid", "Nitrogen Gas",
    "Dissolved Silica", "Rubber", "Plastic"  # Note: Rubber/Plastic are solids but packaged from fluids
}

@dataclass
class RecipeNode:
    item: str
    recipe_id: str
    recipe_name: str
    building: str
    power_mw: float
    duration_s: float
    outputs: dict[str, float]   # item -> quantity per cycle
    inputs: dict[str, float]    # item -> quantity per cycle
    children: list[RecipeNode] = field(default_factory=list)

    @property
    def output_per_min(self) -> float:
        """Primary output rate at 100% clock."""
        return self.outputs.get(self.item, 0) / self.duration_s * 60

    @property
    def all_outputs_per_min(self) -> dict[str, float]:
        return {item: qty / self.duration_s * 60 for item, qty in self.outputs.items()}

    @property
    def all_inputs_per_min(self) -> dict[str, float]:
        return {item: qty / self.duration_s * 60 for item, qty in self.inputs.items()}

@dataclass
class RecipeDAG:
    root: RecipeNode
    nodes: list[RecipeNode]

    def leaves(self) -> list[RecipeNode]:
        """Nodes whose inputs are all raw resources."""
        return [n for n in self.nodes
                if all(inp in RAW_RESOURCES for inp in n.inputs)]


def _get_recipes_for_item(db, item_name: str) -> list[dict]:
    """Get all recipes that produce a given item, with ingredients."""
    rows = db.execute("""
        SELECT r.id, r.name, r.duration,
               b.name as building_name, b.power_used
        FROM recipes r
        JOIN recipe_products rp ON rp.recipe_id = r.id
        JOIN items i ON i.id = rp.item_id
        JOIN recipe_buildings rb ON rb.recipe_id = r.id
        JOIN buildings b ON b.id = rb.building_id
        WHERE i.name = ?
    """, (item_name,)).fetchall()

    recipes = []
    for row in rows:
        rid = row["id"]
        ingredients = db.execute("""
            SELECT i.name, ri.quantity FROM recipe_ingredients ri
            JOIN items i ON i.id = ri.item_id WHERE ri.recipe_id = ?
        """, (rid,)).fetchall()
        products = db.execute("""
            SELECT i.name, rp.quantity FROM recipe_products rp
            JOIN items i ON i.id = rp.item_id WHERE rp.recipe_id = ?
        """, (rid,)).fetchall()
        recipes.append({
            "id": rid,
            "name": row["name"],
            "duration": row["duration"],
            "building": row["building_name"],
            "power_mw": row["power_used"] or 0,
            "inputs": {r["name"]: r["quantity"] for r in ingredients},
            "outputs": {r["name"]: r["quantity"] for r in products},
        })
    return recipes


def _pick_recipe(recipes: list[dict], excluded: set[str]) -> dict | None:
    """Pick best recipe: prefer default (non-alternate), skip excluded."""
    available = [r for r in recipes if r["name"] not in excluded]
    if not available:
        return None
    # Prefer non-alternate recipes
    defaults = [r for r in available if not r["name"].startswith("Alternate:")]
    return defaults[0] if defaults else available[0]


def build_recipe_dag(db, target_item: str, excluded_recipes: list[str]) -> RecipeDAG:
    """Build full production DAG from target item down to raw resources."""
    excluded = set(excluded_recipes)
    nodes = []
    visited = {}  # item -> RecipeNode (avoid infinite loops)

    def _build(item: str) -> RecipeNode | None:
        if item in RAW_RESOURCES:
            return None
        if item in visited:
            return visited[item]

        recipes = _get_recipes_for_item(db, item)
        recipe = _pick_recipe(recipes, excluded)
        if recipe is None:
            return None

        # Convert fluid quantities from mL to m³ for display consistency
        node = RecipeNode(
            item=item,
            recipe_id=recipe["id"],
            recipe_name=recipe["name"],
            building=recipe["building"],
            power_mw=recipe["power_mw"],
            duration_s=recipe["duration"],
            outputs=recipe["outputs"],
            inputs=recipe["inputs"],
        )
        visited[item] = node
        nodes.append(node)

        for input_item in recipe["inputs"]:
            child = _build(input_item)
            if child:
                node.children.append(child)

        return node

    root = _build(target_item)
    if root is None:
        raise ValueError(f"No recipe found for {target_item}")
    return RecipeDAG(root=root, nodes=nodes)


def get_raw_demands(dag: RecipeDAG, rate: float) -> dict[str, float]:
    """Calculate raw resource demands for producing `rate` items/min of root item."""
    demands: dict[str, float] = {}

    def _trace(node: RecipeNode, needed_rate: float):
        # How many buildings at 100% clock to produce needed_rate
        scale = needed_rate / node.output_per_min if node.output_per_min > 0 else 0
        for input_item, qty in node.inputs.items():
            input_rate = (qty / node.duration_s * 60) * scale
            if input_item in RAW_RESOURCES:
                demands[input_item] = demands.get(input_item, 0) + input_rate
            else:
                # Find the child node that produces this
                child = next((c for c in node.children if c.item == input_item), None)
                if child:
                    _trace(child, input_rate)

    _trace(dag.root, rate)
    return demands
```

**Step 4: Run tests**

Run: `pytest tests/test_recipe_graph.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/engine/recipe_graph.py tests/test_recipe_graph.py
git commit -m "feat: add recipe graph engine for production chain decomposition"
```

---

## Task 4: Theme Assignment Engine

**Files:**
- Create: `backend/engine/theme_assigner.py`
- Create: `tests/test_theme_assigner.py`

**Reference:** Design doc "Recipe-to-Theme Assignment Algorithm" section. This is new logic not in existing scripts.

**Step 1: Write failing tests**

```python
# tests/test_theme_assigner.py
import pytest
import json
import os
from backend.db import get_db, init_resource_nodes
from backend.engine.recipe_graph import build_recipe_dag
from backend.engine.theme_assigner import assign_themes, load_themes

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data")

@pytest.fixture
def db():
    conn = get_db()
    init_resource_nodes(conn)
    return conn

@pytest.fixture
def themes():
    return load_themes()

def test_load_themes(themes):
    assert len(themes) >= 8
    assert themes[0]["id"] == "iron-works"

def test_iron_plate_assigns_to_iron_works(db, themes):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    assignments = assign_themes(dag, themes, max_factories=8)
    # Iron Plate only needs iron → should assign to iron-works
    assert len(assignments) >= 1
    theme_ids = [a["theme"]["id"] for a in assignments]
    assert "iron-works" in theme_ids

def test_max_factories_caps_themes(db, themes):
    dag = build_recipe_dag(db, "Heavy Modular Frame", excluded_recipes=[])
    assignments = assign_themes(dag, themes, max_factories=2)
    assert len(assignments) <= 2

def test_trivial_themes_get_merged(db, themes):
    """Themes with <5% of total demand should be merged into a related theme."""
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    assignments = assign_themes(dag, themes, max_factories=8)
    # Simple item shouldn't produce many themes
    assert len(assignments) <= 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_theme_assigner.py -v`

**Step 3: Implement theme_assigner.py**

```python
# backend/engine/theme_assigner.py
"""
Assign recipe DAG nodes to resource-based factory themes.

Algorithm:
1. For each recipe node, determine which raw resources its subtree consumes
2. Map raw resources to themes via themes.json primary_resources
3. Assign each recipe to the theme of its rarest (fewest map nodes) raw resource
4. Merge trivial themes (<5% of total demand) into nearest related theme
5. Cap at max_factories
"""
import json
import os
from backend.engine.recipe_graph import RecipeDAG, RecipeNode, RAW_RESOURCES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Approximate node counts on the map (used for rarity scoring)
RESOURCE_NODE_COUNTS = {
    "Iron Ore": 163, "Limestone": 72, "Copper Ore": 50, "Coal": 43,
    "Caterium Ore": 16, "Raw Quartz": 17, "Sulfur": 15, "Bauxite": 14,
    "Crude Oil": 18, "Uranium": 5, "Nitrogen Gas": 13, "SAM": 25,
    "Water": 999,  # extractors everywhere
}


def load_themes() -> list[dict]:
    with open(os.path.join(DATA_DIR, "themes.json")) as f:
        return json.load(f)


def _resource_to_theme(resource: str, themes: list[dict]) -> dict | None:
    """Find the theme that owns this raw resource."""
    for theme in themes:
        if resource in theme["primary_resources"]:
            return theme
    return None


def _subtree_raw_demands(node: RecipeNode, visited: set | None = None) -> dict[str, float]:
    """Get raw resource demands of a node's entire subtree (rates relative to 1/min output)."""
    if visited is None:
        visited = set()
    if node.item in visited:
        return {}
    visited.add(node.item)

    demands: dict[str, float] = {}
    scale = 1.0 / node.output_per_min if node.output_per_min > 0 else 0

    for input_item, qty in node.inputs.items():
        rate = (qty / node.duration_s * 60) * scale
        if input_item in RAW_RESOURCES:
            demands[input_item] = demands.get(input_item, 0) + rate
        else:
            child = next((c for c in node.children if c.item == input_item), None)
            if child:
                child_demands = _subtree_raw_demands(child, visited)
                for res, child_rate in child_demands.items():
                    # Scale child demands by how much of the child's output we need
                    child_output = child.output_per_min
                    child_scale = rate / child_output if child_output > 0 else 0
                    demands[res] = demands.get(res, 0) + child_rate * child_scale
    return demands


def assign_themes(dag: RecipeDAG, themes: list[dict], max_factories: int) -> list[dict]:
    """
    Assign DAG nodes to themes. Returns list of theme assignments:
    [{"theme": theme_dict, "recipes": [node, ...], "raw_demands": {...}}, ...]
    """
    # Step 1: For each recipe node, find its dominant raw resource
    node_theme_map: dict[str, dict] = {}  # node.item -> theme
    node_demands: dict[str, dict[str, float]] = {}  # node.item -> raw demands

    for node in dag.nodes:
        demands = _subtree_raw_demands(node)
        node_demands[node.item] = demands

        # Find rarest raw resource in this subtree
        rarest_resource = None
        min_nodes = float("inf")
        for resource in demands:
            if resource == "Water":
                continue
            count = RESOURCE_NODE_COUNTS.get(resource, 999)
            if count < min_nodes:
                min_nodes = count
                rarest_resource = resource

        if rarest_resource:
            theme = _resource_to_theme(rarest_resource, themes)
            if theme:
                node_theme_map[node.item] = theme

    # Fall back: assign unthemed nodes to iron-works
    iron_theme = next((t for t in themes if t["id"] == "iron-works"), themes[0])
    for node in dag.nodes:
        if node.item not in node_theme_map:
            node_theme_map[node.item] = iron_theme

    # Step 2: Aggregate by theme
    theme_groups: dict[str, dict] = {}
    for node in dag.nodes:
        theme = node_theme_map[node.item]
        tid = theme["id"]
        if tid not in theme_groups:
            theme_groups[tid] = {"theme": theme, "recipes": [], "raw_demands": {}}
        theme_groups[tid]["recipes"].append(node)

    # Aggregate raw demands per theme from root perspective
    root_demands = node_demands.get(dag.root.item, {})
    total_demand = sum(root_demands.values())

    for tid, group in theme_groups.items():
        resources_owned = set(group["theme"]["primary_resources"])
        for res, demand in root_demands.items():
            # Assign this demand to the theme that owns the resource
            owner_theme = _resource_to_theme(res, themes)
            if owner_theme and owner_theme["id"] == tid:
                group["raw_demands"][res] = demand

    # Step 3: Merge trivial themes (<5% of total demand)
    if total_demand > 0:
        to_merge = []
        for tid, group in theme_groups.items():
            theme_demand = sum(group["raw_demands"].values())
            if theme_demand / total_demand < 0.05 and len(theme_groups) > 1:
                to_merge.append(tid)

        for tid in to_merge:
            # Merge into the largest remaining theme
            remaining = {k: v for k, v in theme_groups.items() if k not in to_merge}
            if remaining:
                largest = max(remaining, key=lambda k: sum(remaining[k]["raw_demands"].values()))
                theme_groups[largest]["recipes"].extend(theme_groups[tid]["recipes"])
                for res, demand in theme_groups[tid]["raw_demands"].items():
                    theme_groups[largest]["raw_demands"][res] = \
                        theme_groups[largest]["raw_demands"].get(res, 0) + demand
                del theme_groups[tid]

    # Step 4: Cap at max_factories (keep largest themes)
    assignments = sorted(theme_groups.values(),
                         key=lambda g: sum(g["raw_demands"].values()), reverse=True)
    if len(assignments) > max_factories:
        # Merge excess into last kept theme
        kept = assignments[:max_factories]
        for excess in assignments[max_factories:]:
            kept[-1]["recipes"].extend(excess["recipes"])
            for res, demand in excess["raw_demands"].items():
                kept[-1]["raw_demands"][res] = kept[-1]["raw_demands"].get(res, 0) + demand
        assignments = kept

    return assignments
```

**Step 4: Run tests**

Run: `pytest tests/test_theme_assigner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/engine/theme_assigner.py tests/test_theme_assigner.py
git commit -m "feat: add theme assignment engine for recipe-to-factory partitioning"
```

---

## Task 5: Location Finder Engine

**Files:**
- Create: `backend/engine/location_finder.py`
- Create: `tests/test_location_finder.py`

**Reference:** `find_factory_locations.py` (360 lines). Adapt the scoring algorithm with parameterized search radius and configurable resource demands.

**Step 1: Write failing tests**

```python
# tests/test_location_finder.py
import pytest
from backend.db import get_db, init_resource_nodes, get_resource_nodes
from backend.engine.location_finder import find_locations, score_location

@pytest.fixture
def db():
    conn = get_db()
    init_resource_nodes(conn)
    return conn

@pytest.fixture
def nodes(db):
    return get_resource_nodes(db)

def test_find_locations_returns_ranked_results(nodes):
    """Find locations for a factory needing iron and limestone."""
    critical = {"Iron Ore": 100.0, "Limestone": 50.0}
    results = find_locations(
        nodes=nodes,
        critical_resources=critical,
        search_radius_m=500,
        n_results=3,
        excluded_quadrants=[]
    )
    assert len(results) <= 3
    assert len(results) >= 1
    # Results should be sorted by score descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

def test_excluded_quadrant_filters_locations(nodes):
    """Excluding a quadrant should remove locations in that area."""
    critical = {"Iron Ore": 100.0}
    all_results = find_locations(nodes, critical, 500, 5, [])
    ne_excluded = find_locations(nodes, critical, 500, 5, ["NE"])
    # Excluding a quadrant should give same or fewer results
    assert len(ne_excluded) <= len(all_results)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_location_finder.py -v`

**Step 3: Implement location_finder.py**

Adapt from `find_factory_locations.py`. Key changes:
- Remove hardcoded FACTORY_CONFIG — accept `critical_resources` dict as parameter
- Accept `search_radius_m` as parameter (convert to game units internally: ×100)
- Accept `excluded_quadrants` list (NE, NW, SE, SW)
- Keep: scoring algorithm (purity weight × demand × rarity^1.5), centroid dedup

```python
# backend/engine/location_finder.py
"""
Find optimal factory locations based on proximity to resource nodes.

Scoring: For each candidate point (every resource node center), score by
sum of purity_weight * (demand * rarity^1.5) for all critical resources
within the search radius.
"""
import math

PURITY_WEIGHT = {"impure": 1, "normal": 2, "pure": 4}
MIN_SEPARATION = 25000  # game units (250m) between distinct locations


def _distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _quadrant(x, y) -> str:
    """Return quadrant label based on game coordinates (origin ~ center of map)."""
    ns = "N" if y < 0 else "S"
    ew = "W" if x < 0 else "E"
    return ns + ew


def _count_by_type(nodes: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in nodes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    return counts


def find_locations(
    nodes: list[dict],
    critical_resources: dict[str, float],  # resource_type -> demand_per_min
    search_radius_m: float,
    n_results: int,
    excluded_quadrants: list[str],
) -> list[dict]:
    """
    Find top N factory locations scored by proximity to critical resources.

    Returns list of dicts with: center (x, y), score, resources breakdown, nearby_nodes.
    """
    radius = search_radius_m * 100  # convert meters to game units
    node_counts = _count_by_type(nodes)
    max_count = max(node_counts.values()) if node_counts else 1

    # Importance weights per resource type
    importance = {}
    for rtype, demand in critical_resources.items():
        count = node_counts.get(rtype, 1)
        rarity = (max_count / count) ** 1.5
        importance[rtype] = demand * rarity

    # Score every resource node as a potential center
    scored = []
    resource_types = set(critical_resources.keys())

    for center_node in nodes:
        if center_node["type"] not in resource_types:
            continue
        cx, cy = center_node["x"], center_node["y"]

        # Check quadrant exclusion
        if _quadrant(cx, cy) in excluded_quadrants:
            continue

        # Find nearby nodes of critical types
        nearby: dict[str, list[dict]] = {t: [] for t in resource_types}
        for n in nodes:
            if n["type"] not in resource_types:
                continue
            d = _distance(cx, cy, n["x"], n["y"])
            if d <= radius:
                nearby[n["type"]].append({**n, "distance": d})

        # Must have at least one node of each critical type
        if not all(nearby[t] for t in resource_types):
            continue

        # Score
        score = 0
        resources_detail = {}
        for rtype in resource_types:
            type_score = sum(
                PURITY_WEIGHT.get(n["purity"], 1) * importance.get(rtype, 1)
                for n in nearby[rtype]
            )
            score += type_score
            purity_breakdown = {}
            for n in nearby[rtype]:
                purity_breakdown[n["purity"]] = purity_breakdown.get(n["purity"], 0) + 1
            resources_detail[rtype] = {
                "node_count": len(nearby[rtype]),
                "purity_breakdown": purity_breakdown,
                "score": type_score,
            }

        # Centroid of nearby critical nodes
        all_nearby = [n for ns in nearby.values() for n in ns]
        centroid_x = sum(n["x"] for n in all_nearby) / len(all_nearby)
        centroid_y = sum(n["y"] for n in all_nearby) / len(all_nearby)

        scored.append({
            "center": {"x": centroid_x, "y": centroid_y},
            "score": score,
            "resources": resources_detail,
            "nearby_nodes": all_nearby,
        })

    # Sort by score descending
    scored.sort(key=lambda s: s["score"], reverse=True)

    # Deduplicate: keep locations at least MIN_SEPARATION apart
    results = []
    for loc in scored:
        too_close = any(
            _distance(loc["center"]["x"], loc["center"]["y"],
                      r["center"]["x"], r["center"]["y"]) < MIN_SEPARATION
            for r in results
        )
        if not too_close:
            results.append(loc)
        if len(results) >= n_results:
            break

    return results
```

**Step 4: Run tests**

Run: `pytest tests/test_location_finder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/engine/location_finder.py tests/test_location_finder.py
git commit -m "feat: add location finder engine with scoring and quadrant exclusion"
```

---

## Task 6: Allocator Engine

**Files:**
- Create: `backend/engine/allocator.py`
- Create: `tests/test_allocator.py`

**Reference:** `allocate_hmf.py` (377 lines). Adapt the effort-balanced binary search with configurable train penalty and water multiplier.

**Step 1: Write failing tests**

```python
# tests/test_allocator.py
import pytest
from backend.engine.allocator import allocate_production

def test_single_factory_gets_all():
    """One factory should get 100% of target rate."""
    factories = [{
        "theme_id": "iron-works",
        "demands_per_unit": {"Iron Ore": 100.0, "Limestone": 50.0},
        "local_capacity": {"Iron Ore": 5000.0, "Limestone": 3000.0},
    }]
    result = allocate_production(
        factories=factories,
        target_rate=10.0,
        train_penalty=2.0,
        water_penalty=3.0,
    )
    assert len(result) == 1
    assert abs(result[0]["allocated_rate"] - 10.0) < 0.01

def test_two_factories_balanced():
    """Two factories should share production proportionally."""
    factories = [
        {
            "theme_id": "iron-works",
            "demands_per_unit": {"Iron Ore": 100.0},
            "local_capacity": {"Iron Ore": 2000.0},
        },
        {
            "theme_id": "coal-forge",
            "demands_per_unit": {"Coal": 100.0},
            "local_capacity": {"Coal": 2000.0},
        },
    ]
    result = allocate_production(
        factories=factories, target_rate=20.0,
        train_penalty=2.0, water_penalty=3.0,
    )
    total = sum(r["allocated_rate"] for r in result)
    assert abs(total - 20.0) < 0.01

def test_train_penalty_affects_allocation():
    """Higher train penalty should shift production toward self-sufficient factories."""
    factories = [
        {
            "theme_id": "a",
            "demands_per_unit": {"Iron Ore": 100.0},
            "local_capacity": {"Iron Ore": 5000.0},  # fully local
        },
        {
            "theme_id": "b",
            "demands_per_unit": {"Iron Ore": 100.0},
            "local_capacity": {"Iron Ore": 500.0},  # needs trains
        },
    ]
    low_penalty = allocate_production(factories, 20.0, train_penalty=2.0, water_penalty=3.0)
    high_penalty = allocate_production(factories, 20.0, train_penalty=10.0, water_penalty=3.0)
    # Factory 'a' should get more with high penalty
    a_low = next(r for r in low_penalty if r["theme_id"] == "a")["allocated_rate"]
    a_high = next(r for r in high_penalty if r["theme_id"] == "a")["allocated_rate"]
    assert a_high >= a_low
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_allocator.py -v`

**Step 3: Implement allocator.py**

```python
# backend/engine/allocator.py
"""
Effort-balanced production allocation across factories.

Uses binary search to find a balanced effort level where total production = target rate.
Effort model: local extraction = 1x, train import = train_penalty, water = water_penalty.
"""

MINER_RATES = {"impure": 300, "normal": 600, "pure": 780}
OIL_RATES = {"impure": 150, "normal": 300, "pure": 600}
WATER_RATE = 120  # m³/min per extractor


def _compute_effort(
    demands_per_unit: dict[str, float],
    local_capacity: dict[str, float],
    rate: float,
    train_penalty: float,
    water_penalty: float,
) -> float:
    """Compute total effort for a factory at a given production rate."""
    total = 0.0
    for resource, per_unit in demands_per_unit.items():
        demand = per_unit * rate
        local_cap = local_capacity.get(resource, 0.0)
        local_used = min(demand, local_cap)
        train_needed = max(0, demand - local_cap)

        if resource == "Water":
            total += demand * water_penalty
        else:
            total += local_used * 1.0 + train_needed * train_penalty
    return total


def _max_rate_for_effort(
    demands_per_unit: dict[str, float],
    local_capacity: dict[str, float],
    target_effort: float,
    train_penalty: float,
    water_penalty: float,
) -> float:
    """Binary search: find max production rate that fits within target_effort."""
    lo, hi = 0.0, 10000.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if _compute_effort(demands_per_unit, local_capacity, mid, train_penalty, water_penalty) <= target_effort:
            lo = mid
        else:
            hi = mid
    return lo


def allocate_production(
    factories: list[dict],
    target_rate: float,
    train_penalty: float,
    water_penalty: float,
) -> list[dict]:
    """
    Allocate target_rate across factories using effort-balanced model.

    Each factory dict: {theme_id, demands_per_unit, local_capacity}
    Returns: [{theme_id, allocated_rate, effort, resources_breakdown}, ...]
    """
    if len(factories) == 1:
        f = factories[0]
        effort = _compute_effort(
            f["demands_per_unit"], f["local_capacity"],
            target_rate, train_penalty, water_penalty
        )
        return [{
            "theme_id": f["theme_id"],
            "allocated_rate": target_rate,
            "effort": effort,
        }]

    # Binary search for balanced effort level
    lo_effort, hi_effort = 0.0, 1e9
    for _ in range(100):
        mid_effort = (lo_effort + hi_effort) / 2
        total = sum(
            _max_rate_for_effort(
                f["demands_per_unit"], f["local_capacity"],
                mid_effort, train_penalty, water_penalty
            )
            for f in factories
        )
        if total >= target_rate:
            hi_effort = mid_effort
        else:
            lo_effort = mid_effort

    balanced_effort = hi_effort

    # Compute each factory's allocation at balanced effort
    results = []
    raw_rates = []
    for f in factories:
        rate = _max_rate_for_effort(
            f["demands_per_unit"], f["local_capacity"],
            balanced_effort, train_penalty, water_penalty
        )
        raw_rates.append(rate)
        results.append({
            "theme_id": f["theme_id"],
            "allocated_rate": rate,
            "effort": _compute_effort(
                f["demands_per_unit"], f["local_capacity"],
                rate, train_penalty, water_penalty
            ),
        })

    # Scale to exactly hit target_rate
    total_raw = sum(raw_rates)
    if total_raw > 0:
        scale = target_rate / total_raw
        for i, r in enumerate(results):
            r["allocated_rate"] = raw_rates[i] * scale
            r["effort"] = _compute_effort(
                factories[i]["demands_per_unit"],
                factories[i]["local_capacity"],
                r["allocated_rate"], train_penalty, water_penalty
            )

    return results
```

**Step 4: Run tests**

Run: `pytest tests/test_allocator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/engine/allocator.py tests/test_allocator.py
git commit -m "feat: add allocator engine with effort-balanced binary search"
```

---

## Task 7: Plan Generator Engine

**Files:**
- Create: `backend/engine/plan_generator.py`
- Create: `tests/test_plan_generator.py`

**Reference:** `generate_factory_plan.py` (535 lines). Adapt building count and power calculation.

**Step 1: Write failing tests**

```python
# tests/test_plan_generator.py
import pytest
from backend.db import get_db, init_resource_nodes
from backend.engine.recipe_graph import build_recipe_dag
from backend.engine.plan_generator import generate_factory_plan

@pytest.fixture
def db():
    conn = get_db()
    init_resource_nodes(conn)
    return conn

def test_generate_plan_for_iron_plate(db):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    plan = generate_factory_plan(
        dag=dag,
        allocated_rate=10.0,
        local_resources={"Iron Ore": 5000.0, "Limestone": 3000.0},
    )
    assert plan["target_rate"] == 10.0
    assert len(plan["buildings"]) > 0
    assert plan["total_power_mw"] > 0
    # Should have smelters and constructors
    building_types = {b["building"] for b in plan["buildings"]}
    assert "Smelter" in building_types or "Constructor" in building_types

def test_plan_calculates_train_imports(db):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    plan = generate_factory_plan(
        dag=dag, allocated_rate=100.0,
        local_resources={"Iron Ore": 50.0},  # not enough locally
    )
    assert plan["train_imports"]["Iron Ore"] > 0
```

**Step 2: Run tests, verify failure, implement**

Core logic from `generate_factory_plan.py`:
- For each recipe node in the DAG at allocated_rate: `count = demand / output_per_min`
- Power: `base_power × (clock_pct / 100) ^ 1.321929`
- Train imports: `max(0, demand - local_capacity)` per raw resource

```python
# backend/engine/plan_generator.py
"""Generate comprehensive factory plan: building counts, power, resource sourcing."""
import math
from backend.engine.recipe_graph import RecipeDAG, RecipeNode, RAW_RESOURCES

POWER_EXPONENT = 1.321929


def generate_factory_plan(
    dag: RecipeDAG,
    allocated_rate: float,
    local_resources: dict[str, float],
) -> dict:
    """
    Generate a full production plan for one factory.

    Returns dict with: target_rate, buildings[], total_power_mw,
    total_buildings, train_imports, local_extraction, building_summary.
    """
    buildings = []
    total_power = 0.0
    raw_demands: dict[str, float] = {}

    def _plan_node(node: RecipeNode, needed_rate: float):
        nonlocal total_power
        if node.output_per_min <= 0:
            return

        count_exact = needed_rate / node.output_per_min
        count_ceil = math.ceil(count_exact)
        frac = count_exact - math.floor(count_exact)

        # Power calculation
        full_buildings = math.floor(count_exact)
        power_full = full_buildings * node.power_mw
        power_partial = node.power_mw * (frac ** POWER_EXPONENT) if frac > 0.001 else 0
        power_total = power_full + power_partial
        total_power += power_total

        buildings.append({
            "item": node.item,
            "recipe": node.recipe_name,
            "building": node.building,
            "count_exact": round(count_exact, 4),
            "count": count_ceil,
            "last_clock_pct": round(frac * 100, 1) if frac > 0.01 else 100.0,
            "power_mw": round(power_total, 1),
        })

        # Trace inputs
        scale = needed_rate / node.output_per_min
        for input_item, qty in node.inputs.items():
            input_rate = (qty / node.duration_s * 60) * scale
            if input_item in RAW_RESOURCES:
                raw_demands[input_item] = raw_demands.get(input_item, 0) + input_rate
            else:
                child = next((c for c in node.children if c.item == input_item), None)
                if child:
                    _plan_node(child, input_rate)

    _plan_node(dag.root, allocated_rate)

    # Resource sourcing
    train_imports = {}
    local_extraction = {}
    for resource, demand in raw_demands.items():
        local_cap = local_resources.get(resource, 0.0)
        local_used = min(demand, local_cap)
        train_needed = max(0, demand - local_cap)
        local_extraction[resource] = round(local_used, 2)
        if train_needed > 0.01:
            train_imports[resource] = round(train_needed, 2)

    # Building summary
    building_summary: dict[str, int] = {}
    for b in buildings:
        building_summary[b["building"]] = building_summary.get(b["building"], 0) + b["count"]

    return {
        "target_rate": allocated_rate,
        "buildings": buildings,
        "total_buildings": sum(b["count"] for b in buildings),
        "total_power_mw": round(total_power, 1),
        "raw_demands": {k: round(v, 2) for k, v in raw_demands.items()},
        "train_imports": train_imports,
        "local_extraction": local_extraction,
        "building_summary": building_summary,
    }
```

**Step 3: Run tests**

Run: `pytest tests/test_plan_generator.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add backend/engine/plan_generator.py tests/test_plan_generator.py
git commit -m "feat: add plan generator engine for building counts and power"
```

---

## Task 8: Module Builder Engine

**Files:**
- Create: `backend/engine/module_builder.py`
- Create: `tests/test_module_builder.py`

**Reference:** `compute_modules.py` (786 lines). Simplify into the core stamp-copy logic.

**Step 1: Write failing tests**

```python
# tests/test_module_builder.py
import pytest
from backend.engine.plan_generator import generate_factory_plan
from backend.engine.module_builder import compute_modules
from backend.engine.recipe_graph import build_recipe_dag
from backend.db import get_db, init_resource_nodes

@pytest.fixture
def db():
    conn = get_db()
    init_resource_nodes(conn)
    return conn

def test_module_for_iron_plate(db):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    plan = generate_factory_plan(dag, 10.0, {"Iron Ore": 5000.0})
    module = compute_modules(dag, plan)
    assert module["copies"] >= 1
    assert module["buildings_per_module"] > 0
    assert module["rate_per_module"] > 0
    assert abs(module["rate_per_module"] * module["copies"] - 10.0) < 0.5
```

**Step 2: Implement module_builder.py**

```python
# backend/engine/module_builder.py
"""
Decompose a factory plan into smallest repeatable module.

Module = 1 final-product building at 100% clock + all upstream buildings.
Total copies = ceil(target_rate / rate_per_module).
"""
import math
from backend.engine.recipe_graph import RecipeDAG

def compute_modules(dag: RecipeDAG, plan: dict) -> dict:
    """
    Compute the repeatable module for a factory plan.

    Returns: {rate_per_module, copies, buildings_per_module, power_per_module, buildings[]}
    """
    # Module basis: 1 root building at 100% clock
    root = dag.root
    rate_per_module = root.output_per_min  # rate from 1 building at 100%
    target_rate = plan["target_rate"]

    if rate_per_module <= 0:
        return {"rate_per_module": 0, "copies": 0, "buildings_per_module": 0,
                "power_per_module": 0, "buildings": []}

    copies_exact = target_rate / rate_per_module
    copies = math.ceil(copies_exact)

    # Scale each building in the plan to 1-module basis
    module_buildings = []
    total_module_power = 0.0
    for b in plan["buildings"]:
        count_per_module = b["count_exact"] / copies_exact if copies_exact > 0 else 0
        power_per_module = b["power_mw"] / copies_exact if copies_exact > 0 else 0
        module_buildings.append({
            "item": b["item"],
            "recipe": b["recipe"],
            "building": b["building"],
            "count_exact": round(count_per_module, 4),
            "count": math.ceil(count_per_module),
            "power_mw": round(power_per_module, 1),
        })
        total_module_power += power_per_module

    return {
        "rate_per_module": round(rate_per_module, 4),
        "copies": copies,
        "buildings_per_module": sum(b["count"] for b in module_buildings),
        "power_per_module": round(total_module_power, 1),
        "buildings": module_buildings,
    }
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_module_builder.py -v`

```bash
git add backend/engine/module_builder.py tests/test_module_builder.py
git commit -m "feat: add module builder engine for stamp-copy decomposition"
```

---

## Task 9: API Routers — Items & Themes

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/items.py`
- Create: `backend/routers/themes.py`
- Modify: `backend/main.py` (register routers)
- Create: `tests/test_api_items.py`

**Step 1: Write failing tests**

```python
# tests/test_api_items.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200

def test_get_target_items():
    r = client.get("/api/items/targets")
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    # Should include complex items like Heavy Modular Frame
    names = [i["name"] for i in items]
    assert "Heavy Modular Frame" in names

def test_get_recipes_for_item():
    r = client.get("/api/recipes", params={"item_name": "Iron Plate"})
    assert r.status_code == 200
    recipes = r.json()
    assert len(recipes) >= 1
    assert recipes[0]["name"]

def test_get_themes():
    r = client.get("/api/themes")
    assert r.status_code == 200
    themes = r.json()
    assert len(themes) >= 8
```

**Step 2: Implement routers**

```python
# backend/routers/items.py
from fastapi import APIRouter
from backend.db import get_db

router = APIRouter(prefix="/api")

@router.get("/items/targets")
def get_target_items():
    """Items with Manufacturer or Assembler recipes — viable production targets."""
    db = get_db()
    rows = db.execute("""
        SELECT DISTINCT i.name, i.id
        FROM items i
        JOIN recipe_products rp ON rp.item_id = i.id
        JOIN recipe_buildings rb ON rb.recipe_id = rp.recipe_id
        JOIN buildings b ON b.id = rb.building_id
        WHERE b.name IN ('Manufacturer', 'Assembler', 'Blender', 'Particle Accelerator')
        ORDER BY i.name
    """).fetchall()
    return [{"id": r["id"], "name": r["name"]} for r in rows]

@router.get("/recipes")
def get_recipes(item_name: str):
    """All recipes that produce a given item."""
    db = get_db()
    rows = db.execute("""
        SELECT r.id, r.name, r.duration, b.name as building, b.power_used
        FROM recipes r
        JOIN recipe_products rp ON rp.recipe_id = r.id
        JOIN items i ON i.id = rp.item_id
        JOIN recipe_buildings rb ON rb.recipe_id = r.id
        JOIN buildings b ON b.id = rb.building_id
        WHERE i.name = ?
    """, (item_name,)).fetchall()

    recipes = []
    for row in rows:
        ingredients = db.execute("""
            SELECT i.name, ri.quantity FROM recipe_ingredients ri
            JOIN items i ON i.id = ri.item_id WHERE ri.recipe_id = ?
        """, (row["id"],)).fetchall()
        products = db.execute("""
            SELECT i.name, rp.quantity FROM recipe_products rp
            JOIN items i ON i.id = rp.item_id WHERE rp.recipe_id = ?
        """, (row["id"],)).fetchall()
        recipes.append({
            "id": row["id"],
            "name": row["name"],
            "duration": row["duration"],
            "building": row["building"],
            "power_mw": row["power_used"],
            "is_alternate": row["name"].startswith("Alternate:"),
            "inputs": [{"item": i["name"], "quantity": i["quantity"]} for i in ingredients],
            "outputs": [{"item": p["name"], "quantity": p["quantity"]} for p in products],
        })
    return recipes
```

```python
# backend/routers/themes.py
from fastapi import APIRouter
from backend.engine.theme_assigner import load_themes

router = APIRouter(prefix="/api")

@router.get("/themes")
def get_themes():
    return load_themes()
```

Update `backend/main.py` to register routers:
```python
from backend.routers import items, themes
app.include_router(items.router)
app.include_router(themes.router)
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_api_items.py -v`

```bash
git add backend/routers/ backend/main.py tests/test_api_items.py
git commit -m "feat: add items, recipes, and themes API endpoints"
```

---

## Task 10: API Routers — Plan Pipeline

**Files:**
- Create: `backend/routers/plan.py`
- Create: `backend/routers/map_api.py`
- Create: `backend/models.py`
- Modify: `backend/main.py` (register routers)
- Create: `tests/test_api_plan.py`

**Step 1: Write failing tests**

```python
# tests/test_api_plan.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_analyze():
    r = client.post("/api/plan/analyze", json={
        "target_item": "Iron Plate",
        "target_rate": 10.0,
        "excluded_recipes": [],
        "max_factories": 8,
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data["themes"]) >= 1
    assert "dag" in data

def test_locations():
    r = client.post("/api/plan/locations", json={
        "themes": [{"theme_id": "iron-works", "critical_resources": {"Iron Ore": 100.0}}],
        "search_radius_m": 500,
        "excluded_quadrants": [],
        "n_results": 3,
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1

def test_allocate():
    r = client.post("/api/plan/allocate", json={
        "factories": [{
            "theme_id": "iron-works",
            "demands_per_unit": {"Iron Ore": 100.0},
            "local_capacity": {"Iron Ore": 5000.0},
        }],
        "target_rate": 10.0,
        "train_penalty": 2.0,
        "water_penalty": 3.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert abs(data[0]["allocated_rate"] - 10.0) < 0.01

def test_map_nodes():
    r = client.get("/api/map/nodes")
    assert r.status_code == 200
    nodes = r.json()
    assert len(nodes) > 500
```

**Step 2: Implement models.py and routers**

```python
# backend/models.py
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    target_item: str
    target_rate: float
    excluded_recipes: list[str] = []
    max_factories: int = 8

class LocationTheme(BaseModel):
    theme_id: str
    critical_resources: dict[str, float]

class LocationsRequest(BaseModel):
    themes: list[LocationTheme]
    search_radius_m: float = 500
    excluded_quadrants: list[str] = []
    n_results: int = 3

class AllocateFactory(BaseModel):
    theme_id: str
    demands_per_unit: dict[str, float]
    local_capacity: dict[str, float]

class AllocateRequest(BaseModel):
    factories: list[AllocateFactory]
    target_rate: float
    train_penalty: float = 2.0
    water_penalty: float = 3.0

class GenerateFactory(BaseModel):
    theme_id: str
    target_item: str
    excluded_recipes: list[str]
    allocated_rate: float
    local_resources: dict[str, float]

class GenerateRequest(BaseModel):
    factories: list[GenerateFactory]
```

```python
# backend/routers/plan.py
from fastapi import APIRouter
from backend.models import AnalyzeRequest, LocationsRequest, AllocateRequest, GenerateRequest
from backend.db import get_db, init_resource_nodes, get_resource_nodes
from backend.engine.recipe_graph import build_recipe_dag, get_raw_demands
from backend.engine.theme_assigner import assign_themes, load_themes
from backend.engine.location_finder import find_locations
from backend.engine.allocator import allocate_production
from backend.engine.plan_generator import generate_factory_plan
from backend.engine.module_builder import compute_modules

router = APIRouter(prefix="/api/plan")

@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    db = get_db()
    init_resource_nodes(db)
    dag = build_recipe_dag(db, req.target_item, req.excluded_recipes)
    themes = load_themes()
    assignments = assign_themes(dag, themes, req.max_factories)
    raw_demands = get_raw_demands(dag, req.target_rate)

    # Serialize DAG for frontend visualization
    dag_nodes = []
    for node in dag.nodes:
        dag_nodes.append({
            "item": node.item,
            "recipe": node.recipe_name,
            "building": node.building,
            "inputs": list(node.inputs.keys()),
            "children": [c.item for c in node.children],
        })

    return {
        "themes": [{"theme": a["theme"], "raw_demands": a["raw_demands"]} for a in assignments],
        "dag": dag_nodes,
        "raw_demands": raw_demands,
    }

@router.post("/locations")
def locations(req: LocationsRequest):
    db = get_db()
    init_resource_nodes(db)
    nodes = get_resource_nodes(db)
    results = {}
    for theme in req.themes:
        results[theme.theme_id] = find_locations(
            nodes, theme.critical_resources,
            req.search_radius_m, req.n_results, req.excluded_quadrants,
        )
    return results

@router.post("/allocate")
def allocate(req: AllocateRequest):
    factories = [f.model_dump() for f in req.factories]
    return allocate_production(factories, req.target_rate, req.train_penalty, req.water_penalty)

@router.post("/generate")
def generate(req: GenerateRequest):
    db = get_db()
    init_resource_nodes(db)
    results = []
    for f in req.factories:
        dag = build_recipe_dag(db, f.target_item, f.excluded_recipes)
        plan = generate_factory_plan(dag, f.allocated_rate, f.local_resources)
        module = compute_modules(dag, plan)
        results.append({
            "theme_id": f.theme_id,
            "plan": plan,
            "module": module,
        })
    return results
```

```python
# backend/routers/map_api.py
from fastapi import APIRouter
from backend.db import get_db, init_resource_nodes, get_resource_nodes

router = APIRouter(prefix="/api/map")

@router.get("/nodes")
def nodes():
    db = get_db()
    init_resource_nodes(db)
    return get_resource_nodes(db)
```

Register in `main.py`:
```python
from backend.routers import items, themes, plan, map_api
app.include_router(plan.router)
app.include_router(map_api.router)
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_api_plan.py -v`

```bash
git add backend/routers/plan.py backend/routers/map_api.py backend/models.py tests/test_api_plan.py
git commit -m "feat: add plan pipeline and map API endpoints"
```

---

## Task 11: Frontend — TypeScript Types & API Hooks

**Files:**
- Create: `frontend/src/types/plan.ts`
- Create: `frontend/src/hooks/usePlanAPI.ts`

**Step 1: Create TypeScript types matching Pydantic models**

```typescript
// frontend/src/types/plan.ts
export interface TargetItem {
  id: string
  name: string
}

export interface Recipe {
  id: string
  name: string
  duration: number
  building: string
  power_mw: number
  is_alternate: boolean
  inputs: { item: string; quantity: number }[]
  outputs: { item: string; quantity: number }[]
}

export interface Theme {
  id: string
  name: string
  primary_resources: string[]
  description: string
}

export interface DAGNode {
  item: string
  recipe: string
  building: string
  inputs: string[]
  children: string[]
}

export interface AnalyzeResult {
  themes: { theme: Theme; raw_demands: Record<string, number> }[]
  dag: DAGNode[]
  raw_demands: Record<string, number>
}

export interface LocationCandidate {
  center: { x: number; y: number }
  score: number
  resources: Record<string, {
    node_count: number
    purity_breakdown: Record<string, number>
    score: number
  }>
  nearby_nodes: ResourceNode[]
}

export interface ResourceNode {
  type: string
  purity: string
  x: number
  y: number
  z: number
}

export interface AllocationResult {
  theme_id: string
  allocated_rate: number
  effort: number
}

export interface Building {
  item: string
  recipe: string
  building: string
  count_exact: number
  count: number
  last_clock_pct: number
  power_mw: number
}

export interface FactoryPlan {
  target_rate: number
  buildings: Building[]
  total_buildings: number
  total_power_mw: number
  raw_demands: Record<string, number>
  train_imports: Record<string, number>
  local_extraction: Record<string, number>
  building_summary: Record<string, number>
}

export interface Module {
  rate_per_module: number
  copies: number
  buildings_per_module: number
  power_per_module: number
  buildings: Building[]
}

export interface FactoryResult {
  theme_id: string
  plan: FactoryPlan
  module: Module
}

export interface UserPreferences {
  targetItem: string
  targetRate: number
  maxFactories: number
  optimization: "balanced" | "min_buildings" | "min_power"
  trainPenalty: number
  searchRadiusM: number
  excludedQuadrants: string[]
  excludedRecipes: string[]
}
```

**Step 2: Create API hooks**

```typescript
// frontend/src/hooks/usePlanAPI.ts
import type {
  TargetItem, Recipe, Theme, AnalyzeResult,
  LocationCandidate, AllocationResult, FactoryResult,
  ResourceNode
} from "../types/plan"

const API = "/api"

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export function usePlanAPI() {
  return {
    getTargetItems: () =>
      fetchJSON<TargetItem[]>(`${API}/items/targets`),

    getRecipes: (itemName: string) =>
      fetchJSON<Recipe[]>(`${API}/recipes?item_name=${encodeURIComponent(itemName)}`),

    getThemes: () =>
      fetchJSON<Theme[]>(`${API}/themes`),

    analyze: (targetItem: string, targetRate: number, excludedRecipes: string[], maxFactories: number) =>
      fetchJSON<AnalyzeResult>(`${API}/plan/analyze`, {
        method: "POST",
        body: JSON.stringify({
          target_item: targetItem,
          target_rate: targetRate,
          excluded_recipes: excludedRecipes,
          max_factories: maxFactories,
        }),
      }),

    findLocations: (themes: { theme_id: string; critical_resources: Record<string, number> }[],
                     searchRadiusM: number, excludedQuadrants: string[], nResults: number) =>
      fetchJSON<Record<string, LocationCandidate[]>>(`${API}/plan/locations`, {
        method: "POST",
        body: JSON.stringify({
          themes, search_radius_m: searchRadiusM,
          excluded_quadrants: excludedQuadrants, n_results: nResults,
        }),
      }),

    allocate: (factories: { theme_id: string; demands_per_unit: Record<string, number>;
               local_capacity: Record<string, number> }[],
               targetRate: number, trainPenalty: number, waterPenalty: number) =>
      fetchJSON<AllocationResult[]>(`${API}/plan/allocate`, {
        method: "POST",
        body: JSON.stringify({
          factories, target_rate: targetRate,
          train_penalty: trainPenalty, water_penalty: waterPenalty,
        }),
      }),

    generate: (factories: { theme_id: string; target_item: string;
               excluded_recipes: string[]; allocated_rate: number;
               local_resources: Record<string, number> }[]) =>
      fetchJSON<FactoryResult[]>(`${API}/plan/generate`, {
        method: "POST",
        body: JSON.stringify({ factories }),
      }),

    getMapNodes: () =>
      fetchJSON<ResourceNode[]>(`${API}/map/nodes`),
  }
}
```

**Step 3: Commit**

```bash
git add frontend/src/types/ frontend/src/hooks/
git commit -m "feat: add TypeScript types and API hooks for plan pipeline"
```

---

## Task 12: Frontend — Wizard Shell & Preferences Step

**Files:**
- Create: `frontend/src/components/wizard/WizardShell.tsx`
- Create: `frontend/src/components/wizard/PreferencesStep.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Implement WizardShell (step management)**

```tsx
// frontend/src/components/wizard/WizardShell.tsx
import { useState } from "react"
import type { UserPreferences, AnalyzeResult, LocationCandidate, FactoryResult } from "../../types/plan"
import PreferencesStep from "./PreferencesStep"
// RecipeStep and LocationStep created in later tasks

type WizardStep = "preferences" | "recipes" | "locations" | "dashboard"

interface WizardState {
  preferences: UserPreferences | null
  analysis: AnalyzeResult | null
  selectedLocations: Record<string, LocationCandidate> | null
  results: FactoryResult[] | null
}

export default function WizardShell() {
  const [step, setStep] = useState<WizardStep>("preferences")
  const [state, setState] = useState<WizardState>({
    preferences: null, analysis: null, selectedLocations: null, results: null,
  })

  return (
    <div>
      {/* Step indicator */}
      <nav style={{ display: "flex", gap: 16, padding: 16, borderBottom: "1px solid #333" }}>
        {(["preferences", "recipes", "locations", "dashboard"] as const).map((s, i) => (
          <span key={s} style={{
            color: s === step ? "#fff" : "#666",
            fontWeight: s === step ? "bold" : "normal",
          }}>
            {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
          </span>
        ))}
      </nav>

      {step === "preferences" && (
        <PreferencesStep onComplete={(prefs) => {
          setState(s => ({ ...s, preferences: prefs }))
          setStep("recipes")
        }} />
      )}
      {/* Other steps rendered in later tasks */}
      {step === "recipes" && <div>Recipe Selection (Task 13)</div>}
      {step === "locations" && <div>Location Selection (Task 14)</div>}
      {step === "dashboard" && <div>Dashboard (Task 15-18)</div>}
    </div>
  )
}
```

**Step 2: Implement PreferencesStep**

The PreferencesStep component includes:
- Searchable target item dropdown (fetches from `/api/items/targets`)
- Target rate slider + manual input
- Number of factories slider (1-8 or auto)
- Optimization radio group
- Train penalty slider (2x-10x)
- Search radius slider (200m-1000m)
- Minimap quadrant exclusion (clickable 2x2 grid)

Implementation: standard React form with `useState` for each field, `useEffect` to fetch items on mount. On submit, calls `onComplete` with the UserPreferences object.

**Step 3: Update App.tsx**

```tsx
// frontend/src/App.tsx
import WizardShell from "./components/wizard/WizardShell"

export default function App() {
  return (
    <div style={{ background: "#0d1117", color: "#ccc", minHeight: "100vh",
                  fontFamily: "'Courier New', monospace" }}>
      <WizardShell />
    </div>
  )
}
```

**Step 4: Verify frontend renders, commit**

Run: `cd frontend && npm run dev` — should show preferences form

```bash
git add frontend/src/
git commit -m "feat: add wizard shell and preferences step"
```

---

## Task 13: Frontend — Recipe Selection Step

**Files:**
- Create: `frontend/src/components/wizard/RecipeStep.tsx`
- Create: `frontend/src/components/recipes/RecipeDAG.tsx`
- Modify: `frontend/src/components/wizard/WizardShell.tsx`

This step calls `/api/plan/analyze`, displays the recipe DAG, and lets users toggle default/alternate recipes. Sidebar shows active themes.

**Key UI elements:**
- DAG visualization showing recipe nodes connected by edges (adapt from factory-map.html DAG rendering, lines ~900-1100)
- Each node: item name, building icon, click to cycle recipe variants
- Right sidebar: active themes list with colored indicators
- "Re-analyze" button to update after recipe changes
- "Next" button to proceed to location selection

**RecipeDAG.tsx:** Renders DAG as SVG with nodes positioned in topological layers. Nodes are clickable. Edges connect inputs to outputs. Reference the existing canvas-based DAG in factory-map.html for layout logic.

**Step: Commit**

```bash
git add frontend/src/components/wizard/RecipeStep.tsx frontend/src/components/recipes/
git commit -m "feat: add recipe selection step with interactive DAG"
```

---

## Task 14: Frontend — Location Selection Step (Map)

**Files:**
- Create: `frontend/src/components/wizard/LocationStep.tsx`
- Create: `frontend/src/components/map/GameMap.tsx`
- Create: `frontend/src/components/map/ResourceNodes.tsx`
- Create: `frontend/src/components/map/FactoryMarkers.tsx`
- Modify: `frontend/src/components/wizard/WizardShell.tsx`

**Key UI elements:**
- Full-screen Leaflet map using CRS.Simple with the game map image as tile layer
- Resource nodes rendered as colored circles (by type)
- Candidate locations rendered as larger circles with theme color
- Click candidate to select it (one per theme)
- Overlap warnings when two selections share resource nodes
- Sidebar: selected locations with score breakdown
- "Auto-select best" button
- "Next" button → triggers allocation + generation, transitions to dashboard

**GameMap.tsx:** Leaflet map with CRS.Simple. Map image bounds match game coordinates. Coordinate transform: game units to Leaflet LatLng using `L.CRS.Simple` with custom bounds.

Reference `factory-map.html` for coordinate mapping (the canvas-based approach used `xToCanvas` / `yToCanvas` transforms from game coordinates to pixel space — Leaflet equivalent uses `L.imageOverlay` with bounds).

**Step: Commit**

```bash
git add frontend/src/components/wizard/LocationStep.tsx frontend/src/components/map/
git commit -m "feat: add map-based location selection with Leaflet"
```

---

## Task 15: Frontend — Dashboard Summary & Factories Tab

**Files:**
- Create: `frontend/src/components/dashboard/Dashboard.tsx`
- Create: `frontend/src/components/dashboard/SummaryBanner.tsx`
- Create: `frontend/src/components/dashboard/FactoriesTab.tsx`
- Modify: `frontend/src/components/wizard/WizardShell.tsx`

**SummaryBanner:** Total buildings, total power, total train imports, factory count — styled like the existing summary banner in factory-map.html (lines 48-80).

**FactoriesTab:** Factory cards with building summaries, power, resource breakdown. Click card for detailed view with per-building table. Reference the factory card rendering from factory-map.html (lines 85-130).

**Step: Commit**

```bash
git add frontend/src/components/dashboard/
git commit -m "feat: add dashboard with summary banner and factories tab"
```

---

## Task 16: Frontend — Dashboard Map & Modules Tabs

**Files:**
- Create: `frontend/src/components/dashboard/MapTab.tsx`
- Create: `frontend/src/components/dashboard/ModulesTab.tsx`

**MapTab:** Reuse GameMap component with final selected locations, factory markers, and mining town indicators. Non-interactive (view-only, no selection).

**ModulesTab:** Per-factory module breakdown cards. Shows: rate per module, number of copies, building list per module, total buildings, power per module.

**Step: Commit**

```bash
git add frontend/src/components/dashboard/MapTab.tsx frontend/src/components/dashboard/ModulesTab.tsx
git commit -m "feat: add dashboard map and modules tabs"
```

---

## Task 17: Frontend — Export Tab

**Files:**
- Create: `frontend/src/components/dashboard/ExportTab.tsx`

**ExportTab:** Two buttons:
- "Download JSON" — serializes the full plan results to a JSON file
- "Download Markdown" — generates a markdown summary similar to `factory-plan.md`

Uses `Blob` + `URL.createObjectURL` for client-side file download.

**Step: Commit**

```bash
git add frontend/src/components/dashboard/ExportTab.tsx
git commit -m "feat: add export tab with JSON and markdown download"
```

---

## Task 18: Dockerfile & Railway Config

**Files:**
- Create: `Dockerfile`
- Create: `railway.toml`
- Create: `.dockerignore`

**Step 1: Write Dockerfile**

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
```

**Step 2: Write railway.toml**

```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 30
```

**Step 3: Write .dockerignore**

```
__pycache__/
*.pyc
node_modules/
frontend/dist/
.git/
*.md
tests/
analysis/
```

**Step 4: Test local Docker build**

Run: `docker build -t satisfy . && docker run -p 8000:8000 satisfy`
Expected: App accessible at http://localhost:8000

**Step 5: Commit**

```bash
git add Dockerfile railway.toml .dockerignore
git commit -m "feat: add Dockerfile and Railway deployment config"
```

---

## Task 19: Integration Test — Full Pipeline

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write end-to-end test**

```python
# tests/test_integration.py
"""
Integration test: run the full pipeline for Heavy Modular Frame at 10/min.
Exercises: analyze → locations → allocate → generate.
"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_pipeline():
    # Step 1: Analyze
    analyze = client.post("/api/plan/analyze", json={
        "target_item": "Heavy Modular Frame",
        "target_rate": 10.0,
        "excluded_recipes": [],
        "max_factories": 3,
    })
    assert analyze.status_code == 200
    analysis = analyze.json()
    assert len(analysis["themes"]) >= 1
    assert len(analysis["dag"]) >= 5  # HMF has a deep chain

    # Step 2: Find locations
    theme_requests = [
        {"theme_id": t["theme"]["id"], "critical_resources": t["raw_demands"]}
        for t in analysis["themes"]
    ]
    locs = client.post("/api/plan/locations", json={
        "themes": theme_requests,
        "search_radius_m": 500,
        "excluded_quadrants": [],
        "n_results": 3,
    })
    assert locs.status_code == 200
    locations = locs.json()
    assert len(locations) >= 1

    # Step 3: Allocate (use first location for each theme)
    # Build local capacity from location data
    factories = []
    for theme_data in analysis["themes"]:
        tid = theme_data["theme"]["id"]
        theme_locs = locations.get(tid, [])
        if not theme_locs:
            continue
        # Simplified: assume large local capacity for test
        factories.append({
            "theme_id": tid,
            "demands_per_unit": theme_data["raw_demands"],
            "local_capacity": {k: v * 100 for k, v in theme_data["raw_demands"].items()},
        })

    alloc = client.post("/api/plan/allocate", json={
        "factories": factories,
        "target_rate": 10.0,
        "train_penalty": 2.0,
        "water_penalty": 3.0,
    })
    assert alloc.status_code == 200
    allocations = alloc.json()
    total_rate = sum(a["allocated_rate"] for a in allocations)
    assert abs(total_rate - 10.0) < 0.1

    # Step 4: Generate
    gen_factories = []
    for a in allocations:
        matching_theme = next(t for t in analysis["themes"] if t["theme"]["id"] == a["theme_id"])
        gen_factories.append({
            "theme_id": a["theme_id"],
            "target_item": "Heavy Modular Frame",
            "excluded_recipes": [],
            "allocated_rate": a["allocated_rate"],
            "local_resources": {k: v * 100 for k, v in matching_theme["raw_demands"].items()},
        })

    gen = client.post("/api/plan/generate", json={"factories": gen_factories})
    assert gen.status_code == 200
    results = gen.json()
    assert len(results) >= 1
    for r in results:
        assert r["plan"]["total_buildings"] > 0
        assert r["plan"]["total_power_mw"] > 0
        assert r["module"]["copies"] >= 1
```

**Step 2: Run integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add full pipeline integration test for HMF"
```

---

## Summary

| Task | What | Estimated Steps |
|------|------|-----------------|
| 1 | Project scaffolding (FastAPI + React + Vite) | 4 |
| 2 | Database layer + data migration + themes.json | 6 |
| 3 | Recipe graph engine (DAG builder) | 5 |
| 4 | Theme assignment engine | 5 |
| 5 | Location finder engine | 5 |
| 6 | Allocator engine (binary search) | 5 |
| 7 | Plan generator engine (building counts, power) | 4 |
| 8 | Module builder engine (stamp-copy) | 3 |
| 9 | API routers: items, recipes, themes | 3 |
| 10 | API routers: plan pipeline + map | 3 |
| 11 | Frontend: TypeScript types + API hooks | 3 |
| 12 | Frontend: wizard shell + preferences step | 4 |
| 13 | Frontend: recipe selection step + DAG viz | 3 |
| 14 | Frontend: location selection step (Leaflet map) | 3 |
| 15 | Frontend: dashboard summary + factories tab | 3 |
| 16 | Frontend: dashboard map + modules tabs | 3 |
| 17 | Frontend: export tab | 3 |
| 18 | Dockerfile + Railway config | 5 |
| 19 | Integration test: full pipeline | 3 |

**Dependencies:**
- Tasks 1-2 must be done first (scaffolding + data)
- Tasks 3-8 (engine modules) can be done in order (each builds on prior)
- Tasks 9-10 (API) depend on tasks 3-8
- Task 11 (types) can be done in parallel with backend tasks
- Tasks 12-17 (frontend) depend on tasks 9-11
- Task 18 (Docker) can be done anytime after task 1
- Task 19 (integration) depends on tasks 9-10
