#!/usr/bin/env python3
"""JISA X1 (coverage-repair arm) and X2 (step-budget-scaled main grid and repair), IoT-23, k = 1.
Predeclared in predeclarations/jisa_X1_X2_X4_seeds_budget_multiclass.md (2026-10-20, sha256 2e4d3aa6...).

Arms (every arm: partition seeds 10-39, N = 20, k = 1, exact certification on the fine beta grid):
  repair         PB04 arm a's coverage-repaired partitions (coverage_repaired_device), member seed s
  main_budget    the main-grid device-derived partitions (P.build, as exp_e2.py), member seed 0, step budget
                 scaled per client (PB18 rule: E_i = ceil(14 / b_i), b_i = ceil(n_i / 512))
  repair_budget  the coverage-repaired partitions, member seed 0, the same step-budget rule
  main           the main-grid partitions, plain budget (control only: must reproduce e5f)

    python3 scripts/jisa_x_runs.py --dry-run
    python3 scripts/jisa_x_runs.py --control            # predeclared reproduction check, run first
    python3 scripts/jisa_x_runs.py --workers 4          # X1 repair seeds 1-4 and the two X2 arms
Restart-safe: rows already in results/jisa/x_runs.jsonl (or x_control.jsonl) are skipped.

The partition constructor and the member/certificate code are the ones that produced the paper's results
(scripts/tmlr_rev: pb04_partitions.coverage_repaired_device, common.py, pb03_cvm.cvm_predict;
src/fedhomeguard: fl.fl_run, exactcert.certify_exact).
"""
import argparse
import copy
import json
import math
import multiprocessing as mp
import os
import sys
import time

import numpy as np

P2 = "<artifact-root>/scripts/tmlr_rev"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "results", "jisa", "x_runs.jsonl")
OUT_CONTROL = os.path.join(REPO, "results", "jisa", "control", "x_control.jsonl")
BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
N, K1 = 20, 1
STEPS_EQUAL = 14          # batches per epoch of an equal-size client (PB18)
SEEDS = range(10, 40)


def jobs(control=False):
    if control:
        return ([dict(arm="repair", member_seed=0, pseed=s) for s in (10, 11, 12)] +
                [dict(arm="main", member_seed=0, pseed=s) for s in (10, 11)])
    J = [dict(arm="repair", member_seed=ms, pseed=s) for ms in (1, 2, 3, 4) for s in SEEDS]
    J += [dict(arm=a, member_seed=0, pseed=s) for a in ("main_budget", "repair_budget") for s in SEEDS]
    return J


def key(j):
    return f"{j['arm']}|ms={j['member_seed']}|ps={j['pseed']}|k={K1}"


_S = {}


def state():
    if not _S:
        sys.path.insert(0, P2)
        import common as C
        _S["C"] = C
        _S["tb"] = C.prepare_base("iot-23")
    return _S["C"], _S["tb"]


def run(j):
    import torch
    C, tb = state()
    from pb04_partitions import coverage_repaired_device
    from pb03_cvm import cvm_predict
    from fedhomeguard import fl as FL
    ytr_np, dtr, yte = tb["ytr_np"], tb["dtr"], tb["yte_np"]
    if j["arm"] in ("repair", "repair_budget"):
        parts, info = coverage_repaired_device(ytr_np, dtr, j["pseed"])
        if parts is None:
            return dict(key=key(j), **j, failed="repair did not converge", info=info)
    else:
        cfg_p = C.base_cfg("iot-23", "device_derived", j["pseed"])
        parts = C.with_partition(tb, cfg_p)["parts_np"]
        info = {}
    cfg = C.base_cfg("iot-23", "device_derived", j["pseed"])
    cfg.fl.seed = j["member_seed"]
    budget = j["arm"].endswith("_budget")

    def cfg_for(S):
        if not budget:
            return cfg
        c = copy.deepcopy(cfg)
        n = sum(len(parts[i]) for i in S)
        b = max(1, math.ceil(n / cfg.fl.batch_size))
        c.fl.local_epochs_E = max(1, math.ceil(STEPS_EQUAL / b))
        return c

    parts_t = {i: torch.tensor(v, device="cpu") for i, v in parts.items()}
    preds, kept, epochs = [], [], {}
    t0 = time.time()
    for S in [(i,) for i in range(N)]:
        c = cfg_for(S)
        try:
            g, snaps = FL.fl_run(c, list(S), tb["Xtr"], tb["ytr"], parts_t, snapshot_last=FL.EA_WINDOW)
        except ValueError as e:
            if "enough rows" not in str(e):
                raise
            continue
        FL.set_flat(g, snaps[-1])
        preds.append(FL.predict(g, tb["Xte"]).astype(np.int8))
        kept.append(S)
        epochs[str(S[0])] = c.fl.local_epochs_E
    preds = np.stack(preds)
    votes = C.votes_from_member_preds(preds)
    cert = C.XC.certify_exact(votes, yte, kept, N, K1, BF, tb["tau"])
    grid = [dict(beta=g["beta"], CA=g["CA"], CTR_mal=g["CTR_mal"], CTR_ben=g["CTR_ben"],
                 coverage=g["coverage"], c_max=g["c_max"]) for g in cert["grid"]]
    ca20 = next(g["CA"] for g in cert["grid"] if abs(g["beta"] - 0.2) < 1e-9)
    meta = C.P.measure_skew(parts, ytr_np, dtr)
    sizes = {str(i): int(len(v)) for i, v in parts.items()}
    return dict(key=key(j), **j, k=K1, K=len(kept), budget=budget, beta_star=cert["beta_star"],
                mean_margin=cert["mean_margin"], collapse20=bool(ca20 <= tb["tau"] + 1e-12), tau=tb["tau"],
                cvm_pred=cvm_predict(parts, ytr_np, K1, BF, tb["tau"])["bstar_pred"], grid=grid, sizes=sizes,
                epochs=epochs, info=info, secs=round(time.time() - t0, 1),
                partition={k: v for k, v in meta.items() if isinstance(v, (int, float, str))})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--control", action="store_true")
    a = ap.parse_args()
    out = OUT_CONTROL if a.control else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    J = jobs(a.control)
    done = {json.loads(l)["key"] for l in open(out) if l.strip()} if os.path.exists(out) else set()
    todo = [j for j in J if key(j) not in done]
    if a.dry_run:
        import collections
        print(f"{len(J)} jobs, {len(done)} done, {len(todo)} to run:",
              dict(collections.Counter((j['arm'], j['member_seed']) for j in todo)))
        return
    t0 = time.time()
    with mp.get_context("spawn").Pool(a.workers) as pool, open(out, "a") as fh:
        for r in pool.imap_unordered(run, todo):
            fh.write(json.dumps(r, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
            fh.flush()
            print(f"{r['key']}: beta*={r.get('beta_star')} collapse20={r.get('collapse20')} K={r.get('K')} "
                  f"[{time.time() - t0:.0f}s]", flush=True)
    print(f"DONE {len(todo)} jobs -> {out}")


if __name__ == "__main__":
    main()
