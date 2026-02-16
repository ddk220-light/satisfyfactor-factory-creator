"""
Integration test: run the full pipeline for Heavy Modular Frame at 10/min.
Exercises: analyze -> locations -> allocate -> generate.
"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_pipeline():
    # Step 1: Analyze
    analyze = client.post("/api/plan/analyze", json={
        "target_item": "Heavy Modular Frame",
        "target_rate": 10.0,
        "excluded_recipes": [],
        "max_factories": 3,
    })
    assert analyze.status_code == 200
    analysis = analyze.json()
    assert len(analysis["themes"]) >= 1
    assert len(analysis["dag"]) >= 5  # HMF has a deep chain

    # Step 2: Find locations
    theme_requests = [
        {"theme_id": t["theme"]["id"], "critical_resources": t["raw_demands"]}
        for t in analysis["themes"]
    ]
    locs = client.post("/api/plan/locations", json={
        "themes": theme_requests,
        "search_radius_m": 500,
        "excluded_quadrants": [],
        "n_results": 3,
    })
    assert locs.status_code == 200
    locations = locs.json()
    assert len(locations) >= 1

    # Step 3: Allocate (use first location for each theme)
    factories = []
    for theme_data in analysis["themes"]:
        tid = theme_data["theme"]["id"]
        theme_locs = locations.get(tid, [])
        if not theme_locs:
            continue
        # Simplified: assume large local capacity for test
        factories.append({
            "theme_id": tid,
            "demands_per_unit": theme_data["raw_demands"],
            "local_capacity": {k: v * 100 for k, v in theme_data["raw_demands"].items()},
        })

    alloc = client.post("/api/plan/allocate", json={
        "factories": factories,
        "target_rate": 10.0,
        "train_penalty": 2.0,
        "water_penalty": 3.0,
    })
    assert alloc.status_code == 200
    allocations = alloc.json()
    total_rate = sum(a["allocated_rate"] for a in allocations)
    assert abs(total_rate - 10.0) < 0.1

    # Step 4: Generate
    gen_factories = []
    for a in allocations:
        matching_theme = next(t for t in analysis["themes"] if t["theme"]["id"] == a["theme_id"])
        gen_factories.append({
            "theme_id": a["theme_id"],
            "target_item": "Heavy Modular Frame",
            "excluded_recipes": [],
            "allocated_rate": a["allocated_rate"],
            "local_resources": {k: v * 100 for k, v in matching_theme["raw_demands"].items()},
        })

    gen = client.post("/api/plan/generate", json={"factories": gen_factories})
    assert gen.status_code == 200
    results = gen.json()
    assert len(results) >= 1
    for r in results:
        assert r["plan"]["total_buildings"] > 0
        assert r["plan"]["total_power_mw"] > 0
        assert r["module"]["copies"] >= 1
