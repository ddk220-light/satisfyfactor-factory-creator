# tests/test_location_finder.py
import pytest
from backend.db import get_db, init_resource_nodes, get_resource_nodes
from backend.engine.location_finder import find_locations

@pytest.fixture
def db():
    conn = get_db()
    init_resource_nodes(conn)
    return conn

@pytest.fixture
def nodes(db):
    return get_resource_nodes(db)

def test_find_locations_returns_ranked_results(nodes):
    critical = {"Iron Ore": 100.0, "Limestone": 50.0}
    results = find_locations(nodes, critical, 500, 3, [])
    assert len(results) <= 3
    assert len(results) >= 1
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

def test_find_locations_single_resource(nodes):
    critical = {"Iron Ore": 100.0}
    results = find_locations(nodes, critical, 500, 5, [])
    assert len(results) >= 1
    for r in results:
        assert "Iron Ore" in r["resources"]
        assert r["resources"]["Iron Ore"]["node_count"] > 0

def test_excluded_quadrant_filters_locations(nodes):
    critical = {"Iron Ore": 100.0}
    all_results = find_locations(nodes, critical, 500, 10, [])
    ne_excluded = find_locations(nodes, critical, 500, 10, ["NE"])
    assert len(ne_excluded) <= len(all_results)

def test_locations_are_separated(nodes):
    critical = {"Iron Ore": 100.0}
    results = find_locations(nodes, critical, 500, 5, [])
    from backend.engine.location_finder import _distance, MIN_SEPARATION
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            d = _distance(
                results[i]["center"]["x"], results[i]["center"]["y"],
                results[j]["center"]["x"], results[j]["center"]["y"]
            )
            assert d >= MIN_SEPARATION
