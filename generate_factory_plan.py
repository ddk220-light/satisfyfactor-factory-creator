#!/usr/bin/env python3
"""Generate comprehensive factory plan files (MD + JSON)."""

import json
import math
from collections import defaultdict
from datetime import date

# === Load data ===
with open('/Users/deepak/AI/satisfy/selected-factory-locations.json') as f:
    locations = json.load(f)
with open('/Users/deepak/AI/satisfy/factory-plans.json') as f:
    plans = json.load(f)
with open('/Users/deepak/AI/satisfy/hmf-allocation.json') as f:
    allocation = json.load(f)
with open('/Users/deepak/AI/satisfy/resource_nodes.json') as f:
    all_nodes = json.load(f)['resource_nodes']

SEARCH_RADIUS = 50_000
BELT_CAP = 780
PIPE_CAP = 600
MINER_RATES = {'impure': min(300, BELT_CAP), 'normal': min(600, BELT_CAP), 'pure': min(780, BELT_CAP)}
OIL_RATES = {'impure': 150, 'normal': 300, 'pure': 600}
POWER_EXP = 1.321929

FACTORY_ORDER = ['ferrium', 'naphtheon', 'forgeholm', 'luxara', 'cathera']

# === Production chain: buildings per 1 HMF/min ===
# (item, recipe_name, building, power_mw, demand_per_min, output_per_min)
CHAIN = {
    'ferrium': [
        ('Heavy Modular Frame', 'Alternate: Heavy Encased Frame', 'Manufacturer', 55, 1.0, 2.8125),
        ('Modular Frame', 'Alternate: Steeled Frame', 'Assembler', 15, 2.667, 3.0),
        ('Reinforced Iron Plate', 'Alternate: Stitched Iron Plate', 'Assembler', 15, 1.778, 5.625),
        ('Wire', 'Alternate: Iron Wire', 'Constructor', 4, 11.852, 22.5),
        ('Iron Plate', 'Iron Plate', 'Constructor', 4, 5.926, 20.0),
        ('Steel Pipe', 'Alternate: Iron Pipe', 'Constructor', 4, 40.889, 25.0),
        ('Encased Industrial Beam', 'Alternate: Encased Industrial Pipe', 'Assembler', 15, 3.333, 4.0),
        ('Concrete', 'Concrete', 'Constructor', 4, 24.0, 15.0),
        ('Iron Ingot', 'Iron Ingot', 'Smelter', 4, 179.0, 30.0),
    ],
    'naphtheon': [
        ('Heavy Modular Frame', 'Alternate: Heavy Flexible Frame', 'Manufacturer', 55, 1.0, 3.75),
        ('Modular Frame', 'Modular Frame', 'Assembler', 15, 5.0, 2.0),
        ('Reinforced Iron Plate', 'Alternate: Adhered Iron Plate', 'Assembler', 15, 7.5, 3.75),
        ('Iron Plate', 'Alternate: Coated Iron Plate', 'Assembler', 15, 22.5, 75.0),
        ('Screw', 'Screws', 'Constructor', 4, 104.0, 40.0),
        ('Iron Rod', 'Iron Rod', 'Constructor', 4, 56.0, 15.0),
        ('Iron Ingot', 'Iron Ingot', 'Smelter', 4, 67.25, 30.0),
        ('Encased Industrial Beam', 'Encased Industrial Beam', 'Assembler', 15, 3.0, 6.0),
        ('Steel Beam', 'Steel Beam', 'Constructor', 4, 9.0, 15.0),
        ('Steel Ingot', 'Alternate: Coke Steel Ingot', 'Foundry', 16, 36.0, 100.0),
        ('Concrete', 'Alternate: Rubber Concrete', 'Assembler', 15, 18.0, 90.0),
        ('Rubber', 'Rubber', 'Refinery', 30, 31.5, 20.0),
        ('Plastic', 'Plastic', 'Refinery', 30, 2.25, 20.0),
        ('Petroleum Coke', 'Petroleum Coke', 'Refinery', 30, 27.0, 120.0),
    ],
    'forgeholm': [
        ('Heavy Modular Frame', 'Heavy Modular Frame', 'Manufacturer', 55, 1.0, 2.0),
        ('Modular Frame', 'Alternate: Steeled Frame', 'Assembler', 15, 5.0, 3.0),
        ('Reinforced Iron Plate', 'Reinforced Iron Plate', 'Assembler', 15, 3.333, 5.0),
        ('Screw', 'Alternate: Steel Screws', 'Constructor', 4, 160.0, 260.0),
        ('Iron Plate', 'Alternate: Steel Cast Plate', 'Foundry', 16, 20.0, 45.0),
        ('Steel Pipe', 'Steel Pipe', 'Constructor', 4, 66.667, 20.0),
        ('Steel Beam', 'Steel Beam', 'Constructor', 4, 3.077, 15.0),
        ('Encased Industrial Beam', 'Alternate: Encased Industrial Pipe', 'Assembler', 15, 5.0, 4.0),
        ('Concrete', 'Concrete', 'Constructor', 4, 25.0, 15.0),
        ('Steel Ingot', 'Steel Ingot', 'Foundry', 16, 118.974, 45.0),
        ('Iron Ingot', 'Iron Ingot', 'Smelter', 4, 6.667, 30.0),
    ],
    'luxara': [
        ('Heavy Modular Frame', 'Heavy Modular Frame', 'Manufacturer', 55, 1.0, 2.0),
        ('Modular Frame', 'Modular Frame', 'Assembler', 15, 5.0, 2.0),
        ('Reinforced Iron Plate', 'Reinforced Iron Plate', 'Assembler', 15, 7.5, 5.0),
        ('Screw', 'Screws', 'Constructor', 4, 210.0, 40.0),
        ('Iron Rod', 'Alternate: Aluminum Rod', 'Constructor', 4, 82.5, 52.5),
        ('Iron Plate', 'Iron Plate', 'Constructor', 4, 45.0, 20.0),
        ('Steel Pipe', 'Steel Pipe', 'Constructor', 4, 20.0, 20.0),
        ('Encased Industrial Beam', 'Encased Industrial Beam', 'Assembler', 15, 5.0, 6.0),
        ('Steel Beam', 'Alternate: Aluminum Beam', 'Constructor', 4, 15.0, 22.5),
        ('Concrete', 'Concrete', 'Constructor', 4, 30.0, 15.0),
        ('Iron Ingot', 'Iron Ingot', 'Smelter', 4, 67.5, 30.0),
        ('Steel Ingot', 'Steel Ingot', 'Foundry', 16, 30.0, 45.0),
        ('Aluminum Ingot', 'Aluminum Ingot', 'Foundry', 16, 26.786, 60.0),
        ('Aluminum Scrap', 'Aluminum Scrap', 'Refinery', 30, 40.179, 360.0),
        ('Alumina Solution', 'Alumina Solution', 'Refinery', 30, None, 120.0),  # overproduced
    ],
    'cathera': [
        ('Heavy Modular Frame', 'Alternate: Heavy Encased Frame', 'Manufacturer', 55, 1.0, 2.8125),
        ('Modular Frame', 'Alternate: Steeled Frame', 'Assembler', 15, 2.667, 3.0),
        ('Reinforced Iron Plate', 'Alternate: Stitched Iron Plate', 'Assembler', 15, 1.778, 5.625),
        ('Wire', 'Alternate: Fused Wire', 'Assembler', 15, 11.852, 90.0),
        ('Iron Plate', 'Iron Plate', 'Constructor', 4, 5.926, 20.0),
        ('Steel Pipe', 'Alternate: Iron Pipe', 'Constructor', 4, 40.889, 25.0),
        ('Encased Industrial Beam', 'Alternate: Encased Industrial Pipe', 'Assembler', 15, 3.333, 4.0),
        ('Concrete', 'Concrete', 'Constructor', 4, 24.0, 15.0),
        ('Iron Ingot', 'Alternate: Iron Alloy Ingot', 'Foundry', 16, 172.444, 75.0),
        ('Copper Ingot', 'Copper Ingot', 'Smelter', 4, 1.580, 30.0),
        ('Caterium Ingot', 'Caterium Ingot', 'Smelter', 4, 0.395, 15.0),
    ],
}

# Luxara Alumina Solution special: overproduced for Silica balance
# Need 33.482 Silica/min per HMF. Alumina Solution produces 50/min Silica per recipe unit.
# mult = 33.482/50 = 0.6696 recipe units → demand = 0.6696 * 120 = 80.357 m³/min Alumina Solution
LUXARA_ALUMINA_MULT = 0.6696  # recipe multiplier per 1 HMF

RAW_PER_HMF = {
    'ferrium': {'Iron Ore': 179.0, 'Limestone': 72.0},
    'naphtheon': {'Iron Ore': 94.25, 'Crude Oil': 50.625, 'Limestone': 20.0},
    'forgeholm': {'Iron Ore': 125.64, 'Coal': 118.97, 'Limestone': 75.0},
    'luxara': {'Iron Ore': 97.5, 'Coal': 43.4, 'Limestone': 90.0, 'Bauxite': 80.36, 'Water': 107.14},
    'cathera': {'Iron Ore': 91.97, 'Copper Ore': 24.57, 'Caterium Ore': 1.185, 'Limestone': 72.0},
}

RAW_TO_NODE = {
    'Iron Ore': 'iron', 'Limestone': 'limestone', 'Coal': 'coal',
    'Copper Ore': 'copper', 'Caterium Ore': 'caterium', 'Bauxite': 'bauxite',
    'Crude Oil': 'oil', 'Water': 'water',
}

# === Extraction sites (from analysis) ===
EXTRACTION_SITES = {
    'iron': [
        {'name': 'Iron Hub Alpha', 'x': 241941, 'y': 3242,
         'nodes': 8, 'pure': 3, 'normal': 5, 'impure': 0,
         'capacity': 5340, 'note': 'Best iron cluster. Near Luxara (1,047m) and Forgeholm (1,198m).'},
        {'name': 'Iron Hub Beta', 'x': 179893, 'y': -118392,
         'nodes': 2, 'pure': 2, 'normal': 0, 'impure': 0,
         'capacity': 1560, 'note': 'Between Cathera, Forgeholm, Ferrium. Strategic for multi-factory.'},
        {'name': 'Iron West Gamma', 'x': -218000, 'y': -119429,
         'nodes': 7, 'pure': 4, 'normal': 3, 'impure': 0,
         'capacity': 4920, 'note': 'Remote western site. High purity but far from all factories.'},
    ],
    'limestone': [
        {'name': 'Limestone Central', 'x': 169486, 'y': -45968,
         'nodes': 4, 'pure': 1, 'normal': 3, 'impure': 0,
         'capacity': 2580, 'note': 'Reachable by 4 factories. Near Forgeholm (487m).'},
        {'name': 'Limestone South', 'x': 168003, 'y': -86516,
         'nodes': 3, 'pure': 0, 'normal': 3, 'impure': 0,
         'capacity': 1800, 'note': 'Near Forgeholm and Cathera. Closest unclaimed to Ferrium route.'},
        {'name': 'Limestone West', 'x': -195258, 'y': -135899,
         'nodes': 6, 'pure': 5, 'normal': 1, 'impure': 0,
         'capacity': 4500, 'note': 'Massive capacity. Remote but highest purity cluster on map.'},
    ],
}


def distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def find_local_nodes(cx, cy):
    nearby = defaultdict(list)
    for n in all_nodes:
        if distance(cx, cy, n['x'], n['y']) <= SEARCH_RADIUS:
            nearby[n['type']].append(n)
    return nearby


def extraction_cap(rtype, nodes):
    rates = OIL_RATES if rtype == 'oil' else MINER_RATES
    return sum(rates[n['purity']] for n in nodes)


def compute_buildings(fid, hmf_rate):
    """Compute building counts at given HMF rate."""
    chain = CHAIN[fid]
    buildings = []
    total_power = 0

    for item, recipe, btype, power, demand_per_hmf, output_rate in chain:
        # Special: Luxara Alumina Solution overproduction
        if fid == 'luxara' and item == 'Alumina Solution':
            mult = LUXARA_ALUMINA_MULT * hmf_rate
            count = mult
        else:
            demand = demand_per_hmf * hmf_rate
            count = demand / output_rate

        count_floor = int(count)
        count_ceil = math.ceil(count)
        frac = count - count_floor

        # Power: full buildings at 100%, last at frac%
        if frac < 0.001:
            pw = count_floor * power
        else:
            pw = count_floor * power + power * (frac ** POWER_EXP)

        total_power += pw
        buildings.append({
            'item': item,
            'recipe': recipe,
            'building': btype,
            'power_mw': power,
            'count_exact': round(count, 4),
            'count': count_ceil,
            'last_clock_pct': round(frac * 100, 1) if frac > 0.001 else 100.0,
            'power_total_mw': round(pw, 1),
        })

    return buildings, round(total_power, 1)


def building_summary(buildings):
    """Aggregate building counts by type."""
    summary = defaultdict(int)
    for b in buildings:
        summary[b['building']] += b['count']
    return dict(sorted(summary.items()))


def gen_json():
    """Generate comprehensive JSON plan."""
    output = {
        'meta': {
            'title': 'Satisfactory HMF Factory Plan',
            'target': '95 HMF/min across 5 themed mini-factories',
            'date': str(date.today()),
            'parameters': {
                'total_hmf': 95,
                'search_radius_m': 500,
                'miner_tier': 'Mk.3',
                'miner_overclock': '250%',
                'belt_limit': 780,
                'pipe_limit': 600,
                'effort_model': {'local': '1x', 'train': '2x', 'water': '3x'},
            },
        },
        'factories': {},
        'extraction_sites': EXTRACTION_SITES,
        'train_network': {},
    }

    total_train = defaultdict(float)

    for fid in FACTORY_ORDER:
        sel = locations['selections'][fid]
        alloc = allocation['allocations'][fid]
        hmf = alloc['hmf_per_min']
        cx, cy = sel['center']['x'], sel['center']['y']

        # Find factory plan entry
        fplan = next(f for f in plans['factories'] if f['id'] == fid)

        # Local nodes
        local = find_local_nodes(cx, cy)
        local_caps = {rt: extraction_cap(rt, nodes) for rt, nodes in local.items()}

        # Buildings
        bldgs, total_pw = compute_buildings(fid, hmf)
        bsummary = building_summary(bldgs)

        # Raw resources
        raw_detail = {}
        for rname, demand_per in RAW_PER_HMF[fid].items():
            demand = demand_per * hmf
            ntype = RAW_TO_NODE.get(rname)
            if rname == 'Water':
                raw_detail[rname] = {
                    'demand_per_min': round(demand, 1),
                    'source': 'water_extractor',
                    'extractors_needed': math.ceil(demand / 120),
                    'effort_multiplier': 3,
                }
            else:
                cap = local_caps.get(ntype, 0)
                local_used = min(demand, cap)
                train = max(0, demand - cap)
                if train > 0:
                    total_train[rname] += train
                raw_detail[rname] = {
                    'demand_per_min': round(demand, 1),
                    'local_capacity': round(cap, 0),
                    'local_used': round(local_used, 1),
                    'train_import': round(train, 1),
                    'source': 'all_local' if train < 1 else ('all_train' if local_used < 1 else 'mixed'),
                }

        # Local node detail
        node_detail = {}
        for ntype in sorted(local.keys()):
            nodes = local[ntype]
            if ntype not in [RAW_TO_NODE.get(r) for r in RAW_PER_HMF[fid]]:
                continue
            node_detail[ntype] = {
                'count': len(nodes),
                'capacity': local_caps[ntype],
                'by_purity': {
                    'pure': sum(1 for n in nodes if n['purity'] == 'pure'),
                    'normal': sum(1 for n in nodes if n['purity'] == 'normal'),
                    'impure': sum(1 for n in nodes if n['purity'] == 'impure'),
                },
            }

        output['factories'][fid] = {
            'name': fplan['name'],
            'theme': fplan['theme'],
            'hmf_per_min': hmf,
            'location': {'x': cx, 'y': cy},
            'effort': alloc['effort'],
            'raw_resources_per_hmf': {k: round(v, 2) for k, v in RAW_PER_HMF[fid].items()},
            'raw_resources': raw_detail,
            'local_nodes': node_detail,
            'recipes': [{
                'item': b['item'],
                'recipe': b['recipe'],
                'building': b['building'],
                'count': b['count'],
                'count_exact': b['count_exact'],
                'last_clock_pct': b['last_clock_pct'],
                'power_mw_each': b['power_mw'],
                'power_mw_total': b['power_total_mw'],
            } for b in bldgs],
            'building_summary': bsummary,
            'total_buildings': sum(bsummary.values()),
            'total_power_mw': total_pw,
        }

    # Train network summary
    output['train_network'] = {
        rname: {
            'total_demand_per_min': round(amt, 1),
            'consumers': [
                fid for fid in FACTORY_ORDER
                if output['factories'][fid]['raw_resources'].get(rname, {}).get('train_import', 0) > 0
            ],
        }
        for rname, amt in sorted(total_train.items(), key=lambda x: -x[1])
    }

    return output


def gen_markdown(data):
    """Generate markdown plan document."""
    lines = []
    a = lines.append

    a("# Satisfactory HMF Factory Plan\n")
    a(f"*Generated {date.today()}*\n")
    a("## Overview\n")
    a(f"- **Target:** {data['meta']['parameters']['total_hmf']} Heavy Modular Frames/min")
    a(f"- **Factories:** 5 themed mini-factories")
    a(f"- **Strategy:** Iron shipped by train (except Ferrium). Local resources mined within 500m.")
    a(f"- **Miners:** Mk.3 @ 250% overclock, capped by Mk.5 belt (780/min)")
    a(f"- **Effort model:** Local extraction = 1x, Train import = 2x, Water = 3x\n")

    # Summary table
    a("## Allocation Summary\n")
    a("| Factory | Theme | HMF/min | Buildings | Power (MW) | Self-sufficient? |")
    a("|---------|-------|---------|-----------|------------|------------------|")
    total_hmf = total_bldg = total_pw = 0
    for fid in FACTORY_ORDER:
        f = data['factories'][fid]
        train_res = [r for r, d in f['raw_resources'].items()
                     if d.get('train_import', 0) > 0]
        if not train_res:
            status = "Yes"
        else:
            status = f"Train: {', '.join(train_res)}"
        if fid == 'luxara':
            status += " + Water"
        a(f"| {f['name']} | {f['theme']} | {f['hmf_per_min']:.1f} | "
          f"{f['total_buildings']} | {f['total_power_mw']:.0f} | {status} |")
        total_hmf += f['hmf_per_min']
        total_bldg += f['total_buildings']
        total_pw += f['total_power_mw']
    a(f"| **Total** | | **{total_hmf:.1f}** | **{total_bldg}** | **{total_pw:.0f}** | |")
    a("")

    # Per-factory sections
    for fid in FACTORY_ORDER:
        f = data['factories'][fid]
        sel = locations['selections'][fid]
        fplan = next(fp for fp in plans['factories'] if fp['id'] == fid)

        a(f"---\n")
        a(f"## {f['name']} — {f['theme']} ({f['hmf_per_min']:.1f} HMF/min)\n")
        a(f"**Location:** ({f['location']['x']}, {f['location']['y']})  ")
        a(f"**Effort:** {f['effort']:.0f}  ")
        a(f"**Total buildings:** {f['total_buildings']}  ")
        a(f"**Total power:** {f['total_power_mw']:.0f} MW\n")

        # Character description
        if 'character' in fplan:
            a(f"> {fplan['character']}\n")

        # Raw resources
        a("### Raw Resources\n")
        a("| Resource | Per HMF | Total/min | Local Cap | Local Used | Train Import | Source |")
        a("|----------|---------|-----------|-----------|------------|-------------|--------|")
        for rname in RAW_PER_HMF[fid]:
            per_hmf = RAW_PER_HMF[fid][rname]
            rd = f['raw_resources'][rname]
            demand = rd.get('demand_per_min', rd.get('demand_per_min', 0))
            unit = ' m³' if rname in ('Crude Oil', 'Water') else ''
            if rname == 'Water':
                a(f"| {rname} | {per_hmf:.1f}{unit} | {demand:.0f}{unit} | "
                  f"∞ (extractors) | {demand:.0f}{unit} | — | "
                  f"Water (3x effort, {rd['extractors_needed']} extractors) |")
            else:
                cap = rd['local_capacity']
                local = rd['local_used']
                train = rd['train_import']
                src = rd['source'].replace('_', ' ').title()
                a(f"| {rname} | {per_hmf:.1f}{unit} | {demand:.0f}{unit} | "
                  f"{cap:.0f}{unit} | {local:.0f}{unit} | {train:.0f}{unit} | {src} |")
        a("")

        # Local nodes
        a("### Local Resource Nodes (within 500m)\n")
        a("| Resource | Nodes | Pure | Normal | Impure | Capacity |")
        a("|----------|-------|------|--------|--------|----------|")
        for ntype, nd in f['local_nodes'].items():
            bp = nd['by_purity']
            unit = ' m³/min' if ntype == 'oil' else '/min'
            a(f"| {ntype.title()} | {nd['count']} | {bp['pure']} | "
              f"{bp['normal']} | {bp['impure']} | {nd['capacity']}{unit} |")
        a("")

        # Recipe chain / buildings
        a("### Production Chain\n")
        a("| # | Item | Recipe | Building | Count | Clock% | Power (MW) |")
        a("|---|------|--------|----------|-------|--------|------------|")
        for i, r in enumerate(f['recipes'], 1):
            clock = f"{r['last_clock_pct']:.0f}%" if r['last_clock_pct'] < 100 else "100%"
            if r['count'] > 1 and r['last_clock_pct'] < 100:
                clock_note = f"{r['count']-1}×100% + 1×{clock}"
            else:
                clock_note = f"{r['count']}×{clock}"
            a(f"| {i} | {r['item']} | {r['recipe']} | "
              f"{r['building']} | {r['count']} | {clock_note} | {r['power_mw_total']:.0f} |")
        a("")

        # Building summary
        a("### Building Summary\n")
        a("| Building | Count |")
        a("|----------|-------|")
        for btype, count in sorted(f['building_summary'].items()):
            a(f"| {btype} | {count} |")
        a("")

    # Train network
    a("---\n")
    a("## Train Network\n")
    a("Resources that must be imported by train:\n")
    a("| Resource | Total Demand/min | Consumers |")
    a("|----------|-----------------|-----------|")
    for rname, info in data['train_network'].items():
        consumers = ', '.join(
            data['factories'][fid]['name'] for fid in info['consumers']
        )
        a(f"| {rname} | {info['total_demand_per_min']:.0f} | {consumers} |")
    a("")

    # Extraction sites
    a("---\n")
    a("## Resource Extraction Sites\n")
    a("Recommended mining outposts to supply train-imported resources.\n")

    for rtype in ['iron', 'limestone']:
        sites = data['extraction_sites'][rtype]
        rname = 'Iron Ore' if rtype == 'iron' else 'Limestone'
        train_demand = data['train_network'].get(rname, {}).get('total_demand_per_min', 0)

        a(f"### {rname} Sites (train demand: {train_demand:.0f}/min)\n")
        a("| Site | Location | Nodes | Purity | Capacity | Notes |")
        a("|------|----------|-------|--------|----------|-------|")
        for s in sites:
            purity = f"{s['pure']}P {s['normal']}N {s['impure']}I"
            a(f"| {s['name']} | ({s['x']}, {s['y']}) | {s['nodes']} | "
              f"{purity} | {s['capacity']}/min | {s['note']} |")
        a("")

    # Recommended extraction plan
    a("### Recommended Extraction Plan\n")
    iron_demand = data['train_network'].get('Iron Ore', {}).get('total_demand_per_min', 0)
    ls_demand = data['train_network'].get('Limestone', {}).get('total_demand_per_min', 0)

    a(f"**Iron Ore** ({iron_demand:.0f}/min needed):")
    a(f"- **Iron Hub Alpha** (241941, 3242): 5,340/min from 8 nodes (3P+5N)")
    a(f"  - Supplies Naphtheon via train (~2,007/min)")
    a(f"  - Supplies Luxara via train (~40/min)")
    a(f"  - Excess capacity: {5340 - iron_demand:.0f}/min for future expansion")
    a("")
    a(f"**Limestone** ({ls_demand:.0f}/min needed):")
    a(f"- **Limestone Central** (169486, -45968): 2,580/min from 4 nodes (1P+3N)")
    a(f"  - Near Forgeholm (487m), serves as central distribution hub")
    a(f"  - Supplies Ferrium via train (~764/min)")
    a(f"  - Supplies Luxara via train (~157/min)")
    a(f"  - Excess capacity: {2580 - ls_demand:.0f}/min for future expansion")
    a("")

    return '\n'.join(lines)


def main():
    print("Generating factory plan...")
    data = gen_json()

    # Write JSON
    with open('/Users/deepak/AI/satisfy/factory-plan.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Written: factory-plan.json")

    # Write Markdown
    md = gen_markdown(data)
    with open('/Users/deepak/AI/satisfy/factory-plan.md', 'w') as f:
        f.write(md)
    print(f"  Written: factory-plan.md")

    # Summary
    print(f"\n{'='*60}")
    print("PLAN SUMMARY")
    print(f"{'='*60}")
    total_hmf = sum(f['hmf_per_min'] for f in data['factories'].values())
    total_bldg = sum(f['total_buildings'] for f in data['factories'].values())
    total_pw = sum(f['total_power_mw'] for f in data['factories'].values())
    print(f"Total HMF/min:   {total_hmf:.1f}")
    print(f"Total buildings: {total_bldg}")
    print(f"Total power:     {total_pw:.0f} MW")
    print(f"\nTrain imports:")
    for rname, info in data['train_network'].items():
        print(f"  {rname}: {info['total_demand_per_min']:.0f}/min")
    print(f"\nExtraction sites:")
    for rtype, sites in data['extraction_sites'].items():
        for s in sites:
            print(f"  {s['name']}: {s['capacity']}/min ({s['nodes']} nodes)")


if __name__ == '__main__':
    main()
