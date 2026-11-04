#!/usr/bin/env python3
"""One-sided anomaly votes for benign-only members (predeclarations/anomaly_vote_2026-11-03.md,
SHA-256 05db1600..., RKA jrn_01M6H1SZ889RGX5MKXJEFPSXXK).

Arms on the same members: P (plurality), A (one-class members abstain), V (as A, but each benign-only member votes
"malicious" when an input is anomalous to its own autoencoder). Two-class members come from the paper's code path
(scripts/tmlr_rev/common.py:member_predictions). Writes results/novelty/anomaly_vote_<set>.jsonl, one row per draw.

    python3 scripts/novelty/anomaly_vote.py --set primary      # IoT-23 device-derived 1-3, seeds 40-69
    python3 scripts/novelty/anomaly_vote.py --set iot1         # IoT-23 device-derived 1-1, seeds 0-29
    python3 scripts/novelty/anomaly_vote.py --set cic          # CIC IoT-IDAD 2024 victim side, 1-3, seeds 0-29
    python3 scripts/novelty/anomaly_vote.py --set nbaiot       # N-BaIoT device-derived (1-2, as the paper), 0-29
"""
import argparse, json, os, sys, time
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the artifact root
sys.path.insert(0, os.path.join(REPO, "scripts", "tmlr_rev"))
import common as C  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402

OUT = os.path.join(REPO, "results", "novelty")
BETAS = [round(0.05 * i, 2) for i in range(11)]
N = 20
ONE_CLASS = 0.05
SETS = {"primary": ("iot-23", (1, 3), range(40, 70)), "iot1": ("iot-23", (1, 1), range(0, 30)),
        "cic": ("cic-idad-victim", (1, 3), range(0, 30)), "nbaiot": ("n-baiot", (1, 2), range(0, 30))}


def cfg_for(ds, seed, dph):
    if ds == "cic-idad-victim":
        cwd = os.getcwd(); os.chdir(REPO)
        try:
            cfg = C.CFG.load("configs/jisa_cic_victim.yaml")
        finally:
            os.chdir(cwd)
        cfg.device = "cpu"; cfg.data.root = os.path.join(REPO, "data", "raw")
        cfg.partition.kind = "device_derived"; cfg.partition.seed = seed; cfg.partition.N = N
        cfg.partition.devices_per_household = list(dph); cfg.fl.seed = 0
        cfg.defense.name = "fedavg"; cfg.defense.observability = C.D.LEVEL["fedavg"]
        cfg.adversary.F3_knowledge = "white_box"
        return cfg
    return C.base_cfg(ds, "device_derived", seed, dph)


_BASE = {}


def base_for(ds, dph):
    if ds not in _BASE:
        cfg = cfg_for(ds, 0, dph)
        cwd = os.getcwd(); os.chdir(REPO)
        try:
            _BASE[ds] = C.R.prepare(cfg, verbose=False)
        finally:
            os.chdir(cwd)
    return _BASE[ds]


def train_ae(X, seed):
    torch.manual_seed(seed)
    d = X.shape[1]
    ae = nn.Sequential(nn.Linear(d, 32), nn.ReLU(), nn.Linear(32, 8), nn.ReLU(),
                       nn.Linear(8, 32), nn.ReLU(), nn.Linear(32, d))
    opt = torch.optim.Adam(ae.parameters(), lr=1e-3)
    g = torch.Generator().manual_seed(seed)
    for _ in range(30):
        perm = torch.randperm(len(X), generator=g)
        for i in range(0, len(X), 256):
            xb = X[perm[i:i + 256]]
            opt.zero_grad(); loss = ((ae(xb) - xb) ** 2).mean(); loss.backward(); opt.step()
    with torch.no_grad():
        thr = float(torch.quantile(((ae(X) - X) ** 2).mean(1), 0.99))
    return ae, thr


def certify(votes, y, ctab, tau):
    """votes (K, n) in {0, 1, -1 = abstain}."""
    v1 = (votes == 1).sum(0); v0 = (votes == 0).sum(0)
    top = (v1 > v0).astype(int)
    margin = np.abs(v1 - v0)
    correct = top == y
    P, Nn = (y == 1), (y == 0)
    grid = []
    for b in BETAS:
        m = int(round(b * N)); cert = margin > 2 * ctab[m]["c_max"]
        grid.append(dict(beta=b, CA=float((cert & correct).mean()),
                         CTR_mal=float((cert & correct & P).sum() / max(P.sum(), 1)),
                         CTR_ben=float((cert & correct & Nn).sum() / max(Nn.sum(), 1))))
    g20 = grid[4]
    return dict(beta_star=max([g["beta"] for g in grid if g["CA"] > tau], default=0.0),
                CA20=g20["CA"], CTR_mal20=g20["CTR_mal"], CTR_ben20=g20["CTR_ben"], collapse20=bool(g20["CA"] <= tau),
                clean_TPR=float((top[P] == 1).mean()), clean_FPR=float((top[Nn] == 1).mean()), grid=grid)


def run_draw(ds, dph, seed):
    t0 = time.time()
    cfg = cfg_for(ds, seed, dph)
    t = C.with_partition(base_for(ds, dph), cfg)
    preds, kept = C.member_predictions(cfg, t, [(i,) for i in range(N)])
    y = np.asarray(t["yte_np"]).astype(int)
    tau = float(t["tau"])
    ctab = C.XC.c_max_table(kept, N, [int(round(b * N)) for b in BETAS])
    ytr = np.asarray(t["ytr_np"])
    Xte = t["Xte"].float().cpu()
    A = preds.astype(int).copy(); V = preds.astype(int).copy()
    n_ben_only = n_mal_only = 0; ae_alarm = []
    for j, (i,) in enumerate(kept):
        idx = t["parts_np"][i]
        p = float(ytr[idx].mean()) if len(idx) else 0.0
        if min(p, 1 - p) >= ONE_CLASS:
            continue
        A[j] = -1; V[j] = -1
        if p < 0.5:                                   # benign-only member: one-sided anomaly votes
            n_ben_only += 1
            ae, thr = train_ae(t["Xtr"][idx].float().cpu(), 1000 * seed + i)
            with torch.no_grad():
                err = ((ae(Xte) - Xte) ** 2).mean(1).numpy()
            alarm = err > thr
            V[j, alarm] = 1
            ae_alarm.append(dict(client=i, alarm_mal=float(alarm[y == 1].mean()), alarm_ben=float(alarm[y == 0].mean())))
        else:
            n_mal_only += 1
    row = dict(set_ds=ds, dph=list(dph), seed=seed, K=len(kept), n_ben_only=n_ben_only, n_mal_only=n_mal_only,
               tau=tau, ae_alarm=ae_alarm, secs=round(time.time() - t0, 1))
    for name, vt in (("P", preds.astype(int)), ("A", A), ("V", V)):
        r = certify(vt, y, ctab, tau)
        row[name] = {k: v for k, v in r.items() if k != "grid"}
        row[name + "_grid"] = r["grid"]
    return row


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--set", required=True, choices=list(SETS))
    ap.add_argument("--seeds", type=int, nargs="*")
    a = ap.parse_args()
    torch.set_num_threads(1)
    ds, dph, seeds = SETS[a.set]
    if a.seeds:
        seeds = a.seeds
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"anomaly_vote_{a.set}.jsonl")
    done = set()
    if os.path.exists(path):
        done = {json.loads(l)["seed"] for l in open(path) if l.strip()}
    with open(path, "a") as f:
        for s in seeds:
            if s in done:
                continue
            row = run_draw(ds, dph, s)
            f.write(json.dumps(row) + "\n"); f.flush()
            print(f"{a.set} seed {s}: K={row['K']} ben_only={row['n_ben_only']} "
                  + " ".join(f"{k}: b*={row[k]['beta_star']:.2f} mal20={row[k]['CTR_mal20']:.3f} "
                             f"ben20={row[k]['CTR_ben20']:.3f}" for k in "PAV") + f" ({row['secs']}s)", flush=True)


if __name__ == "__main__":
    main()
