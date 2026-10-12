#!/usr/bin/env python3
"""PB17 (predeclarations/tmlr_PB17_client_independent_standardization.md) and PB18
(predeclarations/tmlr_PB18_volume_budget_control.md), round tmlr5.

  PB17  standardization variants P (pooled, control), M (per member), R (5% reference sample)
        on IID / device-derived seeds 10-19 and label-Dirichlet alpha 0.5 seeds 100-109, k in {1,2}
  PB18  the 70 PB04 volume-dial partitions at k=1 with budget-scaled local epochs

    python3 pb17_18_runs.py --dry-run
    python3 pb17_18_runs.py --workers 4
    python3 pb17_18_runs.py --summarise
Restart-safe: rows already in results/pb17_18_rows.jsonl are skipped.
"""
import argparse, copy, json, math, os, sys, time
import multiprocessing as mp
from itertools import combinations
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = "<artifact-root>/results/tmlr_rev/pb17_18_rows.jsonl"
SUMMARY = "<artifact-root>/results/tmlr_rev/pb17_18_summary.json"
BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
N = 20
REF_FRAC, REF_SEED, SD_MIN = 0.05, 0, 0.01
STEPS_EQUAL = 14          # batches per epoch of an equal-size client (6,661 rows at batch 512)


def jobs(posthoc=False):
    """posthoc adds variant Rf (NOT predeclared): the reference sample with the SD floor of variant M,
    added after the predeclared R variant was seen to fail on connection states absent from the sample."""
    J = []
    for part, seeds, alpha in (("iid", range(10, 20), None), ("device_derived", range(10, 20), None),
                               ("dirichlet", range(100, 110), 0.5)):
        for s in seeds:
            for k in (1, 2):
                for v in (("P", "M", "R") + (("Rf",) if posthoc else ())):
                    J.append(dict(pb=17, partition=part, alpha=alpha, seed=s, k=k, variant=v))
    for lv in ("equal", 1000, 300, 100, 50, 20, 10):
        for s in range(10):
            J.append(dict(pb=18, partition="volume_dial", level=lv, seed=s, k=1, variant="budget"))
    return J


def key(j):
    return "|".join(f"{a}={j[a]}" for a in sorted(j))


_S = {}


def state():
    """Raw split (unstandardized), the pooled bundle the paper used, and the reference sample."""
    if _S:
        return _S
    import common as C
    cfg = C.base_cfg("iot-23", "iid", 0)
    cwd = os.getcwd(); os.chdir(C.REPO)
    try:
        b = C.DATA.load_dataset(cfg, verbose=False)
    finally:
        os.chdir(cwd)
    tr, te = C.DATA.time_split_within_device(b["y"], b["device"], cfg.data.train_frac, block=b.get("block"))
    Xtr, Xte = b["X"][tr].astype(np.float32), b["X"][te].astype(np.float32)
    tb = C.prepare_base("iot-23")
    # the pooled statistic of the paper, recomputed: must equal runner.prepare's output
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    assert np.allclose((Xtr - mu) / sd, tb["Xtr"].numpy(), atol=1e-5)
    rng = np.random.default_rng(REF_SEED)
    ref = np.sort(rng.choice(len(Xtr), size=int(round(REF_FRAC * len(Xtr))), replace=False))
    _S.update(C=C, cfg0=cfg, Xtr_raw=Xtr, Xte_raw=Xte, tb=tb, ref=ref)
    return _S


def train_members(cfg, Xtr, Xte, ytr, parts, subsets, cfg_for=None, std_for=None):
    """Final-round test predictions of each trainable member (the path of MemberCache/fl_run).
    std_for(S) -> (Xtr_S, Xte_S) gives per-member features; cfg_for(S) a per-member config."""
    import torch
    from fedhomeguard import fl as FL
    preds, kept = [], []
    for S in subsets:
        c = cfg_for(S) if cfg_for else cfg
        xtr, xte = std_for(S) if std_for else (Xtr, Xte)
        try:
            g, snaps = FL.fl_run(c, list(S), xtr, ytr, parts, snapshot_last=FL.EA_WINDOW)
        except ValueError as e:
            if "enough rows" not in str(e):
                raise
            continue
        FL.set_flat(g, snaps[-1])
        preds.append(FL.predict(g, xte).astype(np.int8))
        kept.append(tuple(int(i) for i in S))
    return (np.stack(preds) if preds else np.zeros((0, xte.shape[0]), np.int8)), kept


def run(j):
    import torch
    st = state()
    C, tb = st["C"], st["tb"]
    ytr_np, yte = tb["ytr_np"], tb["yte_np"]
    ytr = tb["ytr"]
    if j["pb"] == 17:
        cfg = C.base_cfg("iot-23", j["partition"], j["seed"], alpha=j["alpha"])
        parts_np, pmeta = C.P.build(cfg, ytr_np, tb["dtr"])
    else:
        from pb04_partitions import volume_dial
        cfg = C.base_cfg("iot-23", "iid", j["seed"])
        parts_np, _ = volume_dial(ytr_np, j["seed"], j["level"])
        pmeta = C.P.measure_skew(parts_np, ytr_np, tb["dtr"])
    subsets = list(combinations(range(N), j["k"]))
    Xtr_p, Xte_p = tb["Xtr"], tb["Xte"]
    cfg_for = std_for = None
    parts_use = parts_np
    if j["pb"] == 17 and j["variant"] in ("R", "Rf"):
        ref = st["ref"]
        Xr = st["Xtr_raw"][ref]
        mu, sd = Xr.mean(0), Xr.std(0) + 1e-6
        if j["variant"] == "Rf":
            sd = np.where(Xr.std(0) < SD_MIN, 1.0, Xr.std(0)).astype(np.float32)
        Xtr_p = torch.tensor((st["Xtr_raw"] - mu) / sd)
        Xte_p = torch.tensor((st["Xte_raw"] - mu) / sd)
        parts_use = {i: np.setdiff1d(v, ref, assume_unique=False) for i, v in parts_np.items()}
    elif j["pb"] == 17 and j["variant"] == "M":
        Xr_tr, Xr_te = st["Xtr_raw"], st["Xte_raw"]

        def std_for(S):
            rows = np.concatenate([parts_np[i] for i in S]) if len(S) else np.array([], int)
            if len(rows) == 0:
                return tb["Xtr"], tb["Xte"]
            mu, sd = Xr_tr[rows].mean(0), Xr_tr[rows].std(0)
            sd = np.where(sd < SD_MIN, 1.0, sd).astype(np.float32)
            return torch.tensor((Xr_tr - mu) / sd), torch.tensor((Xr_te - mu) / sd)
    elif j["pb"] == 18:
        def cfg_for(S):
            c = copy.deepcopy(cfg)
            n = len(parts_np[S[0]])
            b = max(1, math.ceil(n / cfg.fl.batch_size))
            c.fl.local_epochs_E = max(1, math.ceil(STEPS_EQUAL / b))
            return c
    parts_t = {i: torch.tensor(v, device="cpu") for i, v in parts_use.items()}
    t0 = time.time()
    preds, kept = train_members(cfg, Xtr_p, Xte_p, ytr, parts_t, subsets, cfg_for=cfg_for, std_for=std_for)
    votes = C.votes_from_member_preds(preds)
    cert = C.XC.certify_exact(votes, yte, kept, N, j["k"], BF, tb["tau"])
    grid = [dict(beta=g["beta"], CA=g["CA"], CTR_mal=g["CTR_mal"], CTR_ben=g["CTR_ben"],
                 coverage=g["coverage"], c_max=g["c_max"]) for g in cert["grid"]]
    out = dict(key=key(j), **j, K=len(kept), mean_margin=cert["mean_margin"], beta_star=cert["beta_star"],
               grid=grid, secs=round(time.time() - t0, 1),
               pstats={k: v for k, v in pmeta.items() if isinstance(v, (int, float, str))})
    if j["pb"] == 18:
        out["member_acc"] = {str(S[0]): float((preds[n] == yte).mean()) for n, S in enumerate(kept)}
        out["epochs"] = {str(S[0]): cfg_for(S).fl.local_epochs_E for S in kept}
        out["sizes"] = {str(i): int(len(v)) for i, v in parts_np.items()}
    if j["pb"] == 17 and j["variant"] in ("R", "Rf"):
        out["ref_rows"] = int(len(st["ref"]))
    return out


def summarise():
    import collections
    rows = [json.loads(l) for l in open(OUT) if l.strip()]
    S = {}
    by = {(r["partition"], r["seed"], r["k"], r["variant"]): r for r in rows if r["pb"] == 17}
    pb17 = {}
    for part in ("iid", "device_derived", "dirichlet"):
        for k in (1, 2):
            P = [r for (p, s, kk, v), r in by.items() if p == part and kk == k and v == "P"]
            base_b = float(np.median([r["beta_star"] for r in P])) if P else None
            for v in ("M", "R", "Rf"):
                d_b, d_ca, n_changed = [], collections.defaultdict(list), 0
                for r0 in P:
                    r1 = by.get((part, r0["seed"], k, v))
                    if not r1:
                        continue
                    db = r1["beta_star"] - r0["beta_star"]
                    d_b.append(db); n_changed += abs(db) > 1e-9
                    for g0, g1 in zip(r0["grid"], r1["grid"]):
                        d_ca[round(g0["beta"], 2)].append(g1["CA"] - g0["CA"])
                if not d_b:
                    continue
                med_ca = {b: float(np.median(x)) for b, x in d_ca.items()}
                relevant = [b for b in med_ca if base_b is not None and b <= base_b + 1e-9]
                material = (abs(float(np.median(d_b))) >= 0.05 - 1e-9 or n_changed > 3
                            or any(abs(med_ca[b]) >= 0.01 for b in relevant))
                pb17[f"{part}|k{k}|{v}"] = dict(
                    n=len(d_b), control_median_bstar=base_b,
                    variant_median_bstar=float(np.median([by[(part, r0['seed'], k, v)]['beta_star'] for r0 in P
                                                          if (part, r0['seed'], k, v) in by])),
                    median_dbstar=float(np.median(d_b)), min_dbstar=float(min(d_b)), max_dbstar=float(max(d_b)),
                    draws_changed=int(n_changed), median_dCA=med_ca,
                    max_abs_dCA_upto_bstar=max((max(abs(x) for x in d_ca[b]) for b in relevant), default=0.0),
                    material=bool(material))
    S["pb17"] = pb17
    S["pb17_material_any"] = any(v["material"] for v in pb17.values())
    # control reproduces the paper's rows where they exist
    rep = []
    for p in ("iid", "device_derived"):
        canon = {}
        import common as C
        for r in C.load_rows(f"e5f_{p}.jsonl"):
            canon[(r["partition_seed"], r["k"], round(r["beta"], 2))] = r["CA"]
        for (pp, s, k, v), r in by.items():
            if pp == p and v == "P":
                for g in r["grid"]:
                    c = canon.get((s, k, round(g["beta"], 2)))
                    if c is not None:
                        rep.append(abs(c - g["CA"]))
    S["pb17_control_reproduces_e5f_max_abs_diff"] = float(max(rep)) if rep else None
    S["pb17_control_cells_compared"] = len(rep)
    # PB18
    pb04 = [json.loads(l) for l in open("<artifact-root>/results/tmlr_rev/pb04_rows.jsonl")
            if l.strip()]
    base = collections.defaultdict(list)
    for r in pb04:
        if r["arm"] == "c":
            base[str(r["level"])].append(r)
    new = collections.defaultdict(list)
    for r in rows:
        if r["pb"] == 18:
            new[str(r["level"])].append(r)
    pb18 = {}
    for lv in ("equal", "1000", "300", "100", "50", "20", "10"):
        b, n = base.get(lv, []), new.get(lv, [])
        small = [acc for r in n for i, acc in r["member_acc"].items() if lv != "equal" and int(i) < 4]
        small0 = [acc for r in b for i, acc in (r.get("member_acc") or {}).items() if lv != "equal" and int(i) < 4]
        pb18[lv] = dict(n=len(n), baseline_median_bstar=float(np.median([r["beta_star"] for r in b])) if b else None,
                        budget_median_bstar=float(np.median([r["beta_star"] for r in n])) if n else None,
                        baseline_median_margin=float(np.median([r["mean_margin"] for r in b])) if b else None,
                        budget_median_margin=float(np.median([r["mean_margin"] for r in n])) if n else None,
                        small_member_acc_baseline=float(np.median(small0)) if small0 else None,
                        small_member_acc_budget=float(np.median(small)) if small else None)
    S["pb18"] = pb18
    rec = [pb18[l]["budget_median_bstar"] for l in ("300", "100", "20") if pb18[l]["budget_median_bstar"] is not None]
    S["pb18_prediction_held"] = bool(rec) and all(x >= 0.40 - 1e-9 for x in rec)
    S["pb18_falsifier_fired"] = sum(x <= 0.30 + 1e-9 for x in rec) >= 2
    eq = [(r0["beta_star"], r1["beta_star"]) for r0 in base["equal"] for r1 in new["equal"] if r0["seed"] == r1["seed"]]
    S["pb18_equal_reproduces"] = all(a == b for a, b in eq) if eq else None
    json.dump(S, open(SUMMARY, "w"), indent=1)
    print(json.dumps(S, indent=1)[:6000])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--posthoc", action="store_true", help="add the post hoc Rf variant")
    a = ap.parse_args()
    if a.summarise:
        return summarise()
    J = jobs(a.posthoc)
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["key"] for l in open(OUT) if l.strip()}
    todo = [j for j in J if key(j) not in done]
    if a.dry_run:
        import collections
        print(len(J), "jobs;", len(todo), "to run;", collections.Counter((j["pb"], j["k"], j["variant"]) for j in todo))
        return
    t0 = time.time()
    with mp.get_context("spawn").Pool(a.workers) as pool, open(OUT, "a") as fh:
        for r in pool.imap_unordered(run, sorted(todo, key=lambda j: -j["k"])):
            fh.write(json.dumps(r, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
            fh.flush()
            print(f"{r['key']}: beta*={r['beta_star']} K={r['K']} {r['secs']}s [{time.time()-t0:.0f}s]", flush=True)
    print(f"DONE {len(todo)} jobs")


if __name__ == "__main__":
    main()
