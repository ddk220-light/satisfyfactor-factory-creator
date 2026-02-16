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
    """Iron Plate has a simple chain: Iron Ore -> Iron Ingot -> Iron Plate."""
    dag = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=[])
    assert len(dag.nodes) >= 2
    assert dag.root.item == "Iron Plate"
    leaves = [n.item for n in dag.leaves()]
    assert "Iron Ingot" in leaves  # Iron Ingot only needs Iron Ore (raw)

def test_raw_demands_for_iron_plate(db):
    """1/min of Iron Plate should require some Iron Ore."""
    dag = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=[])
    demands = get_raw_demands(dag, rate=1.0)
    assert "Iron Ore" in demands
    assert demands["Iron Ore"] > 0

def test_build_dag_for_hmf(db):
    """HMF has a deep chain with multiple intermediates."""
    dag = build_recipe_dag(db, target_item="Heavy Modular Frame", excluded_recipes=[])
    assert len(dag.nodes) >= 5  # HMF -> Modular Frame -> Reinforced Iron Plate -> etc.
    assert dag.root.item == "Heavy Modular Frame"

def test_excluded_recipe_falls_back(db):
    """Excluding a specific recipe should still produce a valid DAG."""
    # Try excluding a recipe that might not exist - should still work
    dag = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=["Alternate: Coated Iron Plate"])
    assert dag.root.item == "Iron Plate"

def test_raw_demands_scale_linearly(db):
    """Doubling the rate should double the demands."""
    dag = build_recipe_dag(db, target_item="Iron Plate", excluded_recipes=[])
    demands_1 = get_raw_demands(dag, rate=1.0)
    demands_2 = get_raw_demands(dag, rate=2.0)
    for resource in demands_1:
        assert abs(demands_2[resource] - 2 * demands_1[resource]) < 0.01
