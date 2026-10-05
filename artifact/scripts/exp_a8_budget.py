#!/usr/bin/env python3
"""A8 -- matched-budget control (design C3 anti-triviality guard).

The certified ensemble spends K x k x T client-rounds; the empirical arm spends
N x T. If the gap merely reflects the ensemble buying more compute, then giving
the single-model defense the SAME total budget should close it. Headline budget
is equal-total-gradient-steps, fixed in advance.
"""
import copy, json, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, fl as FL, attacks as A, defenses as D

base = yaml.safe_load(open("configs/stage2_empirical.yaml"))
ATTACKS = ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]
DEFENSE = "norm_clip"                    # the best defense at these fractions
BETAS = [0.20, 0.30]
K, k, T_cert = 100, 5, 15                # the certified arm's configuration
N = 20
cert_client_rounds = K * k * T_cert                      # 7500
T_matched = max(1, round(cert_client_rounds / N))        # 375
print(f"certified arm: K={K} k={k} T={T_cert} -> {cert_client_rounds} client-rounds")
print(f"empirical arm matched: T={T_matched} over N={N} -> {N*T_matched} client-rounds\n")

rows, t0 = [], time.time()
for T, label in ((T_cert, "baseline"), (T_matched, "budget_matched")):
    for b in BETAS:
        for atk in ATTACKS:
            d = copy.deepcopy(base)
            d["partition"].update(kind="device_derived", seed=0, N=N)
            d["fl"]["rounds_T"] = T
            d["adversary"].update(beta=b, F3_knowledge="white_box")
            d["defense"].update(name=DEFENSE, observability=D.LEVEL[DEFENSE])
            d["name"] = f"a8_{label}_b{b}_{atk}"
            cfg = CFG.from_dict(d)
            t = R.prepare(cfg, verbose=False)
            mal = A.select_malicious(N, b, cfg.adversary.seed)
            g = FL.fl_run(cfg, list(range(N)), t["Xtr"], t["ytr"], t["parts"],
                          malicious_ids=mal, attack=atk)
            ea = FL.accuracy(g, t["Xte"], t["yte_np"])
            rows.append(dict(arm=label, T=T, beta=b, attack=atk, defense=DEFENSE,
                             EA=round(ea, 6), client_rounds=N * T))
            print(f"  {label:15s} T={T:3d} beta={b:.2f} {atk:11s} EA={ea:.4f} "
                  f"[{time.time()-t0:.0f}s]", flush=True)
            json.dump(rows, open("results/a8_budget.json", "w"), indent=2)

# EA_min per (arm, beta) = worst attack
import collections
agg = collections.defaultdict(list)
for r in rows: agg[(r["arm"], r["beta"])].append(r["EA"])
print("\nEA_min (worst attack) by arm:")
for b in BETAS:
    base_v = min(agg[("baseline", b)]); m = min(agg[("budget_matched", b)])
    print(f"  beta={b:.2f}  baseline(T={T_cert})={base_v:.4f}  "
          f"matched(T={T_matched})={m:.4f}  delta={m-base_v:+.4f}")
json.dump(dict(rows=rows, cert_client_rounds=cert_client_rounds, T_matched=T_matched,
               ea_min={f"{a}_{b}": min(v) for (a, b), v in agg.items()}),
          open("results/a8_budget.json", "w"), indent=2)
print("A8 DONE")
