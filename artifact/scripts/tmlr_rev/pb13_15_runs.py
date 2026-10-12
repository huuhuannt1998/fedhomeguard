#!/usr/bin/env python3
"""PB13-PB15 (predeclared 2026-10-10T14:56:23-04:00, FedHomeGuard-P10/predeclarations/tmlr_PB13..15_*.md;
RKA jrn_01M4KJS1SS7H5EE49PSH0N145K), round tmlr4 of the TMLR revision.

  PB13  device- vs label-Dirichlet, alpha in {1, 0.5, 0.2, 0.1}, seeds 100-129, k = 1      (240 runs, IoT-23)
  PB14  coverage dial on N-BaIoT: MAL-only j in {0,2,4,6,8}, symmetric j = 2, seeds 0-4, k = 1  (30 runs)
  PB15  label-aware vs random pairing at k = 2, device-derived 1-3 types, seeds 10-39, K = 20   (60 runs)

    python3 pb13_15_runs.py --arms 13 15 --workers 5
    python3 pb13_15_runs.py --arms 14 --workers 2
Appends one JSON row per run to results/pb13_15_rows.jsonl (restart-safe by key); --summarise writes
results/pb13_15_summary.json with the predeclared tests."""
import argparse, json, os, sys, time
from itertools import combinations
import multiprocessing as mp
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

N = 20
BF = [round(0.05 * i, 2) for i in range(11)]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "pb13_15_rows.jsonl")


def jobs(arms):
    J = []
    if "13" in arms:
        for fam in ("dirichlet", "dirichlet_device"):
            for a in (1.0, 0.5, 0.2, 0.1):
                for s in range(100, 130):
                    J.append(dict(pb=13, family=fam, alpha=a, seed=s, k=1))
    if "14" in arms:
        for variant, js in (("mal_only", (0, 2, 4, 6, 8)), ("symmetric", (2,))):
            for j in js:
                for s in range(5):
                    J.append(dict(pb=14, variant=variant, j=j, seed=s, k=1))
    if "15" in arms:
        for mode in ("label_aware", "random"):
            for s in range(10, 40):
                J.append(dict(pb=15, mode=mode, seed=s, k=2))
    return J


def key(j):
    return "|".join(f"{k}={j[k]}" for k in sorted(j))


def pair_minshare(parts, ytr):
    mal = {i: float(ytr[parts[i]].sum()) for i in range(N)}
    tot = {i: float(len(parts[i])) for i in range(N)}

    def s(i, j):
        t = tot[i] + tot[j]
        m = mal[i] + mal[j]
        return min(m, t - m) / t if t else 0.0
    return s


def label_aware_cycle(parts, ytr, device, seed, restarts=12, sweeps=60):
    """Cyclic order maximising the sum over adjacent pairs of the smaller class share of the pair's pooled
    rows; multi-start greedy then 2-opt (the structure of grouping.anticluster_cycle); ties by device span."""
    from fedhomeguard import grouping as GR
    share = pair_minshare(parts, ytr)
    dsets = GR.household_device_sets(parts, device)
    sc_pair = lambda i, j: (share(i, j), len(dsets[i] | dsets[j]))  # noqa: E731

    def score(order):
        a = b = 0.0
        for t in range(N):
            x, y = sc_pair(order[t], order[(t + 1) % N])
            a += x; b += y
        return (round(a, 12), b)
    best, best_sc = None, (-1.0, -1)
    for r in range(restarts):
        rng = np.random.default_rng(seed * 1000 + r)
        start = int(rng.integers(0, N)); order = [start]; left = set(range(N)) - {start}
        while left:
            tail = order[-1]
            vals = {j: sc_pair(tail, j) for j in left}
            top_v = max(vals.values())
            top = sorted(j for j, v in vals.items() if v == top_v)
            nxt = int(top[int(rng.integers(0, len(top)))])
            order.append(nxt); left.discard(nxt)
        sc = score(order)
        for _ in range(sweeps):
            improved = False
            for a in range(N):
                for b in range(a + 2, N):
                    cand = order[:a + 1] + order[a + 1:b + 1][::-1] + order[b + 1:]
                    csc = score(cand)
                    if csc > sc:
                        order, sc, improved = cand, csc, True
            if not improved:
                break
        if sc > best_sc:
            best, best_sc = order, sc
    return best, best_sc


_TB = {}


def tb_for(ds):
    import common as C
    if ds not in _TB:
        _TB[ds] = C.prepare_base(ds)
    return _TB[ds]


def run(j):
    import torch
    import common as C
    from pb03_cvm import cvm_predict
    t0 = time.time()
    if j["pb"] == 13:
        tb = tb_for("iot-23")
        cfg = C.base_cfg("iot-23", j["family"], j["seed"], (1, 3), j["alpha"])
        t = C.with_partition(tb, cfg)
        parts = t["parts_np"]
        subs = list(combinations(range(N), 1))
    elif j["pb"] == 14:
        from pb04_partitions import coverage_dial
        tb = tb_for("n-baiot")
        try:
            parts, info = coverage_dial(tb["ytr_np"], j["seed"], j["j"], j["variant"])
        except ValueError as e:
            return dict(key=key(j), **j, infeasible=str(e))
        cfg = C.base_cfg("n-baiot", "iid", j["seed"])
        t = dict(tb)
        t["parts"] = {i: torch.tensor(v, device="cpu") for i, v in parts.items()}
        t["parts_np"] = parts
        subs = list(combinations(range(N), 1))
    else:
        from fedhomeguard import grouping as GR
        tb = tb_for("iot-23")
        cfg = C.base_cfg("iot-23", "device_derived", j["seed"], (1, 3))
        t = C.with_partition(tb, cfg)
        parts = t["parts_np"]
        if j["mode"] == "random":
            subs = GR.cycle_pairs(GR.random_cycle(N, j["seed"]))
            obj = None
        else:
            order, obj = label_aware_cycle(parts, tb["ytr_np"], tb["dtr"], j["seed"])
            subs = GR.cycle_pairs(order)
        share = pair_minshare(parts, tb["ytr_np"])
        pair_cov = [share(*S) for S in subs]
    ytr = tb["ytr_np"]
    meta = C.P.measure_skew(parts, ytr, tb["dtr"])
    preds, kept = C.member_predictions(cfg, t, subs)
    votes = C.votes_from_member_preds(preds)
    cert = C.XC.certify_exact(votes, tb["yte_np"], kept, N, j["k"], BF, tb["tau"])
    row = dict(key=key(j), **j, K=len(kept), tau=tb["tau"], mean_margin=cert["mean_margin"],
               beta_star=cert["beta_star"],
               grid=[dict(beta=g["beta"], CA=g["CA"], CTR_mal=g["CTR_mal"], CTR_ben=g["CTR_ben"],
                          coverage=g["coverage"], c_max=g["c_max"]) for g in cert["grid"]],
               partition={k: v for k, v in meta.items()}, secs=round(time.time() - t0, 1))
    if j["pb"] in (13, 14):
        row["cvm_pred"] = cvm_predict(parts, ytr, 1, BF, tb["tau"])["bstar_pred"]
    if j["pb"] == 15:
        row["pair_minshare_mean"] = float(np.mean(pair_cov))
        row["pairs_covering_both"] = int(sum(x >= 0.05 for x in pair_cov))
        row["collapsed_b02"] = bool([g for g in cert["grid"] if abs(g["beta"] - 0.2) < 1e-9][0]["CA"] <= tb["tau"])
    return row


# ------------------------------------------------------------------ predeclared tests
def perm_test(a, b, reps=100_000, seed=0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b]); n = len(a)
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(reps):
        p = rng.permutation(pool)
        if abs(p[:n].mean() - p[n:].mean()) >= abs(obs) - 1e-12:
            cnt += 1
    return float(obs), (cnt + 1) / (reps + 1)


def summarise():
    rows = [json.loads(l) for l in open(OUT) if l.strip()]
    out = {}
    r13 = [r for r in rows if r["pb"] == 13]
    if r13:
        cell = lambda f, a: [r for r in r13 if r["family"] == f and r["alpha"] == a]  # noqa: E731
        desc = {}
        for f in ("dirichlet_device", "dirichlet"):
            for a in (1.0, 0.5, 0.2, 0.1):
                c = cell(f, a)
                if not c:
                    continue
                q = lambda key_: [float(r["partition"][key_]) if key_ in r["partition"] else float(r[key_]) for r in c]  # noqa: E731
                desc[f"{f}|{a}"] = dict(n=len(c), S_JS_mean=float(np.mean(q("S_JS"))),
                                        fracDegen_median=float(np.median(q("frac_degenerate"))),
                                        margin_mean=float(np.mean([r["mean_margin"] for r in c])),
                                        margin_median=float(np.median([r["mean_margin"] for r in c])),
                                        bstar_median=float(np.median([r["beta_star"] for r in c])),
                                        bstar_mean=float(np.mean([r["beta_star"] for r in c])),
                                        collapse_b02=int(sum([g for g in r["grid"] if abs(g["beta"] - 0.2) < 1e-9][0]["CA"] <= r["tau"] for r in c)),
                                        K_min=int(min(r["K"] for r in c)), K_max=int(max(r["K"] for r in c)),
                                        cvm_exact=float(np.mean([r["cvm_pred"] == r["beta_star"] for r in c])),
                                        cvm_within1=float(np.mean([abs(r["cvm_pred"] - r["beta_star"]) <= 0.05 + 1e-9 for r in c])))
        out["pb13_cells"] = desc
        d5, l2, d1 = cell("dirichlet_device", 0.5), cell("dirichlet", 0.2), cell("dirichlet_device", 0.1)
        if len(d5) == 30 and len(l2) == 30:
            dm, pm = perm_test([r["mean_margin"] for r in d5], [r["mean_margin"] for r in l2])
            db, pb_ = perm_test([r["beta_star"] for r in d5], [r["beta_star"] for r in l2])
            out["pb13_primary"] = dict(contrast="device a=0.5 vs label a=0.2, k=1 mean vote margin", diff=dm, p=pm,
                                       n=[len(d5), len(l2)], prediction_held=bool(dm > 0 and pm < 0.05))
            out["pb13_S1_bstar"] = dict(diff=db, p=pb_)
        if len(d1) == 30 and len(l2) == 30:
            dm2, pm2 = perm_test([r["mean_margin"] for r in d1], [r["mean_margin"] for r in l2])
            out["pb13_S2"] = dict(contrast="device a=0.1 vs label a=0.2, margin", diff=dm2, p=pm2)
        if len(r13) == 240:
            y = np.array([r["mean_margin"] for r in r13])
            X = np.column_stack([np.ones(len(r13)), [r["family"] == "dirichlet_device" for r in r13],
                                 [r["partition"]["frac_degenerate"] for r in r13],
                                 [r["partition"]["S_JS"] for r in r13]]).astype(float)
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            rng = np.random.default_rng(0); bs = []
            for _ in range(10_000):
                ix = rng.integers(0, len(y), len(y))
                bs.append(np.linalg.lstsq(X[ix], y[ix], rcond=None)[0][1])
            raw = float(np.mean([r["mean_margin"] for r in d5]) - np.mean([r["mean_margin"] for r in l2]))
            out["pb13_S3"] = dict(family_coef=float(beta[1]), ci95=[float(np.percentile(bs, 2.5)),
                                  float(np.percentile(bs, 97.5))], fracDegen_coef=float(beta[2]),
                                  S_JS_coef=float(beta[3]), raw_primary_diff=raw,
                                  coverage_falsifier_fired=bool(beta[1] >= 0.10 and np.percentile(bs, 2.5) > 0))
    r14 = [r for r in rows if r["pb"] == 14]
    if r14:
        cells = {}
        for r in r14:
            cells.setdefault(f"{r['variant']}|{r['j']}", []).append(r)
        pred = {"mal_only|0": 0.45, "mal_only|2": 0.35, "mal_only|4": 0.25, "mal_only|6": 0.15, "mal_only|8": 0.05,
                "symmetric|2": 0.40}
        res, off = {}, 0
        for kk, c in sorted(cells.items()):
            ok = [r for r in c if "infeasible" not in r]
            if not ok:
                res[kk] = dict(infeasible=c[0]["infeasible"]); continue
            med = float(np.median([r["beta_star"] for r in ok]))
            res[kk] = dict(n=len(ok), predicted=pred[kk], median=med,
                           exact=float(np.mean([abs(r["beta_star"] - pred[kk]) < 1e-9 for r in ok])),
                           within1=float(np.mean([abs(r["beta_star"] - pred[kk]) <= 0.05 + 1e-9 for r in ok])),
                           cvm_pred=[r["cvm_pred"] for r in ok], observed=[r["beta_star"] for r in ok])
            off += abs(med - pred[kk]) > 0.05 + 1e-9
        out["pb14"] = dict(cells=res, cells_off_by_more_than_one_step=off, falsifier_fired=bool(off >= 2),
                           exact_all=float(np.mean([abs(r["beta_star"] - pred[f"{r['variant']}|{r['j']}"]) < 1e-9
                                                    for r in r14 if "infeasible" not in r])),
                           n_runs=len([r for r in r14 if "infeasible" not in r]))
    r15 = [r for r in rows if r["pb"] == 15]
    if r15:
        res = {}
        for m in ("label_aware", "random"):
            c = [r for r in r15 if r["mode"] == m]
            res[m] = dict(n=len(c), bstar_median=float(np.median([r["beta_star"] for r in c])),
                          bstar_mean=float(np.mean([r["beta_star"] for r in c])),
                          collapse_b02=int(sum(r["collapsed_b02"] for r in c)),
                          margin_median=float(np.median([r["mean_margin"] for r in c])),
                          pair_minshare_mean=float(np.mean([r["pair_minshare_mean"] for r in c])),
                          pairs_covering_both_median=float(np.median([r["pairs_covering_both"] for r in c])))
        e26 = [json.loads(l) for l in open(os.path.join(os.path.dirname(OUT), "e26_pairing_recount.json"))] \
            if False else None
        res["prediction_held"] = bool(res["label_aware"]["bstar_median"] >= 0.15 - 1e-9 and
                                      res["label_aware"]["collapse_b02"] < res["random"]["collapse_b02"])
        res["falsifier_fired"] = bool(res["label_aware"]["bstar_median"] <= 0.100 + 1e-9)
        out["pb15"] = res
    json.dump(out, open(os.path.join(os.path.dirname(OUT), "pb13_15_summary.json"), "w"), indent=1)
    print(json.dumps(out, indent=1)[:6000])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["13", "14", "15"])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.summarise:
        summarise(); return
    J = jobs(a.arms)
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["key"] for l in open(OUT) if l.strip()}
    todo = [j for j in J if key(j) not in done]
    print(f"{len(J)} jobs, {len(done)} done, {len(todo)} to run", flush=True)
    if a.dry_run:
        return
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for r in pool.imap_unordered(run, todo):
            with open(OUT, "a") as fh:
                fh.write(json.dumps(r, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
            print(f"{r['key']}: beta*={r.get('beta_star')} K={r.get('K')} {r.get('secs')}s", flush=True)


if __name__ == "__main__":
    main()
