#!/usr/bin/env python3
"""
Build a SQLite database from the Satisfactory game data JSON files.

Schema design:
- buildings: flat table with category_name, extraction rates as columns
- items: unified table (items + tools) with source type and category_name
- recipes: one row per recipe with flat scalar fields
- recipe_ingredients: recipe_id -> item_class -> quantity
- recipe_products: recipe_id -> item_class -> quantity
- recipe_buildings: recipe_id -> building_class (where it's crafted)
- schematics: milestones/research with tier info
- schematic_recipes: schematic_id -> recipe_class (what it unlocks)
- schematic_requirements: schematic_id -> required schematic_class
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(__file__).parent / "satisfactory.db"


def load(name):
    with open(DATA_DIR / f"{name}.json") as f:
        return json.load(f)


def extract_short_id(class_path):
    """Extract the short ID from a full class path.
    '/Game/.../Build_MinerMk1.Build_MinerMk1_C' -> 'Build_MinerMk1_C'
    """
    if not class_path:
        return None
    return class_path.rsplit(".", 1)[-1] if "." in class_path else class_path


def build():
    buildings = load("buildings")
    building_cats = load("buildings_categories")
    items_data = load("items")
    items_cats = load("items_categories")
    tools_data = load("tools")
    tools_cats = load("tools_categories")
    recipes = load("recipes")
    schematics = load("schematics")

    DB_PATH.unlink(missing_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    cur = db.cursor()

    # ── Buildings ──
    cur.execute("""
        CREATE TABLE buildings (
            id                  TEXT PRIMARY KEY,   -- e.g. Build_MinerMk1_C
            class_name          TEXT,
            name                TEXT NOT NULL,
            description         TEXT,
            category            TEXT,               -- key
            category_name       TEXT,               -- human-readable
            power_used          REAL,
            power_generated     TEXT,               -- REAL or JSON for variable (geothermal)
            power_production_exponent REAL,
            power_used_recipes  TEXT,               -- JSON: recipe-specific power ranges
            extraction_rate_impure  INTEGER,
            extraction_rate_normal  INTEGER,
            extraction_rate_pure    INTEGER,
            belt_speed          INTEGER,
            max_flow_rate       INTEGER,
            width               REAL,
            length              REAL,
            height              REAL,
            accepted_fuels      TEXT,               -- JSON array of item IDs
            input_count         INTEGER,
            output_count        INTEGER,
            image_url           TEXT
        )
    """)

    for bid, b in buildings.items():
        ext = b.get("extractionRate") or {}
        pg = b.get("powerGenerated")
        if isinstance(pg, dict):
            pg = json.dumps(pg)
        pur = b.get("powerUsedRecipes")
        if isinstance(pur, dict):
            pur = json.dumps(pur)
        else:
            pur = None
        af = b.get("acceptedFuels")
        if isinstance(af, list):
            af = json.dumps(af)
        else:
            af = None
        cur.execute("""
            INSERT INTO buildings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            bid,
            b.get("className"),
            b["name"],
            b.get("description"),
            b.get("category"),
            building_cats.get(b.get("category", ""), ""),
            b.get("powerUsed"),
            pg,
            b.get("powerProductionExponent"),
            pur,
            ext.get("impure"),
            ext.get("normal"),
            ext.get("pure"),
            b.get("beltSpeed"),
            b.get("maxFlowRate"),
            b.get("width"),
            b.get("length"),
            b.get("height"),
            af,
            b.get("input"),
            b.get("output"),
            b.get("image"),
        ))

    # ── Items (items + tools unified) ──
    cur.execute("""
        CREATE TABLE items (
            id                  TEXT PRIMARY KEY,   -- e.g. Desc_OreIron_C
            class_name          TEXT,
            name                TEXT NOT NULL,
            description         TEXT,
            source              TEXT NOT NULL,       -- 'item' or 'tool'
            category            TEXT,
            category_name       TEXT,
            stack_size          INTEGER,
            sink_points         INTEGER,
            energy              REAL,
            radioactive_decay   REAL,
            damage              REAL,
            image_url           TEXT
        )
    """)

    for iid, item in items_data.items():
        cur.execute("""
            INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            iid,
            item.get("className"),
            item["name"],
            item.get("description"),
            "item",
            item.get("category"),
            items_cats.get(item.get("category", ""), ""),
            item.get("stack"),
            item.get("resourceSinkPoints"),
            item.get("energy"),
            item.get("radioactiveDecay"),
            item.get("damage"),
            item.get("image"),
        ))

    for tid, tool in tools_data.items():
        cur.execute("""
            INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            tid,
            tool.get("className"),
            tool["name"],
            tool.get("description"),
            "tool",
            tool.get("category"),
            tools_cats.get(tool.get("category", ""), ""),
            tool.get("stack"),
            tool.get("resourceSinkPoints"),
            tool.get("energy"),
            tool.get("radioactiveDecay"),
            tool.get("damage"),
            tool.get("image"),
        ))

    # ── Recipes ──
    cur.execute("""
        CREATE TABLE recipes (
            id                  TEXT PRIMARY KEY,   -- e.g. Recipe_IngotIron_C
            class_name          TEXT,
            name                TEXT NOT NULL,
            duration            REAL,               -- seconds per craft cycle
            manual_multiplier   REAL
        )
    """)

    cur.execute("""
        CREATE TABLE recipe_ingredients (
            recipe_id           TEXT NOT NULL REFERENCES recipes(id),
            item_id             TEXT NOT NULL,       -- short ID into items table
            item_class          TEXT NOT NULL,       -- full class path
            quantity            REAL NOT NULL,
            PRIMARY KEY (recipe_id, item_class)
        )
    """)

    cur.execute("""
        CREATE TABLE recipe_products (
            recipe_id           TEXT NOT NULL REFERENCES recipes(id),
            item_id             TEXT NOT NULL,
            item_class          TEXT NOT NULL,
            quantity            REAL NOT NULL,
            PRIMARY KEY (recipe_id, item_class)
        )
    """)

    cur.execute("""
        CREATE TABLE recipe_buildings (
            recipe_id           TEXT NOT NULL REFERENCES recipes(id),
            building_id         TEXT NOT NULL,       -- short ID
            building_class      TEXT NOT NULL,       -- full class path
            PRIMARY KEY (recipe_id, building_class)
        )
    """)

    for rid, r in recipes.items():
        cur.execute("""
            INSERT INTO recipes VALUES (?,?,?,?,?)
        """, (
            rid,
            r.get("className"),
            r["name"],
            r.get("mManufactoringDuration"),
            r.get("mManualManufacturingMultiplier"),
        ))

        ingredients = r.get("ingredients", {})
        if isinstance(ingredients, dict):
            for item_class, qty in ingredients.items():
                cur.execute("""
                    INSERT INTO recipe_ingredients VALUES (?,?,?,?)
                """, (rid, extract_short_id(item_class), item_class, qty))

        produce = r.get("produce", {})
        if isinstance(produce, dict):
            for item_class, qty in produce.items():
                cur.execute("""
                    INSERT INTO recipe_products VALUES (?,?,?,?)
                """, (rid, extract_short_id(item_class), item_class, qty))

        produced_in = r.get("mProducedIn", [])
        if isinstance(produced_in, list):
            for bclass in produced_in:
                if not bclass:
                    continue
                cur.execute("""
                    INSERT INTO recipe_buildings VALUES (?,?,?)
                """, (rid, extract_short_id(bclass), bclass))

    # ── Schematics ──
    cur.execute("""
        CREATE TABLE schematics (
            id                  TEXT PRIMARY KEY,
            class_name          TEXT,
            name                TEXT NOT NULL,
            category            TEXT,
            sub_category        TEXT,
            tier                INTEGER,
            time                REAL
        )
    """)

    cur.execute("""
        CREATE TABLE schematic_recipes (
            schematic_id        TEXT NOT NULL REFERENCES schematics(id),
            recipe_class        TEXT NOT NULL,
            recipe_id           TEXT NOT NULL,
            PRIMARY KEY (schematic_id, recipe_class)
        )
    """)

    cur.execute("""
        CREATE TABLE schematic_requirements (
            schematic_id            TEXT NOT NULL REFERENCES schematics(id),
            required_schematic_class TEXT NOT NULL,
            required_schematic_id   TEXT NOT NULL,
            PRIMARY KEY (schematic_id, required_schematic_class)
        )
    """)

    for sid, s in schematics.items():
        cur.execute("""
            INSERT INTO schematics VALUES (?,?,?,?,?,?,?)
        """, (
            sid,
            s.get("className"),
            s["name"],
            s.get("category"),
            s.get("subCategory"),
            s.get("tier"),
            s.get("time"),
        ))

        for rc in s.get("recipes", []):
            cur.execute("""
                INSERT OR IGNORE INTO schematic_recipes VALUES (?,?,?)
            """, (sid, rc, extract_short_id(rc)))

        for req in s.get("requirements", []):
            cur.execute("""
                INSERT OR IGNORE INTO schematic_requirements VALUES (?,?,?)
            """, (sid, req, extract_short_id(req)))

    # ── Indexes for common queries ──
    cur.execute("CREATE INDEX idx_items_name ON items(name)")
    cur.execute("CREATE INDEX idx_items_category ON items(category)")
    cur.execute("CREATE INDEX idx_buildings_name ON buildings(name)")
    cur.execute("CREATE INDEX idx_buildings_category ON buildings(category)")
    cur.execute("CREATE INDEX idx_recipes_name ON recipes(name)")
    cur.execute("CREATE INDEX idx_recipe_ingredients_item ON recipe_ingredients(item_id)")
    cur.execute("CREATE INDEX idx_recipe_products_item ON recipe_products(item_id)")
    cur.execute("CREATE INDEX idx_recipe_buildings_building ON recipe_buildings(building_id)")
    cur.execute("CREATE INDEX idx_schematics_tier ON schematics(tier)")

    db.commit()

    # ── Summary ──
    print("Database built successfully!\n")
    tables = cur.execute("""
        SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
    """).fetchall()
    for (t,) in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        print(f"  {t}: {count} rows")

    size = DB_PATH.stat().st_size
    print(f"\n  Total: {size:,} bytes ({size/1024:.0f} KB)")
    print(f"  Path: {DB_PATH}")

    db.close()


if __name__ == "__main__":
    build()
