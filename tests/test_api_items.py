import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200

def test_get_target_items():
    r = client.get("/api/items/targets")
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    names = [i["name"] for i in items]
    assert "Heavy Modular Frame" in names

def test_get_recipes_for_item():
    r = client.get("/api/recipes", params={"item_name": "Iron Plate"})
    assert r.status_code == 200
    recipes = r.json()
    assert len(recipes) >= 1
    assert recipes[0]["name"]

def test_get_themes():
    r = client.get("/api/themes")
    assert r.status_code == 200
    themes = r.json()
    assert len(themes) >= 8
