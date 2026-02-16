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
