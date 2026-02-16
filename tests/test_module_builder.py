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
    assert abs(module["rate_per_module"] * module["copies"] - 10.0) < module["rate_per_module"]

def test_module_for_hmf(db):
    dag = build_recipe_dag(db, "Heavy Modular Frame", excluded_recipes=[])
    plan = generate_factory_plan(dag, 5.0, {"Iron Ore": 50000.0, "Limestone": 50000.0, "Coal": 50000.0})
    module = compute_modules(dag, plan)
    assert module["copies"] >= 1
    assert module["buildings_per_module"] >= 3  # HMF needs multiple building types
    assert module["power_per_module"] > 0

def test_module_buildings_match_plan(db):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    plan = generate_factory_plan(dag, 10.0, {"Iron Ore": 5000.0})
    module = compute_modules(dag, plan)
    # Module building items should match plan building items
    module_items = {b["item"] for b in module["buildings"]}
    plan_items = {b["item"] for b in plan["buildings"]}
    assert module_items == plan_items
