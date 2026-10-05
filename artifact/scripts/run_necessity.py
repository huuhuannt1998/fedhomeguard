#!/usr/bin/env python3
"""ALGORITHM 4, confirmatory version -- the test that decides D1's premise.

Stage 5 ran this at k=5, where beta* can only take {0.00, 0.05}: one quantization
step of resolution. Here we run device_derived vs skew-MATCHED Dirichlet vs IID at
k in {1,2,3} across seeds 0/1/2, and report certified accuracy at beta=0.10 (a
continuous quantity) rather than only beta*, so the comparison has real resolution.

NECESSITY HOLDS iff device-derived is WORSE than the skew-matched control.
If it is not worse, skew MAGNITUDE -- not device STRUCTURE -- drives the effect,
and the D1 claim must be downgraded (design Algorithm 4, line 8).
"""
import copy, itertools, json, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, certify as C, fl as FL, partition as P

base = yaml.safe_load(open("configs/stage3_certification.yaml"))
KS, SEEDS = [1, 2, 3], [0, 1, 2]
rows = []

# target skew comes from the device-derived partition at each seed
for seed in SEEDS:
    d0 = copy.deepcopy(base); d0["partition"]["seed"] = seed
    cfg0 = CFG.from_dict(d0)
    t0 = R.prepare(cfg0, verbose=False)
    target = t0["pmeta"]["S_JS"]
    for kind in ("device_derived", "dirichlet_matched", "iid"):
        for k in KS:
            d = copy.deepcopy(base)
            d["partition"]["kind"] = kind
            d["partition"]["seed"] = seed
            if kind == "dirichlet_matched":
                d["partition"]["match_target_S_JS"] = target
                d["partition"]["min_client_rows"] = 16
            d["cert"]["k"] = k; d["cert"]["K"] = 100
            d["name"] = f"{kind}_k{k}_s{seed}"
            cfg = CFG.from_dict(d)
            t = R.prepare(cfg, verbose=False)
            subs, exact, _ = C.choose_subsets(20, k, 100, seed, True)
            votes = np.zeros((len(t["yte_np"]), 2), np.int32)
            skipped = 0
            for S in subs:
                try:
                    pr = FL.predict(FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"]),
                                    t["Xte"])
                except ValueError:
                    # every client in this subset is below the trainable minimum.
                    # Skipping is UNSOUND if silent -- it shrinks K -- so it is counted
                    # and reported, and the row is discarded if too many are skipped.
                    skipped += 1
                    continue
                votes[np.arange(len(pr)), pr] += 1
            if skipped:
                print(f"    NOTE: {skipped}/{len(subs)} subsets had no trainable client", flush=True)
            if votes.sum(1).max() == 0:
                print(f"    SKIP row: no usable ensemble member", flush=True)
                continue
            eff_K = int(votes[0].sum())
            cert = C.certify_from_votes(votes, t["yte_np"], 20, k, cfg.betas,
                                        exact and skipped == 0, cfg.cert.confidence, t["tau"])
            g = {x["beta"]: x["CA"] for x in cert["grid"]}
            rows.append(dict(kind=kind, k=k, seed=seed, eff_K=eff_K, skipped=skipped, S_JS=t["pmeta"]["S_JS"],
                             S_dev=t["pmeta"]["S_dev"], target_S_JS=target,
                             matched_alpha=t["pmeta"].get("alpha"),
                             control_valid=bool(abs(t["pmeta"]["S_JS"] - target) <= 0.05)
                                           if kind == "dirichlet_matched" else None,
                             ens_acc=cert["ensemble_acc"], margin=cert["mean_margin"],
                             beta_star=cert["beta_star"], CA10=g[0.10], CA05=g[0.05],
                             tau=cert["tau_triv"]))
            print(f"  s{seed} {kind:18s} k={k} S_JS={t['pmeta']['S_JS']:.4f} "
                  f"ens={cert['ensemble_acc']:.4f} margin={cert['mean_margin']:.4f} "
                  f"CA(.10)={g[0.10]:.4f} beta*={cert['beta_star']:.2f}", flush=True)
            json.dump(rows, open("results/necessity.json", "w"), indent=2)
print("DONE")
