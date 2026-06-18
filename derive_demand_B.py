#!/usr/bin/env python3
"""
derive_demand_B.py — INDEPENDENT cross-check (derivation #2 of 2).

Computes the TRUE gap demand for the "Special Factories" plan in
planner-export/sftools-export-2026-04-01-20-02-03.sft, from scratch.

KEY MODELLING DECISIONS (my own, to catch errors in the other derivation):
  * Each .sft tab is an INDEPENDENT production request:
      production[] = SET targets (units/min).
      input[]      = already-available; decomposition STOPS here (never built).
      blockedRecipes/allowedAlternateRecipes/blockedResources honored.
      resourceWeight = per-raw cost; we minimize total weighted raw cost.
  * Recipe usable in a tab iff: (base recipe OR in allowedAlternateRecipes)
      AND not in blockedRecipes AND it is not a packaging/unpackaging recipe
      (those only move fluids in/out of canisters and create cost loops — never
       needed because no tab targets a packaged item).
  * DB stores FLUIDS (category liquid/gas) in mL; divide qty by 1000 -> m^3/min.
  * Cost solve: cheapest weighted-raw cost to make 1 unit of each item, by
    fixed-point relaxation. We DO NOT take by-product credits in the COST metric
    (prevents negative-cost / loop artifacts); we DO net by-products in the
    QUANTITY solve so surplus by-products offset demand.
  * Quantity solve: cycle-safe topological expansion. Build only items that are
    NOT raw and NOT a tab input. Stop at raws (-> raw_demand) and inputs (-> used).
  * Gap = items the chain must MANUFACTURE that are NOT covered by input and NOT
    raw. Then credit live production (current-production.txt) for the net gap.

Run: python3 derive_demand_B.py
"""
import base64, zlib, json, sqlite3, os, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(ROOT, 'satisfactory.db')
SFT  = os.path.join(ROOT, 'planner-export', 'sftools-export-2026-04-01-20-02-03.sft')
PROD = os.path.join(ROOT, 'planner-export', 'current-production.txt')

KNOWN_RAW = {
    'Desc_OreIron_C','Desc_OreCopper_C','Desc_Stone_C','Desc_Coal_C','Desc_OreGold_C',
    'Desc_LiquidOil_C','Desc_RawQuartz_C','Desc_Sulfur_C','Desc_OreBauxite_C',
    'Desc_OreUranium_C','Desc_NitrogenGas_C','Desc_SAM_C','Desc_Water_C',
}

# ---------------------------------------------------------------- load .sft
def load_sft(fn):
    lines = open(fn).read().splitlines()
    payload = next(l for l in lines if l and not l.startswith('#'))
    return json.loads(zlib.decompress(base64.b64decode(payload[1:])))

# ---------------------------------------------------------------- load DB
def load_db():
    con = sqlite3.connect(DB); cur = con.cursor()
    items = {}
    for iid, name, cat in cur.execute('select id,name,category from items'):
        items[iid] = {'name': name, 'category': cat}
    fluids = {iid for iid, d in items.items() if d['category'] in ('liquid', 'gas')}
    # recipe_ingredients/products.recipe_id == recipes.id (short Recipe_*_C),
    # which is the form the .sft uses for blocked/allowed lists. NOT class_name.
    dur = {rid: (nm, d) for rid, nm, d in cur.execute('select id,name,duration from recipes')}
    ing = collections.defaultdict(list)
    for rid, it, q in cur.execute('select recipe_id,item_id,quantity from recipe_ingredients'):
        ing[rid].append((it, q))
    prod = collections.defaultdict(list)
    for rid, it, q in cur.execute('select recipe_id,item_id,quantity from recipe_products'):
        prod[rid].append((it, q))
    con.close()

    def rate(it, q, d):
        r = q * 60.0 / d
        if it in fluids:
            r /= 1000.0   # mL -> m^3
        return r

    recipes = {}
    for rid in set(list(ing) + list(prod)):
        nm, d = dur.get(rid, (rid, None))
        if not d:
            continue
        recipes[rid] = {
            'name': nm, 'duration': d,
            'in':  [(it, rate(it, q, d)) for it, q in ing.get(rid, [])],
            'out': [(it, rate(it, q, d)) for it, q in prod.get(rid, [])],
        }
    return items, recipes, fluids

ITEMS, RECIPES, FLUIDS = load_db()

def is_packaging(rid):
    return rid.startswith('Recipe_Package') or rid.startswith('Recipe_Unpackage')

def usable_recipes(req):
    allowed = set(req.get('allowedAlternateRecipes', []))
    blocked = set(req.get('blockedRecipes', []))
    out = {}
    for rid, r in RECIPES.items():
        if rid in blocked: continue
        if is_packaging(rid): continue
        if rid.startswith('Recipe_Alternate_') and rid not in allowed: continue
        if not r['out']: continue
        out[rid] = r
    return out

def producers_index(recs):
    idx = collections.defaultdict(list)
    for rid, r in recs.items():
        for it, rate in r['out']:
            if rate > 0:
                idx[it].append(rid)
    return idx

# ---- cost solve (no by-product credit, to stay loop-free & non-negative) ----
def weighted_costs(recs, weights, raws, stop_items):
    INF = float('inf')
    cost = {it: weights.get(it, 0.0) for it in raws}
    for it in stop_items:
        cost[it] = 0.0    # tab inputs are free; we never build them
    idx = producers_index(recs)
    for _ in range(500):
        changed = False
        for it, rids in idx.items():
            if it in stop_items or it in raws:
                continue
            best = cost.get(it, INF)
            for rid in rids:
                r = recs[rid]
                out_rate = dict(r['out']).get(it, 0)
                if out_rate <= 0: continue
                tot = 0.0; ok = True
                for ii, irate in r['in']:
                    c = cost.get(ii, INF)
                    if c == INF: ok = False; break
                    tot += c * irate
                if not ok: continue
                unit = tot / out_rate
                if unit < best - 1e-12:
                    best = unit; changed = True
            if best < cost.get(it, INF) - 1e-12:
                cost[it] = best
        if not changed:
            break
    return cost

def choose_recipe(it, recs, cost):
    idx = producers_index(recs)
    best = None; bestc = float('inf')
    for rid in idx.get(it, []):
        r = recs[rid]
        out_rate = dict(r['out']).get(it, 0)
        if out_rate <= 0: continue
        tot = 0.0; ok = True
        for ii, irate in r['in']:
            c = cost.get(ii, float('inf'))
            if c == float('inf'): ok = False; break
            tot += c * irate
        if not ok: continue
        unit = tot / out_rate
        if unit < bestc - 1e-12:
            bestc = unit; best = rid
    return best

# ---- quantity solve: cycle-safe topological expansion -----------------------
def decompose_tab(tab):
    req = tab['request']
    weights = req.get('resourceWeight', {})
    blocked_res = set(req.get('blockedResources', []))
    raws = (set(KNOWN_RAW) | set(weights.keys())) - blocked_res
    inputs = {p['item']: p['amount'] for p in req.get('input', [])}
    stop = set(inputs)
    recs = usable_recipes(req)
    cost = weighted_costs(recs, weights, raws, stop)

    # lock one recipe per buildable item
    rchoice = {}

    # net demand vector; positive = still needed, negative = surplus by-product
    need = collections.defaultdict(float)
    for p in req.get('production', []):
        need[p['item']] += p['amount']

    manufactured = collections.defaultdict(float)
    raw_demand   = collections.defaultdict(float)
    used_input   = collections.defaultdict(float)
    unbuildable  = collections.defaultdict(float)

    # Cycle-safe: repeatedly drain the most-downstream positive need. To avoid
    # infinite loops from recipe cycles, we cap iterations and process items in a
    # stable order; by-products net into `need` (can go negative = surplus).
    for _ in range(2_000_000):
        target = None
        for it, q in need.items():
            if q <= 1e-9:
                continue
            if it in stop:
                used_input[it] += q; need[it] = 0.0; continue
            if it in raws:
                raw_demand[it] += q; need[it] = 0.0; continue
            target = it; break
        else:
            # no positive buildable need remains
            pass
        if target is None:
            # drain any residual raw/input positives
            leftover = [it for it, q in need.items() if q > 1e-9 and (it in stop or it in raws)]
            if not leftover:
                break
            for it in leftover:
                q = need[it]
                if it in stop: used_input[it] += q
                else: raw_demand[it] += q
                need[it] = 0.0
            continue

        q = need[target]; need[target] = 0.0
        rid = rchoice.get(target) or choose_recipe(target, recs, cost)
        rchoice[target] = rid
        if rid is None:
            unbuildable[target] += q
            continue
        r = recs[rid]
        out_rate = dict(r['out']).get(target, 0)
        runs = q / out_rate
        manufactured[target] += q
        for oi, orate in r['out']:
            if oi == target: continue
            need[oi] -= orate * runs   # by-product reduces demand elsewhere
        for ii, irate in r['in']:
            need[ii] += irate * runs

    return {
        'name': tab['metadata'].get('name'),
        'production': {p['item']: p['amount'] for p in req.get('production', [])},
        'manufactured': dict(manufactured),
        'raw_demand': dict(raw_demand),
        'used_input': dict(used_input),
        'unbuildable': dict(unbuildable),
        'inputs': inputs,
        'rchoice': rchoice,
    }

def nm(it):
    return ITEMS.get(it, {}).get('name', it)

# ---------------------------------------------------------------- live
def load_live():
    live = {}
    for line in open(PROD):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 3: continue
        name = parts[0].strip()
        def num(s):
            s = s.replace('units per minute', '').replace(',', '').strip()
            try: return float(s)
            except: return None
        p = num(parts[1]); c = num(parts[2])
        if p is None: continue
        live[name] = {'produced': p, 'consumed': c or 0.0, 'net': p - (c or 0.0)}
    return live

if __name__ == '__main__':
    j = load_sft(SFT)
    results = [decompose_tab(t) for t in j['tabs']]
    live = load_live()

    print('================ PER-TAB ================')
    for i, r in enumerate(results):
        print(f"\n--- TAB {i} {r['name']!r} ---")
        print('  targets:', {nm(k): v for k, v in r['production'].items()})
        print('  MANUFACTURED:')
        for it, q in sorted(r['manufactured'].items(), key=lambda x: -x[1]):
            print(f"      {nm(it):30s} {q:11.2f}/min")
        if r['unbuildable']:
            print('  UNBUILDABLE:', {nm(k): round(v,2) for k,v in r['unbuildable'].items()})
        print('  raw_demand:')
        for it, q in sorted(r['raw_demand'].items(), key=lambda x: -x[1]):
            unit = 'm3/min' if it in FLUIDS else '/min'
            print(f"      {nm(it):24s} {q:13.2f} {unit}")
        print('  input consumed (stops):')
        for it, q in sorted(r['used_input'].items(), key=lambda x: -x[1]):
            print(f"      {nm(it):26s} {q:11.2f}/min")

    agg_mfg = collections.defaultdict(float)
    agg_raw = collections.defaultdict(float)
    for r in results:
        for it, q in r['manufactured'].items(): agg_mfg[it] += q
        for it, q in r['raw_demand'].items():   agg_raw[it] += q

    print('\n================ AGGREGATE RAW DEMAND ================')
    for it, q in sorted(agg_raw.items(), key=lambda x: -x[1]):
        unit = 'm3/min' if it in FLUIDS else '/min'
        print(f"  {nm(it):24s} {q:13.2f} {unit}")

    print('\n================ FOCUS: HSC & COPPER POWDER ================')
    for key, item in [('High-Speed Connector','Desc_HighSpeedConnector_C'),
                      ('Copper Powder','Desc_CopperDust_C')]:
        tabs_in = [i for i,r in enumerate(results) if item in r['inputs']]
        built = agg_mfg.get(item, 0.0)
        lv = live.get(key, {})
        print(f"\n  {key} ({item}):")
        print(f"     in input list of tabs: {tabs_in}  (caps: {[results[i]['inputs'][item] for i in tabs_in]})")
        print(f"     manufactured by my decomposition: {built:.2f}/min")
        print(f"     live: produced {lv.get('produced')} consumed {lv.get('consumed')} net {lv.get('net')}")
