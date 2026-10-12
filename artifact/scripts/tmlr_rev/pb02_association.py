#!/usr/bin/env python3
"""PB02 (preregistered, predeclarations/tmlr_PB02_oos_association.md): out-of-sample association of
normalised beta* with class coverage, volume skew, vote margin and divergence, grouped by draw.
Rows only (results/analysis/instruments.jsonl + canonical margins); no training, no partitions.
Writes results/pb02_association.json."""
import argparse, collections, json, os, sys
import numpy as np
from scipy.stats import spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

# statistic -> sign of its pooled Spearman rho in the paper's Table 11 (direction of the isotonic fit)
STATS = {"min_class_support": +1, "frac_degenerate": -1, "min_size_share": +1, "S_lab": -1,
         "S_JS": -1, "S_dev": -1, "margin": +1}
GROUPS = {"coverage": ["min_class_support", "frac_degenerate"], "volume": ["min_size_share"],
          "divergence": ["S_JS", "S_dev", "S_lab"], "post_training": ["margin"]}
SRC = {("iot23", "device_derived"): "e5f_device_derived.jsonl", ("iot23", "iid"): "e5f_iid.jsonl",
       ("iot23", "dirichlet"): "e7f_labelskew.jsonl", ("iot23", "dirichlet_device"): "e7f_devskew.jsonl",
       ("iot23", "volume"): "e7_volskew.jsonl", ("nbaiot", "device_derived"): "nb9_cert_device_derived.jsonl",
       ("nbaiot", "iid"): "nb9_cert_iid.jsonl"}


def load_cells():
    cells = [json.loads(l) for l in open(os.path.join(C.REPO, "results/analysis/instruments.jsonl"))]
    rows = {f: C.load_rows(f) for f in set(SRC.values())}
    miss = 0
    for c in cells:
        rs = [r for r in rows[SRC[(c["dataset"], c["family"])]]
              if r["partition_seed"] == c["pseed"] and r["k"] == c["k"]
              and r.get("dirichlet_alpha") == c["alpha"]]
        if not rs or abs(rs[0]["S_JS"] - c["S_JS"]) > 1e-5:
            miss += 1; c["margin"] = np.nan; continue
        c["margin"] = rs[0]["mean_vote_margin"]
        c["y"] = c["beta_star"] / c["beta_geo"]
    if miss:
        raise SystemExit(f"{miss} audit cells could not be joined to canonical rows by S_JS")
    for c in cells:
        c["y"] = c["beta_star"] / c["beta_geo"]
        c["draw"] = f"{c['dataset']}|{c['family']}|{c['alpha']}|{c['pseed']}"
        c["fam"] = f"{c['dataset']}|{c['family']}"
    return cells


def oof(cells, feats, splitter, groups):
    X = np.array([[c[f] for f in feats] for c in cells], float)
    y = np.array([c["y"] for c in cells]); kk = np.array([c["k"] for c in cells])
    pred = np.full(len(y), np.nan)
    for tr, te in splitter:
        for k in (1, 2):
            a, b = tr[kk[tr] == k], te[kk[te] == k]
            if len(b) == 0:
                continue
            if len(feats) == 1:
                m = IsotonicRegression(increasing=STATS[feats[0]] > 0, out_of_bounds="clip")
                m.fit(X[a, 0], y[a]); pred[b] = m.predict(X[b, 0])
            else:
                m = HistGradientBoostingRegressor(max_depth=2, max_iter=100, random_state=0,
                                                  monotonic_cst=[STATS[f] for f in feats])
                m.fit(X[a], y[a]); pred[b] = m.predict(X[b])
    return pred, y


def metrics(pred, y, groups, reps=1000, seed=0):
    def one(ix):
        p, t = pred[ix], y[ix]
        sst = ((t - t.mean()) ** 2).sum()
        r2 = 1 - ((t - p) ** 2).sum() / sst if sst > 0 else np.nan
        return r2, np.abs(t - p).mean(), spearmanr(p, t).statistic
    base = one(np.arange(len(y)))
    ug = np.unique(groups); idx = {g: np.where(groups == g)[0] for g in ug}
    rng = np.random.default_rng(seed); bs = []
    for _ in range(reps):
        ix = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        bs.append(one(ix))
    bs = np.array(bs)
    ci = lambda j: [float(np.nanpercentile(bs[:, j], 2.5)), float(np.nanpercentile(bs[:, j], 97.5))]
    return dict(R2=float(base[0]), R2_ci95=ci(0), MAE=float(base[1]), MAE_ci95=ci(1),
                spearman=float(base[2]), spearman_ci95=ci(2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    if a.dry_run:
        print("PB02: 318 cells x 8 predictor sets x {GroupKFold(10), leave-one-family-out}; rows only"); return
    cells = load_cells()
    groups = np.array([c["draw"] for c in cells]); fams = np.array([c["fam"] for c in cells])
    gkf = list(GroupKFold(n_splits=10).split(np.zeros(len(cells)), groups=groups))
    lofo = [(np.where(fams != f)[0], np.where(fams == f)[0]) for f in np.unique(fams)]
    out = dict(n_cells=len(cells), n_draws=int(len(np.unique(groups))), n_families=int(len(np.unique(fams))),
               results={})
    sets = [[s] for s in STATS] + [["min_class_support", "min_size_share"]]
    for feats in sets:
        name = "+".join(feats)
        r = {}
        for sname, spl in (("groupkfold10", gkf), ("leave_one_family_out", lofo)):
            p, y = oof(cells, feats, spl, groups)
            ok = ~np.isnan(p)
            r[sname] = metrics(p[ok], y[ok], groups[ok])
        out["results"][name] = r
    best = lambda grp: max(GROUPS[grp], key=lambda s: out["results"][s]["groupkfold10"]["R2"])
    bc, bd = best("coverage"), best("divergence")
    out["falsifier"] = dict(best_coverage=bc, best_coverage_R2=out["results"][bc]["groupkfold10"]["R2"],
                            best_divergence=bd, best_divergence_R2=out["results"][bd]["groupkfold10"]["R2"],
                            fired=bool(out["results"][bd]["groupkfold10"]["R2"] >=
                                       out["results"][bc]["groupkfold10"]["R2"] - 0.05))
    C.dump("pb02_association.json", out)
    for k, v in out["results"].items():
        print(f"{k:38s} GKF R2={v['groupkfold10']['R2']:.3f} rho={v['groupkfold10']['spearman']:.3f}  "
              f"LOFO R2={v['leave_one_family_out']['R2']:.3f} rho={v['leave_one_family_out']['spearman']:.3f}")
    print("falsifier:", out["falsifier"])


if __name__ == "__main__":
    main()
