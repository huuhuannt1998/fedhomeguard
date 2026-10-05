#!/usr/bin/env python3
"""k-sweep across partition seeds.

M1's probe reported device-derived k=1 ensemble accuracy 0.2700, but a single
re-run with a different partition seed gave certified accuracy 0.8323 at beta=0.10.
Small k means each ensemble member trains on ONE household, so the result depends
heavily on WHICH households the draw produced. Multiple seeds are therefore not
optional here -- a single draw cannot support the claim either way.
"""
import copy, itertools, json, os, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, certify as C, fl as FL, partition as P

KS = [1, 2, 3, 5, 8]
SEEDS = [0, 1, 2]
KINDS = ["device_derived", "iid"]
OUT = "results/ksweep_seeds.json"

base = yaml.safe_load(open("configs/stage3_certification.yaml"))
rows = []
t_start = time.time()
for kind, k, seed in itertools.product(KINDS, KS, SEEDS):
    d = copy.deepcopy(base)
    d["partition"]["kind"] = kind
    d["partition"]["seed"] = seed
    d["cert"]["k"] = k
    d["cert"]["K"] = 100
    d["name"] = f"{kind}_k{k}_s{seed}"
    cfg = CFG.from_dict(d)
    t = R.prepare(cfg, verbose=False)
    subs, exact, total = C.choose_subsets(cfg.partition.N, k, cfg.cert.K,
                                          seed, cfg.cert.prefer_exact)
    votes = np.zeros((len(t["yte_np"]), 2), np.int32)
    t0 = time.time()
    for S in subs:
        pred = FL.predict(FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"]), t["Xte"])
        votes[np.arange(len(pred)), pred] += 1
    cert = C.certify_from_votes(votes, t["yte_np"], cfg.partition.N, k,
                                cfg.betas, exact, cfg.cert.confidence, t["tau"])
    g = {x["beta"]: x["CA"] for x in cert["grid"]}
    row = dict(kind=kind, k=k, seed=seed, S_JS=t["pmeta"]["S_JS"], S_dev=t["pmeta"]["S_dev"],
               size_min=t["pmeta"]["size_min"], beta_geo=cert["beta_geo"],
               ensemble_acc=cert["ensemble_acc"], mean_margin=cert["mean_margin"],
               MC_het=cert["MC_het"], beta_star=cert["beta_star"], tau_triv=cert["tau_triv"],
               exact=exact, K=len(subs), CA=g, secs=round(time.time() - t0, 1))
    rows.append(row)
    print(f"{kind:15s} k={k} s={seed} S_JS={row['S_JS']:.4f} ens={row['ensemble_acc']:.4f} "
          f"margin={row['mean_margin']:.4f} beta*={row['beta_star']:.2f} "
          f"CA(.10)={g[0.10]:.4f} CA(.20)={g[0.20]:.4f} [{row['secs']}s]", flush=True)
    json.dump(dict(rows=rows, tau_triv=rows[0]["tau_triv"]), open(OUT, "w"), indent=2)
print(f"\nDONE in {time.time()-t_start:.0f}s -> {OUT}")
