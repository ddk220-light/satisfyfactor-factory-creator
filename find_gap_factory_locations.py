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
import base64
import json
import math
import re
import sqlite3
import zlib
from collections import defaultdict, deque

MAP_HTML = 'factory-map.html'
SFT_EXPORT = 'planner-export/sftools-export-2026-04-01-20-02-03.sft'

# ---------------------------------------------------------------- paths/const
DB_PATH            = 'satisfactory.db'
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

# Trained resources of these types are NOT reserved per-factory; instead
# they're consolidated into shared mining towns (per user: "mining towns mine
# resources and ship to factories over longer distances; you don't need a
# new factory for everything"). Matches the existing Siderith/Calcara pattern.
SHARED_MINING_RESOURCES = {'iron', 'copper', 'limestone', 'coal'}
MAX_NEW_TOWNS_PER_RESOURCE = 6   # cap on new gap towns per resource —
                                  # geography forces a minimum, this stops
                                  # fragmenting tail demand into single-node
                                  # "towns" (per user "as few as possible")
MIN_TOWN_NODES             = 2   # a town claims ≥2 nodes; isolated single
                                  # nodes spill to a private outpost on the
                                  # largest-demand consumer instead

BUILDING_FOOTPRINT = {        # reused from build_factory_crazy.py
    'Manufacturer': 440, 'Blender': 304, 'Refinery': 200, 'Assembler': 150,
    'Constructor': 80, 'Foundry': 72, 'Smelter': 54,
    'Packager': 24, 'Particle Accelerator': 912, 'Quantum Encoder': 912,
    'Converter': 240,
}

SEARCH_RADIUS  = 70_000          # 700 m cluster radius: a wider primary capture lets
                                  # factories meet more demand from LOCAL nodes, cutting
                                  # far railway hauls ~63% (3081k->1138k) without
                                  # sprawling primaries (90k+ starts to over-spread)
MIN_SEPARATION = 25_000          # 250 m between distinct sites/centers
MAP_SPAN          = 750_000      # ~full map extent in game units
LOCAL_RADIUS      = MAP_SPAN // 16  # ≈46.9k: signature clusters within this of a
                                  # factory's home are "local"; farther clusters are
                                  # railwayed-in and distance-penalized in scoring, so
                                  # the planner keeps a factory's inputs close (prefers
                                  # local lower-purity nodes over distant pure ones).
LOCAL_PENALTY_EXP = 1.6          # steepness of the remote-cluster distance penalty
BELT_LIMIT     = 780             # items/min per node; user's belt cap
                                 # (pure Mk.3 @ 250% = 1200 but belt clamps to
                                 # 780, so shard 3 on pure is wasted)
PURITY_WEIGHT  = {'impure': 1, 'normal': 2, 'pure': 4}
PURE_PREF_BUCKET = 12_000        # SOFT pure-node preference: when claiming nodes
                                  # around a factory, distances are bucketed into
                                  # ~120 m bands and PURE nodes are taken first
                                  # within a band — so pure nodes get more chance
                                  # of being used for REAL demand, without dragging
                                  # a factory far off its recipe's resources.
# All extractors assumed at max overclock (3 power shards = 250%) per user.
# Base Mk.3: 120/240/480; OIL: 60/120/240; WELL satellite: 30/60/120.
_OC = 2.5
MINER_RATE     = {'impure': int(120 * _OC), 'normal': int(240 * _OC), 'pure': int(480 * _OC)}
OIL_RATE       = {'impure':  60 * _OC,      'normal': 120 * _OC,      'pure': 240 * _OC}
WELL_RATE      = {'impure':  30 * _OC,      'normal':  60 * _OC,      'pure': 120 * _OC}
QUADRANT_WEIGHT = {'NW': 1.5, 'NE': 1.4, 'SE': 1.4, 'SW': 1.0}
                                 # soft NW-majority bias (balanced; replaces the
                                 # old flat 1.5x for NW/SE only — now includes NE)
POCKET_MATCH_WEIGHT = 1.0        # strength of the pocket-match score term: a
                                 # candidate center is favored when the LOCAL
                                 # unreserved nodes around it are predominantly
                                 # the job's own signature type, so a (e.g.)
                                 # copper factory lands INSIDE a copper pocket
                                 # rather than parked on a foreign-ore field.
POCKET_MATCH_FLOOR  = 0.15       # never zero out a center entirely (avoids
                                 # starving a job whose only nodes sit amid
                                 # other ore); blend toward 1.0 by weight.
NE_SATURATION_BONUS = 6.0        # >> quadrant weight; biases scoring toward
                                 # claiming/anchoring NE pure nodes.
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
# CORRECTED gap-factory END-PRODUCT targets (2026-06 retarget). Each =
# .sft SET production target − live PRODUCED (current-production.txt). The old
# hand-authored dict ignored both the .sft `input` declarations (items already
# supplied) and live production, inventing five PHANTOM lines (High-Speed
# Connector, Copper Powder, Cooling System, Rubber-export, Modular Frame) that
# are either .sft input-only or already covered by live output. Those are gone.
#   Aluminum Casing     5000 − 1350 live = 3650
#   Steel Beam           900 −  302 live =  598   (Desc_SteelPlate_C)
#   Motor                250 −   45 live =  205
#   Stator               250 −  120 live =  130
#   Smart Plating        150 −    0 live =  150   (Desc_SpaceElevatorPart_1_C)
#   Heavy Modular Frame   95 −   35 live =   60   (Desc_ModularFrameHeavy_C)
# Copper Powder is consumed by Nuclear Pasta (a Phase-5 SET production target in
# the main assembly .sft tab): 200/pasta -> 1000/min for the 5 pasta/min target.
# The .sft lists CopperDust ONLY as an input (assumed supplied) and live
# production makes zero, so nothing actually produces it -> a VERIFIED real gap,
# NOT a phantom. Whitelisted in PHANTOM_EXCEPTIONS so the phantom guard allows it
# while still rejecting genuine input-only phantoms (High-Speed Connector, etc.).
PHANTOM_EXCEPTIONS = {'Copper Powder'}
GAP_TARGETS = {  # items/min, end-product gap demand
    'Aluminum Casing': 3650, 'Steel Beam': 598, 'Motor': 205, 'Stator': 130,
    'Smart Plating': 150, 'Heavy Modular Frame': 60, 'Copper Powder': 1000,
}
# Flavor splits as relative WEIGHTS, rescaled to GAP_TARGETS[item] at load
# (so a split can never silently drift from its target). Weights preserve the
# old proportions where the products survive:
#   Aluminum Casing  1700:1100:1100  (aldercast:bauxhold:silvashade)
#   Steel Beam        400:50          (moldmarsh bulk : silvashade Al-Beam id)
#   Motor             1:1             (voltreach : classic_iron_motor)
#   Stator            159:130         (moldmarsh : voltreach)
FLAVOR_WEIGHTS = {
    'Aluminum Casing': {'aldercast': 1700, 'bauxhold': 1100, 'silvashade': 1100},
    'Steel Beam':       {'moldmarsh': 400, 'silvashade': 50},
    'Motor':            {'voltreach': 1},   # classic_iron_motor removed; voltreach is ('fixed',) now
    'Stator':           {'moldmarsh': 159, 'voltreach': 130},
}
# HMF split weights: Luxara's HMF chain is the only bauxite one, so weight 0
# (Luxara exists at base scale, just takes no increment). The remaining 60/min
# spreads evenly across ferrium/naphtheon/forgeholm/cathera (15 each).
HMF_WEIGHTS = {'ferrium': 1, 'naphtheon': 1,
               'forgeholm': 1, 'cathera': 1, 'luxara': 0}


def _rescale(weights, total):
    """Distribute `total` across {key: weight} proportionally. Keys with
    weight 0 get exactly 0; the remainder is split by weight share, rounded to
    0.1 with the rounding residue dropped on the largest share so the sum is
    exactly `total`."""
    wsum = sum(weights.values())
    if wsum <= 0:
        return {k: 0.0 for k in weights}
    out = {k: round(w / wsum * total, 1) for k, w in weights.items()}
    drift = round(total - sum(out.values()), 1)
    if abs(drift) > 1e-9:
        big = max((k for k in out if weights[k] > 0), key=lambda k: out[k])
        out[big] = round(out[big] + drift, 1)
    return out


# Rescale weights -> absolute per-factory amounts that sum to the target.
FLAVOR_SPLITS = {item: _rescale(w, GAP_TARGETS[item])
                 for item, w in FLAVOR_WEIGHTS.items()}
HMF_SPLIT = _rescale(HMF_WEIGHTS, GAP_TARGETS['Heavy Modular Frame'])


def _decode_sft(path=SFT_EXPORT):
    """Decode a Satisfactory Tools .sft export -> top-level dict.
    Format: first non-blank/non-# line is a version byte + base64(zlib(json))."""
    line = next(ln for ln in open(path).read().splitlines()
                if ln.strip() and not ln.startswith('#'))
    return json.loads(zlib.decompress(base64.b64decode(line[1:])))


def _sft_name_maps(db):
    """Build {Desc_*_C suffix: human name} from items.class_name."""
    suffix = {}
    for name, cn in db.c.execute('SELECT name, class_name FROM items'):
        suffix[cn.rsplit('.', 1)[-1]] = name   # trailing Desc_*_C
    return suffix


def sft_production_and_inputs(db):
    """Decode the .sft and return (production_names, input_names) as sets of
    human item names. `production_names` = every item appearing in any tab's
    production[] (genuine SET targets). `input_names` = every item in any tab's
    input[] (declared already-supplied)."""
    data = _decode_sft()
    suffix = _sft_name_maps(db)

    def nm(cn):
        return suffix.get(cn, cn)
    prod, inputs = set(), set()
    for t in data.get('tabs', []):
        req = t.get('request', {})
        for p in req.get('production', []):
            prod.add(nm(p['item']))
        for i in req.get('input', []):
            inputs.add(nm(i['item']))
    return prod, inputs


def assert_no_phantom_targets(db):
    """GUARD: no GAP_TARGETS key may be a PHANTOM. A phantom = an item that
    appears in a .sft input[] list but in NO production[] list (i.e. declared
    already-supplied, never an actual SET target). This is what produced the
    old High-Speed Connector / Copper Powder / Cooling System / Rubber lines.
    Genuine SET-target items (Aluminum Casing, Steel Beam, Motor, Stator,
    Smart Plating, HMF) appear in production[] AND may also appear in other
    tabs' input[] — that is fine; only input-ONLY items are phantoms."""
    prod, inputs = sft_production_and_inputs(db)
    phantoms = inputs - prod
    bad = [k for k in GAP_TARGETS if k in phantoms and k not in PHANTOM_EXCEPTIONS]
    assert not bad, (f"PHANTOM gap targets (input-only in .sft, never a SET "
                     f"production target): {bad}")
    # Also assert each gap target is a real .sft production target (defense in
    # depth — catches typos / future drift away from the .sft). Whitelisted
    # exceptions (Copper Powder) are verified-real gaps not in .sft production.
    missing = [k for k in GAP_TARGETS if k not in prod and k not in PHANTOM_EXCEPTIONS]
    assert not missing, (f"GAP_TARGETS not found among .sft production "
                         f"targets: {missing}")


def assert_splits_match_targets():
    """Every flavor split must sum to its GAP_TARGETS total (±0.2 for the
    0.1-rounding residue), so a split can never silently diverge."""
    for item, splits in FLAVOR_SPLITS.items():
        s = round(sum(splits.values()), 1)
        assert abs(s - GAP_TARGETS[item]) <= 0.2, \
            f"FLAVOR_SPLITS[{item}] sums to {s}, target {GAP_TARGETS[item]}"
    s = round(sum(HMF_SPLIT.values()), 1)
    assert abs(s - GAP_TARGETS['Heavy Modular Frame']) <= 0.2, \
        f"HMF_SPLIT sums to {s}, target {GAP_TARGETS['Heavy Modular Frame']}"

# pinned signature recipes (output item -> exact DB recipe name), design §3
NEW_FACTORIES = {
    'aldercast': {
        'theme': 'Alclad / Copper-fused', 'signature': 'bauxite',
        'products': {'Aluminum Casing': ('split',)},
        'recipes': {'Alumina Solution': 'Alternate: Sloppy Alumina',
                    'Aluminum Scrap': 'Alternate: Electrode Aluminum Scrap',
                    'Aluminum Ingot': 'Alternate: Pure Aluminum Ingot',
                    'Aluminum Casing': 'Alternate: Alclad Casing'},
        'imports': {'Petroleum Coke'}},   # Rubber dropped with Cooling System
    'bauxhold': {
        'theme': 'Chemical / Sulfuric', 'signature': 'bauxite',
        'products': {'Aluminum Casing': ('split',)},
        'recipes': {'Aluminum Scrap': 'Alternate: Instant Scrap',
                    'Aluminum Ingot': 'Alternate: Pure Aluminum Ingot',
                    'Aluminum Casing': 'Aluminum Casing'},
        'imports': set()},
    # ---- SATURATED themed factories: maxed to ON-SITE signature @250% OC; for
    # the outpost-bound ones (voltreach quartz) the EXISTING outpost runs to
    # 250% but is NOT grown. Output via ('fixed', amt) = a deliberate surplus
    # beyond the .sft target; the split factories (aldercast/bauxhold) still
    # cover the requirement, so the fixed amount stacks extra on top. ----
    'silvashade': {
        'theme': 'Classic Silica Foundry', 'signature': 'bauxite',
        # local bauxite cluster = 4 nodes (belt-capped ~2280/min); sized to fit
        # ONE site (1917 over-claimed and spilled 109k to a distant field).
        'products': {'Aluminum Casing': ('fixed', 1409), 'Steel Beam': ('fixed', 91)},
        'recipes': {'Alumina Solution': 'Alumina Solution',
                    'Aluminum Scrap': 'Aluminum Scrap',
                    'Aluminum Ingot': 'Aluminum Ingot',
                    'Aluminum Casing': 'Aluminum Casing',
                    'Steel Beam': 'Alternate: Aluminum Beam'},
        'imports': set()},
    'voltreach': {
        'theme': 'Electric Motion', 'signature': 'caterium',
        'products': {'Motor': ('fixed', 240), 'Stator': ('fixed', 137)},
        'recipes': {'Rotor': 'Alternate: Copper Rotor',
                    'Stator': 'Alternate: Quickwire Stator',
                    'Motor': 'Alternate: Rigor Motor'},
        'imports': set()},
    'moldmarsh': {
        'theme': 'Cast Steel', 'signature': 'limestone',
        'products': {'Steel Beam': ('fixed', 990), 'Stator': ('fixed', 133)},
        'recipes': {'Steel Beam': 'Alternate: Molded Beam',
                    'Steel Pipe': 'Alternate: Molded Steel Pipe',
                    'Stator': 'Stator'},
        'imports': set()},   # Wire "(or in-house)" -> A6 default in-house
    # ---- iron-copper Smart Plating + Motor, split across two pinned sites
    # (extreme NE + near Cathera). Drops pure-iron: copper Wire (30/min) kills
    # the iron-wire bottleneck; Iron-Alloy Ingot blends copper+iron ore. Each
    # makes SP 75 + Motor 51 (sum SP 150 = target; Motor 102 stacks on the
    # voltreach surplus). Anchored via NEW_FACTORY_ANCHORS. ----
    'ironclad_ne': {
        'name': 'Bronzereach', 'theme': 'Iron-Copper Plating & Motors',
        'signature': 'iron',   # site on abundant NE iron; copper via shared towns
                               # (avoids on-site copper contention with Dustforge)
        'products': {'Smart Plating': ('fixed', 75), 'Motor': ('fixed', 51)},
        'recipes': {'Iron Ingot': 'Alternate: Iron Alloy Ingot',
                    'Copper Ingot': 'Copper Ingot', 'Wire': 'Wire',
                    'Iron Plate': 'Iron Plate',
                    'Steel Pipe': 'Alternate: Iron Pipe',
                    'Reinforced Iron Plate': 'Alternate: Stitched Iron Plate',
                    'Rotor': 'Alternate: Steel Rotor', 'Stator': 'Stator',
                    'Motor': 'Motor', 'Smart Plating': 'Smart Plating'},
        'imports': set()},
    'ironclad_cathera': {
        'name': 'Brasshold', 'theme': 'Iron-Copper Plating & Motors',
        'signature': 'iron',
        'products': {'Smart Plating': ('fixed', 75), 'Motor': ('fixed', 51)},
        'recipes': {'Iron Ingot': 'Alternate: Iron Alloy Ingot',
                    'Copper Ingot': 'Copper Ingot', 'Wire': 'Wire',
                    'Iron Plate': 'Iron Plate',
                    'Steel Pipe': 'Alternate: Iron Pipe',
                    'Reinforced Iron Plate': 'Alternate: Stitched Iron Plate',
                    'Rotor': 'Alternate: Steel Rotor', 'Stator': 'Stator',
                    'Motor': 'Motor', 'Smart Plating': 'Smart Plating'},
        'imports': set()},
    # ---- standalone Copper Powder for Nuclear Pasta (1000/min). Pure Copper
    # Ingot (ore+water) keeps the copper-ore draw tractable (~2400/min). ----
    'coppermill': {
        'name': 'Dustforge', 'theme': 'Copper Powder (Nuclear Pasta)',
        'signature': 'copper',
        'products': {'Copper Powder': ('target',)},
        'recipes': {'Copper Ingot': 'Alternate: Pure Copper Ingot',
                    'Copper Powder': 'Copper Powder'},
        'imports': set()},
}
# Pinned anchors for new factories (extreme-NE copper field, near-Cathera iron
# pocket, and a SEPARATE NE copper field for the powder mill so the three do not
# collide). Un-anchored NEW_FACTORIES auto-place via score_centers as before.
NEW_FACTORY_ANCHORS = {
    'ironclad_ne':      {'x': 296569, 'y': -199802},   # extreme-NE iron cluster
    'ironclad_cathera': {'x': 84199,  'y': -86394},    # near-Cathera iron (E, clear of cathera_hmf)
    'coppermill':       {'x': 355462, 'y': -149808},   # 4500-cap NE copper field (powder mill)
}
# Per-factory HMF saturate override = max on the LOCAL signature cluster (one
# site, belt-capped 780/node, no far satellites): naphtheon oil 2 wells -> 17,
# cathera 1 copper node (780/min) -> 30. Others use HMF_SPLIT.
HMF_SATURATE = {'naphtheon': 17, 'cathera': 30}
# The pure-iron NE Smart Plating (ferrium ext) and classic_iron_motor are REMOVED
# — their Smart Plating 150 + Motor now come from the iron-copper factories.
EXTENSIONS = {}
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


# Live nodes the user marked REUSE-ELIGIBLE in the Occupied Nodes picker
# (reuse-nodes.json export). Matched by position; these are NOT marked occupied,
# so the optimizer is free to repurpose them. Unmarked live miners stay locked.
def load_released(path='reuse-nodes.json'):
    try:
        data = json.load(open(path))
    except (OSError, ValueError):
        return []
    return [(n['x'], n['y']) for n in data if 'x' in n and 'y' in n]


RELEASED = load_released()


def is_released(x, y):
    return any(abs(rx - x) <= OCC_MATCH_TOL and abs(ry - y) <= OCC_MATCH_TOL
               for rx, ry in RELEASED)


def mark_occupied(pool):
    occ = json.load(open(OCCUPIED_NODES))
    recs = []
    released = 0
    for rec in occ:
        p = rec.get('node_pos') or rec.get('miner_pos')
        if not p:
            recs.append((math.inf, None, rec))
            continue
        if is_released(p[0], p[1]):
            released += 1
            continue                       # user freed this node -> leave available
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
    if released:
        print(f"Released {released} live node(s) per reuse-nodes.json -> back in pool")
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
    # Distance-first, but within a ~PURE_PREF_BUCKET band prefer higher purity
    # so PURE nodes get used preferentially for real demand (soft, not forced).
    cand.sort(key=lambda n: (round(dist(center, (n['x'], n['y'])) / PURE_PREF_BUCKET),
                             -PURITY_WEIGHT[n['purity']],
                             round(dist(center, (n['x'], n['y'])), 1),
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
    """{item: per_min} from a factory.products dict (mode 'split'/'target'/'fixed')."""
    return {p: _rate(p, m, fid) for p, m in products.items()}


def split_rate(item, fid):
    if item in FLAVOR_SPLITS and fid in FLAVOR_SPLITS[item]:
        return FLAVOR_SPLITS[item][fid]
    return GAP_TARGETS[item]


def _rate(item, mode, fid):
    """Resolve a products[] mode tuple to an absolute per-min rate.
      ('split',)      -> this factory's FLAVOR_SPLITS share of the target.
      ('fixed', amt)  -> the literal `amt`. Used by SATURATED/maxed factories
                         whose output is a deliberate surplus decoupled from the
                         rescaled split (the split totals still cover the .sft
                         requirement; the fixed amount stacks extra on top).
      ('target',)     -> the whole GAP_TARGETS[item] (single-factory products)."""
    if mode[0] == 'split':
        return split_rate(item, fid)
    if mode[0] == 'fixed':
        return mode[1]
    return GAP_TARGETS[item]


def job_raw_demand(db, fid, products, pinned, imports):
    """{node_type: per_min} for mined solids + oil + nitrogenGas. Decomposes
    each FINAL product end-to-end (A7); Water dropped (sited-anywhere)."""
    agg = defaultdict(float)
    for item, mode in products.items():
        rate = _rate(item, mode, fid)
        for raw, pm in decompose(db, item, rate, pinned, imports).items():
            if raw == 'Water':
                continue
            nt = ITEM_TO_NODETYPE.get(raw)
            if nt:
                agg[nt] += pm
    return dict(agg), {p: _rate(p, m, fid) for p, m in products.items()}


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
def score_centers(pool, sig, sig_demand, placed_centers, home=None,
                  demand_types=None):
    """Candidate centers = available signature nodes; HMF-style score with
    quadrant soft bonus; exclude within MIN_SEPARATION of any placed center
    (A4). When `home` is given (a factory's primary center, i.e. satellite
    rounds), clusters farther than LOCAL_RADIUS are distance-penalized so the
    planner keeps inputs local.

    POCKET MATCH (Change 3): the score is multiplied by the fraction of ALL
    unreserved pool nodes within SEARCH_RADIUS of the center whose type matches
    the job's signature (or, when given, any of `demand_types`). A center that
    sits inside a pocket of its own ore beats one merely reachable across a
    foreign-ore field, so e.g. a copper factory never parks on an iron pocket.
    Returns sorted [(score, center, cluster_nodes, path)]."""
    sig_nodes = avail(pool, sig)
    if not sig_nodes:                               # A9 empty guard
        return []
    match_types = set(demand_types) if demand_types else set()
    match_types.add(sig)
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
        sc *= QUADRANT_WEIGHT.get(quadrant(*ctr), 1.0)
        # Pocket-match: fraction of all unreserved local nodes that are the
        # job's own ore. Blended toward 1.0 by POCKET_MATCH_WEIGHT and floored
        # so a sparse-signature job is penalized, not eliminated.
        local_all = [n for n in pool if n['reserved_by'] is None
                     and dist(ctr, (n['x'], n['y'])) <= SEARCH_RADIUS]
        if local_all:
            frac = sum(1 for n in local_all if n['type'] in match_types) \
                / len(local_all)
        else:
            frac = 1.0
        frac = max(frac, POCKET_MATCH_FLOOR)
        sc *= (1.0 - POCKET_MATCH_WEIGHT) + POCKET_MATCH_WEIGHT * frac
        # Locality penalty for satellites: clusters beyond LOCAL_RADIUS of the
        # factory's home are railwayed-in, so down-weight them by distance —
        # this favors local (even lower-purity) nodes over distant pure ones.
        if home is not None:
            d = dist(ctr, home)
            sc *= min(1.0, LOCAL_RADIUS / max(d, 1.0)) ** LOCAL_PENALTY_EXP
        out.append((round(sc, 3), ctr, near, c['path']))
    out.sort(key=lambda t: (-t[0], t[3]))
    return out


def alloc_signature(pool, job, placed_centers, home=None):
    """Claim signature sites for one job: best cluster, spill to satellites
    up to MAX_SITES. Mutates pool/placed_centers. Sets job sites/infeasible.
    `home` (optional): anchor point for the locality penalty (used by anchored
    ext factories whose real home is the existing factory, not the first spill)."""
    sig = job['signature']
    remaining = job['raw_demand'].get(sig, 0.0)
    if remaining <= 0:
        job['sites'] = []
        return
    dem_types = set(job.get('raw_demand', {}).keys())
    sites = []
    for _ in range(MAX_SITES):
        if remaining <= 1e-6:
            break
        # Penalize distant clusters relative to the factory's home: an explicit
        # `home` (anchored/ext factories) else the already-placed primary site.
        cur_home = home if home is not None else \
            ((sites[0]['center']['x'], sites[0]['center']['y']) if sites else None)
        ranked = score_centers(pool, sig, remaining, placed_centers, cur_home,
                               demand_types=dem_types)
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
        if nt in SHARED_MINING_RESOURCES:
            continue                              # handled by mining towns
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


def load_existing_mining_towns():
    """Parse selected-factory-locations.json mining_town entries — these are
    real in-game outposts (Siderith, Calcara) we can route gap demand
    through up to their spare capacity, *before* building any new towns."""
    sel = json.load(open(EXISTING_LOCATIONS))['selections']
    existing = []
    for fid, e in sel.items():
        if e.get('type') != 'mining_town':
            continue
        used = 0
        for s in e.get('supplies', []):
            # supplies look like "Naphtheon (2,007/min)"
            m = re.search(r'\(([\d,\.]+)/min\)', s)
            if m:
                used += float(m.group(1).replace(',', ''))
        existing.append({
            'id': fid, 'name': e['factory_name'],
            'resource': e['required_resources'][0].lower().split()[0],
            'center': e['center'],
            'capacity_max': e.get('capacity_per_min', 0),
            'used_existing': round(used, 1),
            'spare': round(e.get('capacity_per_min', 0) - used, 1),
            'nodes': e.get('nodes', []),
            'existing': True,
        })
    return existing


def consolidate_mining_towns(pool, jobs, placed_centers):
    """For each SHARED_MINING_RESOURCES type:
    1) Route demand through existing mining towns (Siderith, Calcara) up
       to their spare capacity FIRST — they're already built in-game.
    2) Build new gap towns for the remainder, capped at
       MAX_NEW_TOWNS_PER_RESOURCE. Order by raw cluster capacity descending
       (no NW/SE bonus for towns: they go where the resource physically is).
    3) Nearest-only consumer→town supply assignment (sparse graph)."""
    existing_towns = load_existing_mining_towns()
    towns = []
    for r in sorted(SHARED_MINING_RESOURCES):
        consumers = []
        for j in jobs:
            d = j['raw_demand'].get(r, 0)
            if r != j['signature'] and d > 0:
                consumers.append({'factory': j['id'], 'demand': d})
        total_demand = sum(c['demand'] for c in consumers)
        if total_demand <= 0:
            continue
        # Step 1: existing in-game mining towns of resource r supply first
        # (Siderith=iron 3293 spare; Calcara=limestone 879 spare).
        town_capacities = []
        for et in existing_towns:
            if et['resource'] != r:
                continue
            et_copy = dict(et)
            et_copy['nodes'] = []          # nodes already occupied in pool
            et_copy['shards'] = 0           # existing build; no new shards
            town_capacities.append(et_copy)
        remaining = total_demand - sum(et['spare'] for et in town_capacities)
        # Step 2: build new gap towns for the remainder, ranked by RAW
        # cluster capacity (largest first; no NW/SE bias for towns), capped.
        # Phase A: multi-node towns (MIN_TOWN_NODES≥2). Phase B: if demand
        # remains, single-node spillover so demand is fully met (still
        # respecting MAX_NEW_TOWNS_PER_RESOURCE).
        new_built = 0
        min_nodes = MIN_TOWN_NODES
        while remaining > 1.0 and new_built < MAX_NEW_TOWNS_PER_RESOURCE:
            avail_r = avail(pool, r)
            if not avail_r:
                break
            best, best_cap, best_ctr = None, -1, None
            for c in avail_r:
                near = [n for n in avail_r
                        if dist((c['x'], c['y']),
                                (n['x'], n['y'])) <= SEARCH_RADIUS]
                if len(near) < min_nodes:
                    continue
                ctr = centroid(near)
                if any(dist(ctr, pc) < MIN_SEPARATION * 1.25
                       for pc in placed_centers):
                    continue
                cap = sum(rate_of(n) for n in near)
                if cap > best_cap or (cap == best_cap and best
                                       and c['path'] < best['path']):
                    best_cap, best, best_ctr = cap, c, ctr
            if not best:
                if min_nodes > 1:        # exhausted multi-node clusters
                    min_nodes = 1        # spillover phase: single-node OK
                    continue
                break
            town_id = f'town_{r}_{new_built + 1}'
            claimed, _ = claim_nearest(pool, r, best_ctr, remaining, town_id,
                                        radius=SEARCH_RADIUS)
            if not claimed:
                break
            tc = centroid(claimed)
            placed_centers.append(tc)
            town_capacities.append({
                'id': town_id, 'idx': new_built + 1, 'resource': r,
                'name': f'{r.title()} Town {new_built + 1}',
                'center': {'x': tc[0], 'y': tc[1]},
                'nodes': [{'x': n['x'], 'y': n['y'], 't': n['type'],
                           'p': n['purity'][0], 'k': n['kind']}
                          for n in claimed],
                'existing': False,
            })
            remaining -= sum(rate_of(n) for n in claimed)
            new_built += 1
        if not town_capacities:
            continue
        # Nearest-only assignment: each consumer pulls from the closest
        # town with remaining capacity (then spills to next-nearest if it
        # fills). Sparse supply graph instead of pro-rata everywhere.
        for t in town_capacities:
            t['supplies'] = []
            if t.get('existing'):
                t['_remaining_cap'] = t.get('spare', 0)   # in-game spare
            else:
                t['capacity_max'] = sum(rate_of(_full_node(n))
                                        for n in t['nodes'])
                t['_remaining_cap'] = t['capacity_max']
        def consumer_center(fid):
            for j in jobs:
                if j['id'] != fid: continue
                if j.get('sites'): return (j['sites'][0]['center']['x'],
                                            j['sites'][0]['center']['y'])
                if j.get('anchor'): return (j['anchor']['x'], j['anchor']['y'])
            return (0, 0)
        # Allocate biggest consumers first so they get nearest pick
        consumers_sorted = sorted(consumers, key=lambda c: -c['demand'])
        for c in consumers_sorted:
            cctr = consumer_center(c['factory'])
            remaining_c = c['demand']
            ranked = sorted(town_capacities,
                             key=lambda t: dist(cctr, (t['center']['x'],
                                                       t['center']['y'])))
            for t in ranked:
                if remaining_c <= 0: break
                if t['_remaining_cap'] <= 0: continue
                amt = min(remaining_c, t['_remaining_cap'])
                t['supplies'].append({'factory': c['factory'],
                                       'amount_per_min': round(amt, 1)})
                t['_remaining_cap'] -= amt
                remaining_c -= amt
        for t in town_capacities:
            t['demand_share'] = round(t['capacity_max'] - t['_remaining_cap'], 1)
            del t['_remaining_cap']
        towns.extend(town_capacities)
        if remaining > 1.0:
            towns.append({'id': f'town_{r}_SHORTFALL', 'resource': r,
                          'name': f'{r.title()} shortfall',
                          'shortfall_per_min': round(remaining, 1)})
    return towns


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
    built = job.get('built', False)
    claimed, cap = claim_nearest(pool, sig, actr, demand, job['id'],
                                 radius=SEARCH_RADIUS)
    if claimed:
        c2 = centroid(claimed) if not built else (actr[0], actr[1])
        # For a BUILT factory the primary site stays exactly on the anchor —
        # the factory physically exists there; claimed coal feeds it in place.
        job['sites'] = [{'center': {'x': c2[0], 'y': c2[1]},
                         'signature_capacity': round(cap, 1),
                         'nodes': [{'x': n['x'], 'y': n['y'], 't': n['type'],
                                    'p': n['purity'][0], 'k': n['kind']}
                                   for n in claimed]}]
        placed_centers.append(c2)
    elif built:
        # Built but no coal claimable at the anchor — still keep the pinned
        # primary site at the anchor (it exists in-game); shortfall spills.
        job['sites'] = [{'center': {'x': actr[0], 'y': actr[1]},
                         'signature_capacity': 0.0, 'nodes': []}]
        placed_centers.append(actr)
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
    alloc_signature(pool, free, placed_centers, home=actr)   # penalize vs the anchor
    job['sites'] += free.get('sites', [])
    short = free.get('sig_shortfall', 0.0)
    job['sig_shortfall'] = short
    if built:
        # PINNED: never relocate. Home stays at the anchor; only the shortfall
        # spilled to satellites. Disposition reflects scale-in-place vs spill.
        job['disposition'] = 'pinned_satellite' if free.get('sites') \
            else 'scaled_in_place'
        job['infeasible'] = short > 1e-6
    elif short <= 1e-6 and job['sites']:
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
        jobs.append({'id': fid, 'name': f.get('name', fid), 'kind': 'new',
                     'theme': f['theme'], 'signature': f['signature'],
                     'raw_demand': rd, 'targets': tgt,
                     'anchor': NEW_FACTORY_ANCHORS.get(fid),
                     'imports_resolved': sorted(imports),
                     'building_chain': chain,
                     'building_totals': factory_building_totals(chain)})
    exist = json.load(open(EXISTING_LOCATIONS))['selections']
    for fid, e in EXTENSIONS.items():
        added = dict(e['added'])
        prods, recipes = added, e.get('recipes', {})
        imports = extras.get(fid + '+', set())
        rd, tgt = job_raw_demand(db, fid, prods, recipes, imports)
        ext_products = {p: (split_rate(p, fid) if m[0] == 'split'
                            else GAP_TARGETS[p]) for p, m in prods.items()}
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
        inc = HMF_SATURATE.get(fid, HMF_SPLIT.get(fid, 0.0))
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
        # Anvilreach is the gap +HMF increment — a DISTINCT factory from the
        # built base Forgeholm, so it must NOT pin onto the base (that stacked
        # the two map markers on the same spot). It relocates to its own coal
        # cluster; the base center is still seeded into placed_centers via this
        # job's anchor, so every other factory also keeps clear of it.
        built = False
        jobs.append({'id': fid + '_hmf',
                     'name': ({'forgeholm': 'Anvilreach', 'ferrium': 'Heavyhold'}
                              .get(fid, fid + ' (+HMF)')),
                     'kind': 'hmf', 'theme': f'HMF +{inc:.1f}', 'signature': crit,
                     'raw_demand': rd, 'targets': {'Heavy Modular Frame': round(inc, 1)},
                     'anchor': {'x': ctr['x'], 'y': ctr['y']},
                     'built': built, 'pinned': built,
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
    # Pre-seed anchored (ext/hmf) job centers: they sit at FIXED existing
    # in-game factory locations and cannot move, so seeding them up front makes
    # every `new` factory respect MIN_SEPARATION from them regardless of the
    # pressure order in which jobs are placed (avoids a new factory landing on
    # top of e.g. the pinned forgeholm/Anvilreach or a themed HMF site).
    anchored_seed = [(j['anchor']['x'], j['anchor']['y'])
                     for j in jobs if j.get('anchor')]
    placed_centers.extend(anchored_seed)
    pending = sorted(jobs, key=lambda j: pressure_key(pool, j))
    done = set()
    order = []
    # PHASE 1 — reserve ALL signature sites first (B1: a trained grab must
    # never starve a later job's signature resource).
    for j in pending:
        if j['id'] in done:
            continue
        if j['kind'] == 'new' and not j.get('anchor'):  # A3 round-robin peers
            peers = [p for p in pending if p['kind'] == 'new'
                     and not p.get('anchor')            # anchored new -> alloc_anchored
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
                                           p['remaining'], placed_centers,
                                           demand_types=set(p['raw_demand']))
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
    # PHASE 2.5 — shared mining towns for SHARED_MINING_RESOURCES (consolidate
    # what would otherwise be many private iron/copper/limestone/coal outposts).
    mining_towns = consolidate_mining_towns(pool, order, placed_centers)
    # PHASE 3 — per-node min overclock (Task 10): replace blanket 250% with
    # the smallest clock per node that meets each site/outpost/town's demand.
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
    # Towns also get min-overclock applied.
    for t in mining_towns:
        if 'nodes' not in t:
            continue
        cap_max = sum(rate_of(_full_node(n)) for n in t['nodes'])
        this_demand = min(t.get('demand_share', cap_max), cap_max)
        oc, shards, cap = site_min_overclock(t['nodes'], this_demand)
        for n in t['nodes']:
            n['oc'] = oc[id(n)]['clock']
            n['sh'] = oc[id(n)]['shards']
        t['capacity'] = cap
        t['shards'] = shards
    return order, placed_centers, mining_towns


def _full_node(compact):
    """Shim: build a minimal full-shape node dict from compact (for rate_of)."""
    return {'kind': compact.get('k') or compact.get('kind'),
            'type': compact.get('t') or compact.get('type'),
            'purity': _PUR_FULL[compact.get('p') or compact.get('purity')]}


# ---------------------------------------------------------------- output
def build_output(db, pool, jobs, occ_stat, placed_centers,
                 out_erosion_report=None, mining_towns=None):
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
                        'quadrant_weight': QUADRANT_WEIGHT},
        'flavor_splits': FLAVOR_SPLITS,
        'hmf_split': HMF_SPLIT,
        'caveat_centroid': 'A14: a node-centroid can land on water/cliff; '
                           'not a buildability guarantee',
        'occupancy_match': f'{matched}/{total_occ}',
        'pool_balance': pool_balance,
        'erosion_report': out_erosion_report,
        'total_shards_global': (sum(f['total_shards'] for f in facs.values())
                                 + sum(t.get('shards', 0)
                                       for t in (mining_towns or [])))},
        'factory_locations': facs,
        'gap_mining_towns': mining_towns or []}
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
        # Saturation anchors deliberately RELAX MIN_SEPARATION (Change 2) so
        # clustered pure nodes inside another factory's exclusion zone are not
        # stranded — exempt them from the A4 separation hard check.
        if j.get('kind') == 'saturation':
            continue
        # ext/hmf jobs are ANCHORED at fixed existing in-game factory centers
        # (the user already built them); a new factory landing within
        # MIN_SEPARATION of such a fixed point is not a buildability conflict so
        # long as no node is double-booked (checked above). Flag the pair only
        # when BOTH sides are freely-placeable `new`/saturation centers.
        anchored = j.get('kind') in ('ext', 'hmf') or bool(j.get('anchor'))
        for s in j.get('sites', []):
            centers.append((s['center']['x'], s['center']['y'], j['id'],
                            anchored))
    for i in range(len(centers)):
        for k in range(i + 1, len(centers)):
            if centers[i][2] == centers[k][2]:
                continue
            if centers[i][3] or centers[k][3]:     # one side is an anchor
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
            'prod': [{'item': k, 'amt': v}
                     for k, v in (f.get('targets') or {}).items()
                     if not k.endswith('(export)')],
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
    towns = []
    for t in out.get('gap_mining_towns', []):
        if 'nodes' not in t:
            continue           # skip shortfall sentinels
        if t.get('existing'):
            continue           # already drawn via MINING_TOWNS const
        towns.append({
            'id': t['id'], 'name': t['name'],
            'r': t['resource'],
            'cap': t.get('capacity', 0),
            'sh': t.get('shards', 0),
            'cx': t['center']['x'], 'cy': t['center']['y'],
            'nodes': t['nodes'],
            'supplies': t.get('supplies', []),
        })
    js = ('// <GAP_DATA> — rewritten by find_gap_factory_locations.py; '
          'do not hand-edit\nconst GAP_FACTORIES = '
          + json.dumps(arr, separators=(',', ':')) + ';\n'
          + 'const GAP_TOWNS = '
          + json.dumps(towns, separators=(',', ':')) + ';\n'
          + '// </GAP_DATA>')
    html = open(MAP_HTML, encoding='utf-8').read()
    new = re.sub(r'// <GAP_DATA>.*?// </GAP_DATA>', lambda _: js, html,
                 count=1, flags=re.DOTALL)
    if new == html and '// <GAP_DATA>' not in html:
        raise RuntimeError("GAP_DATA markers not found in factory-map.html")
    open(MAP_HTML, 'w', encoding='utf-8').write(new)
    # parse-check both injected literals (A10/Task7 Step7)
    m1 = re.search(r'const GAP_FACTORIES = (\[.*?\]);', new, re.DOTALL)
    m2 = re.search(r'const GAP_TOWNS = (\[.*?\]);', new, re.DOTALL)
    json.loads(m1.group(1))
    json.loads(m2.group(1))
    return len(arr), len(towns)


def main():
    db = DB(DB_PATH)
    # CHANGE 1 module-init guards: targets must be real .sft SET targets (no
    # input-only phantoms) and every flavor split must sum to its target.
    assert_no_phantom_targets(db)
    assert_splits_match_targets()
    print("Gap targets (corrected, gap = .sft SET - live):")
    for k, v in GAP_TARGETS.items():
        print(f"  {k:22} {v}")
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

    order, placed, mining_towns = allocate(pool, jobs)
    # `order` includes the NE saturation factories (Change 2) added during
    # allocation; build output from it so they reach the JSON + map injection.
    out, unmatched = build_output(db, pool, order, occ_stat, placed,
                                   erosion_report, mining_towns)
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
    n_f, n_t = inject_map(out)
    print(f"Injected {n_f} gap factories + {n_t} mining towns into {MAP_HTML} "
          f"(GAP_DATA block, parse-checked OK)")


if __name__ == '__main__':
    main()
