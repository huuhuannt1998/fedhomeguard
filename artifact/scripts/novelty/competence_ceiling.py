#!/usr/bin/env python3
"""Aggregator-agnostic competence ceiling (predeclarations/competence_ceiling_2026-11-03.md, SHA-256 5af05223...,
RKA jrn_01M6HD68326Y5XWHB3F1F3VA26).

For each draw (k = 1, binary) and m: the largest certified accuracy ANY aggregator of the members' outputs can reach.
Two oppositely labelled inputs conflict when their member-output vectors are within Hamming distance 2c (c = c_max(m)).
The ceiling is the maximum-weight independent set of that bipartite conflict graph over distinct output vectors,
computed as total weight minus a max-flow (Konig). Writes results/novelty/competence_ceiling_<set>.jsonl.

    python3 scripts/novelty/competence_ceiling.py --set iot23_main|iot23_iid|cic
"""
import argparse, glob, json, os, sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abstain_feasibility as AF  # noqa: E402  (certify(), member_minority(), the same bank and labels)
import anomaly_vote as AV  # noqa: E402  (CIC config and base data)

C = AF.C
N = 20
MS = list(range(11))                 # m = 0..10 so beta*_max can be read on the 0.05 grid
BANK_SETS = {"iot23_main": AF.GROUPS["main_dd_1-3_k1"], "iot23_iid": AF.GROUPS["control_iid_k1"]}


def popcount(a):
    a = a.astype(np.uint32)
    a = a - ((a >> 1) & 0x55555555)
    a = (a & 0x33333333) + ((a >> 2) & 0x33333333)
    return ((((a + (a >> 4)) & 0x0F0F0F0F) * 0x01010101) & 0xFFFFFFFF) >> 24


def ceiling_counts(preds, y, cs):
    """preds (K, n) in {0,1}; returns {c: max number of test inputs any aggregator certifies correctly}."""
    K, n = preds.shape
    code = (preds.astype(np.int64) << np.arange(K, dtype=np.int64)[:, None]).sum(0)
    uniq, inv = np.unique(code, return_inverse=True)
    w0 = np.bincount(inv, weights=(y == 0), minlength=len(uniq)).astype(np.int64)
    w1 = np.bincount(inv, weights=(y == 1), minlength=len(uniq)).astype(np.int64)
    A = np.nonzero(w0)[0]; B = np.nonzero(w1)[0]
    D = popcount(uniq[A][:, None] ^ uniq[B][None, :])        # pairwise Hamming distances, benign x malicious groups
    out = {}
    for c in sorted(set(cs)):
        ii, jj = np.nonzero(D <= 2 * c)
        nA, nB = len(A), len(B)
        s, t = 0, nA + nB + 1
        inf = int(w0.sum() + w1.sum() + 1)
        rows = np.concatenate([np.zeros(nA, int), 1 + ii, 1 + nA + np.arange(nB)])
        cols = np.concatenate([1 + np.arange(nA), 1 + nA + jj, np.full(nB, t)])
        caps = np.concatenate([w0[A], np.full(len(ii), inf), w1[B]]).astype(np.int32)
        G = csr_matrix((caps, (rows, cols)), shape=(t + 1, t + 1))
        G.sum_duplicates()
        flow = maximum_flow(G, s, t).flow_value
        out[c] = int(w0.sum() + w1.sum() - flow)
    return out


def analyse(preds, y, subs, meta_minority, tau):
    K, n = preds.shape
    ctab = C.XC.c_max_table(subs, N, MS)
    cs = [ctab[m]["c_max"] for m in MS]
    ceil = ceiling_counts(preds, y, cs)
    plur = AF.certify(preds, y, np.ones(K, bool), ctab, tau)
    absn = AF.certify(preds, y, np.asarray(meta_minority) >= AF.ONE_CLASS, ctab, tau)
    CA_max = {m: ceil[ctab[m]["c_max"]] / n for m in MS}
    beta = lambda m: round(m / N, 2)
    pg = {round(g["beta"], 2): g["CA"] for g in plur["grid"]}; ag = {round(g["beta"], 2): g["CA"] for g in absn["grid"]}
    n_const = int(sum(1 for j in range(K) if preds[j].min() == preds[j].max()))
    return dict(K=K, n_const=n_const, tau=tau,
                CA_max={str(m): CA_max[m] for m in MS}, c={str(m): ctab[m]["c_max"] for m in MS},
                CA_plur={str(m): pg[beta(m)] for m in MS}, CA_abst={str(m): ag[beta(m)] for m in MS},
                beta_star_max=max([beta(m) for m in MS if CA_max[m] > tau], default=0.0),
                beta_star_plur=plur["beta_star"], beta_star_abst=absn["beta_star"])


def bank_rows(pattern):
    t = C.prepare_base("iot-23")
    y = np.asarray(t["yte_np"]).astype(int); tau = float(max(y.mean(), 1 - y.mean()))
    for f in sorted(glob.glob(os.path.join(AF.BANK, pattern + ".npz"))):
        z = np.load(f); meta = json.load(open(f[:-4] + ".json"))
        preds = np.unpackbits(z["packed"], axis=1)[:, :len(y)].astype(int)
        subs = [tuple(int(i) for i in s) for s in z["subsets"]]
        mino = [AF.member_minority(meta, S) for S in subs]
        r = analyse(preds, y, subs, mino, tau)
        r.update(id=meta["id"], seed=meta["job"]["seed"], stored_beta_star=meta["beta_star"])
        yield r


def cic_rows():
    stored = {}
    for l in open(os.path.join(AF.REPO, "results", "jisa", "js01_cic_victim_dd13.jsonl")):
        r = json.loads(l)
        if r["k"] == 1:
            stored.setdefault(r["partition_seed"], {})[round(r["beta"], 2)] = r
    for seed in range(10, 40):
        cfg = AV.cfg_for("cic-idad-victim", seed, (1, 3))
        t = C.with_partition(AV.base_for("cic-idad-victim", (1, 3)), cfg)
        preds, kept = C.member_predictions(cfg, t, [(i,) for i in range(N)])
        y = np.asarray(t["yte_np"]).astype(int); tau = float(t["tau"])
        ytr = np.asarray(t["ytr_np"])
        mino = []
        for (i,) in kept:
            idx = t["parts_np"][i]; p = float(ytr[idx].mean()) if len(idx) else 0.0
            mino.append(min(p, 1 - p))
        r = analyse(preds.astype(int), y, kept, mino, tau)
        st = stored.get(seed, {})
        ref = max([b for b, row in st.items() if row["CA"] > row["tau_triv"]], default=0.0)
        mism = [m for m in MS if round(m / N, 2) in st and abs(st[round(m / N, 2)]["CA"] - r["CA_plur"][str(m)]) > 1e-6]
        r.update(id=f"cic_dd13_s{seed}", seed=seed, stored_beta_star=ref, plur_CA_mismatch_m=mism)
        yield r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--set", required=True, choices=["iot23_main", "iot23_iid", "cic"])
    a = ap.parse_args()
    os.makedirs(AF.OUT, exist_ok=True)
    path = os.path.join(AF.OUT, f"competence_ceiling_{a.set}.jsonl")
    rows = cic_rows() if a.set == "cic" else bank_rows(BANK_SETS[a.set])
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n"); f.flush()
            print(f"{r['id']}: K={r['K']} const={r['n_const']} beta* plur {r['beta_star_plur']:.2f} "
                  f"(stored {r['stored_beta_star']:.2f}) abst {r['beta_star_abst']:.2f} MAX {r['beta_star_max']:.2f} | "
                  f"CA@m=4 plur {r['CA_plur']['4']:.3f} abst {r['CA_abst']['4']:.3f} max {r['CA_max']['4']:.3f} "
                  f"tau {r['tau']:.3f}" + (f" MISMATCH m={r['plur_CA_mismatch_m']}" if r.get("plur_CA_mismatch_m") else ""),
                  flush=True)


if __name__ == "__main__":
    main()
