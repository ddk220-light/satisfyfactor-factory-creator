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
    plan = generate_factory_plan(dag, 10.0, {"Iron Ore": 5000.0})
    assert plan["target_rate"] == 10.0
    assert len(plan["buildings"]) > 0
    assert plan["total_power_mw"] > 0
    building_types = {b["building"] for b in plan["buildings"]}
    assert len(building_types) >= 1

def test_plan_calculates_train_imports(db):
    dag = build_recipe_dag(db, "Iron Plate", excluded_recipes=[])
    plan = generate_factory_plan(dag, 100.0, {"Iron Ore": 50.0})
    assert plan["train_imports"].get("Iron Ore", 0) > 0

def test_plan_has_building_summary(db):
    dag = build_recipe_dag(db, "Heavy Modular Frame", excluded_recipes=[])
    plan = generate_factory_plan(dag, 1.0, {"Iron Ore": 5000.0, "Limestone": 5000.0, "Coal": 5000.0})
    assert len(plan["building_summary"]) > 0
    assert plan["total_buildings"] > 0
    assert plan["total_buildings"] == sum(plan["building_summary"].values())
