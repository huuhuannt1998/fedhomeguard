#!/usr/bin/env python3
"""A5 (N sweep) + A4 (exact enumeration), run together.

A5 asks how p_clean geometry drives beta*; C2 claims the ceiling is independent
of N, and every experiment so far used N=20 only. A4 asks whether the results are
a Monte-Carlo artifact; exact enumeration removes the Clopper-Pearson penalty
entirely, so where C(N,k) is affordable we enumerate rather than sample.
"""
import copy, itertools, json, math, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, certify as C, fl as FL

NS, KS, SEEDS = [10, 12, 16, 20], [1, 2, 3], [0, 1, 2]
KINDS = ["device_derived", "iid"]
EXACT_CAP = 600                      # enumerate below this, sample above
base = yaml.safe_load(open("configs/stage3_certification.yaml"))
rows, t0 = [], time.time()

for N, kind, k, seed in itertools.product(NS, KINDS, KS, SEEDS):
    if k >= N: continue
    d = copy.deepcopy(base)
    d["partition"].update(kind=kind, seed=seed, N=N)
    total = math.comb(N, k)
    d["cert"].update(k=k, K=min(total, EXACT_CAP), prefer_exact=True)
    d["name"] = f"N{N}_{kind}_k{k}_s{seed}"
    cfg = CFG.from_dict(d)
    try:
        t = R.prepare(cfg, verbose=False)
    except Exception as e:
        print(f"  SKIP N={N} {kind} k={k} s={seed}: {type(e).__name__}", flush=True); continue
    subs, exact, _ = C.choose_subsets(N, k, cfg.cert.K, seed, True)
    votes = np.zeros((len(t["yte_np"]), 2), np.int32)
    skipped = 0
    for S in subs:
        try:
            pr = FL.predict(FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"]), t["Xte"])
        except ValueError:
            skipped += 1; continue
        votes[np.arange(len(pr)), pr] += 1
    if votes.sum() == 0:
        print(f"  SKIP N={N} {kind} k={k} s={seed}: no trainable subset", flush=True); continue
    cert = C.certify_from_votes(votes, t["yte_np"], N, k, cfg.betas,
                                exact and skipped == 0, cfg.cert.confidence, t["tau"])
    g = {x["beta"]: x["CA"] for x in cert["grid"]}
    rows.append(dict(N=N, kind=kind, k=k, seed=seed, exact=bool(exact and skipped == 0),
                     K=len(subs) - skipped, total_subsets=total, skipped=skipped,
                     beta_geo=C.beta_geo(N, k), beta_geo_asym=C.beta_geo_asymptotic(k),
                     beta_star=cert["beta_star"], ens_acc=cert["ensemble_acc"],
                     margin=cert["mean_margin"], tau=cert["tau_triv"],
                     S_JS=t["pmeta"]["S_JS"], CA=g))
    print(f"  N={N:2d} {kind:15s} k={k} s={seed} exact={rows[-1]['exact']!s:5s} "
          f"K={rows[-1]['K']:4d} beta_geo={rows[-1]['beta_geo']:.3f} "
          f"beta*={cert['beta_star']:.2f} acc={cert['ensemble_acc']:.4f} "
          f"[{time.time()-t0:.0f}s]", flush=True)
    json.dump(rows, open("results/a5_a4_nsweep.json", "w"), indent=2)
print(f"A5/A4 DONE {len(rows)} rows in {time.time()-t0:.0f}s")
