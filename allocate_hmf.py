#!/usr/bin/env python3
"""Allocate 95 HMF/min across 5 factories based on resource availability and effort.

Effort model:
- Local resources (within 500m): 1x effort per unit/min
- Train resources (beyond 500m): 2x effort per unit/min
- Water: 3x effort per m³/min (always, no fixed nodes)

Goal: Balance effort across all 5 factories while totaling 95 HMF/min.
"""

import json
import math
from collections import defaultdict

# === Load data ===
with open('/Users/deepak/AI/satisfy/selected-factory-locations.json') as f:
    locations = json.load(f)

with open('/Users/deepak/AI/satisfy/resource_nodes.json') as f:
    nodes_data = json.load(f)

all_nodes = nodes_data['resource_nodes']

TARGET_HMF = 95
SEARCH_RADIUS = 50_000  # 500m in game units (cm)
TRAIN_MULT = 2.0
WATER_MULT = 3.0

# Mk.3 Miner @ 250% overclock, capped by Mk.5 belt (780/min)
BELT_CAP = 780
MINER_RATES = {
    'impure': min(120 * 2.5, BELT_CAP),   # 300
    'normal': min(240 * 2.5, BELT_CAP),   # 600
    'pure':   min(480 * 2.5, BELT_CAP),   # 780
}
# Oil Extractor @ 250% overclock, capped by pipe (600 m³/min)
PIPE_CAP = 600
OIL_RATES = {
    'impure': min(60 * 2.5, PIPE_CAP),    # 150
    'normal': min(120 * 2.5, PIPE_CAP),   # 300
    'pure':   min(240 * 2.5, PIPE_CAP),   # 600
}

# Raw resources needed per 1 HMF/min (verified by tracing each factory's recipe chain)
# Units: items/min for solids, m³/min for fluids
RAW_PER_HMF = {
    'ferrium': {
        'iron': 179.0,
        'limestone': 72.0,
    },
    'naphtheon': {
        'iron': 94.25,
        'oil': 50.625,        # m³/min
        'limestone': 20.0,
    },
    'forgeholm': {
        'iron': 125.64,
        'coal': 118.97,
        'limestone': 75.0,
    },
    'luxara': {
        'iron': 97.5,
        'coal': 43.4,
        'limestone': 90.0,
        'bauxite': 80.36,
        'water': 107.14,       # m³/min
    },
    'cathera': {
        'iron': 91.97,
        'copper': 24.57,
        'caterium': 1.185,
        'limestone': 72.0,
    },
}

FACTORY_ORDER = ['ferrium', 'naphtheon', 'forgeholm', 'luxara', 'cathera']
FLUID_RESOURCES = {'oil', 'water'}


def distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def find_local_nodes(center_x, center_y):
    """Find all resource nodes within 500m of center."""
    nearby = defaultdict(list)
    for n in all_nodes:
        d = distance(center_x, center_y, n['x'], n['y'])
        if d <= SEARCH_RADIUS:
            nearby[n['type']].append(n)
    return nearby


def extraction_capacity(resource_type, nodes):
    """Total extraction rate from a list of nodes."""
    if resource_type == 'oil':
        return sum(OIL_RATES[n['purity']] for n in nodes)
    else:
        return sum(MINER_RATES[n['purity']] for n in nodes)


def compute_effort(factory_id, hmf_rate, local_capacity):
    """Compute total effort for a factory at given HMF rate.

    Returns (total_effort, details_dict).
    """
    raw = RAW_PER_HMF[factory_id]
    total_effort = 0
    details = {}

    for resource, demand_per_hmf in raw.items():
        demand = demand_per_hmf * hmf_rate

        if resource == 'water':
            effort = demand * WATER_MULT
            details[resource] = {
                'demand': demand,
                'local': 0,
                'train': 0,
                'water': demand,
                'effort': effort,
            }
        else:
            local_cap = local_capacity.get(resource, 0)
            local_used = min(demand, local_cap)
            train_needed = max(0, demand - local_cap)
            effort = local_used * 1.0 + train_needed * TRAIN_MULT
            details[resource] = {
                'demand': demand,
                'local_cap': local_cap,
                'local_used': local_used,
                'train': train_needed,
                'effort': effort,
            }

        total_effort += details[resource]['effort']

    return total_effort, details


def max_hmf_for_effort(factory_id, target_effort, local_capacity):
    """Binary search for max HMF rate that produces <= target_effort."""
    lo, hi = 0.0, 200.0
    for _ in range(200):
        mid = (lo + hi) / 2
        effort, _ = compute_effort(factory_id, mid, local_capacity)
        if effort <= target_effort:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    # === Compute local capacity for each factory ===
    factory_caps = {}
    factory_local_nodes = {}

    print("=" * 70)
    print("LOCAL EXTRACTION CAPACITY (500m radius, Mk.3 miners)")
    print("=" * 70)

    for fid in FACTORY_ORDER:
        sel = locations['selections'][fid]
        cx = sel['center']['x']
        cy = sel['center']['y']
        local_nodes = find_local_nodes(cx, cy)
        factory_local_nodes[fid] = local_nodes

        caps = {}
        for rtype, nodes in local_nodes.items():
            caps[rtype] = extraction_capacity(rtype, nodes)
        factory_caps[fid] = caps

        print(f"\n{sel['factory_name']} ({fid}) @ ({cx:.0f}, {cy:.0f})")
        needed = RAW_PER_HMF[fid]
        for rtype in sorted(caps.keys()):
            nodes = local_nodes[rtype]
            unit = 'm³/min' if rtype in FLUID_RESOURCES else '/min'
            purity_counts = defaultdict(int)
            for n in nodes:
                purity_counts[n['purity']] += 1
            purity_str = ', '.join(
                f"{purity_counts[p]}{p[0].upper()}"
                for p in ['pure', 'normal', 'impure']
                if purity_counts[p] > 0
            )
            needed_tag = " [NEEDED]" if rtype in needed else ""
            print(f"  {rtype:12s}: {caps[rtype]:7.0f} {unit:8s} "
                  f"({len(nodes)} nodes: {purity_str}){needed_tag}")

    # === Show raw resource requirements per HMF ===
    print(f"\n{'=' * 70}")
    print("RAW RESOURCES PER 1 HMF/min")
    print("=" * 70)

    for fid in FACTORY_ORDER:
        sel = locations['selections'][fid]
        raw = RAW_PER_HMF[fid]
        caps = factory_caps[fid]
        print(f"\n{sel['factory_name']}:")
        for r in sorted(raw.keys()):
            unit = 'm³/min' if r in FLUID_RESOURCES else '/min'
            local_cap = caps.get(r, 0)
            max_local_hmf = local_cap / raw[r] if raw[r] > 0 else float('inf')
            print(f"  {r:12s}: {raw[r]:7.1f} {unit}  "
                  f"(local cap: {local_cap:.0f} → max {max_local_hmf:.1f} HMF local)")

    # === Find balanced allocation via binary search on effort ===
    print(f"\n{'=' * 70}")
    print(f"OPTIMIZING ALLOCATION FOR {TARGET_HMF} HMF/min")
    print("=" * 70)
    print(f"\nEffort model: local=1x, train=2x, water=3x")
    print(f"Strategy: Equal effort across all factories (min-max)\n")

    # Binary search on the balanced effort level
    lo_effort, hi_effort = 0.0, 10_000_000.0
    for _ in range(200):
        mid_effort = (lo_effort + hi_effort) / 2
        total_hmf = sum(
            max_hmf_for_effort(fid, mid_effort, factory_caps[fid])
            for fid in FACTORY_ORDER
        )
        if total_hmf < TARGET_HMF:
            lo_effort = mid_effort
        else:
            hi_effort = mid_effort

    balanced_effort = hi_effort

    # Get final allocation
    allocations = {}
    for fid in FACTORY_ORDER:
        h = max_hmf_for_effort(fid, balanced_effort, factory_caps[fid])
        effort, details = compute_effort(fid, h, factory_caps[fid])
        allocations[fid] = {
            'hmf': h,
            'effort': effort,
            'details': details,
        }

    # Fine-tune to hit exactly TARGET_HMF
    total = sum(a['hmf'] for a in allocations.values())
    scale = TARGET_HMF / total
    for fid in FACTORY_ORDER:
        allocations[fid]['hmf'] *= scale
        h = allocations[fid]['hmf']
        effort, details = compute_effort(fid, h, factory_caps[fid])
        allocations[fid]['effort'] = effort
        allocations[fid]['details'] = details

    # === Print results ===
    print(f"{'Factory':12s} {'HMF/min':>8s} {'Effort':>8s} {'Effort/HMF':>10s}")
    print("-" * 42)
    for fid in FACTORY_ORDER:
        a = allocations[fid]
        name = locations['selections'][fid]['factory_name']
        eph = a['effort'] / a['hmf'] if a['hmf'] > 0 else 0
        print(f"{name:12s} {a['hmf']:8.2f} {a['effort']:8.0f} {eph:10.1f}")

    total_hmf = sum(a['hmf'] for a in allocations.values())
    total_effort = sum(a['effort'] for a in allocations.values())
    print("-" * 42)
    print(f"{'TOTAL':12s} {total_hmf:8.2f} {total_effort:8.0f}")

    # === Detailed breakdown ===
    print(f"\n{'=' * 70}")
    print("DETAILED RESOURCE BREAKDOWN")
    print("=" * 70)

    for fid in FACTORY_ORDER:
        a = allocations[fid]
        sel = locations['selections'][fid]
        h = a['hmf']
        print(f"\n{sel['factory_name']} — {h:.2f} HMF/min (effort: {a['effort']:.0f})")
        print(f"  {'Resource':12s} {'Demand':>8s} {'Local':>8s} {'Train':>8s} {'Effort':>8s} {'Source':>12s}")
        print(f"  {'-'*56}")

        for r in sorted(a['details'].keys()):
            d = a['details'][r]
            demand = d['demand']
            unit = 'm³' if r in FLUID_RESOURCES else ''

            if r == 'water':
                print(f"  {r:12s} {demand:7.1f}{unit:2s} {'—':>8s} {'—':>8s} "
                      f"{d['effort']:7.0f}  WATER (3x)")
            else:
                local = d['local_used']
                train = d['train']
                src = "ALL LOCAL" if train < 0.1 else (
                    "ALL TRAIN" if local < 0.1 else "MIXED")
                pct_local = local / demand * 100 if demand > 0 else 0
                print(f"  {r:12s} {demand:7.1f}{unit:2s} {local:7.1f}{unit:2s} "
                      f"{train:7.1f}{unit:2s} {d['effort']:7.0f}  "
                      f"{src} ({pct_local:.0f}% local)")

    # === Bottleneck analysis ===
    print(f"\n{'=' * 70}")
    print("BOTTLENECK ANALYSIS")
    print("=" * 70)

    for fid in FACTORY_ORDER:
        a = allocations[fid]
        sel = locations['selections'][fid]
        h = a['hmf']
        raw = RAW_PER_HMF[fid]
        caps = factory_caps[fid]

        # Find which resource hits local cap first (lowest max_local_hmf)
        bottlenecks = []
        for r, demand in raw.items():
            if r == 'water':
                continue
            local_cap = caps.get(r, 0)
            max_local = local_cap / demand if demand > 0 else float('inf')
            bottlenecks.append((r, max_local, local_cap, demand * h))

        bottlenecks.sort(key=lambda x: x[1])
        print(f"\n{sel['factory_name']} ({h:.2f} HMF/min):")
        for r, max_local, cap, actual_demand in bottlenecks:
            unit = 'm³/min' if r in FLUID_RESOURCES else '/min'
            overflow = max(0, actual_demand - cap)
            if overflow > 0:
                print(f"  {r:12s}: cap {cap:.0f}{unit}, "
                      f"need {actual_demand:.0f}{unit} → "
                      f"overflow {overflow:.0f}{unit} by train "
                      f"(local sustains {max_local:.1f} HMF)")
            else:
                print(f"  {r:12s}: cap {cap:.0f}{unit}, "
                      f"need {actual_demand:.0f}{unit} → ALL LOCAL "
                      f"(local sustains {max_local:.1f} HMF)")

    # === Save allocation ===
    output = {
        'meta': {
            'target_hmf': TARGET_HMF,
            'search_radius_m': SEARCH_RADIUS / 100,
            'effort_model': {
                'local': '1x',
                'train': '2x',
                'water': '3x',
            },
        },
        'allocations': {},
    }

    for fid in FACTORY_ORDER:
        a = allocations[fid]
        sel = locations['selections'][fid]
        resource_detail = {}
        for r, d in a['details'].items():
            resource_detail[r] = {
                'demand_per_min': round(d['demand'], 2),
                'local_per_min': round(d.get('local_used', 0), 2),
                'train_per_min': round(d.get('train', 0), 2),
                'effort': round(d['effort'], 1),
            }
            if r == 'water':
                resource_detail[r]['water_per_min'] = round(d['water'], 2)

        output['allocations'][fid] = {
            'factory_name': sel['factory_name'],
            'hmf_per_min': round(a['hmf'], 2),
            'effort': round(a['effort'], 1),
            'effort_per_hmf': round(a['effort'] / a['hmf'], 2) if a['hmf'] > 0 else 0,
            'resources': resource_detail,
        }

    with open('/Users/deepak/AI/satisfy/hmf-allocation.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n\nAllocation saved to hmf-allocation.json")


if __name__ == '__main__':
    main()
