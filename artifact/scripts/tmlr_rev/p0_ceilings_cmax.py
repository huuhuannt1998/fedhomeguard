#!/usr/bin/env python3
"""P0: verify the geometric ceilings and c_max(m) for every drawn ensemble in the canonical rows.

Independent re-implementation (not the repo's exactcert.c_max_exact):
  * full enumeration (all C(N,k) subsets kept): c_max(m) = C(N,k) - C(N-m,k), the same for every B;
  * otherwise exact enumeration over all |B| = m with a boolean incidence product, or, where
    C(N,m) > 200,000, the sound degree upper bound the repo also uses (reported separately).
The kept subsets are rebuilt from the partition and the trainability rule (a member is dropped
iff no client in its subset holds >= 16 rows), without training anything.

Writes results/p0_ceilings.json and results/p0_cmax_audit.json.
"""
import collections, glob, json, math, os, sys, time
from itertools import combinations
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C


def p_clean(N, m, k):
    return 0.0 if N - m < k else math.comb(N - m, k) / math.comb(N, k)


def beta_geo(N, k):
    best = 0.0
    for m in range(N + 1):
        if p_clean(N, m, k) > 0.5:
            best = m / N
        else:
            break
    return best


def ceilings():
    out = {}
    for N in (10, 20, 21, 50, 1000):
        out[N] = {k: beta_geo(N, k) for k in (1, 2, 3, 5, 8, 20) if k <= N}
    asym = {k: 1 - 2 ** (-1 / k) for k in (1, 2, 3, 5, 8, 20)}
    # threshold table at N = 20 for the grid used in the paper
    thr = {}
    for k in (1, 2, 3, 5, 8):
        thr[k] = {m: round(2 * (1 - p_clean(20, m, k)), 6) for m in range(0, 11)}
    # worked example, k = 1, m = 8: integer form of Eq. (1)
    K, m = 20, 8
    ex = []
    for n1 in range(10, 21):
        n2 = K - n1
        ex.append(dict(votes=f"{n1}-{n2}", n1_minus_n2=n1 - n2,
                       margin=(n1 - n2) / K, threshold=2 * m / K,
                       certified_int=bool(n1 - n2 > 2 * m),
                       certified_float=bool((n1 - n2) / K > 2.0 * m / K)))
    return dict(beta_geo=out, large_N=asym, threshold_N20=thr, worked_k1_m8=ex)


def incidence(subsets, N):
    A = np.zeros((len(subsets), N), bool)
    for j, S in enumerate(subsets):
        A[j, list(S)] = True
    return A


def cmax_indep(subsets, N, m, full):
    k = len(subsets[0])
    K = len(subsets)
    if m == 0:
        return 0, "exact"
    if m >= N:
        return K, "exact"
    if full and K == math.comb(N, k):
        return math.comb(N, k) - math.comb(N - m, k), "closed_form"
    if math.comb(N, m) > 200_000:
        A = incidence(subsets, N)
        deg = A.sum(0)
        return int(min(K, np.sort(deg)[::-1][:m].sum())), "degree_upper_bound"
    A = incidence(subsets, N).astype(np.int32)       # K x N
    best = 0
    combs = combinations(range(N), m)
    while True:
        chunk = [c for _, c in zip(range(20000), combs)]
        if not chunk:
            break
        Bm = np.zeros((len(chunk), N), np.int32)
        for i, c in enumerate(chunk):
            Bm[i, list(c)] = 1
        hits = ((Bm @ A.T) > 0).sum(1)
        best = max(best, int(hits.max()))
    return best, "exact"


def dataset_of(r):
    return "n-baiot" if abs(r["tau_triv"] - 0.900147) < 1e-4 else "iot-23"


def main():
    t0 = time.time()
    res = ceilings()
    C.dump("p0_ceilings.json", res)
    print("beta_geo(20,k):", res["beta_geo"][20])
    print("large N:", {k: round(v, 3) for k, v in res["large_N"].items()})
    print("beta_geo(50,5), (1000,5), (21,2):", res["beta_geo"][50][5], res["beta_geo"][1000][5],
          res["beta_geo"][21][2])

    # every (file, dataset, partition, seed, k, dph, alpha, N, lodo-tau) ensemble in the canonical rows
    groups = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(C.CANON, "*.jsonl"))):
        for r in C.load_rows(f):
            if r.get("k") is None or r.get("c_max") is None:
                continue
            if r.get("pairing"):          # 2-regular pairing ensembles: separate construction
                key = None
            key = (os.path.basename(f), dataset_of(r), r["partition_type"], r["partition_seed"],
                   r["k"], tuple(r.get("devices_per_household") or ()), r.get("dirichlet_alpha"),
                   r["N"], round(r["tau_triv"], 6), r.get("pairing"))
            groups[key].append(r)
    print(f"{len(groups)} ensembles in {sum(len(v) for v in groups.values())} rows")

    base = {}
    audit, mism = [], []
    n_rows = 0
    for key, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
        fname, ds, kind, seed, k, dph, alpha, N, tau, pairing = key
        if pairing is not None:
            # K = N pairs, 2-regular: every household in exactly two members
            Ks = {r["K"] for r in rows}
            for r in rows:
                m = r["m"]
                # degree-2 regular multigraph on N nodes with N edges: c_max = edges meeting B
                audit.append(dict(file=fname, seed=seed, k=k, m=m, K=r["K"], c_max_row=r["c_max"],
                                  note="pairing ensemble; c_max not re-derived (pairs not stored)"))
            continue
        lodo = abs(tau - 0.729961) > 1e-4 and ds == "iot-23"
        if lodo:
            # leave-one-capture-out folds change the training rows; skip re-derivation of K,
            # check only the closed form, which holds whenever K = C(N,k)
            for r in rows:
                if r["K"] == math.comb(N, k):
                    exp = math.comb(N, k) - math.comb(N - r["m"], k) if r["m"] < N else r["K"]
                    n_rows += 1
                    if exp != r["c_max"]:
                        mism.append(dict(key=str(key), m=r["m"], row=r["c_max"], indep=exp))
            continue
        if ds not in base:
            base[ds] = C.prepare_base(ds)
        tb = base[ds]
        cfg = C.base_cfg(ds, kind, seed, dph or (1, 3), alpha, N)
        parts, _ = C.P.build(cfg, tb["ytr_np"], tb["dtr"])
        K_cap = {1: 20, 2: 190, 3: 1140}.get(k, 200)
        if N != 20:
            K_cap = 10_000_000 if k <= 2 else K_cap
        # the ensemble size actually used is in the rows; rebuild accordingly
        Krow = max(r["K"] for r in rows)
        full = all(r.get("full_enumeration") for r in rows)
        if full or rows[0].get("n_subsets_total") == Krow:
            subs = list(combinations(range(N), k))
        else:
            # sampled: exp_e2 build_subsets with the K cap that produced the rows
            cap = 500 if (k == 3 and Krow <= 500) else 200
            cap = Krow if Krow in (200, 500) else cap
            subs, _, _ = C.build_subsets(N, k, cap, seed)
        kept = [S for S in subs if any(len(parts[i]) >= 16 for i in S)]
        for r in rows:
            n_rows += 1
            m = r["m"]
            if len(kept) != r["K"]:
                mism.append(dict(key=str(key), m=m, what="K", row=r["K"], indep=len(kept)))
                continue
            c, mode = cmax_indep(kept, N, m, len(kept) == math.comb(N, k))
            pop = 1 - p_clean(N, m, k)
            audit.append(dict(file=fname, dataset=ds, partition=kind, seed=seed, k=k,
                              dph=list(dph), alpha=alpha, N=N, m=m, K=len(kept),
                              full_enumeration=len(kept) == math.comb(N, k),
                              c_max_row=r["c_max"], c_max_indep=c, mode_indep=mode,
                              mode_row=r.get("c_max_mode"),
                              touched_frac=round(c / len(kept), 6),
                              population_touched=round(pop, 6),
                              sampled_minus_population=round(c / len(kept) - pop, 6)))
            if c != r["c_max"]:
                mism.append(dict(key=str(key), m=m, what="c_max", row=r["c_max"], indep=c,
                                 mode=mode, row_mode=r.get("c_max_mode")))
    # summary over the sampled ensembles
    samp = [a for a in audit if "full_enumeration" in a and not a["full_enumeration"]]
    by_k = collections.defaultdict(list)
    for a in samp:
        if a["m"] > 0:
            by_k[(a["k"], a["K"])].append(a["sampled_minus_population"])
    summary = dict(
        n_ensembles=len(groups), n_rows_checked=n_rows, n_mismatches=len(mism),
        mismatches=mism[:50],
        sampled_excess_touched={f"k={k},K={K}": dict(n=len(v), min=min(v), max=max(v),
                                                     median=float(np.median(v)))
                                for (k, K), v in sorted(by_k.items())},
        n_sampled_rows_below_population=sum(1 for a in samp if a["sampled_minus_population"] < -1e-12),
        secs=round(time.time() - t0, 1))
    C.dump("p0_cmax_audit.json", dict(summary=summary, rows=audit))
    print(json.dumps(summary, indent=1)[:3000])


if __name__ == "__main__":
    main()
