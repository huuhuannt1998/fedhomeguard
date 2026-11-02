#!/usr/bin/env python3
"""JS01 scoring (predeclarations/jisa_JS01_cic_victim_replication.md): the coverage-vote model (CVM) on CIC IoT-IDAD
2024 read on the victim side. For every draw, the CVM prediction and the one-class share (fracDegen) come from the
partition alone (rebuilt from its seed; no training); the observed beta* and collapse come from the trained rows.

  P1  CVM beta* within one 0.05 step of observed on >= 80% of device-derived draws (arms B and C pooled), at each k;
      mean signed error in steps >= 0
  P2  IID (arm A) at the ceiling (0.45 at k=1, 0.25 at k=2) on >= 28 of 30 draws at each k
  P3  at k=1, CVM collapse prediction at beta=0.20 agrees with observed collapse on >= 80% of device-derived draws
  P4  Spearman(fracDegen, observed beta*) < 0 across device-derived draws at k=1; S_JS reported, no prediction

Writes results/jisa/js01_cvm.json and js01_summary.md.
"""
import json
import os
import statistics as st
import sys

import numpy as np
from scipy.stats import spearmanr

P2 = "<artifact-root>/scripts/tmlr_rev"
sys.path.insert(0, P2)
import common as C  # noqa: E402
from pb03_cvm import cvm_predict  # noqa: E402

REPO = C.REPO
J = os.path.join(REPO, "results", "jisa")
BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
ARMS = {"A": ("iid", (1, 3), "js01_cic_victim_iid.jsonl"),
        "B": ("device_derived", (1, 3), "js01_cic_victim_dd13.jsonl"),
        "C": ("device_derived", (1, 1), "js01_cic_victim_dd11.jsonl")}
SEEDS = range(10, 40)
DS = "cic-idad-victim"


def observed(path):
    d = {}
    for l in open(path):
        if not l.startswith("{"):
            continue
        r = json.loads(l)
        if r.get("mal_seed", 0) == 0:
            d.setdefault((r["partition_seed"], r["k"]), {})[round(r["beta"], 4)] = r
    out = {}
    for key, bm in d.items():
        ok = [b for b, r in bm.items() if r["CA"] > r["tau_triv"] + 1e-12]
        out[key] = dict(bstar=max(ok) if ok else 0.0,
                        collapse20=bm[0.2]["CA"] <= bm[0.2]["tau_triv"] + 1e-12,
                        tau=bm[0.0]["tau_triv"], S_JS=bm[0.0]["S_JS"], K=bm[0.0]["K"])
    return out


def main():
    tb = C.prepare_base(DS)
    ytr = tb["ytr_np"]
    rows, res = [], {}
    for arm, (kind, dph, fn) in ARMS.items():
        obs = observed(os.path.join(J, fn))
        for s in SEEDS:
            cfg = C.base_cfg(DS, kind, s, dph=dph)
            t = C.with_partition(tb, cfg)
            parts = t["parts_np"]
            frac_degen = float(np.mean([(ytr[v].mean() > 0.95 or ytr[v].mean() < 0.05) if len(v) else False
                                        for v in parts.values()]))
            for k in (1, 2):
                o = obs[(s, k)]
                p = cvm_predict(parts, ytr, k, BF, o["tau"])
                rows.append(dict(arm=arm, seed=s, k=k, fracDegen=frac_degen, S_JS=o["S_JS"], tau=o["tau"],
                                 bstar_obs=o["bstar"], bstar_pred=p["bstar_pred"], collapse20_obs=o["collapse20"],
                                 collapse20_pred=p["collapse02_pred"], n_M=p["n_M"], n_B=p["n_B"], K=o["K"]))
    dd = lambda k: [r for r in rows if r["arm"] in ("B", "C") and r["k"] == k]  # noqa: E731
    for k in (1, 2):
        e = np.round((np.array([r["bstar_pred"] for r in dd(k)]) - np.array([r["bstar_obs"] for r in dd(k)])) / 0.05)
        res[f"P1_k{k}"] = dict(within_one=int((abs(e) <= 1).sum()), n=len(e), share=float((abs(e) <= 1).mean()),
                               mean_signed_error_steps=float(e.mean()), exact=int((e == 0).sum()),
                               holds=bool((abs(e) <= 1).mean() >= 0.8 and e.mean() >= 0))
        a = [r for r in rows if r["arm"] == "A" and r["k"] == k]
        ceil = 0.45 if k == 1 else 0.25
        res[f"P2_k{k}"] = dict(at_ceiling=sum(r["bstar_obs"] == ceil for r in a), n=len(a),
                               holds=sum(r["bstar_obs"] == ceil for r in a) >= 28)
    agree = [r["collapse20_pred"] == r["collapse20_obs"] for r in dd(1)]
    res["P3"] = dict(agree=int(sum(agree)), n=len(agree), share=float(np.mean(agree)), holds=bool(np.mean(agree) >= 0.8))
    rho = spearmanr([r["fracDegen"] for r in dd(1)], [r["bstar_obs"] for r in dd(1)]).statistic
    rho_js = spearmanr([r["S_JS"] for r in dd(1)], [r["bstar_obs"] for r in dd(1)]).statistic
    res["P4"] = dict(spearman_fracDegen=float(rho), spearman_S_JS=float(rho_js), holds=bool(rho < 0))
    for arm in ARMS:
        for k in (1, 2):
            a = [r for r in rows if r["arm"] == arm and r["k"] == k]
            res[f"arm_{arm}_k{k}"] = dict(median_bstar=st.median(r["bstar_obs"] for r in a),
                                          collapse20=sum(r["collapse20_obs"] for r in a),
                                          median_fracDegen=st.median(r["fracDegen"] for r in a))
    res["outcome"] = ("count rule transfers" if res["P1_k1"]["holds"] and res["P1_k2"]["holds"] and res["P3"]["holds"]
                      else "count rule does not transfer")
    if not (res["P2_k1"]["holds"] and res["P2_k2"]["holds"]):
        res["outcome"] += "; P2 failed: setup suspect, not the mechanism"
    json.dump(dict(scores=res, draws=rows), open(os.path.join(J, "js01_cvm.json"), "w"), indent=1, default=float)
    md = ["# JS01: CIC IoT-IDAD 2024, victim side", ""] + [f"- {k}: {v}" for k, v in res.items()]
    open(os.path.join(J, "js01_summary.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
