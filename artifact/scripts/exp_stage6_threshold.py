#!/usr/bin/env python3
"""Stage 6 -- the honest-region map: beta*(S) at the best subsample size.

The design's flagship object is R_lit \\ R_hon, the region where the literature
asserts robustness and no certificate supports any. R_hon needs beta* as a
function of MEASURED skew, taken at the best k rather than one fixed k (k is a
free parameter of the scheme). Stage 5 measured this at k=5 only, where beta*
compresses to {0.00, 0.05} and carries no resolution.

Fine beta grid (step 0.025), exact enumeration at k<=2, two seeds per skew level.
Two seeds is thin, and deliberately reported per-seed rather than averaged,
because certified accuracy at small k is bimodal.
"""
import copy, itertools, json, math, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, certify as C, fl as FL

GRID = [round(0.025*i, 3) for i in range(21)]
KS, SEEDS, N = [1, 2, 3], [0, 1], 20
# span the skew range with as few partitions as gives a readable curve
# Locate S_0, the threshold where beta* leaves the literature band. The first
# pass left a gap between S_JS 0.36 and 0.70 that the curve crosses beta=0.40
# inside; interpolating across it would assert an unmeasured crossing point.
ARMS = [("dirichlet_device", 0.4), ("dirichlet_device", 0.3),
        ("dirichlet_device", 0.2), ("dirichlet_device", 0.15)]
base = yaml.safe_load(open("configs/stage3_certification.yaml"))
rows, t0 = [], time.time()

for (kind, alpha), seed in itertools.product(ARMS, SEEDS):
    best = None
    for k in KS:
        d = copy.deepcopy(base)
        d["partition"].update(kind=kind, seed=seed, N=N)
        if alpha is not None: d["partition"]["dirichlet_alpha"] = alpha
        d["cert"].update(k=k, K=min(math.comb(N, k), 600), prefer_exact=True)
        d["betas"] = GRID
        d["name"] = f"s6_{kind}_{alpha}_k{k}_s{seed}"
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
        if votes.sum() == 0: continue
        cert = C.certify_from_votes(votes, t["yte_np"], N, k, GRID, exact,
                                    cfg.cert.confidence, t["tau"])
        g = {x["beta"]: x["CA"] for x in cert["grid"]}
        bs = max([b for b in GRID if g[b] > cert["tau_triv"]], default=0.0)
        if best is None or bs > best["beta_star"]:
            best = dict(kind=kind, alpha=alpha, seed=seed, S_JS=t["pmeta"]["S_JS"],
                        S_dev=t["pmeta"]["S_dev"], best_k=k, beta_star=bs,
                        tau=cert["tau_triv"], ens_acc=cert["ensemble_acc"], exact=exact)
    if best:
        rows.append(best)
        print(f"  {kind:18s} a={str(alpha):5s} s={seed} S_JS={best['S_JS']:.4f} "
              f"best_k={best['best_k']} beta*={best['beta_star']:.3f} [{time.time()-t0:.0f}s]",
              flush=True)
        json.dump(rows, open("results/stage6_threshold.json", "w"), indent=2)
print(f"STAGE6 DONE {len(rows)} arms in {time.time()-t0:.0f}s")
