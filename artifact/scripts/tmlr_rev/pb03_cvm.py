#!/usr/bin/env python3
"""PB03 (preregistered, predeclarations/tmlr_PB03_coverage_vote_model.md): the coverage-vote model
(CVM) predicts beta* at k = 1 and k = 2 from per-client label composition alone, before training,
and is scored against the observed beta* in the canonical rows. Partition rebuilds only (no
training). Also harvests the pre-stated counterexample classes CX1-CX4.

    python3 pb03_cvm.py --dry-run      # list the draw sets it will score
    python3 pb03_cvm.py                # full run (IoT-23 + N-BaIoT via nbaiot_light)
Writes results/pb03_cvm.json and results/pb03_cvm_draws.jsonl.
"""
import argparse, collections, glob, json, math, os, sys
from itertools import combinations
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

MIN_ROWS, LO, HI = 16, 0.05, 0.95
BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]

# (label, dataset, partition kind, dph, file pattern, k list)
SETS = [("iot23 IID", "iot-23", "iid", (1, 3), ["e5f_iid.jsonl"], (1, 2)),
        ("iot23 device 1-3 (e5f)", "iot-23", "device_derived", (1, 3), ["e5f_device_derived.jsonl"], (1, 2))]
for lo, hi in ((1, 1), (1, 3), (2, 5), (3, 8), (5, 10)):
    SETS.append((f"iot23 device {lo}-{hi} (e11b/e22)", "iot-23", "device_derived", (lo, hi),
                 [f"e11b_dph{lo}_{hi}.jsonl", f"e22_k2rich_{lo}_{hi}.jsonl"], (1, 2)))
SETS += [("iot23 label-Dirichlet fine", "iot-23", "dirichlet", (1, 3), ["e7f_labelskew.jsonl"], (1, 2)),
         ("iot23 device-Dirichlet fine", "iot-23", "dirichlet_device", (1, 3), ["e7f_devskew.jsonl"], (1, 2)),
         ("iot23 label-Dirichlet coarse a>=3", "iot-23", "dirichlet", (1, 3), ["e7_labelskew.jsonl"], (1, 2)),
         ("iot23 device-Dirichlet coarse a>=3", "iot-23", "dirichlet_device", (1, 3), ["e7_devskew.jsonl"], (1, 2)),
         ("iot23 volume", "iot-23", "volume", (1, 3), ["e7_volskew.jsonl"], (1, 2)),
         ("nbaiot IID", "n-baiot", "iid", (1, 2), ["nb9_cert_iid.jsonl"], (1, 2)),
         ("nbaiot device 1-2", "n-baiot", "device_derived", (1, 2), ["nb9_cert_device_derived.jsonl"], (1, 2))]
for lo, hi in ((1, 1), (1, 3), (2, 5), (3, 8), (5, 9)):
    SETS.append((f"nbaiot device {lo}-{hi} (e21/e23)", "n-baiot", "device_derived", (lo, hi),
                 [f"e21_nbrich_{lo}_{hi}.jsonl", f"e23_nbk2rich_{lo}_{hi}.jsonl"], (1, 2)))


def observed(rows):
    """{(seed, alpha, k): dict(bstar, grid, S_JS, tau, collapse02)}"""
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["partition_seed"], r.get("dirichlet_alpha"), r["k"])].append(r)
    out = {}
    for key, v in by.items():
        good = [r["beta"] for r in v if r["CA"] > r["tau_triv"]]
        c02 = [r["CA"] <= r["tau_triv"] for r in v if abs(r["beta"] - 0.2) < 1e-9]
        out[key] = dict(bstar=max(good) if good else 0.0, grid=sorted({round(r["beta"], 4) for r in v}),
                        S_JS=v[0]["S_JS"], tau=v[0]["tau_triv"], K=v[0]["K"],
                        collapse02=(c02[0] if c02 else None))
    return out


def cvm_predict(parts, ytr, k, grid, tau, N=20):
    sizes = {i: len(parts[i]) for i in range(N)}
    active = {i for i in range(N) if sizes[i] >= MIN_ROWS}
    mal = {i: float(ytr[parts[i]].sum()) for i in range(N)}
    kept, types = [], []
    for S in combinations(range(N), k):
        act = [i for i in S if i in active]
        if not act:
            continue
        n = sum(sizes[i] for i in act); q = sum(mal[i] for i in act) / n
        kept.append(S); types.append("M" if q > HI else ("B" if q < LO else "X"))
    K = len(kept)
    nM, nB = types.count("M"), types.count("B")
    ms = sorted({int(round(b * N)) for b in grid})
    if K == math.comb(N, k):                       # full enumeration: closed form
        cm = {m: (math.comb(N, k) - math.comb(N - m, k)) if m < N else K for m in ms}
    elif k == 1:                                   # one client per member
        cm = {m: min(m, K) for m in ms}
    else:                                          # dropped members: exact enumeration (repo code)
        ctab = C.XC.c_max_table(kept, N, ms)
        cm = {m: ctab[m]["c_max"] for m in ms}
    best = 0.0
    ca_pred = {}
    for b in grid:
        c = cm[int(round(b * N))]
        ben_ok = (K - 2 * nM) > 2 * c
        mal_ok = (K - 2 * nB) > 2 * c
        ca = tau * mal_ok + (1 - tau) * ben_ok
        ca_pred[b] = ca
        if ca > tau + 1e-12:
            best = max(best, b)
    return dict(bstar_pred=best, K=K, n_M=nM, n_B=nB, n_X=types.count("X"),
                collapse02_pred=(ca_pred.get(0.2, None) is not None and ca_pred[0.2] <= tau + 1e-12))


def base_for(ds):
    if ds == "iot-23":
        tb = C.prepare_base("iot-23")
        return dict(ytr_np=tb["ytr_np"], dtr=tb["dtr"])
    import nbaiot_light
    return nbaiot_light.load_labels_devices()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    plan = []
    for label, ds, kind, dph, files, ks in SETS:
        rows = [r for f in files for r in C.load_rows(f)]
        if "coarse" in label:
            rows = [r for r in rows if (r.get("dirichlet_alpha") or 0) >= 3.0]
        obs = observed(rows)
        plan.append((label, ds, kind, dph, obs))
    if a.dry_run:
        for label, ds, kind, dph, obs in plan:
            ks = collections.Counter(k for (_, _, k) in obs)
            print(f"{label:38s} {ds:8s} {kind:17s} dph={dph} draws by k: {dict(ks)}")
        print("total (draw, k) cells:", sum(len(p[4]) for p in plan)); return
    bases = {}
    out_rows, problems = [], []
    for label, ds, kind, dph, obs in plan:
        if ds not in bases:
            bases[ds] = base_for(ds)
        b = bases[ds]
        cache = {}
        for (seed, alpha, k), o in sorted(obs.items(), key=lambda kv: str(kv[0])):
            if (seed, alpha) not in cache:
                cfg = C.base_cfg(ds, kind, seed, dph, alpha)
                parts, meta = C.P.build(cfg, b["ytr_np"], b["dtr"])
                cache[(seed, alpha)] = (parts, meta)
            parts, meta = cache[(seed, alpha)]
            if abs(meta["S_JS"] - o["S_JS"]) > 1e-5:
                problems.append(dict(set=label, seed=seed, alpha=alpha, k=k, S_JS_row=o["S_JS"],
                                     S_JS_rebuilt=meta["S_JS"])); continue
            p = cvm_predict(parts, b["ytr_np"], k, o["grid"], o["tau"])
            if p["K"] != o["K"]:
                problems.append(dict(set=label, seed=seed, alpha=alpha, k=k, K_row=o["K"], K_cvm=p["K"]))
            step = 0.05
            out_rows.append(dict(set=label, dataset=ds, kind=kind, dph=list(dph), seed=seed, alpha=alpha, k=k,
                                 S_JS=o["S_JS"], frac_degenerate=meta["frac_degenerate"],
                                 min_class_support=meta["min_class_support"],
                                 min_size_share=meta["min_size_share"],
                                 bstar_obs=o["bstar"], bstar_pred=p["bstar_pred"],
                                 err_steps=round((p["bstar_pred"] - o["bstar"]) / step),
                                 collapse02_obs=o["collapse02"], collapse02_pred=p["collapse02_pred"],
                                 K=p["K"], n_M=p["n_M"], n_B=p["n_B"], n_X=p["n_X"]))
    def score(rs):
        if not rs:
            return dict(n=0)
        e = np.array([r["err_steps"] for r in rs])
        po = np.array([r["bstar_obs"] for r in rs]); pp = np.array([r["bstar_pred"] for r in rs])
        rho = spearmanr(pp, po).statistic if len(set(po)) > 1 and len(set(pp)) > 1 else None
        cc = [(r["collapse02_obs"], r["collapse02_pred"]) for r in rs if r["collapse02_obs"] is not None]
        return dict(n=len(rs), exact=float((e == 0).mean()), within1=float((abs(e) <= 1).mean()),
                    mae_steps=float(abs(e).mean()), mean_signed_steps=float(e.mean()),
                    spearman=(None if rho is None else float(rho)),
                    collapse02_agree=(float(np.mean([x == y for x, y in cc])) if cc else None))
    summary = {}
    for k in (1, 2):
        for label in [s[0] for s in SETS]:
            summary[f"{label}|k{k}"] = score([r for r in out_rows if r["set"] == label and r["k"] == k])
    dev_k1 = [r for r in out_rows if r["dataset"] == "iot-23" and r["kind"] == "device_derived" and r["k"] == 1]
    # e5f and e11b 1-3 share 20 draws: count each (dph, seed) once for the falsifier
    seen, dedup = set(), []
    for r in dev_k1:
        key = (tuple(r["dph"]), r["seed"])
        if key not in seen:
            seen.add(key); dedup.append(r)
    fz = score(dedup)
    falsifier = dict(**fz, fired=bool(fz["within1"] < 0.70 or (fz["spearman"] or 0) < 0.80))
    # counterexamples CX1-CX3 over the audit cells, CX4 over all clean canonical rows
    cells = [json.loads(l) for l in open(os.path.join(C.REPO, "results/analysis/instruments.jsonl"))]
    med_sjs = float(np.median([c["S_JS"] for c in cells]))
    norm = lambda c: c["beta_star"] / c["beta_geo"]
    cx = dict(
        CX1=[c for c in cells if c["S_JS"] >= 0.8 and norm(c) >= 0.8],
        CX2=[c for c in cells if c["S_JS"] <= med_sjs and norm(c) <= 0.34],
        CX3=[c for c in cells if c["frac_degenerate"] == 0 and c["min_class_support"] == 1 and norm(c) <= 0.67])
    cx4 = []
    for f in sorted(glob.glob(os.path.join(C.CANON, "*.jsonl"))):
        for r in C.load_rows(f):
            if r.get("coverage") is not None and r.get("n_class", 2) == 2 and r["coverage"] >= 0.9 \
                    and r["CA"] <= r["tau_triv"] and r.get("combinatorially_possible", True):
                cx4.append(dict(file=os.path.basename(f), seed=r.get("partition_seed"), k=r.get("k"), beta=r.get("beta"),
                                coverage=r["coverage"], CA=r["CA"], cert_wrong=r.get("cert_wrong")))
    short = lambda c: {k: c[k] for k in ("dataset", "family", "pseed", "alpha", "k", "S_JS",
                                         "frac_degenerate", "min_class_support", "min_size_share", "beta_star")}
    res = dict(summary=summary, falsifier_iot23_device_k1=falsifier, problems=problems,
               counterexamples=dict(median_S_JS=med_sjs,
                                    **{k: dict(n=len(v), cells=[short(c) for c in v]) for k, v in cx.items()},
                                    CX4=dict(n=len(cx4), n_distinct=len({(x["file"], x["seed"], x["k"]) for x in cx4}),
                                             rows=cx4[:200])))
    C.dump("pb03_cvm.json", res)
    with open(os.path.join(C.OUTDIR, "pb03_cvm_draws.jsonl"), "w") as fh:
        for r in out_rows:
            fh.write(json.dumps(r) + "\n")
    for k, v in summary.items():
        print(k, v)
    print("FALSIFIER (iot23 device-derived k=1):", falsifier)
    print("problems:", len(problems), "CX counts:", {k: len(v) for k, v in cx.items()}, "CX4", len(cx4))


if __name__ == "__main__":
    main()
