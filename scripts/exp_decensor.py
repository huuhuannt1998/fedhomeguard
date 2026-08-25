#!/usr/bin/env python3
"""Decensor beta*: the reported 0.40 was the grid maximum, not a breakdown point.

beta_geo(N=20,k=1)=0.450 and beta_geo(k=2)=0.250, both of which sit ON or ABOVE
grid points the coarse sweep never tested. Here the grid runs to 0.50 in steps of
0.025 with exact enumeration, so beta* is observed rather than clipped.
"""
import copy, itertools, json, math, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, certify as C, fl as FL

GRID = [round(0.025*i, 3) for i in range(21)]      # 0.000 .. 0.500
KS, SEEDS, N = [1, 2, 3], [0, 1, 2], 20
base = yaml.safe_load(open("configs/stage3_certification.yaml"))
rows, t0 = [], time.time()

for kind, k, seed in itertools.product(("iid", "device_derived"), KS, SEEDS):
    d = copy.deepcopy(base)
    d["partition"].update(kind=kind, seed=seed, N=N)
    total = math.comb(N, k)
    d["cert"].update(k=k, K=min(total, 600), prefer_exact=True)
    d["betas"] = GRID
    d["name"] = f"dec_{kind}_k{k}_s{seed}"
    cfg = CFG.from_dict(d)
    t = R.prepare(cfg, verbose=False)
    subs, exact, _ = C.choose_subsets(N, k, cfg.cert.K, seed, True)
    votes = np.zeros((len(t["yte_np"]), 2), np.int32)
    for S in subs:
        try:
            pr = FL.predict(FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"]), t["Xte"])
        except ValueError:
            continue
        votes[np.arange(len(pr)), pr] += 1
    cert = C.certify_from_votes(votes, t["yte_np"], N, k, GRID, exact,
                                cfg.cert.confidence, t["tau"])
    g = {x["beta"]: x["CA"] for x in cert["grid"]}
    # highest grid point still above the trivial floor
    bstar = max([b for b in GRID if g[b] > cert["tau_triv"]], default=0.0)
    censored = bstar >= max(GRID)
    rows.append(dict(kind=kind, k=k, seed=seed, exact=exact, K=len(subs),
                     beta_geo=C.beta_geo(N, k), beta_star_fine=bstar,
                     censored=censored, tau=cert["tau_triv"], CA=g))
    print(f"  {kind:15s} k={k} s={seed} exact={exact!s:5s} beta_geo={C.beta_geo(N,k):.3f} "
          f"beta*={bstar:.3f} censored={censored} [{time.time()-t0:.0f}s]", flush=True)
    json.dump(rows, open("results/decensor.json", "w"), indent=2)

import statistics as st
print("\nMEDIAN beta* (fine grid) vs analytic ceiling:")
for kind in ("iid", "device_derived"):
    for k in KS:
        rs=[r for r in rows if r['kind']==kind and r['k']==k]
        if rs: print(f"  {kind:15s} k={k}  beta*={st.median(r['beta_star_fine'] for r in rs):.3f}"
                     f"  beta_geo={rs[0]['beta_geo']:.3f}")
print("DECENSOR DONE")
