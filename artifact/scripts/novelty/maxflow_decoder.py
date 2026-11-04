#!/usr/bin/env python3
"""Max-flow certified decoder (predeclarations/maxflow_decoder_2026-11-03.md, SHA-256 662176bb...,
RKA jrn_01M6HGKJ7S9MHGHTY4YJ4NMNJ4).

The server learns the aggregation rule from a small labelled set (first 10% of every device's test rows): Theorem 1's
max-flow picks a conflict-free set of labelled output vectors; g(v) = label of a chosen vector within Hamming distance c,
else benign. Certified exactly on the remaining 90%. Arms: plurality (P), abstention (A), decoder (D), and the oracle
ceiling on the evaluation set (MAX). Writes results/novelty/maxflow_decoder_<set>[_frac<f>].jsonl.

    python3 scripts/novelty/maxflow_decoder.py --set iot23|cic [--frac 0.10]
"""
import argparse, itertools, json, os, sys, time
from collections import deque
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abstain_feasibility as AF  # noqa: E402
import anomaly_vote as AV  # noqa: E402
import competence_ceiling as CC  # noqa: E402

C = AF.C
N = 20
MS = [0, 1, 2, 3, 4]
SETS = {"iot23": ("iot-23", (1, 3), range(70, 100)), "cic": ("cic-idad-victim", (1, 3), range(40, 70)),
        "nbaiot": ("n-baiot", (1, 2), range(70, 100))}  # nbaiot: decoder_followup_2026-11-03.md R1
_SPLIT = {}


def test_devices(ds, cfg):
    """Device id of every test row, in runner.prepare's order (time order within each device)."""
    if ds not in _SPLIT:
        cwd = os.getcwd(); os.chdir(AV.REPO)
        try:
            b = C.DATA.load_dataset(cfg, verbose=False)
        finally:
            os.chdir(cwd)
        _, te = C.DATA.time_split_within_device(b["y"], b["device"], cfg.data.train_frac, block=b.get("block"))
        _SPLIT[ds] = (np.asarray(b["device"])[te], np.asarray(b["y"])[te])
    return _SPLIT[ds]


def server_mask(dev, frac):
    m = np.zeros(len(dev), bool)
    for d in np.unique(dev):
        idx = np.nonzero(dev == d)[0]
        m[idx[:max(1, int(round(frac * len(idx))))]] = True
    return m


def codes_of(preds):
    K = preds.shape[0]
    return (preds.astype(np.int64) << np.arange(K, dtype=np.int64)[:, None]).sum(0)


def learn_decoder(code, y, c):
    """Theorem 1's max-flow on the server set; returns (chosen benign codes, chosen malicious codes, value)."""
    uniq, inv = np.unique(code, return_inverse=True)
    w0 = np.bincount(inv, weights=(y == 0), minlength=len(uniq)).astype(np.int64)
    w1 = np.bincount(inv, weights=(y == 1), minlength=len(uniq)).astype(np.int64)
    A = np.nonzero(w0)[0]; B = np.nonzero(w1)[0]; nA, nB = len(A), len(B)
    D = CC.popcount(uniq[A][:, None] ^ uniq[B][None, :]) if nA and nB else np.zeros((nA, nB), int)
    ii, jj = np.nonzero(D <= 2 * c)
    s, t = 0, nA + nB + 1
    inf = int(w0.sum() + w1.sum() + 1)
    rows = np.concatenate([np.zeros(nA, int), 1 + ii, 1 + nA + np.arange(nB)])
    cols = np.concatenate([1 + np.arange(nA), 1 + nA + jj, np.full(nB, t)])
    caps = np.concatenate([w0[A], np.full(len(ii), inf), w1[B]]).astype(np.int32)
    G = csr_matrix((caps, (rows, cols)), shape=(t + 1, t + 1)); G.sum_duplicates()
    res = maximum_flow(G, s, t)
    F = res.flow.tocsr()
    R = (G - F).tocsr()                                # residual on forward edges
    Rb = F.T.tocsr()                                   # residual on reverse edges (positive flow)
    seen = np.zeros(t + 1, bool); seen[s] = True; q = deque([s])
    while q:
        u = q.popleft()
        for M in (R, Rb):
            row = M.getrow(u)
            for v, cap in zip(row.indices, row.data):
                if cap > 0 and not seen[v]:
                    seen[v] = True; q.append(v)
    chosen_b = uniq[A][seen[1:1 + nA]]                 # left nodes on the source side
    chosen_m = uniq[B][~seen[1 + nA:1 + nA + nB]]      # right nodes on the sink side
    value = int(w0[A][seen[1:1 + nA]].sum() + w1[B][~seen[1 + nA:1 + nA + nB]].sum())
    assert value == int(w0.sum() + w1.sum() - res.flow_value), "independent set does not match the max-flow value"
    return chosen_b, chosen_m, value


_MASKS = {}


def masks(K, c):
    if (K, c) not in _MASKS:
        out = [0]
        for r in range(1, c + 1):
            for comb in itertools.combinations(range(K), r):
                out.append(sum(1 << i for i in comb))
        _MASKS[(K, c)] = np.array(out, np.int64)
    return _MASKS[(K, c)]


def decoder_certified(code, y, chosen_m, K, c):
    """Per-input certified-correct flags for g on (code, y)."""
    uniq, inv = np.unique(code, return_inverse=True)
    ok_b = np.zeros(len(uniq), bool); ok_m = np.zeros(len(uniq), bool)
    Mk = masks(K, c)
    for g, u in enumerate(uniq):
        dm = CC.popcount(chosen_m ^ u) if len(chosen_m) else np.zeros(0, int)
        ok_b[g] = not (dm <= 2 * c).any()              # benign: no chosen malicious vector within 2c
        near = chosen_m[dm <= 2 * c]                   # only these can cover the ball
        if len(near) and (dm <= c).any():
            ball = u ^ Mk
            ok = True
            for i in range(0, len(ball), 2048):
                blk = ball[i:i + 2048]
                if not (CC.popcount(blk[:, None] ^ near[None, :]) <= c).any(1).all():
                    ok = False; break
            ok_m[g] = ok
    return np.where(y == 0, ok_b[inv], ok_m[inv]), uniq, inv


def run_draw(ds, dph, seed, frac):
    t0 = time.time()
    cfg = AV.cfg_for(ds, seed, dph)
    t = C.with_partition(AV.base_for(ds, dph), cfg)
    preds, kept = C.member_predictions(cfg, t, [(i,) for i in range(N)])
    preds = preds.astype(int)
    y = np.asarray(t["yte_np"]).astype(int)
    dev, ycheck = test_devices(ds, cfg)
    assert np.array_equal(ycheck.astype(int), y), "test split mismatch"
    srv = server_mask(dev, frac); ev = ~srv
    K = len(kept)
    ctab = C.XC.c_max_table(kept, N, list(range(11)))
    ytr = np.asarray(t["ytr_np"])
    mino = []
    for (i,) in kept:
        idx = t["parts_np"][i]; p = float(ytr[idx].mean()) if len(idx) else 0.0
        mino.append(min(p, 1 - p))
    ye, Pe = y[ev], preds[:, ev]
    tau = float(max(ye.mean(), 1 - ye.mean()))
    plur = AF.certify(Pe, ye, np.ones(K, bool), ctab, tau)
    absn = AF.certify(Pe, ye, np.asarray(mino) >= AF.ONE_CLASS, ctab, tau)
    pg = {round(g["beta"], 2): g["CA"] for g in plur["grid"]}; ag = {round(g["beta"], 2): g["CA"] for g in absn["grid"]}
    ceil = CC.ceiling_counts(Pe, ye, [ctab[m]["c_max"] for m in MS])
    cs, cv = codes_of(preds[:, srv]), codes_of(Pe)
    row = dict(set_ds=ds, seed=seed, frac=frac, K=K, n_server=int(srv.sum()), n_eval=int(ev.sum()), tau=tau, by_m={})
    for m in MS:
        c = ctab[m]["c_max"]
        tl = time.time()
        chosen_b, chosen_m, val = learn_decoder(cs, y[srv], c)
        tc = time.time()
        okD, _, _ = decoder_certified(cv, ye, chosen_m, K, c)
        tcert = time.time() - tc
        gP = next(g for g in plur["grid"] if round(g["beta"], 2) == round(m / N, 2))
        gA = next(g for g in absn["grid"] if round(g["beta"], 2) == round(m / N, 2))
        row["by_m"][str(m)] = dict(c=c, CA_P=pg[round(m / N, 2)], CA_A=ag[round(m / N, 2)], CA_D=float(okD.mean()),
                                   CA_MAX=ceil[c] / len(ye), n_chosen_b=int(len(chosen_b)),
                                   n_chosen_m=int(len(chosen_m)), server_value=val / int(srv.sum()),
                                   # per-class certified rates (decoder_followup_2026-11-03.md R3) and timing (R4)
                                   cTPR_P=gP["CTR_mal"], cTPR_A=gA["CTR_mal"], cTPR_D=float(okD[ye == 1].mean()),
                                   cBEN_P=gP["CTR_ben"], cBEN_A=gA["CTR_ben"], cBEN_D=float(okD[ye == 0].mean()),
                                   secs_learn=round(tc - tl, 3), ms_cert_per_input=round(1000 * tcert / len(ye), 4))
    top = (Pe.sum(0) * 2 > K).astype(int)
    row["clean_acc_P"] = float((top == ye).mean())
    cb0, cm0, _ = learn_decoder(cs, y[srv], 0)
    gm = np.isin(cv, cm0)                              # c = 0: g(v) = 1 iff v is a chosen malicious vector
    row["clean_acc_D"] = float((gm.astype(int) == ye).mean())
    bs = lambda k: max([round(m / N, 2) for m in MS if row["by_m"][str(m)][k] > tau], default=0.0)
    row.update(beta_star_P=bs("CA_P"), beta_star_A=bs("CA_A"), beta_star_D=bs("CA_D"), beta_star_MAX=bs("CA_MAX"),
               secs=round(time.time() - t0, 1))
    return row


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--set", required=True, choices=list(SETS))
    ap.add_argument("--frac", type=float, default=0.10); ap.add_argument("--seeds", type=int, nargs="*")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import torch; torch.set_num_threads(1)
    ds, dph, seeds = SETS[a.set]
    os.makedirs(AF.OUT, exist_ok=True)
    path = os.path.join(AF.OUT, f"maxflow_decoder_{a.set}" + ("" if a.frac == 0.10 else f"_frac{a.frac:g}") + (f"_{a.tag}" if a.tag else "") + ".jsonl")
    done = {json.loads(l)["seed"] for l in open(path)} if os.path.exists(path) else set()
    for s in (a.seeds or seeds):
        if s in done:
            continue
        r = run_draw(ds, dph, s, a.frac)
        with open(path, "a") as f:
            f.write(json.dumps(r) + "\n")
        b = r["by_m"]["4"]
        print(f"{a.set} seed {s}: K={r['K']} beta* P/A/D/MAX {r['beta_star_P']:.2f}/{r['beta_star_A']:.2f}/"
              f"{r['beta_star_D']:.2f}/{r['beta_star_MAX']:.2f} | CA@m4 P {b['CA_P']:.3f} A {b['CA_A']:.3f} "
              f"D {b['CA_D']:.3f} MAX {b['CA_MAX']:.3f} tau {r['tau']:.3f} | clean P {r['clean_acc_P']:.3f} "
              f"D {r['clean_acc_D']:.3f} ({r['secs']}s)", flush=True)


if __name__ == "__main__":
    main()
