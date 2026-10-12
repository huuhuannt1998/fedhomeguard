#!/usr/bin/env python3
"""PB01 (preregistered): device-skew vs label-skew matched pairs -- dependence, uncertainty,
matching sensitivity, coverage conditioning. Rows only + partition rebuilds (no training).
Writes results/pb01_pairs.json."""
import collections, json, math, os, sys
import numpy as np
from scipy.optimize import linear_sum_assignment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

TOL = 0.10
REPS = 10_000


def cells(f, fam):
    by = collections.defaultdict(list)
    for r in C.load_rows(f):
        if r["k"] == 1 and r["K"] == 20:
            by[(r["dirichlet_alpha"], r["partition_seed"])].append(r)
    out = []
    for (a, s), v in sorted(by.items()):
        good = [x["beta"] for x in v if x["CA"] > x["tau_triv"]]
        out.append(dict(fam=fam, alpha=a, seed=s, S=float(np.mean([x["S_JS"] for x in v])),
                        Sdev=float(np.mean([x["S_dev"] for x in v])),
                        margin=float(np.mean([x["mean_vote_margin"] for x in v])),
                        bstar=max(good) if good else 0.0))
    return out


def add_coverage(cs, kind):
    tb = C.prepare_base("iot-23")
    for c in cs:
        cfg = C.base_cfg("iot-23", kind, c["seed"], alpha=c["alpha"])
        parts, meta = C.P.build(cfg, tb["ytr_np"], tb["dtr"])
        assert abs(meta["S_JS"] - c["S"]) < 1e-6, (c, meta["S_JS"])
        c["fracDegen"] = meta["frac_degenerate"]
        c["minClassSup"] = meta["min_class_support"]


def nn_pairs(dev, lab, key="S", tol=TOL, tiebreak="S"):
    pairs = []
    for l in lab:
        best = min(dev, key=lambda d: (abs(d[key] - l[key]), abs(d[tiebreak] - l[tiebreak])))
        if abs(best[key] - l[key]) <= tol + 1e-12:
            pairs.append((best, l))
    return pairs


def summ(pairs):
    if not pairs:
        return dict(n=0)
    dm = np.array([d["margin"] - l["margin"] for d, l in pairs])
    db = np.array([d["bstar"] - l["bstar"] for d, l in pairs])
    return dict(n=len(pairs), n_dev_draws=len({(d["alpha"], d["seed"]) for d, _ in pairs}),
                mean_dm=float(dm.mean()), mean_db=float(db.mean()),
                n_dm_pos=int((dm > 0.005).sum()), n_dm_neg=int((dm < -0.005).sum()),
                n_dm_near0=int((abs(dm) <= 0.005).sum()))


def main():
    dev = cells("e7_devskew.jsonl", "device")
    lab = cells("e7_labelskew.jsonl", "label")
    add_coverage(dev, "dirichlet_device"); add_coverage(lab, "dirichlet")
    res = dict(n_dev=len(dev), n_lab=len(lab))
    base = nn_pairs(dev, lab)
    res["paper_rule"] = summ(base)
    inf = [(d, l) for d, l in base if l["alpha"] <= 1.0]
    nul = [(d, l) for d, l in base if l["alpha"] >= 3.0]
    res["a_informative"] = summ(inf)
    res["a_informative_pairs"] = [dict(dev=(d["alpha"], d["seed"]), lab=(l["alpha"], l["seed"]),
                                       dm=round(d["margin"] - l["margin"], 4),
                                       db=round(d["bstar"] - l["bstar"], 4),
                                       lab_fracDegen=l["fracDegen"], dev_fracDegen=d["fracDegen"])
                                  for d, l in inf]
    res["a_nearIID"] = summ(nul)
    res["a_nearIID_max_abs_dm"] = max(abs(d["margin"] - l["margin"]) for d, l in nul)

    # (b) two-way draw-level bootstrap with re-matching
    rng = np.random.default_rng(20261008)
    bm, bb, bn = [], [], []
    for _ in range(REPS):
        D = [dev[i] for i in rng.integers(0, len(dev), len(dev))]
        L = [lab[i] for i in rng.integers(0, len(lab), len(lab))]
        p = nn_pairs(D, L)
        if not p:
            continue
        s = summ(p); bm.append(s["mean_dm"]); bb.append(s["mean_db"]); bn.append(s["n"])
    res["b_twoway_bootstrap"] = dict(
        reps=len(bm), margin_ci95=[float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))],
        bstar_ci95=[float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))],
        frac_margin_le0=float(np.mean(np.array(bm) <= 0)), median_n_pairs=float(np.median(bn)))
    # same, informative stratum only (label alpha <= 1)
    lab_inf = [l for l in lab if l["alpha"] <= 1.0]
    bm2 = []
    for _ in range(REPS):
        D = [dev[i] for i in rng.integers(0, len(dev), len(dev))]
        L = [lab_inf[i] for i in rng.integers(0, len(lab_inf), len(lab_inf))]
        p = nn_pairs(D, L)
        if p:
            bm2.append(summ(p)["mean_dm"])
    res["b_twoway_bootstrap_informative"] = dict(
        n_label_draws=len(lab_inf), reps=len(bm2),
        margin_ci95=[float(np.percentile(bm2, 2.5)), float(np.percentile(bm2, 97.5))])

    # (c) matching sensitivity
    sens = {}
    for tol in (0.05, 0.10, 0.20):
        sens[f"nn_SJS_tol{tol}"] = summ(nn_pairs(dev, lab, "S", tol))
    cost = np.array([[abs(d["S"] - l["S"]) for d in dev] for l in lab])
    ri, ci = linear_sum_assignment(cost)
    oto = [(dev[c], lab[r]) for r, c in zip(ri, ci) if cost[r, c] <= TOL]
    sens["one_to_one_SJS_tol0.10"] = summ(oto)
    sens["nn_Sdev_tol0.10"] = summ(nn_pairs(dev, lab, "Sdev", 0.10, tiebreak="S"))
    res["c_sensitivity"] = sens

    # (d) coverage conditioning
    cov = {}
    for key in ("fracDegen", "minClassSup"):
        p = nn_pairs(dev, lab, key, 0.05, tiebreak="S")
        cov[f"nn_{key}_tol0.05"] = summ(p)
        cov[f"nn_{key}_tol0.05_informative"] = summ([(d, l) for d, l in p if l["alpha"] <= 1.0])
        cov[f"{key}_label_draws_unmatched"] = [(l["alpha"], l["seed"], l[key]) for l in lab
                                               if l not in [x for _, x in p]]
    res["d_coverage_matched"] = cov
    res["coverage_by_draw"] = [dict(fam=c["fam"], alpha=c["alpha"], seed=c["seed"],
                                    S_JS=round(c["S"], 4), S_dev=round(c["Sdev"], 4),
                                    fracDegen=c["fracDegen"], minClassSup=c["minClassSup"],
                                    margin=round(c["margin"], 4), bstar=c["bstar"])
                               for c in dev + lab]

    # (e) descriptive ANCOVA: margin ~ 1 + label + S_JS, draw bootstrap
    allc = dev + lab
    def ols(cs):
        X = np.array([[1.0, c["fam"] == "label", c["S"]] for c in cs], float)
        y = np.array([c["margin"] for c in cs])
        return np.linalg.lstsq(X, y, rcond=None)[0]
    b0 = ols(allc)
    bs = []
    for _ in range(2000):
        D = [dev[i] for i in rng.integers(0, len(dev), len(dev))]
        L = [lab[i] for i in rng.integers(0, len(lab), len(lab))]
        bs.append(ols(D + L)[1])
    res["e_ancova"] = dict(n=len(allc), coef_label=float(b0[1]), coef_SJS=float(b0[2]),
                           coef_label_ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    C.dump("pb01_pairs.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "coverage_by_draw"}, indent=1, default=str))


if __name__ == "__main__":
    main()
