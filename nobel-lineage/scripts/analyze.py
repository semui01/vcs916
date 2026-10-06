"""Build the Nobel-visible lineage graph and compute the Step 6 statistics.

Usage:  python3 -I scripts/analyze.py      (from nobel-lineage/)
Writes: output/results.json, output/nodes.csv, output/edges.csv, output/lineages.csv
"""
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from prizes import PRIZES, EXTERNAL, NOT_AWARDED, FIELD_LABELS  # noqa: E402
from edges import EDGES  # noqa: E402

OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

W = {"H": 1.0, "M": 0.5, "L": 0.1}
EVIDENCE = {"H": "documented", "M": "strong inference", "L": "speculative"}
TYPE = {"TF": "theoretical foundation", "EC": "experimental confirmation",
        "IT": "instrumental/technological foundation", "AE": "new application or extension",
        "DF": "direct discovery follow-up", "PD": "independent parallel development"}

# ------------------------------------------------------------------ load
nodes = {}
for nid, year, laur, mot, field, kind, wy in PRIZES:
    nodes[nid] = dict(id=nid, year=year, laureates=laur, motivation=mot, field=field,
                      kind=kind, work_year=wy, nobel=True)
for nid, year, laur, mot, field, kind, wy in EXTERNAL:
    nodes[nid] = dict(id=nid, year=None, laureates=laur, motivation=mot, field=field,
                      kind=kind, work_year=wy, nobel=False)

# A "citation" is one Nobel prize citation. Split citations (2003a/b, 2016a/b) count once.
for n in nodes.values():
    if n["nobel"]:
        nid = n["id"]
        n["citation"] = nid[:4] if nid[:4] in ("2003", "2016") else nid

edges = []
seen = set()
for s, t, typ, conf, scope, claim, srcs, ver in EDGES:
    assert s in nodes, f"unknown source {s}"
    assert t in nodes, f"unknown target {t}"
    assert typ in TYPE and conf in W, (s, t)
    assert (s, t) not in seen, f"duplicate edge {s}->{t}"
    seen.add((s, t))
    edges.append(dict(source=s, target=t, type=typ, type_label=TYPE[typ], confidence=conf,
                      evidence_class=EVIDENCE[conf], scope=scope, claim=claim, sources=srcs,
                      verified_in_session=ver,
                      work_gap=nodes[t]["work_year"] - nodes[s]["work_year"],
                      award_gap=(nodes[t]["year"] - nodes[s]["year"]) if nodes[s]["nobel"] else None))

# Directed edges must not run backwards in time of the recognised work.
bad = [e for e in edges if e["type"] != "PD" and e["work_gap"] < 0]
assert not bad, "edges run backwards in work time: " + str([(e["source"], e["target"]) for e in bad])


def graph(min_conf="M", nobel_only=True, direct_only=False):
    ok = {"H": ["H"], "M": ["H", "M"], "L": ["H", "M", "L"]}[min_conf]
    g = defaultdict(list)
    for e in edges:
        if e["type"] == "PD" or e["confidence"] not in ok:
            continue
        if direct_only and e["scope"] != "direct":
            continue
        if nobel_only and not (nodes[e["source"]]["nobel"] and nodes[e["target"]]["nobel"]):
            continue
        g[e["source"]].append(e)
    return g


def topo(g):
    indeg = defaultdict(int)
    vs = set(g)
    for s in g:
        for e in g[s]:
            indeg[e["target"]] += 1
            vs.add(e["target"])
    order, stack = [], sorted(v for v in vs if indeg[v] == 0)
    while stack:
        v = stack.pop()
        order.append(v)
        for e in g.get(v, []):
            indeg[e["target"]] -= 1
            if indeg[e["target"]] == 0:
                stack.append(e["target"])
    assert len(order) == len(vs), "cycle in graph"
    return order


def longest_paths(g, k=5):
    """Longest paths by node count; ties broken by evidence score. Returns top k distinct ends."""
    order = topo(g)
    best = {v: (1, 0.0, [v]) for v in order}
    for v in order:
        for e in g.get(v, []):
            t = e["target"]
            cand = (best[v][0] + 1, best[v][1] + W[e["confidence"]], best[v][2] + [t])
            if cand[:2] > best[t][:2]:
                best[t] = cand
    ranked = sorted(best.values(), key=lambda x: (-x[0], -x[1]))
    out, used = [], set()
    for n, sc, p in ranked:
        key = tuple(p[-2:])
        if key in used:
            continue
        used.add(key)
        out.append(dict(nodes=p, generations=n, score=round(sc, 2)))
        if len(out) == k:
            break
    return out


def edge_between(a, b):
    for e in edges:
        if e["source"] == a and e["target"] == b:
            return e
    return None


def path_stats(path):
    ns = [nodes[p] for p in path]
    links = [edge_between(a, b) for a, b in zip(path, path[1:])]
    assert all(links), f"missing link in {path}"
    nobel_ns = [n for n in ns if n["nobel"]]
    cites = []
    for n in nobel_ns:
        if n["citation"] not in cites:
            cites.append(n["citation"])
    return dict(
        nodes=path,
        generations=len(nobel_ns),
        links=[(l["source"], l["target"], l["type"], l["confidence"]) for l in links],
        score=round(sum(W[l["confidence"]] for l in links), 2),
        weakest_link=min((l["confidence"] for l in links), key=lambda c: W[c]),
        first_work=min(n["work_year"] for n in ns),
        last_work=max(n["work_year"] for n in ns),
        first_award=min(n["year"] for n in nobel_ns),
        last_award=max(n["year"] for n in nobel_ns),
        work_span=max(n["work_year"] for n in ns) - min(n["work_year"] for n in ns),
        award_span=max(n["year"] for n in nobel_ns) - min(n["year"] for n in nobel_ns),
        intermediate_prizes=max(0, len(cites) - 2),
        laureates=sorted({x for n in nobel_ns for x in n["laureates"]}),
        award_inversions=sum(1 for l in links if l["award_gap"] is not None and l["award_gap"] < 0),
        work_gaps=[l["work_gap"] for l in links],
        award_gaps=[l["award_gap"] for l in links if l["award_gap"] is not None],
        mean_work_gap=round(st.mean(l["work_gap"] for l in links), 1),
        mean_award_gap=round(st.mean(l["award_gap"] for l in links if l["award_gap"] is not None), 1),
    )


# ------------------------------------------------------------------ named lineages
# Each lineage is a node set chosen by subject; its spine is the highest-evidence
# path inside that set (computed, not hand-picked).
LINEAGES = [
    ("sc-circuits", "Superconductivity to quantum circuits",
     ["1910", "1913", "1972", "1973a", "1973b", "1996", "2003a", "2003b", "1962", "1978a", "2025"]),
    ("sym-break", "Superconductivity to the Higgs mechanism and electroweak unification",
     ["1913", "1972", "2008a", "X-Anderson1963", "2013", "1979", "1999", "1984", "1988", "1992", "1976"]),
    ("lasers", "Molecular beams to lasers, cold atoms and attosecond pulses",
     ["1943", "1944", "1964", "1966", "2018a", "1997", "2001", "1981a", "2005b", "2018b", "2023", "1989a", "1989b", "2012", "2005a"]),
    ("strong", "Track chambers to quarks and asymptotic freedom",
     ["1927b", "1960", "1968", "1969", "1961a", "1990", "1999", "2004"]),
    ("quantum", "Heat radiation to the quantum and its confirmations",
     ["1911", "1918", "1921", "1905", "1906", "1923", "1922", "1925", "1932", "1927a", "1930", "1915"]),
    ("antimatter", "Matter waves to antimatter",
     ["1929", "1933", "1936a", "1927b", "1936b", "1948", "1958", "1939", "1959", "1949", "1950", "1954a", "1937"]),
    ("radioactivity", "X-rays to radioactivity, the neutron and neutron scattering",
     ["1901", "1903a", "1903b", "1935", "1938", "1994", "1970b"]),
    ("xray", "X-ray diffraction and spectroscopy",
     ["1901", "1914", "1915", "1917", "1924", "1927a", "1937", "1994"]),
    ("qed", "Magnetic resonance to quantum electrodynamics",
     ["1943", "1944", "1933", "1952", "1955", "1965", "1979"]),
    ("neutrino", "Neutrinos: detection to neutrino astronomy",
     ["X-Pauli1930", "X-Fermi1934", "1938", "1995b", "1950", "1988", "1967", "1958", "2002a", "1995a", "2015", "1936a", "2026"]),
    ("qhe", "Transistor to quantum Hall effects and topology",
     ["1956", "2000a", "1985", "1998", "2016b", "2010"]),
    ("semis", "Transistor to heterostructures, LEDs and fibre optics",
     ["1956", "2000a", "2000b", "2014", "1964", "2009a", "1973a"]),
    ("gw", "Pulsars to gravitational waves",
     ["1907", "1964", "1974b", "1993", "2020a", "2017"]),
    ("cmb", "Blackbody radiation to the cosmic microwave background",
     ["1911", "1918", "1964", "1978b", "2019a", "2006"]),
    ("supernova", "Exclusion principle to the accelerating universe",
     ["1945", "1983a", "2009b", "2019a", "2011"]),
    ("cp", "Symmetry principles to CP violation and three quark families",
     ["1963a", "1957", "1980", "2008b"]),
    ("disorder", "Disordered magnets to neural networks",
     ["1977", "2021b", "2024"]),
]


def best_path_in(subset, include_external=False):
    sub = set(subset)
    g = defaultdict(list)
    for e in edges:
        if e["type"] == "PD" or e["confidence"] == "L":
            continue
        if e["source"] in sub and e["target"] in sub:
            if not include_external and not (nodes[e["source"]]["nobel"] and nodes[e["target"]]["nobel"]):
                continue
            g[e["source"]].append(e)
    order = topo(g) if g else []
    best = {v: (0.0, 1, [v]) for v in order}
    for v in order:
        for e in g.get(v, []):
            t = e["target"]
            cand = (best[v][0] + W[e["confidence"]], best[v][1] + 1, best[v][2] + [t])
            if cand[:2] > best[t][:2]:
                best[t] = cand
    return max(best.values(), key=lambda x: (x[0], x[1]))[2] if best else []


lineage_rows = []
for lid, name, members in LINEAGES:
    spine = best_path_in(members)
    ps = path_stats(spine)
    member_edges = [e for e in edges if e["source"] in members and e["target"] in members]
    nobel_members = [m for m in members if nodes[m]["nobel"]]
    lineage_rows.append(dict(
        id=lid, name=name, members=members, spine=ps,
        member_prizes=len({nodes[m]["citation"] for m in nobel_members}),
        member_laureates=len({x for m in nobel_members for x in nodes[m]["laureates"]}),
        member_edges=len(member_edges),
        member_edges_by_conf={c: sum(1 for e in member_edges if e["confidence"] == c) for c in "HML"},
        earliest_work=min(nodes[m]["work_year"] for m in members),
        latest_award=max(nodes[m]["year"] for m in nobel_members),
    ))
lineage_rows.sort(key=lambda r: (-r["spine"]["score"], -r["spine"]["generations"], -r["spine"]["work_span"]))
for i, r in enumerate(lineage_rows, 1):
    r["rank"] = i

# ------------------------------------------------------------------ statistics
gM = graph("M")
gH = graph("H")
gMd = graph("M", direct_only=True)
directed_M = [e for s in gM for e in gM[s]]


def summary(xs):
    xs = list(xs)
    return dict(n=len(xs), mean=round(st.mean(xs), 1), median=st.median(xs), min=min(xs), max=max(xs)) if xs else None


timing = dict(
    work_gap_all=summary(e["work_gap"] for e in directed_M),
    award_gap_all=summary(e["award_gap"] for e in directed_M),
    award_inversions=[(e["source"], e["target"], e["award_gap"]) for e in directed_M if e["award_gap"] < 0],
    theory_to_experiment=summary(e["work_gap"] for e in directed_M
                                 if nodes[e["source"]]["kind"] == "T" and nodes[e["target"]]["kind"] == "E"
                                 and e["type"] in ("TF", "EC")),
    theory_to_experiment_edges=[(e["source"], e["target"], e["work_gap"]) for e in directed_M
                                if nodes[e["source"]]["kind"] == "T" and nodes[e["target"]]["kind"] == "E"
                                and e["type"] in ("TF", "EC")],
    experiment_to_theory=summary(e["work_gap"] for e in directed_M
                                 if nodes[e["source"]]["kind"] == "E" and nodes[e["target"]]["kind"] == "T"),
    experiment_to_theory_edges=[(e["source"], e["target"], e["work_gap"]) for e in directed_M
                                if nodes[e["source"]]["kind"] == "E" and nodes[e["target"]]["kind"] == "T"],
    technology_to_discovery=summary(e["work_gap"] for e in directed_M
                                    if e["type"] == "IT" and nodes[e["source"]]["kind"] == "I"
                                    and nodes[e["target"]]["kind"] == "E"),
    technology_to_discovery_edges=[(e["source"], e["target"], e["work_gap"]) for e in directed_M
                                   if e["type"] == "IT" and nodes[e["source"]]["kind"] == "I"
                                   and nodes[e["target"]]["kind"] == "E"],
    recognition_lag_by_kind={k: summary(n["year"] - n["work_year"] for n in nodes.values()
                                        if n["nobel"] and n["kind"] == k) for k in "TEI"},
    recognition_lag_by_decade={f"{d}s": summary(n["year"] - n["work_year"] for n in nodes.values()
                                                if n["nobel"] and d <= n["year"] < d + 25)
                               for d in (1901, 1926, 1951, 1976, 2001)},
)

# ancestors (transitive, M+, Nobel-only)
rev = defaultdict(list)
for e in directed_M:
    rev[e["target"]].append(e["source"])
revH = defaultdict(list)
for e in (e for s_ in gH for e in gH[s_]):
    revH[e["target"]].append(e["source"])


def ancestors(v, rev=rev):
    seen, stack = set(), [v]
    while stack:
        for u in rev[stack.pop()]:
            if u not in seen:
                seen.add(u)
                stack.append(u)
    return seen


anc_rows = []
for v, n in nodes.items():
    if not n["nobel"]:
        continue
    a = ancestors(v)
    direct = set(rev[v])
    anc_rows.append(dict(id=v, year=n["year"], direct_parents=len(direct),
                         direct_parent_laureates=len({x for u in direct for x in nodes[u]["laureates"]}),
                         ancestor_prizes=len({nodes[u]["citation"] for u in a}),
                         ancestor_laureates=len({x for u in a for x in nodes[u]["laureates"]}),
                         ancestor_laureates_H=len({x for u in ancestors(v, revH) for x in nodes[u]["laureates"]}),
                         earliest_ancestor_work=min((nodes[u]["work_year"] for u in a), default=None)))
anc_rows.sort(key=lambda r: (-r["ancestor_laureates"], -r["ancestor_prizes"]))

# field density
field_nodes = defaultdict(list)
for n in nodes.values():
    if n["nobel"]:
        field_nodes[n["field"]].append(n["id"])
pairs_M = {frozenset((e["source"], e["target"])) for e in directed_M}
field_rows = []
for f, ids in field_nodes.items():
    s = set(ids)
    internal = sum(1 for p in pairs_M if p <= s)
    touching = sum(1 for p in pairs_M if p & s)
    connected = sum(1 for i in ids if any(i in p for p in pairs_M))
    nn = len(ids)
    field_rows.append(dict(field=f, label=FIELD_LABELS[f], prizes=len({nodes[i]["citation"] for i in ids}),
                           nodes=nn, internal_links=internal, all_links=touching,
                           density=round(internal / (nn * (nn - 1) / 2), 3) if nn > 1 else 0,
                           links_per_prize=round(touching / nn, 2),
                           connected_share=round(connected / nn, 2)))
field_rows.sort(key=lambda r: -r["links_per_prize"])

cross = defaultdict(int)
for e in directed_M:
    a, b = nodes[e["source"]]["field"], nodes[e["target"]]["field"]
    if a != b:
        cross[f"{a} -> {b}"] += 1

nobel_ids = [v for v in nodes if nodes[v]["nobel"]]
any_edge = {e["source"] for e in edges} | {e["target"] for e in edges}
isolated = [v for v in nobel_ids if v not in any_edge]

counts = dict(
    prize_years=len({nodes[v]["year"] for v in nobel_ids}),
    citations=len({nodes[v]["citation"] for v in nobel_ids}),
    nodes=len(nobel_ids),
    laureate_names=len({x for v in nobel_ids for x in nodes[v]["laureates"]}),
    laureate_awards=sum(len({x for v in nobel_ids if nodes[v]["year"] == y for x in nodes[v]["laureates"]})
                        for y in {nodes[v]["year"] for v in nobel_ids}),
    years_not_awarded=NOT_AWARDED,
    edges_total=len(edges),
    edges_by_conf={c: sum(1 for e in edges if e["confidence"] == c) for c in "HML"},
    edges_by_type={t: sum(1 for e in edges if e["type"] == t) for t in TYPE},
    edges_verified_in_session=sum(1 for e in edges if e["verified_in_session"]),
    edges_with_external_endpoint=sum(1 for e in edges if not (nodes[e["source"]]["nobel"] and nodes[e["target"]]["nobel"])),
    isolated_nodes=isolated,
    connected_share=round(1 - len(isolated) / len(nobel_ids), 3),
)

results = dict(
    counts=counts,
    longest_paths_H=[{**path_stats(p["nodes"])} for p in longest_paths(gH, 5)],
    longest_paths_M=[{**path_stats(p["nodes"])} for p in longest_paths(gM, 5)],
    longest_paths_M_direct=[{**path_stats(p["nodes"])} for p in longest_paths(gMd, 5)],
    lineages=lineage_rows,
    timing=timing,
    most_ancestors=anc_rows[:12],
    most_direct_parents=sorted(anc_rows, key=lambda r: (-r["direct_parents"], -r["direct_parent_laureates"]))[:8],
    fields=field_rows,
    cross_field=dict(sorted(cross.items(), key=lambda kv: -kv[1])),
    nodes=list(nodes.values()),
    edges=edges,
    field_labels=FIELD_LABELS,
)
(OUT / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))

with open(OUT / "nodes.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "award_year", "nobel_cited", "laureates", "motivation", "field", "kind", "work_year",
                "scientific_background_or_speech", "prize_page"])
    for n in nodes.values():
        y = n["year"]
        doc = "" if not y else (f"https://www.nobelprize.org/prizes/physics/{y}/advanced-information/" if y >= 1995
                                else f"https://www.nobelprize.org/prizes/physics/{y}/ceremony-speech/")
        w.writerow([n["id"], y or "", n["nobel"], "; ".join(n["laureates"]), n["motivation"], n["field"],
                    n["kind"], n["work_year"], doc,
                    f"https://www.nobelprize.org/prizes/physics/{y}/summary/" if y else ""])
with open(OUT / "edges.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["source", "target", "source_award", "target_award", "source_laureates", "target_laureates",
                "relationship", "confidence", "evidence_class", "scope", "work_gap_years", "award_gap_years",
                "claim", "sources", "verified_in_session"])
    for e in edges:
        s, t = nodes[e["source"]], nodes[e["target"]]
        w.writerow([e["source"], e["target"], s["year"] or "not cited", t["year"] or "not cited",
                    "; ".join(s["laureates"]), "; ".join(t["laureates"]), e["type_label"], e["confidence"],
                    e["evidence_class"], e["scope"], e["work_gap"], e["award_gap"] if e["award_gap"] is not None else "",
                    e["claim"], " | ".join(e["sources"]), e["verified_in_session"]])
with open(OUT / "lineages.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["rank", "lineage", "spine", "generations", "score", "weakest_link", "first_work", "last_work",
                "work_span", "first_award", "last_award", "award_span", "intermediate_prizes", "award_inversions",
                "member_prizes", "member_laureates", "member_links"])
    for r in lineage_rows:
        s = r["spine"]
        w.writerow([r["rank"], r["name"], " -> ".join(s["nodes"]), s["generations"], s["score"], s["weakest_link"],
                    s["first_work"], s["last_work"], s["work_span"], s["first_award"], s["last_award"],
                    s["award_span"], s["intermediate_prizes"], s["award_inversions"], r["member_prizes"],
                    r["member_laureates"], r["member_edges"]])

# ------------------------------------------------------------------ console summary
print(json.dumps(dict(counts=counts), indent=1, ensure_ascii=False))
print("\nLineages (ranked):")
for r in lineage_rows:
    s = r["spine"]
    print(f"{r['rank']:>2}. {r['name']}: {' -> '.join(s['nodes'])} | gen {s['generations']} score {s['score']} "
          f"weakest {s['weakest_link']} | work {s['first_work']}-{s['last_work']} ({s['work_span']}y) "
          f"awards {s['first_award']}-{s['last_award']} ({s['award_span']}y) inv {s['award_inversions']}")
print("\nLongest H-only paths:")
for p in results["longest_paths_H"]:
    print(" ", " -> ".join(p["nodes"]), p["generations"], p["score"], p["work_span"], p["award_span"])
print("Longest M+ paths:")
for p in results["longest_paths_M"]:
    print(" ", " -> ".join(p["nodes"]), p["generations"], p["score"], p["work_span"], p["award_span"])
print("Longest M+ direct-only paths:")
for p in results["longest_paths_M_direct"]:
    print(" ", " -> ".join(p["nodes"]), p["generations"], p["score"], p["work_span"], p["award_span"])
print("\nTiming:", json.dumps({k: v for k, v in timing.items() if not k.endswith("edges")}, indent=1))
print("\nMost ancestors:", *[f"{r['id']}: {r['ancestor_laureates']} laureates / {r['ancestor_prizes']} prizes, "
                             f"H-only {r['ancestor_laureates_H']}, direct {r['direct_parents']} ({r['direct_parent_laureates']} laureates)" for r in anc_rows[:8]], sep="\n ")
print("\nFields:", *[f"{r['label']}: n={r['nodes']} links/prize={r['links_per_prize']} density={r['density']} "
                     f"connected={r['connected_share']}" for r in field_rows], sep="\n ")
print("\nCross-field:", dict(list(cross.items())[:12]))
print("\nIsolated:", isolated)
print("Most H-ancestors:", sorted(((r["ancestor_laureates_H"], r["id"]) for r in anc_rows), reverse=True)[:6])
print("Most direct parents:", [(r["id"], r["direct_parents"], r["direct_parent_laureates"]) for r in results["most_direct_parents"]])
