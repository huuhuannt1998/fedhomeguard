#!/usr/bin/env python3
"""PB19 (post hoc re-analysis, round tmlr5; mock review round 2, M2): the PB13 decomposition regression
with draw-level rows and standard errors clustered by concentration level (family x alpha, 8 clusters),
over several covariate sets, plus the level-mean regression (n = 8). Writes results/pb19_decomposition.json."""
import itertools, json, os
import numpy as np
from scipy import stats

RES = "<artifact-root>/results/tmlr_rev"
rows = [json.loads(l) for l in open(os.path.join(RES, "pb13_15_rows.jsonl")) if l.strip()]
rows = [r for r in rows if r["pb"] == 13]
y = np.array([r["mean_margin"] for r in rows])
fam = np.array([1.0 if r["family"] == "dirichlet_device" else 0.0 for r in rows])
cov = {"fracDegen": np.array([r["partition"]["frac_degenerate"] for r in rows]),
       "S_JS": np.array([r["partition"]["S_JS"] for r in rows]),
       "S_lab": np.array([r["partition"]["S_lab"] for r in rows])}
cl = np.array([f"{r['family']}|{r['alpha']}" for r in rows])
G = sorted(set(cl))


def ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta, y - X @ beta


def cr1(X, e, cl):
    n, p = X.shape
    bread = np.linalg.inv(X.T @ X)
    meat = np.zeros((p, p))
    for g in set(cl):
        m = cl == g
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    Gn = len(set(cl))
    c = Gn / (Gn - 1) * (n - 1) / (n - p)
    return np.sqrt(np.diag(c * bread @ meat @ bread))


def wild_cluster_ci(X, y, cl, j=1, B=None):
    """Wild cluster bootstrap-t (Rademacher, all 2^G sign patterns, unrestricted residuals) for coef j."""
    beta, e = ols(X, y)
    se = cr1(X, e, cl)[j]
    gs = sorted(set(cl))
    ts = []
    for signs in itertools.product((-1.0, 1.0), repeat=len(gs)):
        w = np.ones(len(y))
        for g, s in zip(gs, signs):
            w[cl == g] = s
        yb = X @ beta + e * w
        bb, eb = ols(X, yb)
        sb = cr1(X, eb, cl)[j]
        if sb > 0:
            ts.append((bb[j] - beta[j]) / sb)
    lo, hi = np.percentile(ts, [2.5, 97.5])
    return [float(beta[j] - hi * se), float(beta[j] - lo * se)]


sets = [("family only", []), ("+ S_JS", ["S_JS"]), ("+ fracDegen", ["fracDegen"]),
        ("+ fracDegen + S_JS (predeclared)", ["fracDegen", "S_JS"]), ("+ S_lab", ["S_lab"]),
        ("+ S_lab + S_JS", ["S_lab", "S_JS"]), ("+ fracDegen + S_lab + S_JS", ["fracDegen", "S_lab", "S_JS"])]
out = {"n_draws": len(rows), "clusters": len(G), "specs": []}
lv = {g: (float(np.mean(y[cl == g])), float(fam[cl == g][0]), {k: float(np.mean(v[cl == g])) for k, v in cov.items()})
      for g in G}
for name, cs in sets:
    X = np.column_stack([np.ones(len(y)), fam] + [cov[c] for c in cs])
    beta, e = ols(X, y)
    se = cr1(X, e, cl)
    tcrit = stats.t.ppf(0.975, len(G) - 1)
    # level-mean regression (n = 8)
    Ym = np.array([lv[g][0] for g in G])
    Xm = np.column_stack([np.ones(len(G)), [lv[g][1] for g in G]] + [[lv[g][2][c] for g in G] for c in cs])
    bm = None
    if Xm.shape[1] < len(G):
        bm, em = ols(Xm, Ym)
        dfm = len(G) - Xm.shape[1]
        s2 = float(em @ em) / dfm if dfm > 0 else float("nan")
        sem = np.sqrt(np.diag(s2 * np.linalg.inv(Xm.T @ Xm)))
        lm = dict(coef=float(bm[1]), ci95=[float(bm[1] - stats.t.ppf(0.975, dfm) * sem[1]),
                                           float(bm[1] + stats.t.ppf(0.975, dfm) * sem[1])], df=dfm)
    else:
        lm = None
    out["specs"].append(dict(spec=name, family_coef=float(beta[1]),
                             cr1_ci95=[float(beta[1] - tcrit * se[1]), float(beta[1] + tcrit * se[1])],
                             wild_cluster_ci95=wild_cluster_ci(X, y, cl),
                             level_mean=lm))
json.dump(out, open(os.path.join(RES, "pb19_decomposition.json"), "w"), indent=1)
for s in out["specs"]:
    print(f"{s['spec']:36s} {s['family_coef']:+.3f} CR1 [{s['cr1_ci95'][0]:+.3f}, {s['cr1_ci95'][1]:+.3f}] "
          f"wild [{s['wild_cluster_ci95'][0]:+.3f}, {s['wild_cluster_ci95'][1]:+.3f}] "
          f"level-mean {s['level_mean']['coef'] if s['level_mean'] else None}")
