# tests/test_theme_assigner.py
import pytest
from backend.db import get_db, init_resource_nodes
from backend.engine.recipe_graph import build_recipe_dag
from backend.engine.theme_assigner import assign_themes, load_themes

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
    assert len(assignments) >= 1
    theme_ids = [a["theme"]["id"] for a in assignments]
    assert "iron-works" in theme_ids

def test_max_factories_caps_themes(db, themes):
    dag = build_recipe_dag(db, "Heavy Modular Frame", excluded_recipes=[])
    assignments = assign_themes(dag, themes, max_factories=2)
    assert len(assignments) <= 2

def test_trivial_themes_get_merged(db, themes):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    assignments = assign_themes(dag, themes, max_factories=8)
    assert len(assignments) <= 2
