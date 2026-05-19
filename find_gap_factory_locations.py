#!/usr/bin/env python3
"""Auto-place the gap supply-chain factories on the map by raw-resource
proximity. Scarcity-ordered, conflict-free (no factory double-books a node;
the live miners in occupied-nodes.json are excluded), multi-site where one
cluster can't meet demand, soft-biased to the NW (top-left) and SE
(bottom-right) quadrants.

See docs/plans/2026-05-19-gap-factory-locations-plan.md (incl. the v2
amendments A1..A14, which this script implements). Rough siting estimate only
(estimate:true) — exact flavor splits / sizing are the design spec's deferred
amounts phase.

Coordinate convention: +x=east/right, +y=south/bottom, cm (100=1m).
Top-left = NW = (x<0,y<0); bottom-right = SE = (x>0,y>0).
"""
import json
import math
import re
import sqlite3
from collections import defaultdict, deque

MAP_HTML = 'factory-map.html'

# ---------------------------------------------------------------- paths/const
DB_PATH            = '/home/starlight/satisfy/satisfyfactor-factory-creator/satisfactory.db'
RESOURCE_NODES     = 'resource_nodes.json'
OCCUPIED_NODES     = 'planner-export/occupied-nodes.json'
EXISTING_LOCATIONS = 'selected-factory-locations.json'
SUBUNITS           = 'factory-subunits.json'
CURRENT_PRODUCTION = 'planner-export/current-production.txt'
OUTPUT_PATH        = 'gap-factory-locations.json'

# Design §2.2 candidate intermediates: existing net-positive items the new
# factories may consume rather than make in-house. We decide per-item by
# checking existing surplus vs total new consumption (erosion check).
EROSION_CANDIDATES = {'Wire', 'Circuit Board', 'Crystal Oscillator',
                       'Copper Sheet', 'Computer'}
EROSION_MARGIN     = 100      # leave this much surplus buffer

BUILDING_FOOTPRINT = {        # reused from build_factory_crazy.py
    'Manufacturer': 440, 'Blender': 304, 'Refinery': 200, 'Assembler': 150,
    'Constructor': 80, 'Foundry': 72, 'Smelter': 54,
    'Packager': 24, 'Particle Accelerator': 912, 'Quantum Encoder': 912,
    'Converter': 240,
}

SEARCH_RADIUS  = 40_000          # 400 m cluster radius (HMF method, tunable)
MIN_SEPARATION = 25_000          # 250 m between distinct sites/centers
BELT_LIMIT     = 780             # items/min per node; user's belt cap
                                 # (pure Mk.3 @ 250% = 1200 but belt clamps to
                                 # 780, so shard 3 on pure is wasted)
PURITY_WEIGHT  = {'impure': 1, 'normal': 2, 'pure': 4}
# All extractors assumed at max overclock (3 power shards = 250%) per user.
# Base Mk.3: 120/240/480; OIL: 60/120/240; WELL satellite: 30/60/120.
_OC = 2.5
MINER_RATE     = {'impure': int(120 * _OC), 'normal': int(240 * _OC), 'pure': int(480 * _OC)}
OIL_RATE       = {'impure':  60 * _OC,      'normal': 120 * _OC,      'pure': 240 * _OC}
WELL_RATE      = {'impure':  30 * _OC,      'normal':  60 * _OC,      'pure': 120 * _OC}
QUADRANT_BONUS = 1.5             # soft NW/SE multiplier (A-design)
OCC_MATCH_TOL  = 5_000           # 50 m nearest-node occupancy match (A1/Task2)
MAX_SITES      = 8               # satellite cap per factory (design §3.5
                                 # multi-sites Aluminium factories; belt cap
                                 # 780/node forces more sites for big demands)

# explicit RAW set — DB is_raw heuristic is unreliable here (a "Bauxite"
# Converter recipe makes ores look non-raw), so terminate decomposition here.
RAW_SOLID = {'Iron Ore', 'Copper Ore', 'Caterium Ore', 'Limestone', 'Coal',
             'Bauxite', 'Raw Quartz', 'Sulfur', 'SAM', 'Uranium'}
RAW_FLUID = {'Water', 'Crude Oil', 'Nitrogen Gas'}              # Water = sited-anywhere
ITEM_TO_NODETYPE = {
    'Iron Ore': 'iron', 'Copper Ore': 'copper', 'Caterium Ore': 'caterium',
    'Limestone': 'limestone', 'Coal': 'coal', 'Bauxite': 'bauxite',
    'Raw Quartz': 'quartz', 'Sulfur': 'sulfur', 'SAM': 'sam',
    'Uranium': 'uranium', 'Crude Oil': 'oil', 'Nitrogen Gas': 'nitrogenGas',
}
FLUID_ITEMS = {'Water', 'Crude Oil', 'Nitrogen Gas', 'Alumina Solution',
               'Sulfuric Acid', 'Heavy Oil Residue', 'Fuel', 'Liquid Biofuel',
               'Nitric Acid', 'Dissolved Silica', 'Ionized Fuel',
               'Rocket Fuel', 'Turbofuel'}
# default-recipe overrides where the std resolver picks a wrong primary (A8)
DEFAULT_OVERRIDE = {'Heavy Oil Residue': 'Alternate: Heavy Oil Residue'}

OCC_NAME_MAP = {'Iron Ore': 'iron', 'Copper Ore': 'copper',
                'Caterium Ore': 'caterium', 'Crude Oil': 'oil',
                'Raw Quartz': 'quartz', 'SAM Ore': 'sam',
                'Nitrogen Gas': 'nitrogenGas', 'Coal': 'coal',
                'Limestone': 'limestone', 'Bauxite': 'bauxite',
                'Sulfur': 'sulfur', 'Uranium': 'uranium', 'Geyser': 'geyser'}

# ---------------------------------------------------------------- gap targets
GAP_TARGETS = {  # items/min, locked (design spec §2.3)
    'Aluminum Casing': 3900, 'Steel Beam': 450, 'Motor': 220, 'Stator': 289,
    'Cooling System': 150, 'Copper Powder': 1000, 'High-Speed Connector': 115,
    'Smart Plating': 150, 'Modular Frame': 38, 'Rubber': 917,
    'Heavy Modular Frame': 66,
}
# ESTIMATE — heuristic flavor splits, shifted to minimize bauxite use without
# eliminating any factory: max Al Casing to Aldercast (1.33 bauxite/casing,
# most efficient); minima at Bauxhold/Silvashade (1.5) to preserve identity;
# Steel Beam bulk to Moldmarsh (Molded Beam = no bauxite) with a small
# Silvashade share for its Aluminum-Beam identity.
FLAVOR_SPLITS = {
    'Aluminum Casing': {'aldercast': 3500, 'bauxhold': 200, 'silvashade': 200},
    'Steel Beam':       {'moldmarsh': 400, 'silvashade': 50},
    'Motor':            {'voltreach': 110, 'classic_iron_motor': 110},
    'Stator':           {'moldmarsh': 159, 'voltreach': 130},
}
# HMF +66 split: Luxara's HMF chain is the only one using bauxite, so its
# share = 0 (Luxara still exists at base scale; just doesn't take the
# increment). Redistribute 66/min across the 4 non-bauxite HMF flavors.
HMF_SPLIT = {'ferrium': 16.5, 'naphtheon': 16.5,
             'forgeholm': 16.5, 'cathera': 16.5, 'luxara': 0.0}

# pinned signature recipes (output item -> exact DB recipe name), design §3
NEW_FACTORIES = {
    'aldercast': {
        'theme': 'Alclad / Copper-fused', 'signature': 'bauxite',
        'products': {'Aluminum Casing': ('split',), 'Cooling System': ('target',)},
        'recipes': {'Alumina Solution': 'Alternate: Sloppy Alumina',
                    'Aluminum Scrap': 'Alternate: Electrode Aluminum Scrap',
                    'Aluminum Ingot': 'Alternate: Pure Aluminum Ingot',
                    'Aluminum Casing': 'Alternate: Alclad Casing',
                    'Heat Sink': 'Alternate: Heat Exchanger',
                    'Cooling System': 'Cooling System'},
        'imports': {'Petroleum Coke', 'Rubber'}},
    'bauxhold': {
        'theme': 'Chemical / Sulfuric', 'signature': 'bauxite',
        'products': {'Aluminum Casing': ('split',)},
        'recipes': {'Aluminum Scrap': 'Alternate: Instant Scrap',
                    'Aluminum Ingot': 'Alternate: Pure Aluminum Ingot',
                    'Aluminum Casing': 'Aluminum Casing'},
        'imports': set()},
    'silvashade': {
        'theme': 'Classic Silica Foundry', 'signature': 'bauxite',
        'products': {'Aluminum Casing': ('split',), 'Steel Beam': ('split',)},
        'recipes': {'Alumina Solution': 'Alumina Solution',
                    'Aluminum Scrap': 'Aluminum Scrap',
                    'Aluminum Ingot': 'Aluminum Ingot',
                    'Aluminum Casing': 'Aluminum Casing',
                    'Steel Beam': 'Alternate: Aluminum Beam'},
        'imports': set()},
    'voltreach': {
        'theme': 'Electric Motion', 'signature': 'caterium',
        'products': {'Motor': ('split',), 'Stator': ('split',)},
        'recipes': {'Rotor': 'Alternate: Copper Rotor',
                    'Stator': 'Alternate: Quickwire Stator',
                    'Motor': 'Alternate: Rigor Motor'},
        'imports': set()},
    'moldmarsh': {
        'theme': 'Cast Steel', 'signature': 'limestone',
        'products': {'Steel Beam': ('split',), 'Stator': ('split',)},
        'recipes': {'Steel Beam': 'Alternate: Molded Beam',
                    'Steel Pipe': 'Alternate: Molded Steel Pipe',
                    'Stator': 'Stator'},
        'imports': set()},   # Wire "(or in-house)" -> A6 default in-house
    'classic_iron_motor': {
        'theme': 'Classic Iron Motor', 'signature': 'iron',
        'products': {'Motor': ('split',)},
        'recipes': {'Rotor': 'Rotor', 'Stator': 'Stator', 'Motor': 'Motor'},
        'imports': set()},
}
EXTENSIONS = {
    'naphtheon': {'signature': 'oil',
                  'added': {'Rubber': ('target',)}, 'exports': True},
    'cathera':   {'signature': 'copper',
                  'added': {'High-Speed Connector': ('target',),
                            'Copper Powder': ('target',)}, 'exports': False},
    'ferrium':   {'signature': 'iron',
                  'added': {'Smart Plating': ('target',),
                            'Modular Frame': ('target',)},
                  'recipes': {'Rotor': 'Rotor'}, 'exports': False},
}
HMF_CRITICAL = {'ferrium': 'iron', 'naphtheon': 'oil', 'forgeholm': 'coal',
                'luxara': 'bauxite', 'cathera': 'copper'}


# ---------------------------------------------------------------- DB helpers
def israw(item):
    return item in RAW_SOLID or item in RAW_FLUID


def _conv(qty, item):
    return qty / 1000.0 if item in FLUID_ITEMS else qty


class DB:
    def __init__(self, path):
        self.c = sqlite3.connect(path)
        self._cache = {}

    def recipe_io(self, recipe_name):
        if recipe_name in self._cache:
            return self._cache[recipe_name]
        row = self.c.execute("SELECT id,duration FROM recipes WHERE name=?",
                             (recipe_name,)).fetchone()
        if not row:
            raise ValueError(f"recipe not found: {recipe_name!r}")
        rid, dur = row
        prod = self.c.execute(
            "SELECT i.name,rp.quantity FROM recipe_products rp "
            "JOIN items i ON i.id=rp.item_id WHERE rp.recipe_id=?", (rid,)
        ).fetchall()
        ing = self.c.execute(
            "SELECT i.name,ri.quantity FROM recipe_ingredients ri "
            "JOIN items i ON i.id=ri.item_id WHERE ri.recipe_id=?", (rid,)
        ).fetchall()
        out = {n: _conv(q, n) / dur * 60 for n, q in prod}
        inp = {n: _conv(q, n) / dur * 60 for n, q in ing}
        self._cache[recipe_name] = (out, inp)
        return out, inp

    def recipe_building(self, recipe_name):
        row = self.c.execute(
            "SELECT b.name, b.power_used FROM recipes r "
            "JOIN recipe_buildings rb ON rb.recipe_id=r.id "
            "JOIN buildings b ON b.id=rb.building_id "
            "WHERE r.name=?", (recipe_name,)).fetchone()
        return row if row else (None, 0)

    def default_recipe(self, item):
        """Non-alternate, building-based recipe where `item` is the primary
        product; prefer r.name==item; fall back to any alternate. (A8)"""
        if item in DEFAULT_OVERRIDE:
            return DEFAULT_OVERRIDE[item]
        rows = self.c.execute(
            "SELECT r.name, r.duration, "
            " (SELECT MAX(rp2.quantity) FROM recipe_products rp2 "
            "  WHERE rp2.recipe_id=r.id) AS maxq, rp.quantity "
            "FROM recipes r "
            "JOIN recipe_products rp ON rp.recipe_id=r.id "
            "JOIN items i ON i.id=rp.item_id "
            "JOIN recipe_buildings rb ON rb.recipe_id=r.id "
            "JOIN buildings b ON b.id=rb.building_id "
            "WHERE i.name=? AND b.name NOT LIKE '%Converter%' "
            "  AND b.name NOT LIKE '%Packager%' "
            "ORDER BY (r.name LIKE 'Alternate:%') ASC, "
            "         (r.name=?) DESC, "
            "         (rp.quantity = maxq) DESC, r.name ASC",
            (item, item)).fetchall()
        if not rows:
            raise ValueError(f"no producing recipe for {item!r}")
        return rows[0][0]


def decompose(db, product, rate, pinned, imports, _stack=None, _depth=0):
    """Backward to raw. Stop at RAW set or declared `imports`. Returns
    {raw_item: per_min}. Cycle-safe (A7). `pinned` overrides recipe choice."""
    raw = defaultdict(float)
    if _stack is None:
        _stack = set()
    if rate <= 0 or _depth > 40:
        return raw
    if israw(product) or product in imports:
        raw[product] += rate
        return raw
    if product in _stack:                       # cycle break
        return raw
    recipe = pinned.get(product) or db.default_recipe(product)
    out, inp = db.recipe_io(recipe)
    made = out.get(product)
    if not made:                                # product only a by-product here
        raw[product] += rate
        return raw
    scale = rate / made
    _stack = _stack | {product}
    for ing, per_min in inp.items():
        sub = decompose(db, ing, per_min * scale, pinned, imports,
                         _stack, _depth + 1)
        for k, v in sub.items():
            raw[k] += v
    return raw


# ---------------------------------------------------------------- pool / occ
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def quadrant(x, y):
    return ('N' if y < 0 else 'S') + ('W' if x < 0 else 'E')


def load_pool():
    """Load resource_nodes AND resource_wells (A1). Each entry mutable with
    reserved_by; wells carry `core` (reservation/non-overlap unit)."""
    data = json.load(open(RESOURCE_NODES))
    pool = []
    for n in data['resource_nodes']:
        pool.append({'type': n['type'], 'purity': n['purity'],
                     'x': n['x'], 'y': n['y'], 'kind': 'node',
                     'core': None, 'path': n.get('path_name', ''),
                     'reserved_by': None})
    for w in data['resource_wells']:
        if not w.get('type'):
            continue
        pool.append({'type': w['type'], 'purity': w['purity'],
                     'x': w['x'], 'y': w['y'], 'kind': 'well',
                     'core': w.get('core') or w.get('path_name'),
                     'path': w.get('path_name', ''), 'reserved_by': None})
    return pool


def mark_occupied(pool):
    occ = json.load(open(OCCUPIED_NODES))
    recs = []
    for rec in occ:
        p = rec.get('node_pos') or rec.get('miner_pos')
        if not p:
            recs.append((math.inf, None, rec))
            continue
        ntype = OCC_NAME_MAP.get(rec.get('resource'), '')
        same = [n for n in pool if n['type'] == ntype]
        nd = min((dist((p[0], p[1]), (n['x'], n['y'])) for n in same),
                 default=math.inf)
        recs.append((nd, (p[0], p[1], ntype), rec))
    # nearest-match-first: exact hits (real miners sit on their node) claim
    # their own node before greedy cascades can steal it.
    recs.sort(key=lambda r: r[0])
    matched = 0
    unmatched = []
    for nd, key, rec in recs:
        if key is None:
            unmatched.append((rec.get('resource'), None, None))
            continue
        px, py, ntype = key
        best, bd = None, OCC_MATCH_TOL
        for n in pool:
            if n['reserved_by'] is not None or n['type'] != ntype:
                continue
            d = dist((px, py), (n['x'], n['y']))
            if d <= bd:
                best, bd = n, d
        if best:
            best['reserved_by'] = '__occupied__'
            matched += 1
        else:
            unmatched.append((rec.get('resource'), round(px), round(py)))
    return matched, len(occ), unmatched


def avail(pool, ntype):
    return [n for n in pool if n['reserved_by'] is None and n['type'] == ntype]


def rate_of(node):
    """Max effective rate at full overclock, after belt cap."""
    if node['kind'] == 'well':
        return WELL_RATE[node['purity']]
    if node['type'] == 'oil':
        return OIL_RATE[node['purity']]    # fluids: pipes 600 m3/min, OK
    return min(MINER_RATE[node['purity']], BELT_LIMIT)


def effective_at_shards(node, shards):
    """Effective rate for a node at `shards` (0..3) clock = 100+50*shards %.
    Solid mining capped at BELT_LIMIT. Fluids use pipe capacity (already
    well below BELT-style limits in our config)."""
    pur = _PUR_FULL.get(node.get('purity') or node.get('p'), 'normal')
    kind = node.get('kind') or node.get('k')
    t = node.get('type') or node.get('t')
    clock = 1.0 + 0.5 * shards
    if kind == 'well':
        return WELL_RATE[pur] / 2.5 * clock
    if t == 'oil':
        return OIL_RATE[pur] / 2.5 * clock
    return min(MINER_RATE[pur] / 2.5 * clock, BELT_LIMIT)


def claim_nearest(pool, ntype, center, demand, job_id, radius=None):
    """Single distance-first policy (A5), used for BOTH counting and
    reservation. Wells reserve by whole `core` (A1). Returns
    (claimed_nodes, capacity)."""
    cand = avail(pool, ntype)
    if radius is not None:
        cand = [n for n in cand if dist(center, (n['x'], n['y'])) <= radius]
    cand.sort(key=lambda n: (round(dist(center, (n['x'], n['y'])), 1),
                             n['path']))
    claimed, cap = [], 0.0
    for n in cand:
        if cap >= demand:
            break
        if n['reserved_by'] is not None:
            continue
        group = [n]
        if n['kind'] == 'well' and n['core']:
            group = [m for m in pool if m['reserved_by'] is None
                     and m['kind'] == 'well' and m['core'] == n['core']]
        for m in group:
            m['reserved_by'] = job_id
            claimed.append(m)
            cap += rate_of(m)
    return claimed, cap


def cluster(nodes, radius):
    """Single-linkage clustering at `radius` (A11) -> list of node lists."""
    clusters = []
    for n in nodes:
        placed = False
        for cl in clusters:
            if any(dist((n['x'], n['y']), (m['x'], m['y'])) <= radius
                   for m in cl):
                cl.append(n)
                placed = True
                break
        if not placed:
            clusters.append([n])
    return clusters


def centroid(nodes):
    return (round(sum(n['x'] for n in nodes) / len(nodes), 1),
            round(sum(n['y'] for n in nodes) / len(nodes), 1))


# ---------------------------------------------------------------- demand
def _resolved_products(products, fid):
    """{item: per_min} from a factory.products dict (mode='split' or 'target')."""
    return {p: (split_rate(p, fid) if m[0] == 'split' else GAP_TARGETS[p])
            for p, m in products.items()}


def split_rate(item, fid):
    if item in FLAVOR_SPLITS and fid in FLAVOR_SPLITS[item]:
        return FLAVOR_SPLITS[item][fid]
    return GAP_TARGETS[item]


def job_raw_demand(db, fid, products, pinned, imports):
    """{node_type: per_min} for mined solids + oil + nitrogenGas. Decomposes
    each FINAL product end-to-end (A7); Water dropped (sited-anywhere)."""
    agg = defaultdict(float)
    for item, mode in products.items():
        rate = split_rate(item, fid) if mode[0] == 'split' else GAP_TARGETS[item]
        for raw, pm in decompose(db, item, rate, pinned, imports).items():
            if raw == 'Water':
                continue
            nt = ITEM_TO_NODETYPE.get(raw)
            if nt:
                agg[nt] += pm
    return dict(agg), {p: (split_rate(p, fid) if m[0] == 'split'
                           else GAP_TARGETS[p]) for p, m in products.items()}


def aldercast_imports(db):
    """Petroleum Coke + Rubber that Aldercast pulls (attributed to
    Naphtheon+). Decompose Aldercast products but capture the import-boundary
    quantities instead of dropping them."""
    f = NEW_FACTORIES['aldercast']
    need = defaultdict(float)
    for item, mode in f['products'].items():
        rate = split_rate(item, 'aldercast')
        for raw, pm in decompose(db, item, rate, f['recipes'],
                                 f['imports']).items():
            if raw in f['imports']:
                need[raw] += pm
    return dict(need)


def load_current_production():
    """Parse planner-export/current-production.txt -> {item_name: net_per_min}
    (make - consume; positive = surplus, negative = deficit)."""
    net = {}
    with open(CURRENT_PRODUCTION) as f:
        for line in f:
            parts = [p.strip() for p in line.split('\t') if p.strip()]
            if len(parts) < 3:
                continue
            name = parts[0]
            def numify(s):
                tok = s.split(' ')[0].replace(',', '').replace('m³', '')
                try: return float(tok)
                except ValueError: return 0.0
            net[name] = numify(parts[1]) - numify(parts[2])
    return net


def factory_consumption_of(db, fid, products, pinned, target_item):
    """How much of target_item factory fid consumes (per min), assuming
    in-house all the way down except target_item which is treated as a
    boundary (its consumption is the value we want)."""
    total = 0.0
    for item, mode in products.items():
        rate = split_rate(item, fid) if mode[0] == 'split' else GAP_TARGETS[item]
        for raw, pm in decompose(db, item, rate, pinned, {target_item}).items():
            if raw == target_item:
                total += pm
    return total


def resolve_imports(db, current_net):
    """Design §2.2 erosion check. For each EROSION_CANDIDATES intermediate,
    sum potential new consumption across all factories+extensions. If
    current_net[item] - new_consumption >= EROSION_MARGIN -> import from
    existing surplus (add to consuming factories' imports). Else: keep
    in-house. Returns (per_factory_extra_imports, report)."""
    extras = defaultdict(set)
    report = {}
    for it in EROSION_CANDIDATES:
        total_new = 0.0
        consumers = []
        for fid, f in NEW_FACTORIES.items():
            v = factory_consumption_of(db, fid, f['products'], f['recipes'], it)
            if v > 1e-3:
                consumers.append((fid, v)); total_new += v
        for fid, e in EXTENSIONS.items():
            v = factory_consumption_of(db, fid, e['added'],
                                        e.get('recipes', {}), it)
            if v > 1e-3:
                consumers.append((fid + '+', v)); total_new += v
        surplus = current_net.get(it, 0.0)
        residual = surplus - total_new
        is_import = (residual >= EROSION_MARGIN and total_new > 0)
        report[it] = {'existing_net': round(surplus, 1),
                       'new_consumption': round(total_new, 1),
                       'residual_net': round(residual, 1),
                       'decision': 'import_from_existing' if is_import else 'in_house',
                       'consumers': [(c, round(v, 1)) for c, v in consumers]}
        if is_import:
            for c, _ in consumers:
                extras[c].add(it)
    return dict(extras), report


def building_chain(db, products, pinned, imports):
    """Compute building counts for the full chain producing `products`. Stops
    at RAW or `imports`. Returns ordered list of entries:
    {recipe, item, building, rate_per_min, recipe_output_per_min,
     buildings_exact, buildings_ceil, power_mw}."""
    # phase 1: aggregate per-item rates via BFS
    rate = defaultdict(float)
    for p, r in products.items():
        rate[p] += r
    todo = list(products.keys())
    visited = set()
    order = []
    while todo:
        item = todo.pop(0)
        if item in visited or israw(item) or item in imports:
            continue
        visited.add(item); order.append(item)
        recipe = pinned.get(item) or db.default_recipe(item)
        out, inp = db.recipe_io(recipe)
        made = out.get(item, 0)
        if not made: continue
        scale = rate[item] / made
        for ing, pm in inp.items():
            rate[ing] += pm * scale
            todo.append(ing)
    # phase 2: build entries
    entries = []
    for item in order:
        recipe = pinned.get(item) or db.default_recipe(item)
        out, inp = db.recipe_io(recipe)
        made = out.get(item, 0)
        if not made: continue
        bld, power = db.recipe_building(recipe)
        be = rate[item] / made
        entries.append({
            'recipe': recipe, 'item': item, 'building': bld or '?',
            'rate_per_min': round(rate[item], 2),
            'recipe_output_per_min': round(made, 2),
            'buildings_exact': round(be, 2),
            'buildings_ceil': math.ceil(be),
            'power_mw': round(power * be, 1),
        })
    return entries


def factory_building_totals(entries):
    """{building_type: total_count}, plus total power and total footprint."""
    by_b = defaultdict(int)
    power = 0.0
    foot = 0
    for e in entries:
        by_b[e['building']] += e['buildings_ceil']
        power += e['power_mw']
        foot += e['buildings_ceil'] * BUILDING_FOOTPRINT.get(e['building'], 0)
    return {'by_building': dict(by_b),
            'total_buildings': sum(by_b.values()),
            'total_power_mw': round(power, 1),
            'footprint_m2': foot}


_PUR_FULL = {'i': 'impure', 'n': 'normal', 'p': 'pure',
             'impure': 'impure', 'normal': 'normal', 'pure': 'pure'}


def base_rate(node):
    """Per-node base extraction rate (100% clock = no shards). Accepts both
    full ({type,purity,kind}) and compact ({t,p,k}) node dicts."""
    pur = _PUR_FULL[node.get('purity') or node.get('p')]
    kind = node.get('kind') or node.get('k')
    t = node.get('type') or node.get('t')
    if kind == 'well':
        return WELL_RATE[pur] / 2.5            # un-overclock to base
    if t == 'oil':
        return OIL_RATE[pur] / 2.5
    return MINER_RATE[pur] / 2.5


def site_min_overclock(nodes, demand):
    """Pick the minimum overclock per node such that Σ effective_rate >=
    demand, respecting belt cap (no shard wasted past 780/min). Greedy:
    each round pick the node where the NEXT shard adds the most effective
    rate. Returns ({nid: {'clock', 'shards'}}, total_shards, cap_now)."""
    if not nodes:
        return {}, 0, 0.0
    state = {id(n): {'clock': 100, 'shards': 0} for n in nodes}
    total = sum(effective_at_shards(n, 0) for n in nodes)
    total_shards = 0
    while total + 1e-6 < demand:
        # rank by marginal gain of one more shard
        best, best_gain = None, 0
        for n in nodes:
            s = state[id(n)]['shards']
            if s >= 3:
                continue
            gain = effective_at_shards(n, s + 1) - effective_at_shards(n, s)
            if gain > best_gain:
                best, best_gain = n, gain
        if best is None or best_gain <= 1e-6:
            break        # no more useful shards (belt-capped) or all maxed
        state[id(best)]['shards'] += 1
        state[id(best)]['clock'] = 100 + 50 * state[id(best)]['shards']
        total += best_gain
        total_shards += 1
    return state, total_shards, round(total, 1)


# ---------------------------------------------------------------- allocation
def score_centers(pool, sig, sig_demand, placed_centers):
    """Candidate centers = available signature nodes; HMF-style score with
    NW/SE soft bonus; exclude within MIN_SEPARATION of any placed center
    (A4). Returns sorted [(score, center, cluster_nodes)]."""
    sig_nodes = avail(pool, sig)
    if not sig_nodes:                               # A9 empty guard
        return []
    counts = defaultdict(int)
    for n in pool:
        counts[n['type']] += 1
    max_count = max(counts.values())
    rarity = (max_count / max(counts.get(sig, 1), 1)) ** 1.5
    out = []
    for c in sig_nodes:
        near = [n for n in sig_nodes
                if dist((c['x'], c['y']), (n['x'], n['y'])) <= SEARCH_RADIUS]
        if not near:
            continue
        ctr = centroid(near)
        # 1.25× filter margin so post-claim centroid drift (only the chosen
        # subset of nodes within radius is actually claimed) stays within the
        # strict MIN_SEPARATION bound that validation asserts.
        if any(dist(ctr, pc) < MIN_SEPARATION * 1.25 for pc in placed_centers):
            continue
        sc = sum(PURITY_WEIGHT[n['purity']] for n in near) * sig_demand * rarity
        if quadrant(*ctr) in ('NW', 'SE'):
            sc *= QUADRANT_BONUS
        out.append((round(sc, 3), ctr, near, c['path']))
    out.sort(key=lambda t: (-t[0], t[3]))
    return out


def alloc_signature(pool, job, placed_centers):
    """Claim signature sites for one job: best cluster, spill to satellites
    up to MAX_SITES. Mutates pool/placed_centers. Sets job sites/infeasible."""
    sig = job['signature']
    remaining = job['raw_demand'].get(sig, 0.0)
    if remaining <= 0:
        job['sites'] = []
        return
    sites = []
    for _ in range(MAX_SITES):
        if remaining <= 1e-6:
            break
        ranked = score_centers(pool, sig, remaining, placed_centers)
        if not ranked:
            break
        _, ctr, _, _ = ranked[0]
        claimed, cap = claim_nearest(pool, sig, ctr, remaining, job['id'],
                                     radius=SEARCH_RADIUS)
        if not claimed:
            break
        c2 = centroid(claimed)
        sites.append({'center': {'x': c2[0], 'y': c2[1]},
                      'signature_capacity': round(cap, 1),
                      'nodes': [{'x': n['x'], 'y': n['y'], 't': n['type'],
                                 'p': n['purity'][0], 'k': n['kind']}
                                for n in claimed]})
        placed_centers.append(c2)
        remaining -= cap
    job['sites'] = sites
    job['sig_shortfall'] = round(max(remaining, 0.0), 1)
    if remaining > 1e-6:
        job['infeasible'] = True


def alloc_trained(pool, job):
    """Reserve every non-signature mined resource as outposts (A11; wells by
    core A1). Nearest-first, no radius cap."""
    sig = job['signature']
    base = job['sites'][0]['center'] if job.get('sites') else \
        (job.get('anchor') or {'x': 0, 'y': 0})
    base = (base['x'], base['y'])
    outposts = []
    for nt, dmd in sorted(job['raw_demand'].items()):
        if nt == sig or dmd <= 0:
            continue
        claimed, cap = claim_nearest(pool, nt, base, dmd, job['id'])
        if not claimed:
            job.setdefault('trained_shortfall', {})[nt] = round(dmd, 1)
            continue
        for cl in cluster(claimed, SEARCH_RADIUS):
            cc = centroid(cl)
            outposts.append({'resource': nt,
                             'center': {'x': cc[0], 'y': cc[1]},
                             'capacity': round(sum(rate_of(n) for n in cl), 1),
                             'nodes': [{'x': n['x'], 'y': n['y'], 't': n['type'],
                                        'p': n['purity'][0], 'k': n['kind']}
                                       for n in cl]})
        if cap + 1e-6 < dmd:
            job.setdefault('trained_shortfall', {})[nt] = round(dmd - cap, 1)
    job['outposts'] = outposts


def alloc_anchored(pool, job, placed_centers):
    """ext/hmf: prefer the existing center. in_place / satellite / relocated
    (ext) | infeasible (hmf)."""
    sig = job['signature']
    a = job['anchor']
    actr = (a['x'], a['y'])
    demand = job['raw_demand'].get(sig, 0.0)
    if demand <= 0:
        job['sites'] = []
        job['disposition'] = 'scaled_in_place'
        return
    claimed, cap = claim_nearest(pool, sig, actr, demand, job['id'],
                                 radius=SEARCH_RADIUS)
    if claimed:
        c2 = centroid(claimed)
        job['sites'] = [{'center': {'x': c2[0], 'y': c2[1]},
                         'signature_capacity': round(cap, 1),
                         'nodes': [{'x': n['x'], 'y': n['y'], 't': n['type'],
                                    'p': n['purity'][0], 'k': n['kind']}
                                   for n in claimed]}]
        placed_centers.append(c2)
    else:
        job['sites'] = []
    if cap + 1e-6 >= demand:
        job['disposition'] = 'scaled_in_place'
        job['sig_shortfall'] = 0.0
        return
    # shortfall near anchor -> spill to satellites (free-style)
    job['raw_demand'] = dict(job['raw_demand'])
    job['raw_demand'][sig] = demand - cap
    free = dict(job)
    free['sites'] = []
    alloc_signature(pool, free, placed_centers)
    job['sites'] += free.get('sites', [])
    short = free.get('sig_shortfall', 0.0)
    job['sig_shortfall'] = short
    if short <= 1e-6 and job['sites']:
        job['disposition'] = 'satellite' if cap > 0 else 'relocated'
    elif job['kind'] == 'ext':
        job['disposition'] = 'relocated' if not job['sites'] else 'satellite'
        if short > 1e-6:
            job['infeasible'] = True
    else:
        job['disposition'] = 'satellite'
        job['infeasible'] = short > 1e-6
    job['raw_demand'][sig] = demand            # restore for reporting


def build_jobs(db, extras=None):
    extras = extras or {}
    jobs = []
    for fid, f in NEW_FACTORIES.items():
        imports = set(f['imports']) | extras.get(fid, set())
        rd, tgt = job_raw_demand(db, fid, f['products'], f['recipes'], imports)
        chain = building_chain(db, _resolved_products(f['products'], fid),
                                f['recipes'], imports)
        jobs.append({'id': fid, 'name': fid, 'kind': 'new',
                     'theme': f['theme'], 'signature': f['signature'],
                     'raw_demand': rd, 'targets': tgt, 'anchor': None,
                     'imports_resolved': sorted(imports),
                     'building_chain': chain,
                     'building_totals': factory_building_totals(chain)})
    ald_imp = aldercast_imports(db)
    exist = json.load(open(EXISTING_LOCATIONS))['selections']
    for fid, e in EXTENSIONS.items():
        added = dict(e['added'])
        prods, recipes = added, e.get('recipes', {})
        imports = extras.get(fid + '+', set())
        rd, tgt = job_raw_demand(db, fid, prods, recipes, imports)
        if e.get('exports') and fid == 'naphtheon':       # Naphtheon+ exports
            for raw, pm in ald_imp.items():
                for r2, p2 in decompose(db, raw, pm, {}, set()).items():
                    if r2 == 'Water':
                        continue
                    nt = ITEM_TO_NODETYPE.get(r2)
                    if nt:
                        rd[nt] = rd.get(nt, 0) + p2
            tgt = dict(tgt); tgt.update({k + ' (export)': round(v, 1)
                                         for k, v in ald_imp.items()})
        ext_products = {p: (split_rate(p, fid) if m[0] == 'split'
                            else GAP_TARGETS[p]) for p, m in prods.items()}
        if e.get('exports') and fid == 'naphtheon':
            for raw, pm in ald_imp.items():
                ext_products[raw] = ext_products.get(raw, 0) + pm
        chain = building_chain(db, ext_products, recipes, imports)
        assert fid in exist, f"A13: no existing center for {fid}"
        ctr = exist[fid]['center']
        jobs.append({'id': fid + '+', 'name': fid + '+', 'kind': 'ext',
                     'theme': 'extension', 'signature': e['signature'],
                     'raw_demand': rd, 'targets': tgt,
                     'anchor': {'x': ctr['x'], 'y': ctr['y']},
                     'imports_resolved': sorted(imports),
                     'building_chain': chain,
                     'building_totals': factory_building_totals(chain)})
    sub = json.load(open(SUBUNITS))['modules']
    for fid, crit in HMF_CRITICAL.items():
        m = sub[fid]
        per_hmf = {k: v['per_min'] / m['hmf_per_min']
                   for k, v in m['raw_inputs'].items()}
        inc = HMF_SPLIT.get(fid, 66.0 / 5.0)
        if inc <= 0:                             # skip jobs with 0 increment
            continue
        # Building totals for the increment: scale subunits steps by
        # inc / hmf_per_min (steps are per module copy at hmf_per_min HMF/min).
        scale = inc / m['hmf_per_min']
        hmf_chain = []
        for step in m['steps']:
            be = step['buildings_exact'] * scale
            hmf_chain.append({
                'recipe': step['recipe'], 'item': step['item'],
                'building': step['building'],
                'rate_per_min': round(step['outputs'].get(step['item'], 0) * scale, 2),
                'recipe_output_per_min': step['outputs'].get(step['item'], 0),
                'buildings_exact': round(be, 2),
                'buildings_ceil': math.ceil(be),
                'power_mw': round(step['power_mw'] * be, 1),
            })
        rd = {}
        for item, ph in per_hmf.items():
            nt = ITEM_TO_NODETYPE.get(item)
            if nt:
                rd[nt] = ph * inc
        assert fid in exist, f"A13: no existing center for HMF {fid}"
        ctr = exist[fid]['center']
        jobs.append({'id': fid + '_hmf', 'name': fid + ' (+HMF)',
                     'kind': 'hmf', 'theme': f'HMF +{inc:.1f}', 'signature': crit,
                     'raw_demand': rd, 'targets': {'Heavy Modular Frame': round(inc, 1)},
                     'anchor': {'x': ctr['x'], 'y': ctr['y']},
                     'imports_resolved': [],
                     'building_chain': hmf_chain,
                     'building_totals': factory_building_totals(hmf_chain)})
    return jobs


def pressure_key(pool, job):
    counts = defaultdict(int)
    for n in pool:
        if n['reserved_by'] is None:
            counts[n['type']] += 1
    best = math.inf
    for nt, dmd in job['raw_demand'].items():
        if dmd <= 0:
            continue
        best = min(best, counts.get(nt, 0) / math.sqrt(dmd))
    tonnage = sum(job['raw_demand'].values())
    return (best, -tonnage)


def allocate(pool, jobs):
    placed_centers = []
    pending = sorted(jobs, key=lambda j: pressure_key(pool, j))
    done = set()
    order = []
    # PHASE 1 — reserve ALL signature sites first (B1: a trained grab must
    # never starve a later job's signature resource).
    for j in pending:
        if j['id'] in done:
            continue
        if j['kind'] == 'new':                     # A3 round-robin peers
            peers = [p for p in pending if p['kind'] == 'new'
                     and p['signature'] == j['signature']
                     and p['id'] not in done]
            for p in peers:
                p['remaining'] = p['raw_demand'].get(p['signature'], 0.0)
                p['sites'] = []
            active = [p for p in peers if p['remaining'] > 1e-6]
            rounds = 0
            while active and rounds < MAX_SITES:
                for p in list(active):
                    ranked = score_centers(pool, p['signature'],
                                           p['remaining'], placed_centers)
                    if not ranked:
                        active.remove(p)
                        continue
                    _, ctr, _, _ = ranked[0]
                    claimed, cap = claim_nearest(pool, p['signature'], ctr,
                                                 p['remaining'], p['id'],
                                                 radius=SEARCH_RADIUS)
                    if not claimed:
                        active.remove(p)
                        continue
                    c2 = centroid(claimed)
                    p['sites'].append(
                        {'center': {'x': c2[0], 'y': c2[1]},
                         'signature_capacity': round(cap, 1),
                         'nodes': [{'x': n['x'], 'y': n['y'], 't': n['type'],
                                    'p': n['purity'][0], 'k': n['kind']}
                                   for n in claimed]})
                    placed_centers.append(c2)
                    p['remaining'] -= cap
                    if p['remaining'] <= 1e-6 or len(p['sites']) >= MAX_SITES:
                        active.remove(p)
                rounds += 1
            for p in peers:
                p['sig_shortfall'] = round(max(p.get('remaining', 0), 0), 1)
                p['infeasible'] = p['sig_shortfall'] > 1e-6
                p['disposition'] = 'infeasible' if p['infeasible'] else 'new'
                done.add(p['id'])
                order.append(p)
        else:
            alloc_anchored(pool, j, placed_centers)
            done.add(j['id'])
            order.append(j)
    # PHASE 2 — now reserve trained-in resources for every job (B1).
    for j in order:
        alloc_trained(pool, j)
    # PHASE 3 — per-node min overclock (Task 10): replace blanket 250% with
    # the smallest clock per node that meets each site/outpost's demand.
    for j in order:
        total_shards = 0
        sig_demand_remaining = j['raw_demand'].get(j['signature'], 0.0)
        for site in j.get('sites', []):
            cap_max = sum(rate_of(_full_node(n)) for n in site['nodes'])
            this_demand = min(sig_demand_remaining, cap_max)
            sig_demand_remaining -= this_demand
            oc, shards, cap = site_min_overclock(site['nodes'], this_demand)
            for n in site['nodes']:
                n['oc'] = oc[id(n)]['clock']
                n['sh'] = oc[id(n)]['shards']
            site['demand_met'] = round(this_demand, 1)
            site['signature_capacity'] = cap
            site['shards'] = shards
            total_shards += shards
        for out in j.get('outposts', []):
            cap_max = sum(rate_of(_full_node(n)) for n in out['nodes'])
            r_demand = j['raw_demand'].get(out['resource'], 0)
            this_demand = min(r_demand, cap_max)
            oc, shards, cap = site_min_overclock(out['nodes'], this_demand)
            for n in out['nodes']:
                n['oc'] = oc[id(n)]['clock']
                n['sh'] = oc[id(n)]['shards']
            out['demand_met'] = round(this_demand, 1)
            out['capacity'] = cap
            out['shards'] = shards
            total_shards += shards
        j['total_shards'] = total_shards
    return order, placed_centers


def _full_node(compact):
    """Shim: build a minimal full-shape node dict from compact (for rate_of)."""
    return {'kind': compact.get('k') or compact.get('kind'),
            'type': compact.get('t') or compact.get('type'),
            'purity': _PUR_FULL[compact.get('p') or compact.get('purity')]}


# ---------------------------------------------------------------- output
def build_output(db, pool, jobs, occ_stat, placed_centers,
                 out_erosion_report=None):
    matched, total_occ, unmatched = occ_stat
    by_type_total = defaultdict(int)
    by_type_occ = defaultdict(int)
    by_type_res = defaultdict(int)
    for n in pool:
        by_type_total[n['type']] += 1
        if n['reserved_by'] == '__occupied__':
            by_type_occ[n['type']] += 1
        elif n['reserved_by'] is not None:
            by_type_res[n['type']] += 1
    pool_balance = {}
    for t in sorted(by_type_total):
        pool_balance[t] = {
            'total': by_type_total[t], 'occupied': by_type_occ[t],
            'reserved_new': by_type_res[t],
            'remaining': by_type_total[t] - by_type_occ[t] - by_type_res[t]}

    facs = {}
    for j in jobs:
        cap = defaultdict(float)
        for s in j.get('sites', []):
            cap[j['signature']] += s['signature_capacity']
        for o in j.get('outposts', []):
            cap[o['resource']] += o['capacity']
        demand_vs = {t: {'demand': round(d, 1),
                         'reserved_capacity': round(cap.get(t, 0.0), 1)}
                     for t, d in sorted(j['raw_demand'].items()) if d > 0}
        disp = j.get('disposition', 'new')
        prim = j['sites'][0]['center'] if j.get('sites') else \
            (j.get('anchor') or {'x': 0, 'y': 0})
        facs[j['id']] = {
            'factory_name': j['name'], 'theme': j['theme'], 'kind': j['kind'],
            'signature_resource': j['signature'], 'disposition': disp,
            'targets': j.get('targets', {}),
            'center': prim, 'sites': j.get('sites', []),
            'outposts': j.get('outposts', []),
            'resources': demand_vs,
            'sig_shortfall': j.get('sig_shortfall', 0.0),
            'trained_shortfall': j.get('trained_shortfall', {}),
            'imports_resolved': j.get('imports_resolved', []),
            'building_totals': j.get('building_totals'),
            'building_chain': j.get('building_chain', []),
            'total_shards': j.get('total_shards', 0),
            'reason': _reason(j, disp)}

    out = {'meta': {
        'description': 'Auto-placed gap supply-chain factory locations '
                       '(amounts phase resolved)',
        'coordinate_system': {'x': '+east/right', 'y': '+south/bottom',
                              'units': 'cm (100=1m)',
                              'quadrants': 'NW=top-left SE=bottom-right'},
        'assumptions': {'miner_base_items_min': {'impure': 120, 'normal': 240, 'pure': 480},
                        'miner_max_clock_pct': 250,
                        'well_rate_m3min_max': WELL_RATE,
                        'oil_rate_m3min_max': OIL_RATE,
                        'search_radius_m': SEARCH_RADIUS / 100,
                        'min_separation_m': MIN_SEPARATION / 100,
                        'quadrant_bonus': QUADRANT_BONUS},
        'flavor_splits': FLAVOR_SPLITS,
        'hmf_split': HMF_SPLIT,
        'caveat_centroid': 'A14: a node-centroid can land on water/cliff; '
                           'not a buildability guarantee',
        'occupancy_match': f'{matched}/{total_occ}',
        'pool_balance': pool_balance,
        'erosion_report': out_erosion_report,
        'total_shards_global': sum(f['total_shards'] for f in facs.values())},
        'factory_locations': facs}
    return out, unmatched


def _reason(j, disp):
    sites = len(j.get('sites', []))
    bits = [f"{disp}", f"signature={j['signature']}",
            f"{sites} site(s)", f"{len(j.get('outposts', []))} outpost(s)"]
    if j.get('infeasible'):
        bits.append(f"INFEASIBLE shortfall={j.get('sig_shortfall')}")
    return '; '.join(bits)


def validate(out, pool, order, unmatched):
    issues = []
    seen = {}
    for n in pool:
        rb = n['reserved_by']
        if rb and rb != '__occupied__':
            key = (round(n['x']), round(n['y']), n['type'])
            if key in seen and seen[key] != rb:
                issues.append(f"NON-OVERLAP VIOLATION at {key}: "
                              f"{seen[key]} vs {rb}")
            seen[key] = rb
    total = len(pool)
    occ = sum(1 for n in pool if n['reserved_by'] == '__occupied__')
    res = sum(1 for n in pool if n['reserved_by'] not in (None, '__occupied__'))
    free = sum(1 for n in pool if n['reserved_by'] is None)
    assert total == occ + res + free, "pool conservation failed"
    centers = []
    for j in order:
        for s in j.get('sites', []):
            centers.append((s['center']['x'], s['center']['y'], j['id']))
    for i in range(len(centers)):
        for k in range(i + 1, len(centers)):
            if centers[i][2] == centers[k][2]:
                continue
            if dist(centers[i][:2], centers[k][:2]) < MIN_SEPARATION - 1:
                issues.append(f"A4 separation: {centers[i][2]} vs "
                              f"{centers[k][2]} "
                              f"{round(dist(centers[i][:2], centers[k][:2]))}")
    return issues, (total, occ, res, free)


def inject_map(out):
    """Rewrite the // <GAP_DATA> ... // </GAP_DATA> block in factory-map.html
    with a compact GAP_FACTORIES array (Task 7; idempotent)."""
    arr = []
    for fid, f in out['factory_locations'].items():
        bt = f.get('building_totals') or {}
        arr.append({
            'id': fid, 'name': f['factory_name'], 'theme': f['theme'],
            'sig': f['signature_resource'], 'disp': f['disposition'],
            'infeasible': f['disposition'] == 'infeasible'
                          or f.get('sig_shortfall', 0) > 1e-6,
            'shortfall': f.get('sig_shortfall', 0),
            'buildings': bt.get('total_buildings', 0),
            'power_mw': bt.get('total_power_mw', 0),
            'shards': f.get('total_shards', 0),
            'imports': f.get('imports_resolved', []),
            'sites': [{'x': s['center']['x'], 'y': s['center']['y'],
                       'nodes': s['nodes'],
                       'cap': s.get('signature_capacity', 0),
                       'sh': s.get('shards', 0)} for s in f.get('sites', [])],
            'outposts': [{'r': o['resource'], 'x': o['center']['x'],
                          'y': o['center']['y'], 'nodes': o['nodes'],
                          'cap': o.get('capacity', 0),
                          'sh': o.get('shards', 0)}
                         for o in f.get('outposts', [])],
        })
    js = ('// <GAP_DATA> — rewritten by find_gap_factory_locations.py; '
          'do not hand-edit\nconst GAP_FACTORIES = '
          + json.dumps(arr, separators=(',', ':')) + ';\n// </GAP_DATA>')
    html = open(MAP_HTML).read()
    new = re.sub(r'// <GAP_DATA>.*?// </GAP_DATA>', lambda _: js, html,
                 count=1, flags=re.DOTALL)
    if new == html and '// <GAP_DATA>' not in html:
        raise RuntimeError("GAP_DATA markers not found in factory-map.html")
    open(MAP_HTML, 'w').write(new)
    # parse-check the injected literal (A10/Task7 Step7)
    m = re.search(r'const GAP_FACTORIES = (\[.*?\]);\n// </GAP_DATA>',
                  new, re.DOTALL)
    json.loads(m.group(1))
    return len(arr)


def main():
    db = DB(DB_PATH)
    pool = load_pool()
    occ_stat = mark_occupied(pool)
    matched, total_occ, unmatched = occ_stat
    print(f"Occupancy match: {matched}/{total_occ} "
          f"({len(unmatched)} unmatched)")

    # Task 9 — design §2.2 erosion check; resolves which design-§2.2
    # intermediates (Wire/CB/CO/Cu Sheet/Computer) are imported from existing
    # surplus vs in-house per factory.
    current_net = load_current_production()
    extras, erosion_report = resolve_imports(db, current_net)
    print("\n=== Design §2.2 erosion check ===")
    for item, r in erosion_report.items():
        print(f"  {item:20} net_now={r['existing_net']:+7.1f}  "
              f"new={r['new_consumption']:+7.1f}  "
              f"residual={r['residual_net']:+7.1f}  -> {r['decision']}")
    if extras:
        print("  imports resolved per factory:")
        for fid, items in sorted(extras.items()):
            print(f"    {fid}: {sorted(items)}")

    jobs = build_jobs(db, extras)

    # A12 sanity anchor (before allocation)
    print("\n=== A12 demand sanity (bottlenecks) ===")
    for t in ('bauxite', 'copper'):
        dem = sum(j['raw_demand'].get(t, 0) for j in jobs)
        free = [n for n in pool if n['reserved_by'] is None and n['type'] == t]
        cap = sum(rate_of(n) for n in free)
        print(f"  {t:8} demand≈{dem:9.0f}/min  unoccupied "
              f"{len(free)} nodes ≈ {cap:.0f}/min cap")
    assert sum(j['raw_demand'].get('bauxite', 0) for j in jobs) > 0, \
        "A12: zero bauxite demand — decomposition bug"

    print("\n=== job pressure order ===")
    for j in sorted(jobs, key=lambda x: pressure_key(pool, x)):
        pk = pressure_key(pool, j)
        print(f"  {j['name']:22} sig={j['signature']:9} "
              f"pk={pk[0]:.3f} raw={ {k: round(v) for k, v in j['raw_demand'].items()} }")

    order, placed = allocate(pool, jobs)
    out, unmatched = build_output(db, pool, jobs, occ_stat, placed,
                                   erosion_report)
    issues, (total, occ, res, free) = validate(out, pool, order, unmatched)

    print(f"\n=== allocation result ===")
    for j in order:
        bt = j.get('building_totals') or {}
        print(f"  {j['name']:22} {j.get('disposition', '?'):14} "
              f"sites={len(j.get('sites', [])):>2} "
              f"out={len(j.get('outposts', [])):>2} "
              f"bldgs={bt.get('total_buildings', 0):>4} "
              f"pwr={bt.get('total_power_mw', 0):>5.0f}MW "
              f"shards={j.get('total_shards', 0):>3}"
              + ("  *** INFEASIBLE ***" if j.get('infeasible') else ""))

    print(f"\n=== pool balance ===")
    for t, b in out['meta']['pool_balance'].items():
        flag = '  <-- DEFICIT' if (t in ('bauxite', 'copper', 'caterium')
                                   and b['remaining'] < 0) else ''
        print(f"  {t:11} total={b['total']:3} occ={b['occupied']:3} "
              f"reserved={b['reserved_new']:3} free={b['remaining']:3}{flag}")

    nw = sum(1 for j in order for s in j.get('sites', [])
             if quadrant(s['center']['x'], s['center']['y']) in ('NW', 'SE'))
    tot = sum(len(j.get('sites', [])) for j in order)
    print(f"\nQuadrant: {nw}/{tot} sites in NW/SE")
    print(f"Pool: total={total} occupied={occ} reserved={res} free={free}")

    if issues:
        print("\n!!! VALIDATION ISSUES:")
        for i in issues:
            print("  -", i)
    else:
        print("\nAll hard validation checks passed.")

    json.dump(out, open(OUTPUT_PATH, 'w'), indent=2)
    print(f"\nWritten {OUTPUT_PATH}")
    n = inject_map(out)
    print(f"Injected {n} gap factories into {MAP_HTML} "
          f"(GAP_DATA block, parse-checked OK)")


if __name__ == '__main__':
    main()
