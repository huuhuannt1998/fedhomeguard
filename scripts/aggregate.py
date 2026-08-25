#!/usr/bin/env python3
"""Canonical aggregation: results/canonical/*.jsonl -> one analysis object.

Every table, figure and prose number in the paper is produced from the object this
module returns, which is the review's fix (sec 5) for the numerical contradictions
that arose from hand-maintained numbers in separate sections.
"""
from __future__ import annotations
import glob, json, os
import numpy as np


def _key(r: dict) -> tuple:
    return (r.get("partition_type"), r.get("partition_seed"), r.get("k"),
            round(r.get("beta", 0.0), 4), r.get("mal_mode"), r.get("mal_seed"),
            r.get("dirichlet_alpha"), r.get("N"), r.get("arch"),
            tuple(r.get("devices_per_household") or ()))


def load(pattern="results/canonical/e2_*.jsonl") -> list[dict]:
    """Load canonical rows, preferring the same-predictor row where a cell was also
    measured certified-arm-only.

    Some cells are produced twice: once by a --clean-only sweep (certified arm across a
    fine beta grid) and once by a same-predictor sweep (both arms, coarser grid). The
    certified values agree because both build the same clean ensemble, but only the
    second carries EA_ensemble. Keeping both would double-count the cell; keeping the
    richer one loses nothing.
    """
    rows = []
    for path in sorted(glob.glob(pattern)):
        for line in open(path):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    best: dict = {}
    for r in rows:
        k = _key(r)
        cur = best.get(k)
        if cur is None or (cur.get("EA_ensemble") is None
                           and r.get("EA_ensemble") is not None):
            best[k] = r
    return list(best.values())


def med_iqr(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return dict(n=0, median=None, lo=None, hi=None, min=None, max=None)
    a = np.asarray(xs, float)
    return dict(n=len(a), median=round(float(np.median(a)), 6),
                lo=round(float(np.percentile(a, 25)), 6),
                hi=round(float(np.percentile(a, 75)), 6),
                min=round(float(a.min()), 6), max=round(float(a.max()), 6))


def gap_table(rows, ptypes=("iid", "device_derived")):
    """Same-predictor gap G_cert = EA_ensemble - CA, by (partition, k, beta).

    Aggregates over partition draws AND malicious-set draws, which are the two
    sources of variation the review requires to be exposed rather than hidden in a
    single run.
    """
    out = {}
    for p in ptypes:
        for k in sorted({r["k"] for r in rows if r["partition_type"] == p}):
            for b in sorted({r["beta"] for r in rows if r["partition_type"] == p and r["k"] == k}):
                sel = [r for r in rows if r["partition_type"] == p and r["k"] == k
                       and abs(r["beta"] - b) < 1e-9]
                if not sel:
                    continue
                out[(p, k, round(b, 4))] = dict(
                    n_rows=len(sel),
                    n_partition_draws=len({r["partition_seed"] for r in sel}),
                    n_mal_sets=len({(r["mal_mode"], r["mal_seed"]) for r in sel}),
                    CA=med_iqr([r["CA"] for r in sel]),
                    EA_ens=med_iqr([r["EA_ensemble"] for r in sel]),
                    G_cert=med_iqr([r["G_cert"] for r in sel]),
                    coverage=med_iqr([r["coverage"] for r in sel]),
                    ens_acc=med_iqr([r["clean_ensemble_acc"] for r in sel]),
                    margin=med_iqr([r["mean_vote_margin"] for r in sel]),
                    tau=sel[0]["tau_triv"],
                    threshold=sel[0]["cert_threshold"],
                    possible=sel[0]["combinatorially_possible"],
                    collapse_rate=round(float(np.mean([r["collapsed"] for r in sel])), 4),
                    n_collapsed=int(sum(r["collapsed"] for r in sel)),
                    CTR_mal=med_iqr([r["CTR_mal"] for r in sel]),
                    CTR_ben=med_iqr([r["CTR_ben"] for r in sel]),
                    TPR=med_iqr([r["TPR"] for r in sel]),
                    FPR=med_iqr([r["FPR"] for r in sel]),
                    FNR=med_iqr([r["FNR"] for r in sel]),
                    balanced_acc=med_iqr([r["balanced_acc"] for r in sel]),
                    cert_wrong=med_iqr([r["cert_wrong"] for r in sel]),
                )
    return out


def beta_star(rows, ptype, k, pseed):
    """Largest beta with CA > tau on that specific (partition draw, k)."""
    sel = [r for r in rows if r["partition_type"] == ptype and r["k"] == k
           and r["partition_seed"] == pseed]
    good = [r["beta"] for r in sel if r["CA"] > r["tau_triv"]]
    return max(good) if good else 0.0


def collapse_stats(rows, ptype, k, b):
    """Binomial collapse statistics: P(CA <= tau) with a Wilson interval."""
    sel = [r for r in rows if r["partition_type"] == ptype and r["k"] == k
           and abs(r["beta"] - b) < 1e-9]
    # one observation per partition draw (malicious set does not affect CA)
    per_draw = {}
    for r in sel:
        per_draw[r["partition_seed"]] = bool(r["collapsed"])
    n = len(per_draw); x = sum(per_draw.values())
    if n == 0:
        return dict(n=0)
    p = x / n
    z = 1.96
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    healthy = [r["CA"] for r in sel if not r["collapsed"]]
    coll = [r["CA"] for r in sel if r["collapsed"]]
    return dict(n=n, n_collapsed=x, p_collapse=round(p, 4),
                ci95=[round(float(max(0.0, ctr - half)), 4),
                      round(float(min(1.0, ctr + half)), 4)],
                healthy_median_CA=round(float(np.median(healthy)), 6) if healthy else None,
                collapsed_median_CA=round(float(np.median(coll)), 6) if coll else None)


def assertions(rows, gt) -> list[dict]:
    """Automated consistency checks. Any FAIL must stop the build."""
    out = []

    def chk(name, ok, detail=""):
        out.append(dict(check=name, verdict="PASS" if ok else "FAIL", detail=detail))

    # A1 CA can never exceed the clean ensemble accuracy: certified-and-correct is a
    # subset of correct.
    bad = [r for r in rows if r["CA"] > r["clean_ensemble_acc"] + 1e-9]
    chk("CA_le_ensemble_accuracy", not bad, f"{len(bad)} rows")

    # A2 coverage is monotone non-increasing in beta within a (partition, seed, k)
    viol = 0
    for key in {(r["partition_type"], r["partition_seed"], r["k"]) for r in rows}:
        sel = sorted([r for r in rows if (r["partition_type"], r["partition_seed"],
                                          r["k"]) == key], key=lambda r: r["beta"])
        cov = [r["coverage"] for r in sel]
        viol += sum(1 for i in range(1, len(cov)) if cov[i] > cov[i - 1] + 1e-9)
    chk("coverage_monotone_in_beta", viol == 0, f"{viol} violations")

    # A3 nothing is certified where the threshold is >= 1
    bad = [r for r in rows if not r["combinatorially_possible"] and r["coverage"] > 0]
    chk("no_coverage_when_geometrically_impossible", not bad, f"{len(bad)} rows")

    # A4 the four-way decomposition sums to 1
    bad = [r for r in rows if abs(r["frac_correct_certified"] + r["frac_certified_wrong"]
                                  + r["frac_geometric_impossible"]
                                  + r["frac_margin_limited"] - 1.0) > 2e-4]
    chk("failure_decomposition_sums_to_one", not bad, f"{len(bad)} rows")

    # A5 beta=0 rows must have EA == clean ensemble accuracy (no adversary)
    bad = [r for r in rows if r["m"] == 0 and r["EA_ensemble"] is not None
           and abs(r["EA_ensemble"] - r["clean_ensemble_acc"]) > 1e-9]
    chk("beta0_EA_equals_clean", not bad, f"{len(bad)} rows")

    # A6 tau_triv identical everywhere (same test set)
    taus = {r["tau_triv"] for r in rows}
    chk("single_tau_triv", len(taus) == 1, f"{sorted(taus)}")

    # A7c a row whose ensemble lost starved members is a DIFFERENT predictor from a
    # full-enumeration row: K shrinks, so c_max/K and the threshold both move. Sound,
    # but not comparable, so it must be visible rather than silently pooled.
    import math as _math
    shrunk = [r for r in rows
              if r.get("full_enumeration") and r["K"] < _math.comb(r["N"], r["k"])]
    chk("no_silently_shrunk_full_enumerations", not shrunk,
        f"{len(shrunk)} rows lost starved members")

    # A7b every row must say which c_max path produced its threshold, and the
    # load-bearing k<=3 results must all be exact rather than bounded
    bad = [r for r in rows if r.get("c_max_mode") not in ("exact", "degree_upper_bound")]
    chk("c_max_mode_recorded", not bad, f"{len(bad)} rows")
    bounded = [r for r in rows if r.get("c_max_mode") == "degree_upper_bound"]
    chk("main_grid_c_max_is_exact",
        not [r for r in bounded if r["N"] <= 20],
        f"{len(bounded)} bounded rows, {len([r for r in bounded if r['N'] <= 20])} at N<=20")

    # A7 the realised threshold must equal 2*c_max/K
    # cert_threshold is stored rounded to 6 dp, so compare at that precision
    bad = [r for r in rows if abs(r["cert_threshold"] - 2 * r["c_max"] / r["K"]) > 5e-7]
    chk("threshold_equals_2cmax_over_K", not bad, f"{len(bad)} rows")
    return out


def build(pattern="results/canonical/e2_*.jsonl") -> dict:
    rows = load(pattern)
    gt = gap_table(rows)
    return dict(n_rows=len(rows), rows=rows, gap=gt, assertions=assertions(rows, gt))


if __name__ == "__main__":
    import sys
    pat = sys.argv[1] if len(sys.argv) > 1 else "results/canonical/e2_*.jsonl"
    a = build(pat)
    print(f"rows={a['n_rows']}")
    for c in a["assertions"]:
        print(f"  {c['verdict']:5s} {c['check']:44s} {c['detail']}")
    print()
    hdr = f"{'partition':16s} {'k':>2} {'beta':>5} {'n':>3} {'CAmed':>8} {'EAmed':>8} {'Gmed':>8} {'Grange':>17} {'cov':>6} {'coll':>5}"
    print(hdr)
    for (p_, k_, b_), v in sorted(a["gap"].items()):
        g = v["G_cert"]; e = v["EA_ens"]
        rng = f"[{g['min']:.3f},{g['max']:.3f}]" if g["n"] else "-"
        ea = f"{e['median']:.4f}" if e["median"] is not None else "-"
        gm = f"{g['median']:.4f}" if g["median"] is not None else "-"
        print(f"{p_:16s} {k_:>2} {b_:>5.2f} {v['n_rows']:>3} "
              f"{v['CA']['median']:>8.4f} {ea:>8} {gm:>8} {rng:>17} "
              f"{v['coverage']['median']:>6.3f} {v['collapse_rate']:>5.2f}")
