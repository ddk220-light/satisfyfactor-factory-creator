#!/usr/bin/env python3
"""Find optimal factory locations based on proximity to critical (non-trainable) resources.

Logic:
- Iron can be shipped by train to all factories EXCEPT Ferrium (which is iron-centric).
- Each factory scores locations by nearby critical resources, weighted by:
  1. Demand rate (items/min needed for 1 HMF/min)
  2. Rarity (fewer nodes on map = higher weight)
  3. Purity (pure > normal > impure)
- Water is ignored (extractors work anywhere on water bodies).
"""

import json
import math
from collections import defaultdict

RESOURCE_NODES_PATH = '/Users/deepak/AI/satisfy/resource_nodes.json'
FACTORY_PLANS_PATH = '/Users/deepak/AI/satisfy/factory-plans.json'
OUTPUT_PATH = '/Users/deepak/AI/satisfy/factory-locations.json'

SEARCH_RADIUS = 40_000  # 400m in-game (units are cm)
MIN_SEPARATION = 25_000  # Min distance between ranked locations

# Purity weights based on Mk.3 miner extraction rates (120/240/480)
PURITY_WEIGHT = {'impure': 1, 'normal': 2, 'pure': 4}

# --- Resource demands per 1 HMF/min (from calc_resources.py) ---
# critical_resources: resources that must be LOCAL (not trainable)
# demand_per_min: how much is needed for 1 HMF/min
FACTORY_CONFIG = {
    'ferrium': {
        'name': 'Ferrium',
        'theme': 'Pure Iron',
        'all_resources': ['iron', 'limestone'],
        'critical_resources': {  # Ferrium NEEDS local iron
            'iron': 179.0,
            'limestone': 72.0,
        },
    },
    'naphtheon': {
        'name': 'Naphtheon',
        'theme': 'Oil Ecosystem',
        'all_resources': ['iron', 'oil', 'limestone'],
        'critical_resources': {  # Iron trains in; locate near OIL
            'oil': 50.6,
            'limestone': 20.0,
        },
    },
    'forgeholm': {
        'name': 'Forgeholm',
        'theme': 'Steel Spine',
        'all_resources': ['iron', 'coal', 'limestone'],
        'critical_resources': {  # Iron trains in; locate near COAL
            'coal': 119.0,
            'limestone': 75.0,
        },
    },
    'luxara': {
        'name': 'Luxara',
        'theme': 'Aluminum Replacement',
        'all_resources': ['iron', 'coal', 'limestone', 'bauxite'],
        'critical_resources': {  # Iron trains in; locate near BAUXITE
            'bauxite': 80.4,
            'coal': 43.4,
            'limestone': 90.0,
        },
    },
    'cathera': {
        'name': 'Cathera',
        'theme': 'Copper & Caterium',
        'all_resources': ['iron', 'copper', 'caterium', 'limestone'],
        'critical_resources': {  # Iron trains in; locate near COPPER + CATERIUM
            'copper': 24.6,
            'caterium': 1.2,
            'limestone': 72.0,
        },
    },
}


def load_nodes():
    """Load resource nodes from JSON."""
    with open(RESOURCE_NODES_PATH) as f:
        data = json.load(f)
    return data['resource_nodes']


def distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def count_nodes_by_type(nodes):
    """Count total nodes per resource type (for rarity weighting)."""
    counts = defaultdict(int)
    for n in nodes:
        counts[n['type']] += 1
    return dict(counts)


def compute_resource_importance(critical_resources, node_counts):
    """Compute importance weight per resource type.

    importance = demand_per_min * rarity_factor
    rarity_factor = (max_count / this_count)^2  (rare resources get huge boost)
    """
    max_count = max(node_counts.values())
    importance = {}
    for rtype, demand in critical_resources.items():
        count = node_counts.get(rtype, 1)
        rarity = (max_count / count) ** 1.5  # superlinear rarity boost
        importance[rtype] = demand * rarity
    return importance


def find_nearby(center_x, center_y, nodes, radius, resource_types):
    """Find all nodes of given types within radius."""
    nearby = defaultdict(list)
    for n in nodes:
        if n['type'] not in resource_types:
            continue
        d = distance(center_x, center_y, n['x'], n['y'])
        if d <= radius:
            nearby[n['type']].append({**n, 'distance': d})
    return nearby


def score_location(nearby, critical_resources, importance_weights):
    """Score a location based on nearby critical resources.

    Each node contributes: purity_weight * importance_weight_for_type
    Must have ALL critical resource types present.
    """
    found_types = set(nearby.keys())
    required_types = set(critical_resources.keys())
    if not required_types.issubset(found_types):
        return 0, None

    total_score = 0
    type_details = {}
    for rtype in required_types:
        type_nodes = nearby[rtype]
        # Weight each node by purity and resource importance
        type_score = sum(
            PURITY_WEIGHT[n['purity']] * importance_weights[rtype]
            for n in type_nodes
        )
        total_score += type_score
        type_details[rtype] = {
            'count': len(type_nodes),
            'score': round(type_score, 1),
            'nodes': type_nodes,
        }

    return total_score, type_details


def find_best_locations(factory_id, config, all_nodes, node_counts, n_results=3):
    """Find the best N locations for a factory."""
    critical = config['critical_resources']
    importance = compute_resource_importance(critical, node_counts)
    required_types = set(critical.keys())

    # Use every node of any critical type as a candidate center
    candidates = [n for n in all_nodes if n['type'] in required_types]

    scored = []
    for cand in candidates:
        nearby = find_nearby(cand['x'], cand['y'], all_nodes, SEARCH_RADIUS, required_types)
        base_score, details = score_location(nearby, critical, importance)
        if base_score == 0:
            continue

        # Centroid of all nearby critical nodes
        all_nearby = []
        for rtype in required_types:
            all_nearby.extend(nearby[rtype])
        cx = sum(n['x'] for n in all_nearby) / len(all_nearby)
        cy = sum(n['y'] for n in all_nearby) / len(all_nearby)

        # Also gather ALL resource nodes nearby (including iron) for display
        all_resource_types = set(config['all_resources'])
        all_nearby_full = find_nearby(cx, cy, all_nodes, SEARCH_RADIUS, all_resource_types)

        scored.append({
            'center_x': round(cx, 1),
            'center_y': round(cy, 1),
            'score': round(base_score, 1),
            'details': details,
            'all_nearby': all_nearby_full,
        })

    # Sort by score descending
    scored.sort(key=lambda s: s['score'], reverse=True)

    # Deduplicate: keep only locations sufficiently far apart
    selected = []
    for s in scored:
        too_close = False
        for prev in selected:
            if distance(s['center_x'], s['center_y'], prev['center_x'], prev['center_y']) < MIN_SEPARATION:
                too_close = True
                break
        if not too_close:
            selected.append(s)
        if len(selected) >= n_results:
            break

    return selected


def format_results(factory_id, config, locations):
    """Format results for JSON output."""
    results = []
    for rank, loc in enumerate(locations, 1):
        # Resource summary using ALL nearby resources (incl iron for display)
        resource_summary = {}
        for rtype in sorted(config['all_resources']):
            if rtype in loc['all_nearby']:
                nodes_data = loc['all_nearby'][rtype]
            elif rtype in loc['details']:
                nodes_data = loc['details'][rtype]['nodes']
            else:
                continue

            nodes_info = []
            for n in sorted(nodes_data, key=lambda n: PURITY_WEIGHT[n['purity']], reverse=True):
                nodes_info.append({
                    'purity': n['purity'],
                    'x': round(n['x'], 1),
                    'y': round(n['y'], 1),
                    'distance_from_center': round(n.get('distance', distance(
                        n['x'], n['y'], loc['center_x'], loc['center_y'])), 0),
                })

            resource_summary[rtype] = {
                'node_count': len(nodes_data),
                'purity_breakdown': {
                    'pure': sum(1 for n in nodes_data if n['purity'] == 'pure'),
                    'normal': sum(1 for n in nodes_data if n['purity'] == 'normal'),
                    'impure': sum(1 for n in nodes_data if n['purity'] == 'impure'),
                },
                'weighted_score': sum(PURITY_WEIGHT[n['purity']] for n in nodes_data),
                'nodes': nodes_info,
            }

        total_nodes = sum(rd['node_count'] for rd in resource_summary.values())

        # Build reason
        critical = config['critical_resources']
        type_summaries = []
        for rtype in sorted(config['all_resources']):
            if rtype not in resource_summary:
                continue
            rd = resource_summary[rtype]
            is_critical = rtype in critical
            tag = ' [LOCAL]' if is_critical else ' [TRAIN]'
            purities = []
            for p in ['pure', 'normal', 'impure']:
                cnt = rd['purity_breakdown'][p]
                if cnt > 0:
                    purities.append(f"{cnt} {p}")
            type_summaries.append(
                f"{rtype}{tag}: {rd['node_count']} nodes ({', '.join(purities)})")

        reason = (
            f"Rank #{rank} for {config['name']}. "
            f"{total_nodes} total resource nodes within {SEARCH_RADIUS/100:.0f}m. "
            f"Resources: {'; '.join(type_summaries)}. "
            f"Score: {loc['score']} (weighted by demand × rarity)."
        )

        results.append({
            'rank': rank,
            'factory_center': {
                'x': loc['center_x'],
                'y': loc['center_y'],
            },
            'search_radius_m': SEARCH_RADIUS / 100,
            'total_nodes': total_nodes,
            'final_score': loc['score'],
            'resources': resource_summary,
            'reason': reason,
        })

    return results


def main():
    print("Loading resource nodes...")
    all_nodes = load_nodes()
    node_counts = count_nodes_by_type(all_nodes)
    print(f"  {len(all_nodes)} nodes loaded")
    print(f"  Types: {dict(sorted(node_counts.items(), key=lambda x: -x[1]))}")

    output = {
        'meta': {
            'description': 'Factory locations optimized for critical non-trainable resources',
            'strategy': 'Iron shipped by train to all factories except Ferrium. '
                        'Locations chosen for proximity to demand-heavy, rare resources.',
            'search_radius_game_units': SEARCH_RADIUS,
            'search_radius_meters': SEARCH_RADIUS / 100,
            'purity_weights': PURITY_WEIGHT,
            'coordinate_system': {
                'x': 'positive = east/right',
                'y': 'positive = south/bottom',
                'units': 'centimeters (100 units = 1 meter)',
            },
        },
        'factory_locations': {},
    }

    for factory_id, config in FACTORY_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Analyzing: {config['name']} ({config['theme']})")
        critical = config['critical_resources']
        importance = compute_resource_importance(critical, node_counts)
        print(f"  Critical resources (demand × rarity importance):")
        for rtype, imp in sorted(importance.items(), key=lambda x: -x[1]):
            demand = critical[rtype]
            print(f"    {rtype}: demand={demand}/min, importance={imp:.1f}")

        locations = find_best_locations(factory_id, config, all_nodes, node_counts, n_results=3)

        if not locations:
            print(f"  WARNING: No locations found!")
            output['factory_locations'][factory_id] = {
                'factory_name': config['name'],
                'theme': config['theme'],
                'required_resources': config['all_resources'],
                'locations': [],
            }
            continue

        formatted = format_results(factory_id, config, locations)
        output['factory_locations'][factory_id] = {
            'factory_name': config['name'],
            'theme': config['theme'],
            'required_resources': config['all_resources'],
            'critical_resources': {k: round(v, 1) for k, v in critical.items()},
            'train_resources': [r for r in config['all_resources'] if r not in critical],
            'locations': formatted,
        }

        for loc in formatted:
            print(f"\n  #{loc['rank']}: Score {loc['final_score']}")
            print(f"    Center: ({loc['factory_center']['x']:.0f}, {loc['factory_center']['y']:.0f})")
            for rtype, rdata in loc['resources'].items():
                pb = rdata['purity_breakdown']
                tag = '[LOCAL]' if rtype in critical else '[TRAIN]'
                print(f"    {rtype} {tag}: {rdata['node_count']} "
                      f"({pb['pure']}P/{pb['normal']}N/{pb['impure']}I)")

    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n\nResults written to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
