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
OUTPUT_PATH        = 'gap-factory-locations.json'

SEARCH_RADIUS  = 40_000          # 400 m cluster radius (HMF method, tunable)
MIN_SEPARATION = 25_000          # 250 m between distinct sites/centers
PURITY_WEIGHT  = {'impure': 1, 'normal': 2, 'pure': 4}
# All extractors assumed at max overclock (3 power shards = 250%) per user.
# Base Mk.3: 120/240/480; OIL: 60/120/240; WELL satellite: 30/60/120.
_OC = 2.5
MINER_RATE     = {'impure': int(120 * _OC), 'normal': int(240 * _OC), 'pure': int(480 * _OC)}
OIL_RATE       = {'impure':  60 * _OC,      'normal': 120 * _OC,      'pure': 240 * _OC}
WELL_RATE      = {'impure':  30 * _OC,      'normal':  60 * _OC,      'pure': 120 * _OC}
QUADRANT_BONUS = 1.5             # soft NW/SE multiplier (A-design)
OCC_MATCH_TOL  = 5_000           # 50 m nearest-node occupancy match (A1/Task2)
MAX_SITES      = 5               # satellite cap per factory (design §3.5
                                 # explicitly multi-sites Aluminium factories)

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
    if node['kind'] == 'well':
        return WELL_RATE[node['purity']]
    if node['type'] == 'oil':
        return OIL_RATE[node['purity']]
    return MINER_RATE[node['purity']]


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
        if any(dist(ctr, pc) < MIN_SEPARATION for pc in placed_centers):
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


def build_jobs(db):
    jobs = []
    for fid, f in NEW_FACTORIES.items():
        rd, tgt = job_raw_demand(db, fid, f['products'], f['recipes'],
                                 f['imports'])
        jobs.append({'id': fid, 'name': fid, 'kind': 'new',
                     'theme': f['theme'], 'signature': f['signature'],
                     'raw_demand': rd, 'targets': tgt, 'anchor': None})
    ald_imp = aldercast_imports(db)
    exist = json.load(open(EXISTING_LOCATIONS))['selections']
    for fid, e in EXTENSIONS.items():
        added = dict(e['added'])
        prods, recipes = added, e.get('recipes', {})
        rd, tgt = job_raw_demand(db, fid, prods, recipes, set())
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
        assert fid in exist, f"A13: no existing center for {fid}"
        ctr = exist[fid]['center']
        jobs.append({'id': fid + '+', 'name': fid + '+', 'kind': 'ext',
                     'theme': 'extension', 'signature': e['signature'],
                     'raw_demand': rd, 'targets': tgt,
                     'anchor': {'x': ctr['x'], 'y': ctr['y']}})
    sub = json.load(open(SUBUNITS))['modules']
    for fid, crit in HMF_CRITICAL.items():
        m = sub[fid]
        per_hmf = {k: v['per_min'] / m['hmf_per_min']
                   for k, v in m['raw_inputs'].items()}
        inc = HMF_SPLIT.get(fid, 66.0 / 5.0)
        if inc <= 0:                             # skip jobs with 0 increment
            continue
        rd = {}
        for item, ph in per_hmf.items():
            nt = ITEM_TO_NODETYPE.get(item)
            if nt:
                rd[nt] = ph * inc
        assert fid in exist, f"A13: no existing center for HMF {fid}"
        ctr = exist[fid]['center']
        jobs.append({'id': fid + '_hmf', 'name': fid + ' (+HMF)',
                     'kind': 'hmf', 'theme': 'HMF +13.2', 'signature': crit,
                     'raw_demand': rd, 'targets': {'Heavy Modular Frame': round(inc, 1)},
                     'anchor': {'x': ctr['x'], 'y': ctr['y']}})
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
    return order, placed_centers


# ---------------------------------------------------------------- output
def build_output(db, pool, jobs, occ_stat, placed_centers):
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
            'estimate': True, 'targets': j.get('targets', {}),
            'center': prim, 'sites': j.get('sites', []),
            'outposts': j.get('outposts', []),
            'resources': demand_vs,
            'sig_shortfall': j.get('sig_shortfall', 0.0),
            'trained_shortfall': j.get('trained_shortfall', {}),
            'reason': _reason(j, disp)}

    out = {'meta': {
        'description': 'Auto-placed gap supply-chain factory locations '
                       '(rough estimate; amounts phase deferred)',
        'estimate': True,
        'coordinate_system': {'x': '+east/right', 'y': '+south/bottom',
                              'units': 'cm (100=1m)',
                              'quadrants': 'NW=top-left SE=bottom-right'},
        'assumptions': {'miner': 'Mk.3 120/240/480 items/min',
                        'well_rate_m3min': WELL_RATE,
                        'oil_rate_m3min': OIL_RATE,
                        'search_radius_m': SEARCH_RADIUS / 100,
                        'min_separation_m': MIN_SEPARATION / 100,
                        'quadrant_bonus': QUADRANT_BONUS},
        'flavor_splits': FLAVOR_SPLITS,
        'or_in_house_rule': 'A6: Moldmarsh Wire defaulted in-house',
        'caveat_centroid': 'A14: a node-centroid can land on water/cliff; '
                           'not a buildability guarantee',
        'occupancy_match': f'{matched}/{total_occ}',
        'pool_balance': pool_balance},
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
        arr.append({
            'id': fid, 'name': f['factory_name'], 'theme': f['theme'],
            'sig': f['signature_resource'], 'disp': f['disposition'],
            'infeasible': f['disposition'] == 'infeasible'
                          or f.get('sig_shortfall', 0) > 1e-6,
            'shortfall': f.get('sig_shortfall', 0),
            'sites': [{'x': s['center']['x'], 'y': s['center']['y'],
                       'nodes': s['nodes']} for s in f.get('sites', [])],
            'outposts': [{'r': o['resource'], 'x': o['center']['x'],
                          'y': o['center']['y'], 'nodes': o['nodes']}
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

    jobs = build_jobs(db)

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
    out, unmatched = build_output(db, pool, jobs, occ_stat, placed)
    issues, (total, occ, res, free) = validate(out, pool, order, unmatched)

    print(f"\n=== allocation result ===")
    for j in order:
        print(f"  {j['name']:22} {j.get('disposition', '?'):14} "
              f"sites={len(j.get('sites', []))} "
              f"outposts={len(j.get('outposts', []))}"
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
