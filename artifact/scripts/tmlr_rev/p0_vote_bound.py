#!/usr/bin/env python3
"""P0: soundness of Eq. (1) on the ACTUAL drawn ensembles at N = 20, by brute force.

For every banked ensemble (bank A: IoT-23, IID and device-derived, draws 0-2, k = 1, 2, 3 sampled
K=500, 3 full K=1140, 5 and 8 sampled K=200) and every budget m at which the threshold is below 1,
enumerate every malicious set |B| = m. For each test flow, the member-level worst case is that every
touched member voting the flow's clean top class switches to the other class, so the flow keeps its
label against every attack iff

    n1 - n2 > 2 * a1*(x),   a1*(x) = max_{|B|=m} #{touched members voting top(x)}.

Eq. (1) certifies iff n1 - n2 > 2 c_max(m). Soundness requires: certified by Eq. (1) => survives.
This script reports violations (expected 0) and stores a1* per flow for the Phase B tightness
analysis (results/p0_vote_bound_a1.npz), without summarising tightness here.

Also prints one worked flow-level example at k = 1, m = 8.
"""
import json, math, os, sys, time
from itertools import combinations, islice
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from build_member_bank import load_bank, job_id, jobs


def incidence(subsets, N=20):
    A = np.zeros((len(subsets), N), np.float32)
    for j, S in enumerate(subsets):
        A[j, list(S)] = 1
    return A


def worst_a1(preds, subsets, m, cols, N=20, chunk=4096):
    """a1* for the flows in `cols` (indices), grouping identical top-voter patterns."""
    V = preds[:, cols]                                  # K x P0 (0/1 member labels)
    votes1 = V.sum(0)
    K = preds.shape[0]
    top = (votes1 > K - votes1).astype(np.int8)         # argmax tie -> class 0
    T = (V == top[None, :]).astype(np.uint8)            # members voting the flow's top class
    pat, inv = np.unique(T, axis=1, return_inverse=True)
    pat = pat.astype(np.float32)                        # K x P
    A = incidence(subsets, N)                           # K x N
    best = np.zeros(pat.shape[1], np.float32)
    it = combinations(range(N), m)
    while True:
        Bs = list(islice(it, chunk))
        if not Bs:
            break
        Bm = np.zeros((len(Bs), N), np.float32)
        for i, b in enumerate(Bs):
            Bm[i, list(b)] = 1
        touched = ((Bm @ A.T) > 0).astype(np.float32)   # nB x K
        a1 = touched @ pat                              # nB x P
        best = np.maximum(best, a1.max(0))
    return best[inv.ravel()].astype(np.int32), top


def main():
    if "--dry-run" in sys.argv:
        have = [job_id(j) for j in jobs("A")
                if os.path.exists(os.path.join(C.OUTDIR, "member_bank", job_id(j) + ".json"))]
        print(f"P0 brute force: {len(have)} of {len(jobs('A'))} bank-A ensembles present"); return
    t0 = time.time()
    store, report = {}, []
    for j in jobs("A"):
        jid = job_id(j)
        if not os.path.exists(os.path.join(C.OUTDIR, "member_bank", jid + ".npz")):
            report.append(dict(id=jid, status="missing")); continue
        preds, subs, meta = load_bank(jid)
        K, n = preds.shape
        k = j["k"]
        votes1 = preds.sum(0).astype(np.int64)
        n1 = np.maximum(votes1, K - votes1); n2 = K - n1
        gap = n1 - n2
        ctab = C.XC.c_max_table(subs, 20, range(0, 11))
        tested = 0; viol = 0; per_m = {}
        for m in range(1, 11):
            cm = ctab[m]["c_max"]
            if 2 * cm >= K:          # threshold >= 1: nothing certifiable
                break
            cert = gap > 2 * cm
            cols = np.where(cert)[0]
            if len(cols) == 0:
                per_m[m] = dict(c_max=cm, n_cert=0); continue
            a1, _ = worst_a1(preds, subs, m, cols)
            surv = gap[cols] > 2 * a1
            v = int((~surv).sum())
            tested += len(cols); viol += v
            per_m[m] = dict(c_max=cm, n_cert=int(len(cols)), violations=v)
            # store a1* for ALL flows (Phase B tightness), not just certified ones
            a1_all, _ = worst_a1(preds, subs, m, np.arange(n))
            store[f"{jid}|m{m}"] = a1_all
        report.append(dict(id=jid, K=K, k=k, certified_points_tested=tested, violations=viol,
                           per_m=per_m))
        print(f"{jid}: tested {tested} certified (flow, m) pairs, violations {viol}  "
              f"[{time.time()-t0:.0f}s]", flush=True)
    np.savez_compressed(os.path.join(C.OUTDIR, "p0_vote_bound_a1.npz"), **store)
    tot = sum(r.get("certified_points_tested", 0) for r in report)
    vio = sum(r.get("violations", 0) for r in report)

    # worked example: IID draw 0, k = 1, m = 8
    preds, subs, meta = load_bank(job_id(dict(ds="iot-23", kind="iid", seed=0, dph=(1, 3), alpha=None,
                                              k=1, K=20)))
    tb = C.prepare_base("iot-23")
    cwd = os.getcwd(); os.chdir(C.REPO)
    b = C.DATA.load_dataset(C.base_cfg("iot-23", "iid", 0), verbose=False)
    os.chdir(cwd)
    tr, te = C.DATA.time_split_within_device(b["y"], b["device"], 0.8, block=b.get("block"))
    dte = b["df"][te].reset_index(drop=True)
    v1 = preds.sum(0)
    ex = []
    for want in (20, 19, 18, 17):
        idx = np.where((v1 == want) | (v1 == 20 - want))[0]
        if len(idx):
            i = int(idx[0])
            nm = int(max(v1[i], 20 - v1[i])); nn = 20 - nm
            ex.append(dict(test_index=i, uid=str(dte.loc[i, "uid"]), capture=str(dte.loc[i, "device"]),
                           label=str(dte.loc[i, "label"]), detailed=str(dte.loc[i, "detailed"]),
                           votes=f"{nm}-{nn}", top=("malicious" if v1[i] > 10 else "benign"),
                           margin=(nm - nn) / 20, threshold_m8=0.8,
                           certified_m8=bool((nm - nn) > 16), n_flows_with_this_split=int(len(idx))))
    out = dict(total_certified_flow_budget_pairs=tot, total_violations=vio, ensembles=report,
               worked_example_iid_s0_k1_m8=ex, secs=round(time.time() - t0, 1))
    C.dump("p0_vote_bound.json", out)
    print(json.dumps(dict(total=tot, violations=vio, example=ex), indent=1))


if __name__ == "__main__":
    main()
