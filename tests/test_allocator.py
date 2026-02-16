import pytest
from backend.engine.allocator import allocate_production


def test_single_factory_gets_all():
    factories = [{
        "theme_id": "iron-works",
        "demands_per_unit": {"Iron Ore": 100.0, "Limestone": 50.0},
        "local_capacity": {"Iron Ore": 5000.0, "Limestone": 3000.0},
    }]
    result = allocate_production(factories, 10.0, 2.0, 3.0)
    assert len(result) == 1
    assert abs(result[0]["allocated_rate"] - 10.0) < 0.01


def test_two_factories_balanced():
    factories = [
        {"theme_id": "iron-works", "demands_per_unit": {"Iron Ore": 100.0}, "local_capacity": {"Iron Ore": 2000.0}},
        {"theme_id": "coal-forge", "demands_per_unit": {"Coal": 100.0}, "local_capacity": {"Coal": 2000.0}},
    ]
    result = allocate_production(factories, 20.0, 2.0, 3.0)
    total = sum(r["allocated_rate"] for r in result)
    assert abs(total - 20.0) < 0.01


def test_train_penalty_affects_allocation():
    factories = [
        {"theme_id": "a", "demands_per_unit": {"Iron Ore": 100.0}, "local_capacity": {"Iron Ore": 5000.0}},
        {"theme_id": "b", "demands_per_unit": {"Iron Ore": 100.0}, "local_capacity": {"Iron Ore": 500.0}},
    ]
    low_penalty = allocate_production(factories, 20.0, 2.0, 3.0)
    high_penalty = allocate_production(factories, 20.0, 10.0, 3.0)
    a_low = next(r for r in low_penalty if r["theme_id"] == "a")["allocated_rate"]
    a_high = next(r for r in high_penalty if r["theme_id"] == "a")["allocated_rate"]
    assert a_high >= a_low


def test_total_allocation_matches_target():
    factories = [
        {"theme_id": "a", "demands_per_unit": {"Iron Ore": 50.0, "Coal": 30.0}, "local_capacity": {"Iron Ore": 1000.0, "Coal": 500.0}},
        {"theme_id": "b", "demands_per_unit": {"Copper Ore": 80.0}, "local_capacity": {"Copper Ore": 3000.0}},
        {"theme_id": "c", "demands_per_unit": {"Iron Ore": 60.0, "Limestone": 40.0}, "local_capacity": {"Iron Ore": 2000.0, "Limestone": 1000.0}},
    ]
    result = allocate_production(factories, 95.0, 2.0, 3.0)
    total = sum(r["allocated_rate"] for r in result)
    assert abs(total - 95.0) < 0.1
