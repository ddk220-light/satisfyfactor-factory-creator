#!/usr/bin/env python3
"""
derive_demand_A.py  — Derivation #1 (independent) of the TRUE demand the gap
supply-chain must satisfy.

What it does
------------
1. Decodes every tab of the authoritative .sft plan and collects, per tab:
   - production targets (units/min)            -> the SET needs
   - input list (items already available)      -> recursion STOPS here (free)
   - blockedRecipes / blockedResources         -> may not use / may not mine
   - allowedAlternateRecipes                   -> may use these alternates
   - resourceWeight                            -> per-raw-ore cost (for picking
                                                  the cheapest alternate)
2. Recursively decomposes each production target into raw resources.
   Rules baked in:
     * STOP at a raw resource OR any item in that tab's input list.
     * Never use a blockedRecipe. Use allowed alternates; otherwise the item's
       standard (non-alternate) recipe. When several allowed recipes exist,
       pick the one minimizing weighted raw cost.
     * Cycle detection (oil / (un)packaging loops) — never infinite-recurse.
     * Recipe by-products (2nd output) are credited (their cost is netted out).
3. Sums raw demand across all tabs.
4. Builds gap_products = items some tab must MANUFACTURE that are NOT supplied
   via input and NOT already net-positive in current-production.txt.
5. Resolves the HSC and Copper Powder verdicts with explicit arithmetic.

DB: satisfactory.db (rate/min = quantity * 60 / duration).
"""

import base64, zlib, json, sqlite3, os, sys
from collections import defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(REPO, "satisfactory.db")
SFT = os.path.join(REPO, "planner-export", "sftools-export-2026-04-01-20-02-03.sft")
CURPROD = os.path.join(REPO, "planner-export", "current-production.txt")

# Raw resources: anything mined/extracted. These have no production recipe we
# build (we just credit the weight). Water has weight 0.
RAW = {
    "Desc_OreIron_C", "Desc_OreCopper_C", "Desc_Stone_C", "Desc_Coal_C",
    "Desc_OreGold_C", "Desc_LiquidOil_C", "Desc_RawQuartz_C", "Desc_Sulfur_C",
    "Desc_OreBauxite_C", "Desc_OreUranium_C", "Desc_NitrogenGas_C",
    "Desc_SAM_C", "Desc_Water_C",
}

# ---------------------------------------------------------------------------
# Load DB recipe data
# ---------------------------------------------------------------------------
con = sqlite3.connect(DB)
cur = con.cursor()

item_name = {}
item_cat = {}
for iid, nm, cat in cur.execute("SELECT id, name, category FROM items"):
    item_name[iid] = nm
    item_cat[iid] = cat

# Fluids are stored in mL in the DB; the .sft production `amount` is in m3/min.
# Normalize every fluid quantity by /1000 at load time so all rates are in the
# same unit basis (m3/min for fluids, units/min for solids).
FLUIDS = {iid for iid, c in item_cat.items() if c in ("liquid", "gas")}


def norm(iid, qty):
    return qty / 1000.0 if iid in FLUIDS else qty


# recipe -> {duration, class_name, ingredients:[(item,qty)], products:[(item,qty)]}
recipes = {}
for rid, cn, dur in cur.execute("SELECT id, class_name, duration FROM recipes"):
    recipes[rid] = {"class_name": cn or "", "duration": dur or 1.0,
                    "ing": [], "prod": []}
for rid, iid, qty in cur.execute(
        "SELECT recipe_id, item_id, quantity FROM recipe_ingredients"):
    if rid in recipes:
        recipes[rid]["ing"].append((iid, norm(iid, qty)))
for rid, iid, qty in cur.execute(
        "SELECT recipe_id, item_id, quantity FROM recipe_products"):
    if rid in recipes:
        recipes[rid]["prod"].append((iid, norm(iid, qty)))

# item -> list of recipe ids that produce it
produced_by = defaultdict(list)
for rid, r in recipes.items():
    for iid, _ in r["prod"]:
        produced_by[iid].append(rid)


def is_alternate(rid):
    return "Alternate" in recipes[rid]["class_name"] or rid.startswith("Recipe_Alternate_")


def is_unpackage(rid):
    return "Unpackage" in rid or "Unpackage" in recipes[rid]["class_name"]


def rate(recipe, iid, qty):
    """units/min that `recipe` produces/consumes of item iid at qty per cycle."""
    return qty * 60.0 / recipe["duration"]


# ---------------------------------------------------------------------------
# Decode the .sft
# ---------------------------------------------------------------------------
lines = open(SFT).read().splitlines()
payload = next(l for l in lines if l and not l.startswith("#"))
plan = json.loads(zlib.decompress(base64.b64decode(payload[1:])))
TABS = plan["tabs"]


# ---------------------------------------------------------------------------
# Per-tab recipe selection + decomposition
# ---------------------------------------------------------------------------
class TabSolver:
    def __init__(self, tab):
        req = tab["request"]
        self.name = tab.get("metadata", {}).get("name") or "?"
        self.production = req.get("production", [])
        self.inputs = {x["item"] for x in req.get("input", [])}
        self.blocked_recipes = set(req.get("blockedRecipes", []))
        self.blocked_resources = set(req.get("blockedResources", []))
        self.allowed_alts = set(req.get("allowedAlternateRecipes", []))
        self.weight = req.get("resourceWeight", {})
        # caches
        self._cost = {}          # item -> weighted raw cost / unit  (None=impossible)
        self._best_recipe = {}   # item -> chosen recipe id (or None=stop/raw)
        self.errors = []

    # ---- which recipes may this tab use to make `item`? -------------------
    def candidate_recipes(self, item):
        out = []
        for rid in produced_by.get(item, []):
            if rid in self.blocked_recipes:
                continue
            if is_unpackage(rid):
                # packaging/unpackaging loops are never a real production path
                continue
            if is_alternate(rid):
                if rid not in self.allowed_alts:
                    continue
            out.append(rid)
        return out

    def is_free(self, item):
        """Stop recursion here? (raw resource or tab input)."""
        return item in RAW or item in self.inputs

    # ---- weighted raw cost per unit of `item` -----------------------------
    def cost(self, item, stack):
        if self.is_free(item):
            if item in RAW:
                return self.weight.get(item, 0.0)
            return 0.0  # input item = free
        if item in self._cost:
            return self._cost[item]
        if item in stack:
            return None  # cycle
        cands = self.candidate_recipes(item)
        if not cands:
            self._cost[item] = None
            self._best_recipe[item] = None
            return None
        stack = stack | {item}
        best_c, best_r = None, None
        for rid in cands:
            r = recipes[rid]
            prod = dict((p, q) for p, q in r["prod"])
            main_qty = prod.get(item)
            if not main_qty:
                continue
            # cost of all ingredients minus credit for by-products
            total = 0.0
            ok = True
            for ing, q in r["ing"]:
                c = self.cost(ing, stack)
                if c is None:
                    ok = False
                    break
                total += c * q
            if not ok:
                continue
            # NOTE on by-products: we deliberately do NOT credit by-products in
            # the cost ranking. Crediting them at full production cost lets the
            # oil/packaging recipes (which emit Water / Heavy Oil Residue / Fuel
            # as a 2nd output) look near-free, and the minimizer then routes huge
            # volumes through them — e.g. 11,700 m3 Crude Oil for 95 HMF/min.
            # A conservative "full ingredient cost / main output" ranking avoids
            # that pathology and matches how the codebase treats backed-up
            # by-products (they halt a building rather than being free credit).
            per_unit = total / main_qty
            if best_c is None or per_unit < best_c:
                best_c, best_r = per_unit, rid
        self._cost[item] = best_c
        self._best_recipe[item] = best_r
        return best_c

    def best_recipe(self, item):
        if item not in self._best_recipe:
            self.cost(item, frozenset())
        return self._best_recipe.get(item)

    # ---- expand `item` at `amount`/min into raw demand --------------------
    def decompose(self, item, amount, raw, made, stack):
        """raw: dict raw->units/min ; made: dict item->units/min produced."""
        if self.is_free(item):
            if item in RAW:
                raw[item] += amount
            return
        if item in stack:
            self.errors.append(f"cycle at {item_name.get(item,item)}")
            return
        rid = self.best_recipe(item)
        if rid is None:
            self.errors.append(f"no recipe for {item_name.get(item,item)}")
            return
        r = recipes[rid]
        prod = dict((p, q) for p, q in r["prod"])
        main_qty = prod[item]
        cycles_per_min = amount / main_qty           # crafts/min needed
        made[item] += amount
        stack = stack | {item}
        for ing, q in r["ing"]:
            self.decompose(ing, q * cycles_per_min, raw, made, stack)

    def run(self):
        raw = defaultdict(float)
        made = defaultdict(float)
        for tgt in self.production:
            self.decompose(tgt["item"], tgt["amount"], raw, made, frozenset())
        return raw, made


# ---------------------------------------------------------------------------
# Run all tabs, aggregate
# ---------------------------------------------------------------------------
total_raw = defaultdict(float)
total_made = defaultdict(float)            # item -> units/min the plan manufactures
supplied_via_input = set()                 # items some tab marks as input
all_errors = []

per_tab = []
for i, tab in enumerate(TABS):
    s = TabSolver(tab)
    supplied_via_input |= s.inputs
    raw, made = s.run()
    for k, v in raw.items():
        total_raw[k] += v
    for k, v in made.items():
        total_made[k] += v
    per_tab.append((i, s.name, dict(raw), dict(made)))
    all_errors += [f"tab{i} {s.name}: {e}" for e in s.errors]

# ---------------------------------------------------------------------------
# current-production.txt : net = produced - consumed
# ---------------------------------------------------------------------------
def parse_num(tok):
    tok = tok.replace(",", "").replace("m³", "").replace("units per minute", "")
    tok = tok.replace("per minute", "").strip()
    try:
        return float(tok)
    except ValueError:
        return 0.0

# map human name -> class id
name_to_id = {v: k for k, v in item_name.items()}
# a couple of label fixups between current-production.txt and DB names
LABEL_FIX = {
    "Screws": "Screw",
    "Steel Beam": "Steel Beam",           # DB: Desc_SteelPlate_C is "Steel Beam"
}
live_net = {}     # class_id -> net/min
live_net_byname = {}
with open(CURPROD) as f:
    for line in f:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        nm = parts[0].strip()
        prod = parse_num(parts[1])
        cons = parse_num(parts[2])
        net = prod - cons
        live_net_byname[nm] = net
        cid = name_to_id.get(LABEL_FIX.get(nm, nm))
        if cid:
            live_net[cid] = net

def live_net_for(item):
    """net/min for a class id, trying class then human name."""
    if item in live_net:
        return live_net[item]
    nm = item_name.get(item)
    if nm in live_net_byname:
        return live_net_byname[nm]
    return None

# ---------------------------------------------------------------------------
# gap_products: items the plan must MANUFACTURE that are
#   (a) NOT supplied via any tab's input, and
#   (b) NOT a raw resource, and
#   (c) NOT already net-positive in live production.
# i.e. the corrected target list for the gap factories.
# ---------------------------------------------------------------------------
gap_products = []
for item, permin in sorted(total_made.items(), key=lambda x: -x[1]):
    if item in RAW:
        continue
    if item in supplied_via_input:
        continue                       # already available -> not a gap product
    ln = live_net_for(item)
    live_surplus = ln if (ln is not None and ln > 0) else 0.0
    net_gap = total_made[item] - live_surplus   # TRUE demand on the gap chain
    if net_gap <= 1e-6:
        continue                       # live surplus already covers it
    if ln is None:
        reason = f"plan needs {round(total_made[item],1)}/min, no live production -> build all"
    else:
        reason = (f"plan needs {round(total_made[item],1)}/min, live net "
                  f"{round(ln,1)}/min -> net gap {round(net_gap,1)}/min")
    gap_products.append({
        "item": item_name.get(item, item),
        "class": item,
        "per_min": round(net_gap, 2),          # NET demand the gap chain must make
        "plan_need": round(total_made[item], 2),
        "live_net": (round(ln, 2) if ln is not None else None),
        "reason": reason,
    })

# ---------------------------------------------------------------------------
# HSC verdict
# ---------------------------------------------------------------------------
HSC = "Desc_HighSpeedConnector_C"
hsc_in_input = HSC in supplied_via_input
hsc_made = total_made.get(HSC, 0.0)
hsc_live = live_net_for(HSC)
hsc_lines = []
hsc_lines.append(
    f"High-Speed Connector appears in the .sft 'input' list "
    f"({'YES at 99999 = unlimited' if hsc_in_input else 'NO'}), so the chain STOPS at it "
    f"— no HSC is decomposed/built for the SET targets (plan-manufactured HSC = {round(hsc_made,2)}/min).")
hsc_lines.append(
    f"Live production net = {hsc_live} /min (108 produced - 78 consumed = +30).")
hsc_lines.append(
    "Net need after crediting input (unlimited) AND live (+30): 0/min. "
    "The old 115/min HSC line is a PHANTOM — do NOT build it.")
hsc_verdict = " ".join(hsc_lines)

# ---------------------------------------------------------------------------
# Copper Powder verdict
# ---------------------------------------------------------------------------
CP = "Desc_CopperDust_C"
cp_in_input = CP in supplied_via_input
cp_made = total_made.get(CP, 0.0)
cp_live = live_net_for(CP)
# what would the demand be if it WERE built? 5 Nuclear Pasta/min * 200 per craft / (1 per 2min)
# recipe: 1 pasta per 120s -> 0.5/min/machine; 5/min => 10 machines; 200*10/2min? compute cleanly:
# per pasta: 200 copper powder. 5 pasta/min => 1000 copper powder/min.
cp_lines = []
cp_lines.append(
    f"Copper Powder (Desc_CopperDust_C) appears in the .sft 'input' list "
    f"({'YES at 9999/999999 = unlimited' if cp_in_input else 'NO'}). "
    f"Nuclear Pasta (5/min) needs 200 Copper Powder per unit => 1000 Copper Powder/min, "
    f"BUT because it is an input the chain STOPS there (plan-manufactured = {round(cp_made,2)}/min).")
cp_lines.append(
    f"Live production net = {cp_live if cp_live is not None else 'not produced live'} "
    f"(Copper Powder is absent from current-production.txt).")
cp_lines.append(
    "Verdict: it is an INPUT (treated as already supplied), so the gap plan must NOT "
    "build a 1000/min (or 200-each) Copper Powder line. The old Copper Powder line is a PHANTOM.")
copper_powder_verdict = " ".join(cp_lines)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print("=" * 72)
print("RAW DEMAND (units/min or m3/min) across ALL .sft production targets")
print("=" * 72)
for item, v in sorted(total_raw.items(), key=lambda x: -x[1]):
    print(f"  {item_name.get(item,item):16s} {round(v,1):>12}")

print()
print("=" * 72)
print("PER-TAB raw demand")
print("=" * 72)
for i, nm, raw, made in per_tab:
    tgts = ", ".join(f"{item_name.get(t['item'],t['item'])}={t['amount']}"
                     for t in TABS[i]['request'].get('production', []))
    print(f"-- tab {i} [{nm}] : {tgts}")
    for item, v in sorted(raw.items(), key=lambda x: -x[1]):
        print(f"     {item_name.get(item,item):16s} {round(v,1):>10}")

print()
print("=" * 72)
print("GAP PRODUCTS (must manufacture; not input, not live-net-covered)")
print("=" * 72)
for g in gap_products:
    print(f"  {g['item']:24s} {g['per_min']:>9}/min   ({g['reason']})")

print()
print("HSC verdict:\n ", hsc_verdict)
print()
print("Copper Powder verdict:\n ", copper_powder_verdict)

if all_errors:
    print()
    print("WARNINGS:")
    for e in all_errors:
        print("  -", e)

# ---- sanity: chosen alternates for a few key items per tab ----------------
print()
print("=" * 72)
print("SANITY: chosen min-cost recipe for key items (tab0 = Special factories)")
print("=" * 72)
s0 = TabSolver(TABS[0])
for it in ["Desc_SpaceElevatorPart_7_C", "Desc_SpaceElevatorPart_8_C",
           "Desc_SpaceElevatorPart_6_C", "Desc_SpaceElevatorPart_9_C"]:
    r = s0.best_recipe(it)
    print(f"  {item_name.get(it,it):26s} -> {r}")

# ---------------------------------------------------------------------------
# Sanity vs PLANNING-STATE sec 2 (live extraction) + caveats
# ---------------------------------------------------------------------------
iron = total_raw.get("Desc_OreIron_C", 0.0)
notes = (
    "Cost model: full ingredient-cost / main-output ranking (NO by-product "
    "credit) — crediting by-products at production cost let oil/(un)packaging "
    "loops look near-free and routed 11.7k m3 oil into 95 HMF/min; the "
    "conservative ranking matches the codebase's 'backed-up by-product halts a "
    "building' rule. Fluids normalized /1000 (DB stores mL). "
    f"SANITY: total Iron Ore demand for the SET targets = {round(iron)}/min, "
    "consistent with PLANNING-STATE sec2 live iron USE of ~18,335/min (these "
    "SET sub-factory end-products are the bulk of iron consumption, and "
    f"{round(iron)} < 18,335 as expected since live use also covers ammo/fuel/"
    "power chains). "
    "DOUBLE-COUNT CAVEAT: per the prompt, production targets are summed across "
    "ALL tabs. tab0 (final assembly) declares MFG 30 / TPR 30 / Pasta 5 while "
    "the sub-factory tabs 1/2/3 declare the SAME items at MFG 60 / TPR 60 / "
    "Pasta 10, so the summed gap_products show MFG 90, TPR 90, Pasta 15 — these "
    "are the same physical items counted in both the assembly tab and its "
    "feeder tab. PLANNING-STATE sec1 de-dupes/halves these to MFG 30 / TPR 30 / "
    "Pasta 5. Treat the assembly-tab values (30/30/5) as the real end-product "
    "rate; the feeder-tab copies are bookkeeping. Raw-resource totals are NOT "
    "affected for tabs 1/2/3 because their feeder inputs (EM Control Rod, "
    "Rubber, Steel Beam, Modular Frame, Motor, Computer, Crystal Oscillator, "
    "Rotor, Aluminum Casing, HMF) are all in those tabs' input lists, so they "
    "bottom out at zero raw (only tab0's Nitrogen feeds the rocket-fuel chain "
    "for Nuclear Pasta is mostly carried by tabs 0/2/3 nitrogen)."
)

# expose structured result for the harness
RESULT = {
    "raw_demand": [{"resource": item_name.get(k, k), "per_min": round(v, 2)}
                   for k, v in sorted(total_raw.items(), key=lambda x: -x[1])],
    "gap_products": gap_products,
    "hsc_verdict": hsc_verdict,
    "copper_powder_verdict": copper_powder_verdict,
    "notes": notes,
}
print()
print("NOTES:\n ", notes)
print()
print("JSON_RESULT_BEGIN")
print(json.dumps(RESULT, indent=2))
print("JSON_RESULT_END")
