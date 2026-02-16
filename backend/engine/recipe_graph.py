# backend/engine/recipe_graph.py
"""
Build a production DAG for any target item by tracing recipes from the DB.

A DAG node represents one recipe step: item produced, recipe used, building,
power, input/output rates. Edges connect inputs to the recipes that produce them.
Leaves are raw resources (items with no producing recipe).
"""
from __future__ import annotations
from dataclasses import dataclass, field

RAW_RESOURCES = {
    "Iron Ore", "Copper Ore", "Limestone", "Coal", "Caterium Ore",
    "Raw Quartz", "Sulfur", "Bauxite", "Uranium", "Crude Oil",
    "Water", "Nitrogen Gas", "SAM"
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
    defaults = [r for r in available if not r["name"].startswith("Alternate:")]
    return defaults[0] if defaults else available[0]


def build_recipe_dag(db, target_item: str, excluded_recipes: list[str]) -> RecipeDAG:
    """Build full production DAG from target item down to raw resources."""
    excluded = set(excluded_recipes)
    nodes = []
    visited = {}  # item -> RecipeNode

    def _build(item: str) -> RecipeNode | None:
        if item in RAW_RESOURCES:
            return None
        if item in visited:
            return visited[item]

        recipes = _get_recipes_for_item(db, item)
        recipe = _pick_recipe(recipes, excluded)
        if recipe is None:
            return None

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
        scale = needed_rate / node.output_per_min if node.output_per_min > 0 else 0
        for input_item, qty in node.inputs.items():
            input_rate = (qty / node.duration_s * 60) * scale
            if input_item in RAW_RESOURCES:
                demands[input_item] = demands.get(input_item, 0) + input_rate
            else:
                child = next((c for c in node.children if c.item == input_item), None)
                if child:
                    _trace(child, input_rate)

    _trace(dag.root, rate)
    return demands
