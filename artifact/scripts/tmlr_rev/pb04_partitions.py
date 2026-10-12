#!/usr/bin/env python3
"""PB04 (preregistered, predeclarations/tmlr_PB04_one_factor_partitions.md): one-factor-at-a-time
controlled partitions on IoT-23, trained with the repository's member code (fl_run, seed 0).

  a  coverage-repaired device-derived (e5f seeds 10-39, k=1; seeds 10-19 also k=2)
  b  coverage dial from IID (seeds 0-9): symmetric j in {0,2,4,6,8}, MAL-only j in {2,4,6,8}; k=1,
     and k=2 on seeds 0-4
  c  volume dial at full coverage (seeds 0-9): 4 small clients of s rows, s in
     {equal,1000,300,100,50,20,10}; k=1

    python3 pb04_partitions.py --arms a b c --dry-run        # list jobs only
    python3 pb04_partitions.py --arms a b c --workers 8       # full speed (quiet machine)
Restart-safe: rows already in results/pb04_rows.jsonl are skipped. Every job also records the CVM
prediction (pb03_cvm.cvm_predict) made from the partition before training.
"""
import argparse, json, math, os, sys, time
import multiprocessing as mp
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = "<artifact-root>/results/tmlr_rev/pb04_rows.jsonl"
BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
N = 20


# ------------------------------------------------------------------------------ constructors
def coverage_repaired_device(ytr, dtr, seed, dph=(1, 3), lo=0.05, hi=0.95, max_pass=500):
    """device_derived_partition, but households outside [lo, hi] malicious share are re-drawn until
    every household holds both classes. Each device's rows are split evenly among its owners."""
    rng = np.random.default_rng(seed)
    devs = [int(d) for d in np.unique(dtr)]
    rows = {d: np.where(dtr == d)[0] for d in devs}
    nrow = {d: len(rows[d]) for d in devs}
    nmal = {d: float(ytr[rows[d]].sum()) for d in devs}
    draw = lambda: [int(x) for x in rng.choice(devs, size=min(int(rng.integers(dph[0], dph[1] + 1)),
                                                              len(devs)), replace=False)]
    own = [draw() for _ in range(N)]
    passes = 0
    for passes in range(1, max_pass + 1):
        owners = {d: [i for i in range(N) if d in own[i]] for d in devs}
        for d in devs:                                   # no orphaned device type
            if not owners[d]:
                i = int(rng.integers(0, N)); own[i].append(d); owners[d] = [i]
        share = []
        for i in range(N):
            n = sum(nrow[d] / len(owners[d]) for d in own[i])
            m = sum(nmal[d] / len(owners[d]) for d in own[i])
            share.append(m / n if n else 0.0)
        bad = [i for i in range(N) if not (lo <= share[i] <= hi)]
        if not bad:
            break
        for i in bad:
            own[i] = draw()
    else:
        return None, dict(converged=False, passes=passes)
    owners = {d: [i for i in range(N) if d in own[i]] for d in devs}
    buckets = {i: [] for i in range(N)}
    for d in devs:
        idx = rows[d].copy(); rng.shuffle(idx)
        for chunk, i in zip(np.array_split(idx, len(owners[d])), owners[d]):
            buckets[i].append(chunk)
    parts = {i: np.sort(np.concatenate(v)) if v else np.array([], int) for i, v in buckets.items()}
    return parts, dict(converged=True, passes=passes,
                       types_per_household=[len(own[i]) for i in range(N)])


def coverage_dial(ytr, seed, j, variant):
    """IID sizes (equal +-1); j clients made one-class by exchanging rows within class."""
    from fedhomeguard import partition as P
    base = P.iid_partition(len(ytr), N, seed)
    sizes = [len(base[i]) for i in range(N)]
    rng = np.random.default_rng(10_000 + seed)
    chosen = [int(x) for x in rng.choice(N, size=j, replace=False)] if j else []
    if variant == "symmetric":
        cls = {i: (1 if t < j // 2 else 0) for t, i in enumerate(chosen)}
    else:
        cls = {i: 1 for i in chosen}
    pool = {c: list(rng.permutation(np.where(ytr == c)[0])) for c in (0, 1)}
    parts = {}
    for i, c in cls.items():
        take = pool[c][:sizes[i]]; pool[c] = pool[c][sizes[i]:]
        if len(take) < sizes[i]:
            raise ValueError("not enough rows of the class for the one-class clients")
        parts[i] = np.sort(np.array(take))
    rest = rng.permutation(np.array(pool[0] + pool[1], dtype=int))
    pos = 0
    for i in range(N):
        if i in parts:
            continue
        parts[i] = np.sort(rest[pos:pos + sizes[i]]); pos += sizes[i]
    assert pos == len(rest)
    return parts, dict(one_class=sorted(chosen), classes={str(i): c for i, c in cls.items()})


def volume_dial(ytr, seed, s, n_small=4):
    from fedhomeguard import partition as P
    if s == "equal":
        return P.iid_partition(len(ytr), N, seed), dict(small=[])
    rng = np.random.default_rng(20_000 + seed)
    perm = rng.permutation(len(ytr))
    parts = {}
    for i in range(n_small):
        parts[i] = np.sort(perm[i * s:(i + 1) * s])
    rest = perm[n_small * s:]
    for t, chunk in enumerate(np.array_split(rest, N - n_small)):
        parts[n_small + t] = np.sort(chunk)
    return parts, dict(small=list(range(n_small)), s=s)


# ----------------------------------------------------------------------------------- jobs
def jobs(arms):
    J = []
    if "a" in arms:
        for s in range(10, 40):
            J.append(dict(arm="a", variant="coverage_repaired", level="1-3", seed=s, k=1))
            if s < 20:
                J.append(dict(arm="a", variant="coverage_repaired", level="1-3", seed=s, k=2))
    if "b" in arms:
        for variant, js in (("symmetric", (0, 2, 4, 6, 8)), ("mal_only", (2, 4, 6, 8))):
            for j in js:
                for s in range(10):
                    J.append(dict(arm="b", variant=variant, level=j, seed=s, k=1))
                    if s < 5:
                        J.append(dict(arm="b", variant=variant, level=j, seed=s, k=2))
    if "c" in arms:
        for lv in ("equal", 1000, 300, 100, 50, 20, 10):
            for s in range(10):
                J.append(dict(arm="c", variant="volume_dial", level=lv, seed=s, k=1))
    return J


def key(j):
    return f"{j['arm']}|{j['variant']}|{j['level']}|{j['seed']}|{j['k']}"


_TB = {}


def run(j):
    import torch
    import common as C
    from pb03_cvm import cvm_predict
    if "tb" not in _TB:
        _TB["tb"] = C.prepare_base("iot-23")
    tb = _TB["tb"]
    ytr, dtr = tb["ytr_np"], tb["dtr"]
    if j["arm"] == "a":
        parts, info = coverage_repaired_device(ytr, dtr, j["seed"])
        if parts is None:
            return dict(key=key(j), **j, failed="repair did not converge", info=info)
    elif j["arm"] == "b":
        parts, info = coverage_dial(ytr, j["seed"], j["level"], j["variant"])
    else:
        parts, info = volume_dial(ytr, j["seed"], j["level"])
    meta = C.P.measure_skew(parts, ytr, dtr)
    cfg = C.base_cfg("iot-23", "iid", j["seed"])
    t = dict(tb)
    t["parts"] = {i: torch.tensor(v, device="cpu") for i, v in parts.items()}
    t["parts_np"] = parts
    pred = cvm_predict(parts, ytr, j["k"], BF, tb["tau"])
    from itertools import combinations
    subs = list(combinations(range(N), j["k"]))
    preds, kept = C.member_predictions(cfg, t, subs)
    votes = C.votes_from_member_preds(preds)
    cert = C.XC.certify_exact(votes, tb["yte_np"], kept, N, j["k"], BF, tb["tau"])
    grid = [dict(beta=g["beta"], CA=g["CA"], CTR_mal=g["CTR_mal"], CTR_ben=g["CTR_ben"],
                 coverage=g["coverage"], cert_wrong=g["cert_wrong"], c_max=g["c_max"])
            for g in cert["grid"]]
    # small members' clean accuracy (volume dial) and one-class members' accuracy
    acc = {i: float((preds[n] == tb["yte_np"]).mean()) for n, i in enumerate([S[0] for S in kept])} \
        if j["k"] == 1 else None
    return dict(key=key(j), **j, info=info, K=len(kept), mean_margin=cert["mean_margin"],
                beta_star=cert["beta_star"], cvm_pred=pred["bstar_pred"], cvm=pred,
                partition={k: v for k, v in meta.items()}, grid=grid, member_acc=acc,
                member_trainings=len(kept))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["a", "b", "c"])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    J = jobs(a.arms)
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["key"] for l in open(OUT) if l.strip()}
    todo = [j for j in J if key(j) not in done]
    if a.dry_run:
        import collections
        c = collections.Counter((j["arm"], j["k"]) for j in todo)
        tr = sum(20 if j["k"] == 1 else 190 for j in todo)
        print(f"{len(J)} jobs, {len(done)} done, {len(todo)} to run: {dict(c)}; member trainings {tr}")
        return
    t0 = time.time()
    with mp.get_context("spawn").Pool(a.workers) as pool, open(OUT, "a") as fh:
        for r in pool.imap_unordered(run, sorted(todo, key=lambda j: -j["k"])):
            fh.write(json.dumps(r, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
            fh.flush()
            print(f"{r['key']}: beta*={r.get('beta_star')} cvm={r.get('cvm_pred')} K={r.get('K')} "
                  f"[{time.time()-t0:.0f}s]", flush=True)
    print(f"DONE {len(todo)} jobs")


if __name__ == "__main__":
    main()
