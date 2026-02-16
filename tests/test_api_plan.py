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
    assert len(nodes) > 100
