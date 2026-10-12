#!/usr/bin/env python3
"""PB21c (round tmlr6, post hoc; existing rows only, no training): the facts the third mock review asked for.

  python3 pb21_facts.py RESULTS_DIR OUT_JSON

- prior: the 1% re-weighting's denominator (non-void cells of the 0.05-step grid at k <= 2), its best cell, and the
  IID ensemble with no adversary re-weighted to 1% (pb06_prior.json, itself post hoc);
- pb17: per-member standardization against the pooled control on the same 10 draws: device-derived median beta*
  and collapse at beta = 0 and 0.20 (pb17_18_rows.jsonl);
- repair: device types per household of the coverage repair (pb04_rows.jsonl) and of the main 1-3-type grid at the
  same seeds (the constructor's random draws, which do not depend on the data);
- dedup: the deduplicated subset over the 30 draws of Table 1 (pb07a_dedup.json);
- ties: the strict rule's only p_clean = 1/2 case behind Appendix A's non-monotonicity example.
"""
import json, math, os, statistics as st, sys
from fractions import Fraction
import numpy as np

RES, OUT = sys.argv[1], sys.argv[2]
TAU = 0.7299609726808766
out = {}

p6 = json.load(open(os.path.join(RES, "pb06_prior.json")))["e5f (30 draws)"]["cells"]
nv = [k for k, v in p6.items() if not v["void"] and ("|k1|" in k or "|k2|" in k)]
best = max(nv, key=lambda k: p6[k]["CA_pi0.01"]["median"])
out["prior"] = dict(nonvoid_cells_k_le_2=len(nv), beat_floor=sum(bool(p6[k]["beats_floor_pi0.01"]) for k in nv),
                    best_cell=best, best_value=p6[best]["CA_pi0.01"]["median"],
                    iid_k1_b0=dict(CTR_ben=p6["iid|k1|b0"]["CTR_ben"]["median"],
                                   CTR_mal=p6["iid|k1|b0"]["CTR_mal"]["median"],
                                   CA_pi001=p6["iid|k1|b0"]["CA_pi0.01"]["median"]),
                    device_k1_b02_CTR_ben=p6["device_derived|k1|b0.2"]["CTR_ben"]["median"])

rows = [json.loads(l) for l in open(os.path.join(RES, "pb17_18_rows.jsonl"))]
rows = [r for r in rows if r["pb"] == 17]
def ca(r, b):
    return next(c["CA"] for c in r["grid"] if abs(c["beta"] - b) < 1e-9)
p17 = {}
for part in ("device_derived", "iid", "dirichlet"):
    for k in (1, 2):
        for v in ("P", "M", "Rf"):
            rs = [r for r in rows if r["partition"] == part and r["k"] == k and r["variant"] == v]
            p17[f"{part}|k{k}|{v}"] = dict(draws=len(rs), seeds=sorted(r["seed"] for r in rs),
                                           median_bstar=st.median(r["beta_star"] for r in rs),
                                           median_CA_b0=st.median(ca(r, 0.0) for r in rs),
                                           collapse_b0=sum(ca(r, 0.0) <= TAU + 1e-12 for r in rs),
                                           collapse_b02=sum(ca(r, 0.2) <= TAU + 1e-12 for r in rs))
out["pb17"] = p17

def base_types(seed, N=20, lo=1, hi=3, ndev=10):
    """Types per household of device_derived_partition (src/fedhomeguard/partition.py) at this seed."""
    rng = np.random.default_rng(seed); devs = list(range(ndev)); owners = {d: [] for d in devs}; n = [0] * N
    for i in range(N):
        nd = int(rng.integers(lo, hi + 1))
        for d in rng.choice(devs, size=min(nd, ndev), replace=False):
            owners[int(d)].append(i); n[i] += 1
    for d in devs:
        if not owners[d]:
            i = int(rng.integers(0, N)); owners[d].append(i); n[i] += 1
    return st.mean(n)
p4 = [json.loads(l) for l in open(os.path.join(RES, "pb04_rows.jsonl"))]
rep = [r for r in p4 if r["arm"] == "a" and r["k"] == 1]
out["repair"] = dict(draws=len(rep), seeds=sorted(r["seed"] for r in rep),
                     mean_types_repair=st.mean(st.mean(r["info"]["types_per_household"]) for r in rep),
                     mean_types_main_grid=st.mean(base_types(s) for s in sorted(r["seed"] for r in rep)),
                     collapse_b02=sum(ca(r, 0.2) <= TAU + 1e-12 for r in rep),
                     median_bstar=st.median(r["beta_star"] for r in rep))

dd = json.load(open(os.path.join(RES, "pb07a_dedup.json")))
ens = [e for e in dd["ensembles"] if e["k"] == 1 and 10 <= e["seed"] <= 39]
def coll(e):
    return next(g["collapsed_dedup"] for g in e["grid"] if abs(g["beta"] - 0.2) < 1e-9)
out["dedup_30"] = {kind: dict(draws=len([e for e in ens if e["kind"] == kind]),
                              median_bstar=st.median(e["beta_star_dedup"] for e in ens if e["kind"] == kind),
                              collapse_b02=sum(coll(e) for e in ens if e["kind"] == kind))
                   for kind in ("iid", "device_derived")}

pc = Fraction(math.comb(15, 2), math.comb(21, 2))
out["tie_example"] = dict(N=21, k=2, m=6, p_clean=str(pc), C15_2=math.comb(15, 2), C21_2=math.comb(21, 2),
                          strict_beta_geo=5 / 21, tie_aware_benign=6 / 21)
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps(out, indent=1)[:4000])
