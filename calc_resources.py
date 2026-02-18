#!/usr/bin/env python3
"""Calculate raw resource requirements for 1 HMF/min in each mini-factory."""
import json
from collections import defaultdict

with open('/Users/deepak/AI/satisfy/factory-plans.json') as f:
    plans = json.load(f)


def build_recipe_map(factory):
    """Build product -> recipe lookup for a factory."""
    rmap = {}
    for r in factory['recipes']:
        product = r['outputs'][0]['item']
        if product not in rmap:  # first recipe for each product wins
            rmap[product] = r
    return rmap


def calc_raw_resources(factory):
    """Recursively calculate raw resources for 1 HMF/min."""
    rmap = build_recipe_map(factory)
    raw_resources = factory['raw_resources']

    # Track demand for each item
    demands = defaultdict(float)  # item -> per_min needed
    raw_totals = defaultdict(float)

    def trace(item, rate):
        """Trace `rate` items/min of `item` down to raw resources."""
        # Check if it's a raw resource
        if item in raw_resources or item == 'Water':
            raw_totals[item] += rate
            return

        if item not in rmap:
            # Treat as raw if no recipe
            raw_totals[item] += rate
            return

        recipe = rmap[item]
        output_rate = recipe['outputs'][0]['per_min']
        multiplier = rate / output_rate

        for inp in recipe['inputs']:
            inp_item = inp['item']
            inp_rate = inp['per_min'] * multiplier

            # Handle fluid units (mL -> m3)
            if inp_item in ('Crude Oil', 'Water', 'Heavy Oil Residue',
                           'Alumina Solution', 'Petroleum Coke',
                           'Aluminum Scrap', 'Silica'):
                pass  # keep going, trace will resolve

            trace(inp_item, inp_rate)

        # Handle byproducts that feed back into the chain
        # (simplified - doesn't handle circular dependencies perfectly)

    # Start: 1 HMF/min
    trace('Heavy Modular Frame', 1.0)
    return dict(raw_totals)


# Special handling for Luxara's aluminum loop and Naphtheon's oil loop
def calc_luxara():
    """Luxara has Silica circular dependency - solve algebraically."""
    # From manual trace: for 1 HMF/min
    # Iron Plate path: 67.5/min Iron Ingot → 67.5/min Iron Ore
    # Steel path: 30/min Steel Ingot → 30/min Iron Ore + 30/min Coal
    # Al chain (Silica-balanced): need 26.786/min Al Ingot
    #   Over-produce Alumina Solution: 0.6696 machines → 80.4/min Bauxite, ~107 m3/min Water
    #   Coal for Al Scrap: 13.4/min
    # Concrete: 90/min Limestone
    return {
        'Iron Ore': 97.5,
        'Coal': 43.4,
        'Limestone': 90.0,
        'Bauxite': 80.4,
        'Water': 107.1,  # m3/min
    }


def calc_naphtheon():
    """Naphtheon has oil byproduct loop - trace manually."""
    # From manual trace: for 1 HMF/min
    return {
        'Iron Ore': 94.3,
        'Crude Oil': 50.6,  # m3/min
        'Limestone': 20.0,
    }


print("=" * 70)
print("RAW RESOURCES PER 1 HMF/min (by factory)")
print("=" * 70)

for factory in plans['factories']:
    fid = factory['id']
    name = factory['name']
    theme = factory['theme']

    if fid == 'luxara':
        raw = calc_luxara()
    elif fid == 'naphtheon':
        raw = calc_naphtheon()
    else:
        raw = calc_raw_resources(factory)

    print(f"\n{name} ({theme})")
    print(f"  Listed raw: {', '.join(factory['raw_resources'])}")
    print(f"  Per 1 HMF/min:")
    for item, rate in sorted(raw.items(), key=lambda x: -x[1]):
        unit = 'm3/min' if item in ('Water', 'Crude Oil') else '/min'
        print(f"    {item:20s}: {rate:8.1f} {unit}")

    # Determine location-critical resources (non-iron, non-limestone, non-water)
    critical = {k: v for k, v in raw.items()
                if k not in ('Iron Ore', 'Water') and v > 0}
    print(f"  Location-critical (excl iron/water):")
    for item, rate in sorted(critical.items(), key=lambda x: -x[1]):
        print(f"    {item:20s}: {rate:8.1f}/min")
