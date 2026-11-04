#!/usr/bin/env python3
"""Feasibility of certified anomaly-based federated IDS (predeclarations/certified_anomaly_feasibility_2026-11-03.md,
SHA-256 3db3690f..., RKA jrn_01M6H9PP5NH4V7PF3DCJCQRDWW).

One autoencoder per household on its benign training rows, member-local 0.99-quantile thresholds, alarm iff at least t
members alarm. Certified alarm iff a - c >= t, certified no-alarm iff a + c < t, c = c_max(m). t chosen on a benign
validation set for certified false-alarm rate <= 0.01. Writes results/novelty/certified_anomaly_<set>.jsonl.

    python3 scripts/novelty/certified_anomaly.py --set nbaiot|cic|iot23
"""
import argparse, json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anomaly_vote as AV  # noqa: E402  (same config, base data and partition code path)
import torch  # noqa: E402
from torch import nn  # noqa: E402

C = AV.C
OUT = AV.OUT
N = 20
MS = [0, 1, 2, 4]
SETS = {"nbaiot": ("n-baiot", (1, 2)), "cic": ("cic-idad-victim", (1, 3)), "iot23": ("iot-23", (1, 3))}
SEEDS = range(100, 130)


def train_ae(X, seed):
    torch.manual_seed(seed)
    d = X.shape[1]
    ae = nn.Sequential(nn.Linear(d, 32), nn.ReLU(), nn.Linear(32, 8), nn.ReLU(),
                       nn.Linear(8, 32), nn.ReLU(), nn.Linear(32, d))
    opt = torch.optim.Adam(ae.parameters(), lr=1e-3)
    g = torch.Generator().manual_seed(seed)
    for _ in range(20):
        perm = torch.randperm(len(X), generator=g)
        for i in range(0, len(X), 256):
            xb = X[perm[i:i + 256]]
            opt.zero_grad(); ((ae(xb) - xb) ** 2).mean().backward(); opt.step()
    with torch.no_grad():
        thr = float(torch.quantile(((ae(X) - X) ** 2).mean(1), 0.99))
    return ae, thr


_RAW = {}


def raw_split(ds, dph, cfg):
    """Raw (unstandardized) features on runner.prepare's train/test split (deviation of 2026-11-03T18:15Z)."""
    if ds not in _RAW:
        cwd = os.getcwd(); os.chdir(AV.REPO)
        try:
            b = C.DATA.load_dataset(cfg, verbose=False)
        finally:
            os.chdir(cwd)
        tr, te = C.DATA.time_split_within_device(b["y"], b["device"], cfg.data.train_frac, block=b.get("block"))
        X = np.asarray(b["X"], np.float64)
        _RAW[ds] = (X[tr], X[te], np.asarray(b["y"])[tr], np.asarray(b["y"])[te])
    return _RAW[ds]


def run_draw(ds, dph, seed):
    t0 = time.time()
    cfg = AV.cfg_for(ds, seed, dph)
    t = C.with_partition(AV.base_for(ds, dph), cfg)
    ytr = np.asarray(t["ytr_np"]).astype(int); yte = np.asarray(t["yte_np"]).astype(int)
    Rtr, Rte, ry_tr, ry_te = raw_split(ds, dph, cfg)
    assert np.array_equal(ry_tr.astype(int), ytr) and np.array_equal(ry_te.astype(int), yte), "split mismatch"
    members, val_rows, alarms_te = [], [], []
    for i in range(N):
        idx = np.sort(np.asarray(t["parts_np"][i]))
        ben = idx[ytr[idx] == 0]                       # index order = time order within the device split
        if len(ben) < 20:
            continue
        nv = max(1, int(round(0.1 * len(ben))))
        tr, va = ben[:-nv], ben[-nv:]
        if len(tr) > 5000:
            tr = np.sort(np.random.default_rng(7 + 1000 * seed + i).choice(tr, 5000, replace=False))
        mu, sd = Rtr[tr].mean(0), Rtr[tr].std(0) + 1e-6          # the household's own benign statistics
        Z = lambda A, mu=mu, sd=sd: torch.tensor((A - mu) / sd, dtype=torch.float32)
        ae, thr = train_ae(Z(Rtr[tr]), 1000 * seed + i)
        members.append(((i,), ae, thr, Z)); val_rows.append(va)
        with torch.no_grad():
            Xt = Z(Rte)
            alarms_te.append(((ae(Xt) - Xt) ** 2).mean(1).numpy() > thr)
    K = len(members)
    if K == 0:
        return dict(set_ds=ds, seed=seed, K=0, status="no members")
    va_all = np.concatenate(val_rows)
    A_va = np.zeros(len(va_all), int)
    with torch.no_grad():
        for _, ae, thr, Z in members:
            Xv = Z(Rtr[va_all]); A_va += (((ae(Xv) - Xv) ** 2).mean(1).numpy() > thr)
    A_te = np.stack(alarms_te).sum(0)
    ctab = C.XC.c_max_table([s for s, _, _, _ in members], N, MS)
    P, Nn = yte == 1, yte == 0
    res = {}
    for m in MS:
        c = ctab[m]["c_max"]
        curve = []
        for th in range(1, K + 1):
            cert_alarm = A_te - c >= th
            cert_quiet = A_te + c < th
            curve.append(dict(t=th, cTPR=float(cert_alarm[P].mean()), cFPR=float((~cert_quiet[Nn]).mean()),
                              TPR=float((A_te[P] >= th).mean()), FPR=float((A_te[Nn] >= th).mean()),
                              val_cFPR=float((~(A_va + c < th)).mean())))
        ok = [r for r in curve if r["val_cFPR"] <= 0.01]
        sel = ok[0] if ok else None
        res[str(m)] = dict(c=c, selected=sel, empty=sel is None, curve=curve)
    return dict(set_ds=ds, dph=list(dph), seed=seed, K=K, n_val=int(len(va_all)), secs=round(time.time() - t0, 1),
                status="ok", by_m=res)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--set", required=True, choices=list(SETS))
    ap.add_argument("--seeds", type=int, nargs="*")
    a = ap.parse_args()
    torch.set_num_threads(1)
    ds, dph = SETS[a.set]
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"certified_anomaly_{a.set}.jsonl")
    done = {json.loads(l)["seed"] for l in open(path)} if os.path.exists(path) else set()
    for s in (a.seeds or SEEDS):
        if s in done:
            continue
        row = run_draw(ds, dph, s)
        with open(path, "a") as f:
            f.write(json.dumps(row) + "\n")
        sm = {m: (row["by_m"][m]["selected"] or {}) for m in ("2", "4")} if row["status"] == "ok" else {}
        print(f"{a.set} seed {s}: K={row['K']} " + " ".join(
            f"m={m}: t={v.get('t')} cTPR={v.get('cTPR', float('nan')):.3f} cFPR={v.get('cFPR', float('nan')):.3f}"
            for m, v in sm.items()) + f" ({row.get('secs')}s)", flush=True)


if __name__ == "__main__":
    main()
