#!/usr/bin/env python3
"""PB10 (preregistered, predeclarations/tmlr_PB10_worst_case_attack.md): member-level worst-case
attack as a limited adaptive attack, computed exactly from banked clean member predictions.

M1 (worst case of the certificate's threat model): every member touched by B outputs the wrong
class on every flow; ties resolve as the repository's argmax (class 0).
M2 (realisable at k = 1): every touched member outputs the negation of its clean twin.

For each banked ensemble and budget m: accuracy under M1/M2 for the paper's three random malicious
sets (default_rng(1000+s).choice(20, m)) and for the adversary's best set, exhaustive over all
C(20,m) when C(20,m) * K * patterns <= 5e10, otherwise greedy + 2,000 random sets (a search: an upper
bound on the worst-case accuracy). Soundness check: every M1 accuracy must be >= certified accuracy.

    python3 pb10_worstcase.py --dry-run
    python3 pb10_worstcase.py --workers 8
Restart-safe per ensemble (results/pb10/<id>.json). Summary: results/pb10_worstcase.json."""
import argparse, glob, json, math, os, sys, time
from itertools import combinations, islice
import multiprocessing as mp
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUTD = "<artifact-root>/results/tmlr_rev/pb10"
BANKDIR = "<artifact-root>/results/tmlr_rev/member_bank"
BUDGET = 5e10
N = 20


def wanted(meta):
    j = meta["job"]
    if j["ds"] != "iot-23" or j["kind"] not in ("iid", "device_derived") or tuple(j["dph"]) != (1, 3):
        return False
    if j["seed"] in (0, 1, 2):
        return j["k"] in (1, 2, 3)                   # bank A (k=3 sampled and full)
    return 10 <= j["seed"] <= 39 and j["k"] in (1, 2)  # bank B


def patterns(preds, y):
    corr = (preds == y[None, :]).astype(np.uint8)    # K x n
    stack = np.vstack([corr, y[None, :].astype(np.uint8)])
    pat, inv, cnt = np.unique(stack, axis=1, return_inverse=True, return_counts=True)
    return pat[:-1].astype(np.float32), pat[-1].astype(np.int64), cnt.astype(np.float64)


def acc_for(Bs, inc, Cp, yp, w, K, n, model):
    """Accuracy under the attack for each B in Bs (list of tuples)."""
    Bm = np.zeros((len(Bs), N), np.float32)
    for i, b in enumerate(Bs):
        Bm[i, list(b)] = 1
    T = ((Bm @ inc.T) > 0).astype(np.float32)        # nB x K touched
    tc = T @ Cp                                       # touched members voting correct, nB x P
    c0 = Cp.sum(0)[None, :]                           # clean correct votes per pattern
    if model == "M1":
        c = c0 - tc
    else:                                             # M2: touched members flip
        c = c0 - 2 * tc + T.sum(1, keepdims=True)
    ok = np.where(yp[None, :] == 1, 2 * c > K, 2 * c >= K)
    return (ok.astype(np.float64) @ w) / n


def worst(m, inc, Cp, yp, w, K, n, model, rng):
    P = Cp.shape[1]
    if m == 0:
        return float(acc_for([()], inc, Cp, yp, w, K, n, model)[0]), "exhaustive"
    tot = math.comb(N, m)
    chunk = max(1, int(5e7 // max(P, K)))
    if tot * K * P <= BUDGET:
        best = 1.0
        it = combinations(range(N), m)
        while True:
            Bs = list(islice(it, chunk))
            if not Bs:
                break
            best = min(best, float(acc_for(Bs, inc, Cp, yp, w, K, n, model).min()))
        return best, "exhaustive"
    # search: greedy, then 2,000 random sets
    cur = ()
    for _ in range(m):
        cand = [tuple(sorted(cur + (i,))) for i in range(N) if i not in cur]
        a = acc_for(cand, inc, Cp, yp, w, K, n, model)
        cur = cand[int(a.argmin())]
    best = float(acc_for([cur], inc, Cp, yp, w, K, n, model)[0])
    Bs = [tuple(sorted(rng.choice(N, m, replace=False).tolist())) for _ in range(2000)]
    for s in range(0, len(Bs), chunk):
        best = min(best, float(acc_for(Bs[s:s + chunk], inc, Cp, yp, w, K, n, model).min()))
    return best, "search"


def run(mf):
    import common as C
    from build_member_bank import load_bank
    meta = json.load(open(mf))
    out = os.path.join(OUTD, meta["id"] + ".json")
    if os.path.exists(out):
        return meta["id"], "cached"
    j = meta["job"]
    preds, subs, _ = load_bank(meta["id"])
    tb = C.prepare_base("iot-23")
    y = tb["yte_np"]; n = len(y); K = len(subs)
    inc = np.zeros((K, N), np.float32)
    for r, S in enumerate(subs):
        inc[r, list(S)] = 1
    Cp, yp, w = patterns(preds, y)
    votes = C.votes_from_member_preds(preds)
    BF = [round(0.05 * i, 2) for i in range(11)]
    cert = C.XC.certify_exact(votes, y, subs, N, j["k"], BF, tb["tau"])
    rng = np.random.default_rng(12345)
    res = dict(id=meta["id"], kind=j["kind"], seed=j["seed"], k=j["k"], K=K, n_patterns=int(Cp.shape[1]),
               rows=[])
    t0 = time.time()
    for g in cert["grid"]:
        m = g["m"]
        e = dict(beta=g["beta"], m=m, CA=g["CA"], certifiable=g["combinatorially_possible"])
        paperB = [tuple(sorted(np.random.default_rng(1000 + s).choice(N, size=m, replace=False).tolist()))
                  if m else () for s in (0, 1, 2)]
        e["M1_paperB"] = [float(x) for x in acc_for(paperB, inc, Cp, yp, w, K, n, "M1")]
        e["M1_best"], e["M1_mode"] = worst(m, inc, Cp, yp, w, K, n, "M1", rng)
        if j["k"] == 1:
            e["M2_paperB"] = [float(x) for x in acc_for(paperB, inc, Cp, yp, w, K, n, "M2")]
            e["M2_best"], e["M2_mode"] = worst(m, inc, Cp, yp, w, K, n, "M2", rng)
        e["soundness_violation"] = bool(min(e["M1_paperB"] + [e["M1_best"]]) < g["CA"] - 1e-6)  # CA is rounded to 6 dp
        e["slack_exact_M1"] = e["M1_best"] - g["CA"]
        res["rows"].append(e)
    res["secs"] = round(time.time() - t0, 1)
    os.makedirs(OUTD, exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    return meta["id"], res["secs"]


def summarise():
    import common as C
    ens = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(OUTD, "*.json")))]
    # five-attack attacked accuracy (final round, min over attacks) from the corrected e2 rows and e24
    ea = {}
    for f in sorted(glob.glob(os.path.join(C.REPO, "results/r6_nan_fix/corrected/e2_*.jsonl"))) + \
            [os.path.join(C.CANON, "e24_slack30_iid.jsonl")]:
        for r in C.load_rows(f):
            if r.get("EA_final_round"):
                ea.setdefault((r["partition_type"], r["partition_seed"], r["k"], round(r["beta"], 2)), []).append(
                    min(r["EA_final_round"].values()))
    cells = {}
    for e in ens:
        for r in e["rows"]:
            key = (e["kind"], e["k"], e["K"], r["beta"])
            c = cells.setdefault(key, dict(slack=[], M1=[], CA=[], EA5=[], M2=[], viol=0, search=0, n=0))
            c["n"] += 1; c["slack"].append(r["slack_exact_M1"]); c["M1"].append(r["M1_best"]); c["CA"].append(r["CA"])
            # CA is stored rounded to 6 decimals, so compare with a 1e-6 tolerance
            c["viol"] += bool(min(r["M1_paperB"] + [r["M1_best"]]) < r["CA"] - 1e-6)
            c["search"] += r["M1_mode"] == "search"
            if "M2_best" in r:
                c["M2"].append(r["M2_best"])
            x = ea.get((e["kind"], e["seed"], e["k"], round(r["beta"], 2)))
            if x:
                c["EA5"].append(float(np.median(x)))
    summ = {}
    for (kind, k, K, b), c in sorted(cells.items()):
        md = lambda v: (float(np.median(v)) if v else None)
        summ[f"{kind}|k{k}|K{K}|b{b:g}"] = dict(n=c["n"], CA=md(c["CA"]), M1_best=md(c["M1"]), M2_best=md(c["M2"]),
                                               slack_exact_median=md(c["slack"]), slack_exact_max=max(c["slack"]),
                                               EA5_median=md(c["EA5"]), n_EA5=len(c["EA5"]),
                                               search_cells=c["search"], soundness_violations=c["viol"])
    viol = sum(v["soundness_violations"] for v in summ.values())
    fired = [k for k, v in summ.items() if k.startswith("iid|") and int(k.split("|")[1][1:]) <= 2
             and v["CA"] and v["CA"] > 0 and v["slack_exact_median"] is not None and v["slack_exact_median"] > 0.01]
    out = dict(n_ensembles=len(ens), soundness_violations=viol, falsifier_iid_fired=bool(fired), fired_cells=fired,
               cells=summ)
    C.dump("pb10_worstcase.json", out)
    print(json.dumps(dict(n_ensembles=len(ens), soundness_violations=viol, fired=fired), indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summarise-only", action="store_true")
    a = ap.parse_args()
    metas = [f for f in sorted(glob.glob(os.path.join(BANKDIR, "*.json"))) if wanted(json.load(open(f)))]
    todo = [f for f in metas if not os.path.exists(os.path.join(OUTD, os.path.basename(f)))]
    if a.dry_run:
        print(f"{len(metas)} banked ensembles in scope now (expected 144 when banks A and B are complete: "
              f"A 24 = 2 partitions x 3 draws x (k1, k2, k3 K500, k3 K1140); B 120), {len(todo)} to compute"); return
    if not a.summarise_only:
        with mp.get_context("spawn").Pool(a.workers) as pool:
            for jid, secs in pool.imap_unordered(run, todo):
                print(jid, secs, flush=True)
    summarise()


if __name__ == "__main__":
    main()
