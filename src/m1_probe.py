"""
M1 / T5 -- CERTIFICATION FEASIBILITY PROBE (FedHomeGuard).

Purpose: on the EASIEST case (few clients, MILD near-IID partition), apply
FLCert-style subsampling certification and check the certified bound is
non-trivial -- i.e. CA(beta) > tau_triv (the majority-class rate).

If it is vacuous HERE it will certainly be vacuous under realistic
device-derived skew, and the project must go to the PI (mission checkpoint).

Substrate: IoT-23 conn.log.labeled (per-device captures, verified attribution).
Hardware: single MacBook Pro M4 24GB. No cluster, no GPU tier.
"""
import glob, json, math, os, sys, time
from itertools import combinations
import numpy as np, pandas as pd, torch, torch.nn as nn

SEED = 0
RAW = "/Users/huanbui/Research/FedHomeGuard-P10/data/raw/iot23"
OUT = "/Users/huanbui/Research/FedHomeGuard-P10/results"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(SEED); torch.manual_seed(SEED)

COLS = ["ts","uid","orig_h","orig_p","resp_h","resp_p","proto","service","duration",
        "orig_bytes","resp_bytes","conn_state","local_orig","local_resp","missed_bytes",
        "history","orig_pkts","orig_ip_bytes","resp_pkts","resp_ip_bytes",
        "tunnel_parents","label","detailed"]
NUM = ["resp_p","duration","orig_bytes","resp_bytes","missed_bytes",
       "orig_pkts","orig_ip_bytes","resp_pkts","resp_ip_bytes"]
MAXROWS_PER_DEV = 60000


def load():
    frames = []
    for path in sorted(glob.glob(f"{RAW}/*.conn.log.labeled")):
        dev = os.path.basename(path).split(".conn")[0]
        df = pd.read_csv(path, sep=r"\s+", comment="#", names=COLS,
                         header=None, engine="python", on_bad_lines="skip",
                         dtype=str, nrows=400000)
        df = df[df["label"].notna()]
        df["label"] = df["label"].str.lower()
        df = df[df["label"].isin(["benign", "malicious"])]
        if len(df) == 0:
            continue
        if len(df) > MAXROWS_PER_DEV:                      # keep time order
            df = df.iloc[np.linspace(0, len(df) - 1, MAXROWS_PER_DEV).astype(int)]
        df["device"] = dev
        frames.append(df)
        print(f"  {dev:34s} rows={len(df):7d}  mal={ (df.label=='malicious').mean():.3f}")
    return pd.concat(frames, ignore_index=True)


def featurize(df):
    X = []
    for c in NUM:
        v = pd.to_numeric(df[c].replace("-", np.nan), errors="coerce").fillna(0.0).to_numpy(float)
        X.append(np.log1p(np.abs(v)) * np.sign(v))
    for col, k in (("proto", 4), ("conn_state", 12), ("service", 8)):
        vocab = df[col].value_counts().index[:k].tolist()
        for val in vocab:
            X.append((df[col] == val).to_numpy(float))
    X = np.stack(X, 1).astype(np.float32)
    y = (df["label"] == "malicious").to_numpy().astype(np.int64)
    return X, y


class MLP(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, 32), nn.ReLU(), nn.Linear(32, 16),
                                 nn.ReLU(), nn.Linear(16, 2))
    def forward(self, x): return self.net(x)


def get_flat(m): return torch.cat([p.data.flatten() for p in m.parameters()])
def set_flat(m, v):
    i = 0
    for p in m.parameters():
        n = p.numel(); p.data.copy_(v[i:i+n].view_as(p)); i += n


def local_train(model, Xc, yc, epochs, lr, bs, dev):
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9)
    lossf = nn.CrossEntropyLoss()
    n = len(yc)
    for _ in range(epochs):
        perm = torch.randperm(n, device=dev)
        for s in range(0, n, bs):
            idx = perm[s:s+bs]
            opt.zero_grad(); loss = lossf(model(Xc[idx]), yc[idx]); loss.backward(); opt.step()
    return get_flat(model)


def fl_run(client_ids, Xtr, ytr, parts, d, dev, T=15, E=1, lr=0.05, bs=512):
    """Algorithm 1: FLRun. Deterministic given seeds. FedAvg over client_ids."""
    g = MLP(d).to(dev)
    theta = get_flat(g).clone()
    local = MLP(d).to(dev)
    for t in range(T):
        acc = torch.zeros_like(theta); tot = 0
        for i in client_ids:
            idx = parts[i]
            if len(idx) < 16: continue
            set_flat(local, theta)
            u = local_train(local, Xtr[idx], ytr[idx], E, lr, bs, dev)
            acc += u * len(idx); tot += len(idx)
        if tot: theta = acc / tot
    set_flat(g, theta)
    return g


def js_skew(parts, ytr, Xdev_ids, N):
    """Mean pairwise Jensen-Shannon divergence over (label x device) histograms."""
    hists = []
    for i in range(N):
        idx = parts[i].detach().cpu().numpy()
        key = (Xdev_ids[idx].astype(int) * 2 + ytr[idx].detach().cpu().numpy())
        h = np.bincount(key, minlength=int(Xdev_ids.max()) * 2 + 2).astype(float)
        hists.append(h / max(h.sum(), 1))
    tot, cnt = 0.0, 0
    for a in range(N):
        for b in range(a + 1, N):
            p, q = hists[a], hists[b]; m = 0.5 * (p + q)
            def kl(u, v):
                mask = u > 0
                return float(np.sum(u[mask] * np.log2(u[mask] / np.maximum(v[mask], 1e-12))))
            tot += 0.5 * kl(p, m) + 0.5 * kl(q, m); cnt += 1
    return tot / cnt


def main():
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"device={dev}\n=== loading IoT-23 ===")
    df = load()
    X, y = featurize(df)
    devs = pd.Categorical(df["device"]).codes.astype(int)
    print(f"total rows={len(y)}  dim={X.shape[1]}  malicious_frac={y.mean():.4f}")

    # time-ordered 80/20 split WITHIN each device (no random row shuffle)
    tr_mask = np.zeros(len(y), bool)
    for dcode in np.unique(devs):
        ix = np.where(devs == dcode)[0]
        tr_mask[ix[: int(0.8 * len(ix))]] = True
    Xtr_np, ytr_np, dtr = X[tr_mask], y[tr_mask], devs[tr_mask]
    Xte_np, yte_np = X[~tr_mask], y[~tr_mask]

    mu, sd = Xtr_np.mean(0), Xtr_np.std(0) + 1e-6
    Xtr_np = (Xtr_np - mu) / sd; Xte_np = (Xte_np - mu) / sd

    tau_triv = max(yte_np.mean(), 1 - yte_np.mean())
    print(f"train={len(ytr_np)} test={len(yte_np)}  TAU_TRIV={tau_triv:.4f}")

    Xtr = torch.tensor(Xtr_np, device=dev); ytr = torch.tensor(ytr_np, device=dev)
    Xte = torch.tensor(Xte_np, device=dev); yte_t = torch.tensor(yte_np, device=dev)
    d = Xtr.shape[1]

    # ---- MILD partition: IID random split across N clients (the EASY case) ----
    N, k, K = 20, 5, 100
    perm = rng.permutation(len(ytr_np))
    parts = {i: torch.tensor(np.sort(perm[i::N]), device=dev) for i in range(N)}
    S_JS = js_skew(parts, ytr, dtr, N)
    print(f"partition=IID(mild)  N={N} k={k} K={K}  S_JS={S_JS:.4f}")

    # ---- baseline: full-federation FedAvg, no attack ----
    t0 = time.time()
    gfull = fl_run(list(range(N)), Xtr, ytr, parts, d, dev)
    with torch.no_grad():
        acc_full = (gfull(Xte).argmax(1) == yte_t).float().mean().item()
    print(f"FedAvg(all {N}) clean acc = {acc_full:.4f}   [{time.time()-t0:.1f}s]")

    # ---- Algorithm 2: CertifySubsample ----
    all_subsets = list(combinations(range(N), k))
    total_subsets = len(all_subsets)
    exact = K >= total_subsets
    if exact:
        subsets = all_subsets
    else:
        sel = rng.choice(total_subsets, size=K, replace=False)
        subsets = [all_subsets[j] for j in sel]
    print(f"C({N},{k})={total_subsets}  ensemble K={len(subsets)}  exact={exact}")

    t0 = time.time(); votes = np.zeros((len(yte_np), 2), dtype=np.int32)
    for j, C in enumerate(subsets):
        gj = fl_run(list(C), Xtr, ytr, parts, d, dev)
        with torch.no_grad():
            pred = gj(Xte).argmax(1).cpu().numpy()
        votes[np.arange(len(pred)), pred] += 1
        if (j + 1) % 10 == 0:
            print(f"  ensemble {j+1}/{len(subsets)}  [{time.time()-t0:.0f}s]")
    Kn = len(subsets)

    srt = np.sort(votes, 1)
    n1, n2 = srt[:, -1], srt[:, -2]
    top = votes.argmax(1)
    margin = (n1 - n2) / Kn
    ens_acc = (top == yte_np).mean()
    print(f"\nensemble (majority-vote) accuracy = {ens_acc:.4f}")

    # class-balanced test subsample (ablation A7): guards against the vacuity
    # verdict being an artifact of natural class imbalance.
    pos = np.where(yte_np == 1)[0]; neg = np.where(yte_np == 0)[0]
    nb = min(len(pos), len(neg))
    bal = np.concatenate([rng.choice(pos, nb, replace=False),
                          rng.choice(neg, nb, replace=False)])
    tau_bal = 0.5
    print(f"balanced test subsample n={len(bal)}  TAU_TRIV_bal={tau_bal:.4f}")

    rows = []
    for beta in [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]:
        m = int(round(beta * N))
        p_clean = math.comb(N - m, k) / math.comb(N, k) if N - m >= k else 0.0
        thresh = 2 * (1 - p_clean)
        cert = margin > thresh
        CA = float((cert & (top == yte_np)).mean())
        cert_wrong = float((cert & (top != yte_np)).mean())
        CA_bal = float((cert[bal] & (top[bal] == yte_np[bal])).mean())
        def verdict(ca, tau):
            return "VACUOUS" if ca <= tau else ("MARGINAL" if ca <= tau + 0.10 else "INFORMATIVE")
        gap_note = verdict(CA, tau_triv); gap_bal = verdict(CA_bal, tau_bal)
        rows.append(dict(beta=beta, m=m, p_clean=round(p_clean, 4), threshold=round(thresh, 4),
                         CA=round(CA, 4), tau_triv=round(float(tau_triv), 4),
                         CA_minus_tau=round(CA - float(tau_triv), 4),
                         CA_balanced=round(CA_bal, 4), tau_triv_balanced=tau_bal,
                         CA_bal_minus_tau=round(CA_bal - tau_bal, 4),
                         certified_frac=round(float(cert.mean()), 4),
                         cert_wrong=round(cert_wrong, 4),
                         verdict=gap_note, verdict_balanced=gap_bal))
        print(f"beta={beta:4.2f} m={m:2d} p_clean={p_clean:.4f} thr={thresh:.4f} "
              f"CA={CA:.4f}(tau={tau_triv:.3f})->{gap_note:11s} | "
              f"CA_bal={CA_bal:.4f}(tau=0.5)->{gap_bal}")

    MC_het = 1.0 - float(margin.mean())
    beta_star = max([r["beta"] for r in rows if r["CA"] > tau_triv], default=None)
    beta_star_bal = max([r["beta"] for r in rows if r["CA_balanced"] > 0.5], default=None)
    out = dict(device=dev, N=N, k=k, K=Kn, exact=exact, S_JS=round(S_JS, 4),
               partition="iid_mild", dataset="iot-23",
               n_train=int(len(ytr_np)), n_test=int(len(yte_np)), dim=int(d),
               tau_triv=round(float(tau_triv), 4), fedavg_clean_acc=round(acc_full, 4),
               ensemble_acc=round(float(ens_acc), 4), MC_het=round(MC_het, 4),
               mean_margin=round(float(margin.mean()), 4), beta_star=beta_star,
               beta_star_balanced=beta_star_bal, grid=rows)
    with open(f"{OUT}/m1_probe.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n=== SUMMARY ===")
    print(f"MC_het (1 - mean margin) = {MC_het:.4f}")
    print(f"beta_star (max beta with CA > tau_triv)      = {beta_star}")
    print(f"beta_star_balanced (CA_bal > 0.5)             = {beta_star_bal}")
    print(f"wrote {OUT}/m1_probe.json")


if __name__ == "__main__":
    main()
