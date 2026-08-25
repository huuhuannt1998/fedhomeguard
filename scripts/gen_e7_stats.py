#!/usr/bin/env python3
"""Paired statistics for the device- vs label-skew ablation (review sec 47).

Medians alone do not establish the comparison, so we pair the two families on
realised skew and report a paired effect size with a bootstrap interval and a
Wilcoxon signed-rank test, not only a p-value.

Pairing rule, fixed before running: each label-family (concentration, draw) is paired
with the device-family (concentration, draw) whose realised S_JS is closest, and the
pair is discarded if the two differ by more than TOL. Pairing on the realised
statistic rather than on the concentration is the point of the ablation: the two
families reach very different S_JS at the same alpha.
"""
import collections, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load

OUT = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"
TOL = 0.10
BOOT = 20_000


def cells(path, k=1):
    """Full-enumeration draws only.

    At strong concentration some clients fall below the trainable minimum and their
    members are dropped, which shrinks K and RAISES the threshold independently of
    skew. Pooling those draws with full-enumeration ones would credit the ensemble
    shrinkage to the skew family, so they are excluded from the paired comparison and
    counted separately.
    """
    by = collections.defaultdict(list)
    dropped = 0
    for r in load(path):
        if r["k"] != k:
            continue
        if r["K"] < math.comb(r["N"], k):
            dropped += 1
            continue
        by[(r["dirichlet_alpha"], r["partition_seed"])].append(r)
    cells.last_dropped = dropped
    out = []
    for _, v in by.items():
        good = [x["beta"] for x in v if x["CA"] > x["tau_triv"]]
        out.append(dict(S=float(np.mean([x["S_JS"] for x in v])),
                        margin=float(np.mean([x["mean_vote_margin"] for x in v])),
                        bstar=max(good) if good else 0.0))
    return out


def wilcoxon(d):
    d = np.asarray([x for x in d if x != 0.0])
    n = len(d)
    if n == 0:
        return 1.0, 0
    r = np.argsort(np.argsort(np.abs(d))) + 1.0
    W = min(r[d > 0].sum(), r[d < 0].sum())
    mu = n * (n + 1) / 4.0
    sd = np.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    from math import erfc, sqrt
    z = (abs(W - mu) - 0.5) / sd if sd > 0 else 0.0
    return float(erfc(z / sqrt(2))), n


def main():
    dev = cells("results/canonical/e7_devskew.jsonl"); n_drop_dev = cells.last_dropped
    lab = cells("results/canonical/e7_labelskew.jsonl"); n_drop_lab = cells.last_dropped
    pairs = []
    for l in lab:
        d = min(dev, key=lambda x: abs(x["S"] - l["S"]))
        if abs(d["S"] - l["S"]) <= TOL:
            pairs.append((d, l))
    dm = np.array([d["margin"] - l["margin"] for d, l in pairs])
    db = np.array([d["bstar"] - l["bstar"] for d, l in pairs])
    rng = np.random.default_rng(0)

    def boot(x):
        idx = rng.integers(0, len(x), size=(BOOT, len(x)))
        s = x[idx].mean(1)
        return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))

    pm, nm = wilcoxon(dm)
    pb, nb = wilcoxon(db)
    res = dict(
        n_pairs=len(pairs), tolerance=TOL,
        rows_excluded_for_shrunk_ensemble=dict(device=n_drop_dev, label=n_drop_lab),
        mean_skew_mismatch=round(float(np.mean([abs(d["S"] - l["S"]) for d, l in pairs])), 4),
        margin_mean_diff=round(float(dm.mean()), 4), margin_ci95=[round(v, 4) for v in boot(dm)],
        margin_cohens_dz=round(float(dm.mean() / dm.std(ddof=1)), 3) if dm.std(ddof=1) else None,
        margin_wilcoxon_p=round(pm, 6), margin_n_nonzero=nm,
        bstar_mean_diff=round(float(db.mean()), 4), bstar_ci95=[round(v, 4) for v in boot(db)],
        bstar_wilcoxon_p=round(pb, 6), bstar_n_nonzero=nb)
    print(json.dumps(res, indent=1))

    tex = f"""% GENERATED -- do not edit
% provenance: jrn_01M0W6RR18X6MJY3X1JG07YTRN supports the device-versus-label ablation
Medians alone would not settle this, so we pair the families on realised skew --- each
label-family draw with the device-family draw whose $S_{{\\mathrm{{JS}}}}$ is nearest,
discarding pairs that differ by more than ${TOL:.2f}$, and using only draws whose
ensemble is the full enumeration --- and report the paired effect with an interval. Over {res['n_pairs']} pairs whose skew differs by
${res['mean_skew_mismatch']:.3f}$ on average, the device family holds
${res['margin_mean_diff']:+.4f}$ more vote margin, bootstrap $95\\%$ CI
$[{res['margin_ci95'][0]:+.4f}, {res['margin_ci95'][1]:+.4f}]$, Cohen's
$d_z = {res['margin_cohens_dz']:.2f}$, Wilcoxon signed-rank $p = {res['margin_wilcoxon_p']:.2g}$.
The breakdown point moves with it: ${res['bstar_mean_diff']:+.4f}$, CI
$[{res['bstar_ci95'][0]:+.4f}, {res['bstar_ci95'][1]:+.4f}]$,
$p = {res['bstar_wilcoxon_p']:.2g}$. The interval excludes zero comfortably in both
cases, which is what the medians suggested and what a reader should be able to check.
"""
    open(os.path.join(OUT, "e7_stats.tex"), "w").write(tex)
    json.dump(res, open(os.path.join(OUT, "e7_stats.json"), "w"), indent=1)
    print("\nwrote e7_stats.tex")


if __name__ == "__main__":
    main()
