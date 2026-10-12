#!/usr/bin/env python3
"""PB20 (post hoc re-analysis, round tmlr5; mock review round 2, M6): the PB02 out-of-sample association
with minClassSup's usability threshold q chosen INSIDE each training fold (q in {0.01, 0.02, 0.05, 0.10,
0.20}, by training-fold R^2 of the same isotonic fit), against the paper's fixed q = 0.05 and the other
statistics. Rebuilds the 159 audit partitions (no training). Writes results/pb20_oos_threshold.json."""
import json, os, sys
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from pb03_cvm import base_for

QS = (0.01, 0.02, 0.05, 0.10, 0.20)
DPH = {("iot23", "device_derived"): (1, 3), ("nbaiot", "device_derived"): (1, 2)}
STATS = {"S_JS": -1, "S_dev": -1, "S_lab": -1, "frac_degenerate": -1, "min_size_share": +1}


def r2(y, p):
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


def main():
    cells = [json.loads(l) for l in open(os.path.join(C.REPO, "results/analysis/instruments.jsonl"))]
    bases, cache, bad = {}, {}, 0
    for c in cells:
        ds = "iot-23" if c["dataset"] == "iot23" else "n-baiot"
        kind = c["family"]
        key = (ds, kind, c["pseed"], c["alpha"])
        if key not in cache:
            if ds not in bases:
                bases[ds] = base_for(ds)
            b = bases[ds]
            cfg = C.base_cfg(ds, kind, c["pseed"], DPH.get((c["dataset"], kind), (1, 3)), c["alpha"])
            parts, meta = C.P.build(cfg, b["ytr_np"], b["dtr"])
            cache[key] = (meta["S_JS"], {q: C.P.min_class_support(parts, b["ytr_np"], q) for q in QS})
        sjs, mcs = cache[key]
        if abs(sjs - c["S_JS"]) > 1e-5:
            bad += 1
        c["mcs"] = mcs
        c["y"] = c["beta_star"] / c["beta_geo"]
        c["draw"] = f"{c['dataset']}|{c['family']}|{c['alpha']}|{c['pseed']}"
        c["fam"] = f"{c['dataset']}|{c['family']}"
    assert bad == 0, f"{bad} rebuilt partitions differ in S_JS"
    assert all(abs(c["mcs"][0.05] - c["min_class_support"]) < 1e-6 for c in cells)
    y = np.array([c["y"] for c in cells]); kk = np.array([c["k"] for c in cells])
    groups = np.array([c["draw"] for c in cells]); fams = np.array([c["fam"] for c in cells])

    def fit_pred(x_tr, y_tr, x_te, inc):
        m = IsotonicRegression(increasing=inc, out_of_bounds="clip"); m.fit(x_tr, y_tr); return m.predict(x_te)

    def oof(splitter, feat=None, q=None, nested=False):
        pred = np.full(len(y), np.nan); chosen = []
        for tr, te in splitter:
            for k in (1, 2):
                a, b = tr[kk[tr] == k], te[kk[te] == k]
                if len(b) == 0:
                    continue
                if feat is not None:
                    x = np.array([c[feat] for c in cells]); inc = STATS[feat] > 0
                    pred[b] = fit_pred(x[a], y[a], x[b], inc); continue
                if nested:
                    best, bq = None, None
                    for qq in QS:
                        x = np.array([c["mcs"][qq] for c in cells])
                        s = r2(y[a], fit_pred(x[a], y[a], x[a], True))
                        if best is None or s > best:
                            best, bq = s, qq
                    chosen.append(bq); qq = bq
                else:
                    qq = q
                x = np.array([c["mcs"][qq] for c in cells])
                pred[b] = fit_pred(x[a], y[a], x[b], True)
        return r2(y, pred), chosen

    gkf = list(GroupKFold(n_splits=10).split(np.zeros(len(y)), y, groups))
    logo = list(LeaveOneGroupOut().split(np.zeros(len(y)), y, fams))
    out = {"cells": len(cells), "draws": len(set(groups)), "q_grid": QS}
    for name, sp in (("groupkfold_by_draw", gkf), ("leave_one_family_out", logo)):
        res = {}
        r, ch = oof(sp, nested=True)
        res["minClassSup_q_fitted_in_fold"] = dict(R2=r, q_chosen=sorted(set(ch)),
                                                   q_counts={str(q): ch.count(q) for q in QS})
        for q in QS:
            res[f"minClassSup_q{q}"] = oof(sp, q=q)[0]
        for f in STATS:
            res[f] = oof(sp, feat=f)[0]
        out[name] = res
    json.dump(out, open(os.path.join(C.OUTDIR, "pb20_oos_threshold.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
