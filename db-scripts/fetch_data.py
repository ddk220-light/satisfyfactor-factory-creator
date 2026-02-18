#!/usr/bin/env python3
"""
Fetch Satisfactory game data from the Satisfactory Calculator API.
Based on the logic from https://github.com/AnthorNet/SC-ProductionPlanner

The API requires Origin header to return data (CORS policy).
Items data is merged from toolsData + itemsData (matching the original repo's logic).
"""

import json
import urllib.request
from pathlib import Path

API_URL = "https://satisfactory-calculator.com/en/api/game?v=1"
DATA_DIR = Path(__file__).parent / "data"


def fetch_game_data():
    """Fetch game data from the Satisfactory Calculator API."""
    req = urllib.request.Request(API_URL, headers={
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "Origin": "https://satisfactory-calculator.com",
        "Referer": "https://satisfactory-calculator.com/",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def save_json(name, data):
    path = DATA_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    count = len(data) if isinstance(data, (dict, list)) else 1
    print(f"  {path.name}: {count} entries")


def main():
    DATA_DIR.mkdir(exist_ok=True)

    print("Fetching game data from Satisfactory Calculator API...")
    raw = fetch_game_data()
    print(f"Branch: {raw.get('branch', 'unknown')}\n")

    # Save the full raw response
    save_json("_raw_full", raw)

    # Split into individual files (matching the original repo's data keys)
    print("Exporting individual datasets:")
    save_json("buildings", raw["buildingsData"])
    save_json("buildings_categories", raw["buildingsCategories"])
    save_json("recipes", raw["recipesData"])
    save_json("items", raw["itemsData"])
    save_json("items_categories", raw["itemsCategories"])
    save_json("tools", raw["toolsData"])
    save_json("tools_categories", raw["toolsCategories"])
    save_json("fauna", raw["faunaData"])
    save_json("fauna_categories", raw["faunaCategories"])
    save_json("schematics", raw["schematicsData"])
    save_json("mods", raw["modsData"])

    # Merged items (tools + items) — this is what the Production Planner uses
    merged_items = {}
    merged_items.update(raw["toolsData"])
    merged_items.update(raw["itemsData"])
    save_json("items_merged", merged_items)

    print(f"\nDone. All files saved to {DATA_DIR}/")


if __name__ == "__main__":
    main()
