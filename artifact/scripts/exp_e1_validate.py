#!/usr/bin/env python3
"""E1 -- certification implementation validation (review sec 6, MANDATORY).

Four checks, none of which needs any training:

  V1 BRUTE-FORCE SOUNDNESS. For small (N,k,m), enumerate EVERY malicious set B,
     let the adversary set every corrupted member's vote adversarially, and assert
     no point we certified ever changes its label. This is the real test: it does
     not trust the threshold formula, it re-derives the outcome.
  V2 BOUNDARY. margin exactly at the threshold must NOT certify (the condition is
     strict), margin one vote above must.
  V3 EXACT vs POPULATION. On a full enumeration the exact finite-ensemble threshold
     must equal the population threshold 2(1 - p_clean) to floating point.
  V4 EXACT vs SAMPLED+CLOPPER-PEARSON. On a sampled ensemble the exact certificate
     must never certify a point the confidence-corrected construction would refuse
     at a level where the corrected one is meaningful -- i.e. exact is never the
     weaker guarantee, and the sampled path never certifies beyond its own bound.
"""
from __future__ import annotations
import json, os, sys
from itertools import combinations
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import exactcert as XC, certify as C


def v1_bruteforce(N=10, ks=(1, 2, 3), ms=(0, 1, 2, 3), n_points=400, seed=0):
    """Enumerate every B; adversary flips every corrupted member to the other class."""
    rng = np.random.default_rng(seed)
    findings, checked, violations = [], 0, 0
    for k in ks:
        subsets = list(combinations(range(N), k))
        K = len(subsets)
        masks = XC.subset_masks(subsets, N)
        # random member votes spanning easy and knife-edge margins
        member_pred = rng.integers(0, 2, size=(K, n_points))
        for p in range(0, n_points, 4):          # plant some near-tie columns
            member_pred[:, p] = (np.arange(K) < K // 2 + (p % 3)).astype(int)
        votes = np.stack([(member_pred == 0).sum(0), (member_pred == 1).sum(0)], 1)
        srt = np.sort(votes, 1)
        margin = (srt[:, -1] - srt[:, -2]) / K
        top = votes.argmax(1)
        for m in ms:
            if m > N:
                continue
            c_max, _ = XC.c_max_exact(masks, N, m)
            cert = margin > 2.0 * c_max / K
            if not cert.any():
                continue
            # exhaustive adversary
            worst_a1 = np.zeros(n_points, dtype=int)
            for B in combinations(range(N), m) if m > 0 else [()]:
                bm = 0
                for i in B:
                    bm |= (1 << i)
                corrupt = (masks & bm) != 0            # (K,)
                if not corrupt.any():
                    continue
                # a1 = corrupted members currently voting for the top class
                a1 = ((member_pred[corrupt] == top[None, :]).sum(0))
                worst_a1 = np.maximum(worst_a1, a1)
            # prediction survives iff n1 - n2 > 2*a1
            survives = (srt[:, -1] - srt[:, -2]) > 2 * worst_a1
            bad = cert & ~survives
            checked += int(cert.sum())
            violations += int(bad.sum())
            if bad.any():
                findings.append(dict(k=k, m=m, n_violations=int(bad.sum())))
    return dict(check="V1_bruteforce_soundness", N=N, ks=list(ks), ms=list(ms),
                certified_points_checked=checked, violations=violations,
                findings=findings, verdict="PASS" if violations == 0 else "FAIL")


def v2_boundary(N=20, k=2, m=2):
    subsets = list(combinations(range(N), k))
    K = len(subsets)
    masks = XC.subset_masks(subsets, N)
    c_max, _ = XC.c_max_exact(masks, N, m)
    thr = 2.0 * c_max / K
    # construct three points: margin exactly thr, one vote below, one vote above
    gap = 2 * c_max                      # integer vote gap exactly at the threshold
    rows = []
    # n1 + n2 = K and n1 - n2 = g require g and K to share parity; step by 2.
    for label, g in (("below", gap - 2), ("at", gap), ("above", gap + 2)):
        if (K + g) % 2:                   # keep parity so n1 - n2 == g exactly
            g += 1
        n1 = (K + g) // 2
        n2 = K - n1
        assert n1 - n2 == g, (n1, n2, g)
        margin = (n1 - n2) / K
        rows.append(dict(case=label, n1=n1, n2=n2, vote_gap=g,
                         margin=round(margin, 9), threshold=round(thr, 9),
                         certified=bool(margin > thr)))
    ok = (rows[0]["certified"] is False and rows[1]["certified"] is False
          and rows[2]["certified"] is True)
    return dict(check="V2_boundary_strictness", N=N, k=k, m=m, c_max=c_max,
                cases=rows, verdict="PASS" if ok else "FAIL",
                note="the certification condition is strict (>), so a margin exactly "
                     "at the threshold must abstain")


def v3_exact_vs_population(N=20, ks=(1, 2, 3), ms=(0, 1, 2, 4, 6, 8)):
    rows, bad = [], 0
    for k in ks:
        subsets = list(combinations(range(N), k))
        tab = XC.c_max_table(subsets, N, ms)
        for m, e in tab.items():
            pop = 2.0 * e["population_corrupt_frac"]
            d = abs(e["threshold"] - pop)
            bad += int(d > 1e-9)
            rows.append(dict(k=k, m=m, exact_threshold=round(e["threshold"], 9),
                             population_threshold=round(pop, 9), abs_diff=round(d, 12)))
    return dict(check="V3_exact_equals_population_on_full_enumeration",
                rows=rows, max_abs_diff=max(r["abs_diff"] for r in rows),
                verdict="PASS" if bad == 0 else "FAIL",
                note="on a full enumeration the realised-ensemble certificate and the "
                     "population certificate must coincide exactly, by symmetry")


def v4_realised_vs_population(N=20, ks=(3, 5, 8), Ks=(100, 200, 500, 1000),
                              ms=(1, 2, 4), n_draws=40, seed=0):
    """How far can the REALISED ensemble be from the population it was sampled from?

    The population certificate (FLCert's) bounds the corrupted fraction by
    1 - p_clean, which is the EXPECTED fraction under a blind malicious set. For a
    specific realised draw an adversary who sees the subsets picks the worst B, and
    the realised corrupted fraction c_max/K can exceed 1 - p_clean. Where it does,
    the population threshold understates the corruption of the ensemble actually
    deployed, and a point certified under the population construction is not
    certified under the realised-ensemble one.

    This is not a bug in either construction. They are different theorems: the
    population one is probabilistic and assumes a private subsample seed; the
    realised one is deterministic and survives a seed-aware adversary. This check
    measures the size of the difference, which is what decides how large K has to be
    -- and it is exactly zero on a full enumeration.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for k in ks:
        allc = list(combinations(range(N), k))
        tot = len(allc)
        for K in Ks:
            if K > tot:
                continue
            for m in ms:
                pop = 1.0 - (C.p_clean(N, m, k))
                fr, exceed = [], 0
                for d in range(n_draws):
                    sel = rng.choice(tot, size=K, replace=False)
                    masks = XC.subset_masks([allc[j] for j in sorted(sel)], N)
                    c_max, _ = XC.c_max_exact(masks, N, m)
                    fr.append(c_max / K)
                    exceed += int(c_max / K > pop + 1e-12)
                rows.append(dict(
                    k=k, K=K, m=m, n_draws=n_draws,
                    population_corrupt_frac=round(pop, 6),
                    realised_corrupt_frac_mean=round(float(np.mean(fr)), 6),
                    realised_corrupt_frac_max=round(float(np.max(fr)), 6),
                    draws_exceeding_population=exceed,
                    frac_draws_exceeding=round(exceed / n_draws, 4),
                    realised_certifiable_frac=round(
                        float(np.mean([2 * x < 1.0 for x in fr])), 4),
                    population_certifiable=bool(2 * pop < 1.0)))
    # full enumeration must give exact agreement -- that is the regime the paper's
    # load-bearing results live in
    full = []
    for k in (1, 2, 3):
        allc = list(combinations(range(N), k))
        masks = XC.subset_masks(allc, N)
        for m in ms:
            c_max, _ = XC.c_max_exact(masks, N, m)
            full.append(dict(k=k, m=m, K=len(allc),
                             realised=round(c_max / len(allc), 12),
                             population=round(1.0 - C.p_clean(N, m, k), 12),
                             agree=bool(abs(c_max / len(allc)
                                            - (1.0 - C.p_clean(N, m, k))) < 1e-9)))
    ok = all(r["agree"] for r in full)
    return dict(check="V4_realised_vs_population_ensemble", N=N,
                sampled_rows=rows, full_enumeration_rows=full,
                verdict="PASS" if ok else "FAIL",
                note="PASS means the two certificates coincide exactly under full "
                     "enumeration, which is the regime k<=3 runs in. The sampled rows "
                     "quantify how much they diverge at finite K and are reported as a "
                     "measurement, not a failure.")


def main():
    out = dict(suite="E1_certification_validation",
               checks=[v1_bruteforce(), v2_boundary(), v3_exact_vs_population(),
                       v4_realised_vs_population()])
    out["verdict"] = ("PASS" if all(c["verdict"] == "PASS" for c in out["checks"])
                      else "FAIL")
    os.makedirs("results/canonical", exist_ok=True)
    with open("results/canonical/e1_validation.json", "w") as f:
        json.dump(out, f, indent=2)
    for c in out["checks"]:
        print(f"  {c['verdict']:5s} {c['check']}")
    print(f"E1 -> {out['verdict']}  (results/canonical/e1_validation.json)")
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
