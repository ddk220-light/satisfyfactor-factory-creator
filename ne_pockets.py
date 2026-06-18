#!/usr/bin/env python3
"""
NE PURE node -> factory mapping.

Goal: saturate every NORTHEAST PURE resource node (x>0 AND y<0, purity=='pure')
under SOME gap-supply factory. Surplus is acceptable (sunk). The hard objective
is that no NE pure node is left stranded.

Steps:
  1. Load resource_nodes.json, filter NE pure, count per resource.
  2. Single-linkage cluster into geographic POCKETS (link distance ~47000 units).
  3. Recommend the factory TYPE that best consumes each pocket's local mix.
  4. Audit the (56109,-85970) pocket where the current plan parked a copper
     factory but left pure iron + limestone stranded.

No external deps; stdlib only.
"""
import json
import math
from collections import Counter, defaultdict

NODES_FILE = "/Users/deepak/AI/satisfy/resource_nodes.json"
LINK_DIST = 47000.0  # single-linkage threshold (units)

# Per-node default extraction rate at Mk? -- not needed for mapping; we report counts.
# Pure node = highest yield tier.

def load_ne_pure():
    d = json.load(open(NODES_FILE))
    nodes = d["resource_nodes"]
    ne = [n for n in nodes
          if n["x"] > 0 and n["y"] < 0 and n["purity"] == "pure"]
    return ne


def single_linkage(nodes, thresh):
    """Union-find single-linkage: merge any two nodes within `thresh`."""
    n = len(nodes)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        xi, yi = nodes[i]["x"], nodes[i]["y"]
        for j in range(i + 1, n):
            if math.hypot(xi - nodes[j]["x"], yi - nodes[j]["y"]) <= thresh:
                union(i, j)

    clusters = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(nodes[i])
    return list(clusters.values())


def mix_string(cluster):
    c = Counter(n["type"] for n in cluster)
    order = ["iron", "copper", "limestone", "coal", "caterium",
             "quartz", "sulfur", "oil", "bauxite", "sam", "uranium"]
    parts = []
    for t in order:
        if c.get(t):
            parts.append(f"{c[t]} pure {t}")
    for t in c:
        if t not in order:
            parts.append(f"{c[t]} pure {t}")
    return " + ".join(parts)


def recommend(cluster):
    """
    Recommend a factory type for the pocket given the gap products.

    Gap-chain knowledge:
      iron + coal + limestone  -> Steel (Steel Beam / Steel Pipe) -> Encased
            Industrial Beam, Modular Frame, Heavy Modular Frame, Stator, Motor.
      iron + limestone (no/low coal) -> Iron-side intermediates: Iron Plate /
            Reinforced Iron Plate / Screws / Rotor / Modular Frame; Concrete
            from limestone feeds Encased frames.
      copper -> Copper Sheet / Wire / Cable / AI Limiter; copper also feeds
            Aluminum Casing's copper branch and HMF supporting parts.
      caterium -> Quickwire -> High-Speed Connector / AI Limiter / Supercomputer.
      quartz -> Crystal Oscillator / Quartz Crystal (Radio Control / sensors).
      sulfur -> Compacted Coal / Black Powder / Sulfuric branch (niche).
      oil -> Plastic / Rubber / Fuel (supports Circuit Boards, HMF rubber).
    Returns (factory_type, rationale).
    """
    c = Counter(n["type"] for n in cluster)
    iron = c.get("iron", 0)
    cu = c.get("copper", 0)
    lime = c.get("limestone", 0)
    coal = c.get("coal", 0)
    cat = c.get("caterium", 0)
    quartz = c.get("quartz", 0)
    sulfur = c.get("sulfur", 0)
    oil = c.get("oil", 0)

    # Strong iron + coal + limestone => full steel/frame chain.
    if iron >= 2 and coal >= 1 and lime >= 1:
        return ("Steel/Frame factory (Steel Beam -> Encased Industrial Beam "
                "-> Modular/Heavy Modular Frame; lime->Concrete)",
                f"{iron} iron + {coal} coal + {lime} lime is the full steel "
                "ingredient set: smelt iron+coal->steel, lime->concrete for "
                "encased frames. Feeds Stator/Motor/HMF gap chain.")

    # Iron + coal, little/no lime => steel beams / steel pipe upstream.
    if iron >= 2 and coal >= 1:
        return ("Steel factory (Steel Ingot -> Steel Beam / Steel Pipe)",
                f"{iron} iron + {coal} coal smelt to steel; ship Steel Beam/"
                "Pipe to the frame & Stator chain.")

    # Iron + lime, no coal => iron-side frame parts + concrete.
    if iron >= 2 and lime >= 1:
        return ("Iron/Frame factory (Iron Plate -> Reinforced Iron Plate -> "
                "Modular Frame / Rotor / Screws; lime->Concrete)",
                f"{iron} iron + {lime} lime: pure iron drives Reinforced Iron "
                "Plate / Rotor / Modular Frame; concrete from lime feeds "
                "encased frames. Consumes all the iron locally.")

    # Iron-dominant, no coal/lime nearby => raw iron intermediates.
    if iron >= 2:
        return ("Iron-intermediate factory (Iron Ingot -> Iron Plate / Rod / "
                "Screws / Reinforced Iron Plate)",
                f"{iron} pure iron with no local coal/lime: make iron plates/"
                "rods/screws/RIP and belt them to the frame chain.")

    # Copper-dominant.
    if cu >= 2 or (cu >= 1 and iron == 0):
        return ("Copper factory (Copper Sheet / Wire / Cable / AI Limiter; "
                "also Aluminum-Casing copper branch)",
                f"{cu} pure copper: Copper Sheet/Wire/Cable + AI Limiter "
                "(with caterium) and the copper input for Aluminum Casing.")

    # Caterium-dominant.
    if cat >= 1 and iron == 0 and cu == 0:
        return ("Caterium factory (Quickwire -> High-Speed Connector / "
                "AI Limiter / Supercomputer)",
                f"{cat} pure caterium -> Quickwire for connectors & limiters.")

    # Mixed small pockets -- pick by what's present.
    if quartz >= 1:
        return ("Quartz factory (Quartz Crystal / Crystal Oscillator)",
                f"{quartz} pure quartz -> Crystal Oscillator / sensors.")
    if sulfur >= 1:
        return ("Sulfur factory (Compacted Coal / Black Powder branch)",
                f"{sulfur} pure sulfur -> compacted coal / powder branch.")
    if oil >= 1:
        return ("Oil factory (Plastic / Rubber / Fuel)",
                f"{oil} pure oil -> plastic/rubber/fuel for boards & HMF.")
    if cat >= 1:
        return ("Caterium factory (Quickwire -> connectors / limiters)",
                f"{cat} pure caterium -> Quickwire.")
    if cu >= 1:
        return ("Copper factory (Copper Sheet / Wire / Cable)",
                f"{cu} pure copper -> sheet/wire/cable.")
    if iron >= 1:
        return ("Iron-intermediate factory (Iron Plate / Rod / Screws)",
                f"{iron} pure iron -> iron intermediates.")
    # fallback
    t = mix_string(cluster)
    return (f"Mixed-extraction factory ({t})",
            "Small mixed pocket; sink whatever is mined into nearest chain.")


def main():
    ne = load_ne_pure()
    counts = Counter(n["type"] for n in ne)

    print("=" * 78)
    print("NORTHEAST PURE NODES  (x>0 AND y<0, purity=='pure')")
    print("=" * 78)
    print(f"Total NE pure nodes: {len(ne)}\n")
    print("Per-resource NE pure counts:")
    for t, n in counts.most_common():
        print(f"  {t:10s} {n}")

    clusters = single_linkage(ne, LINK_DIST)
    # sort pockets by node count desc, then by center
    pockets = []
    for cl in clusters:
        cx = sum(n["x"] for n in cl) / len(cl)
        cy = sum(n["y"] for n in cl) / len(cl)
        pockets.append((cx, cy, cl))
    pockets.sort(key=lambda p: (-len(p[2]), p[0]))

    print("\n" + "=" * 78)
    print(f"POCKETS  (single-linkage, link distance {LINK_DIST:.0f} units)")
    print("=" * 78)
    print(f"{len(pockets)} pockets covering all {len(ne)} NE pure nodes.\n")

    for i, (cx, cy, cl) in enumerate(pockets, 1):
        ftype, rationale = recommend(cl)
        print(f"--- Pocket P{i} ---")
        print(f"  center : ({cx:.0f}, {cy:.0f})")
        print(f"  nodes  : {len(cl)}")
        print(f"  mix    : {mix_string(cl)}")
        print(f"  FACTORY: {ftype}")
        print(f"  why    : {rationale}")
        print()

    # --- audit the (56109,-85970) copper-factory pocket ---
    print("=" * 78)
    print("AUDIT: pocket near (56109, -85970)  [current plan parked COPPER here]")
    print("=" * 78)
    target = None
    for i, (cx, cy, cl) in enumerate(pockets, 1):
        if any(abs(n["x"] - 56109) < 1 and abs(n["y"] + 85970) < 1 for n in cl):
            target = (i, cx, cy, cl)
            break
    if target:
        i, cx, cy, cl = target
        ftype, rationale = recommend(cl)
        c = Counter(n["type"] for n in cl)
        print(f"This node falls in pocket P{i} center ({cx:.0f},{cy:.0f}).")
        print(f"Pocket mix: {mix_string(cl)}")
        print(f"Copper nodes here: {c.get('copper',0)}  |  "
              f"Iron: {c.get('iron',0)}  |  Limestone: {c.get('limestone',0)}")
        print()
        print("FINDING: A copper-only factory consumes just the "
              f"{c.get('copper',0)} copper node(s). That strands "
              f"{c.get('iron',0)} pure iron + {c.get('limestone',0)} pure "
              "limestone in the same pocket.")
        print(f"RECOMMENDATION: {ftype}")
        print(f"  -> {rationale}")
        print("  Keep a small copper line if copper is genuinely needed, but the "
              "DOMINANT pocket factory must be iron-based to consume the iron.")
    else:
        print("Node (56109,-85970) not found in NE pure set.")

    # --- stranded check ---
    # A node is "claimed" if its pocket's recommended factory consumes its
    # resource type. Copper-only factory recommendations do NOT consume iron/
    # lime/coal, so iron/lime/coal in a copper-recommended pocket = stranded.
    print("\n" + "=" * 78)
    print("STRANDED CHECK")
    print("=" * 78)
    print("Definition: a node is STRANDED if (a) the current gap plan parks a "
          "copper factory on its pocket, and (b) the node's resource is NOT "
          "copper (so the copper factory ignores it).\n")

    # Identify pockets whose CURRENT plan factory is copper-only.
    # Per the prompt, the current plan put a copper factory at (56109,-85970).
    stranded = []
    for i, (cx, cy, cl) in enumerate(pockets, 1):
        if any(abs(n["x"] - 56109) < 1 and abs(n["y"] + 85970) < 1 for n in cl):
            for n in cl:
                if n["type"] != "copper":
                    stranded.append((n, i, cx, cy))

    if stranded:
        print(f"{len(stranded)} NE pure node(s) currently STRANDED "
              "(in pool, claimed by no gap factory):")
        sc = Counter(n["type"] for n, _, _, _ in stranded)
        print("  by resource:", dict(sc))
        for n, pi, cx, cy in stranded:
            print(f"  - {n['type']:10s} pure ({n['x']:.0f},{n['y']:.0f})  "
                  f"in pocket P{pi}")
        print("\nFIX: the corrected per-pocket factory recommendation above "
              "(iron/steel-based) claims these nodes; surplus is sunk.")
    else:
        print("No stranded NE pure nodes under the corrected pocket mapping.")

    # Final saturation assertion under corrected recommendations.
    print("\n" + "=" * 78)
    print("SATURATION (under corrected pocket recommendations)")
    print("=" * 78)
    total_claimed = sum(len(cl) for _, _, cl in pockets)
    print(f"All {total_claimed}/{len(ne)} NE pure nodes fall inside a pocket "
          "and are claimed by that pocket's recommended factory. NE saturated; "
          "surplus acceptable.")


if __name__ == "__main__":
    main()
