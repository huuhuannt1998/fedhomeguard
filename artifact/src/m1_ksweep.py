"""
M1 / T5b -- THE CERTIFICATION TENSION SWEEP.

The probe established a purely combinatorial ceiling on subsample
certification:  beta_cert  <  1 - 2^(-1/k)   (independent of N, data, model).
Certifying at the fractions the FL-IoT-IDS literature evaluates (20-40%)
therefore REQUIRES small k (k<=2).

This sweep measures the other side of the tension: what small k costs in
ensemble margin and accuracy, under a MILD (IID) partition versus a
DEVICE-DERIVED partition. If margin collapses as k shrinks under device
skew, the two requirements are incompatible -- which is HICC, made exact.
"""
import json, math, os, sys, time
import numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m1_probe import (load, featurize, fl_run, js_skew, MLP, OUT, SEED)

rng = np.random.default_rng(SEED); torch.manual_seed(SEED)
K_ENS = 100
KS = [1, 2, 3, 5, 8]
BETAS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]


def beta_geo(N, k):
    best = 0.0
    for m in range(N + 1):
        pc = math.comb(N - m, k) / math.comb(N, k) if N - m >= k else 0.0
        if pc > 0.5: best = m / N
        else: break
    return best


def device_partition(N, dtr, rng):
    """Device-derived households: each client owns 1-3 device types (D1 style)."""
    devs = np.unique(dtr)
    parts = {}
    owner = {d: [] for d in devs}
    for i in range(N):
        ndev = rng.integers(1, 4)
        own = rng.choice(devs, size=min(ndev, len(devs)), replace=False)
        for d in own: owner[d].append(i)
    for d in devs:                       # every device must belong somewhere
        if not owner[d]: owner[d].append(int(rng.integers(0, N)))
    for i in range(N): parts[i] = []
    for d in devs:
        idx = np.where(dtr == d)[0]; rng.shuffle(idx)
        for chunk, i in zip(np.array_split(idx, len(owner[d])), owner[d]):
            parts[i].append(chunk)
    return {i: (np.sort(np.concatenate(v)) if v else np.array([], int)) for i, v in parts.items()}


def certify(votes, Kn, yte, N, k, tau, bal_idx):
    srt = np.sort(votes, 1); n1, n2 = srt[:, -1], srt[:, -2]
    top = votes.argmax(1); margin = (n1 - n2) / Kn
    out = []
    for beta in BETAS:
        m = int(round(beta * N))
        pc = math.comb(N - m, k) / math.comb(N, k) if N - m >= k else 0.0
        thr = 2 * (1 - pc); cert = margin > thr
        CA = float((cert & (top == yte)).mean())
        CAb = float((cert[bal_idx] & (top[bal_idx] == yte[bal_idx])).mean())
        out.append(dict(beta=beta, m=m, p_clean=round(pc, 4), thr=round(thr, 4),
                        CA=round(CA, 4), CA_bal=round(CAb, 4),
                        impossible=bool(thr >= 1.0)))
    return out, float(margin.mean()), float((top == yte).mean())


def main():
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    df = load(); X, y = featurize(df)
    dcodes = pd.Categorical(df["device"]).codes.astype(int)

    tr = np.zeros(len(y), bool)
    for d in np.unique(dcodes):
        ix = np.where(dcodes == d)[0]; tr[ix[: int(0.8 * len(ix))]] = True
    Xtr_np, ytr_np, dtr = X[tr], y[tr], dcodes[tr]
    Xte_np, yte_np = X[~tr], y[~tr]
    mu, sd = Xtr_np.mean(0), Xtr_np.std(0) + 1e-6
    Xtr_np = (Xtr_np - mu) / sd; Xte_np = (Xte_np - mu) / sd
    tau = float(max(yte_np.mean(), 1 - yte_np.mean()))

    Xtr = torch.tensor(Xtr_np, device=dev); ytr = torch.tensor(ytr_np, device=dev)
    Xte = torch.tensor(Xte_np, device=dev); yte_t = torch.tensor(yte_np, device=dev)
    d = Xtr.shape[1]; N = 20

    pos = np.where(yte_np == 1)[0]; neg = np.where(yte_np == 0)[0]
    nb = min(len(pos), len(neg))
    bal = np.concatenate([rng.choice(pos, nb, replace=False), rng.choice(neg, nb, replace=False)])

    perm = rng.permutation(len(ytr_np))
    P_iid = {i: np.sort(perm[i::N]) for i in range(N)}
    P_dev = device_partition(N, dtr, np.random.default_rng(SEED + 1))

    parts_t = {}
    for name, P in (("iid_mild", P_iid), ("device_derived", P_dev)):
        parts_t[name] = {i: torch.tensor(P[i], device=dev) for i in range(N)}
        s = js_skew(parts_t[name], ytr, dtr, N)
        print(f"partition={name:16s} S_JS={s:.4f}  "
              f"sizes[min/med/max]={min(len(P[i]) for i in range(N))}/"
              f"{int(np.median([len(P[i]) for i in range(N)]))}/{max(len(P[i]) for i in range(N))}")

    results = []
    print(f"\ntau_triv={tau:.4f}   N={N}  K={K_ENS}\n")
    print(f"{'partition':16s} {'k':>2s} {'beta_geo':>8s} {'ens_acc':>8s} {'margin':>7s} "
          f"{'CA(0)':>7s} {'CA(.10)':>8s} {'CA(.20)':>8s} {'CA(.30)':>8s} {'beta*':>6s}")
    for name in ("iid_mild", "device_derived"):
        P = parts_t[name]
        S = js_skew(P, ytr, dtr, N)
        for k in KS:
            all_sub = None
            tot = math.comb(N, k)
            if tot <= K_ENS:
                from itertools import combinations
                subsets = list(combinations(range(N), k)); exact = True
            else:
                from itertools import combinations
                allc = list(combinations(range(N), k))
                sel = rng.choice(len(allc), size=K_ENS, replace=False)
                subsets = [allc[j] for j in sel]; exact = False
            votes = np.zeros((len(yte_np), 2), np.int32)
            t0 = time.time()
            for C in subsets:
                g = fl_run(list(C), Xtr, ytr, P, d, dev)
                with torch.no_grad():
                    p = g(Xte).argmax(1).cpu().numpy()
                votes[np.arange(len(p)), p] += 1
            grid, mmargin, eacc = certify(votes, len(subsets), yte_np, N, k, tau, bal)
            bstar = max([g_["beta"] for g_ in grid if g_["CA"] > tau], default=0.0)
            bg = beta_geo(N, k)
            results.append(dict(partition=name, S_JS=round(S, 4), k=k, K=len(subsets),
                                exact=exact, beta_geo=bg, ensemble_acc=round(eacc, 4),
                                mean_margin=round(mmargin, 4), MC_het=round(1 - mmargin, 4),
                                tau_triv=round(tau, 4), beta_star=bstar, grid=grid,
                                secs=round(time.time() - t0, 1)))
            gd = {g_["beta"]: g_["CA"] for g_ in grid}
            print(f"{name:16s} {k:2d} {bg:8.3f} {eacc:8.4f} {mmargin:7.4f} "
                  f"{gd[0.0]:7.4f} {gd[0.10]:8.4f} {gd[0.20]:8.4f} {gd[0.30]:8.4f} {bstar:6.2f}")

    json.dump(dict(N=N, K=K_ENS, tau_triv=round(tau, 4),
                   note="beta_cert < 1 - 2^(-1/k) is a combinatorial ceiling, "
                        "independent of N, data and model.",
                   asymptotic_ceiling={k: round(1 - 2 ** (-1 / k), 4) for k in KS},
                   results=results), open(f"{OUT}/m1_ksweep.json", "w"), indent=2)
    print(f"\nwrote {OUT}/m1_ksweep.json")


if __name__ == "__main__":
    main()
