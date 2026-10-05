#!/usr/bin/env python3
"""CRFL-style parameter smoothing as a second certification family (review W6/E3).

The paper certifies by client subsampling: train K models on client subsets and
certify a prediction when the vote margin exceeds what the adversary could have
touched. The review's point is that the title is about the limits of client-count
certification, and a deployer wants to know whether the OTHER family survives
device-derived skew. This measures one cell of it.

Construction, following Xie et al. (ICML 2021) in mechanism rather than in every
detail -- stated that way in the paper, because it is an adaptation to this
setting and not a reimplementation:

  * every client's parameter vector is clipped to ||.|| <= rho at the server, so
    an UNBOUNDED Byzantine adversary is truncated to a bounded one by construction;
  * Gaussian noise sigma_train is added to the aggregate each round;
  * at test time the deployed theta is smoothed: draw T samples
    theta_i ~ N(theta, sigma^2 I), predict with each, take the majority;
  * a prediction is certified robust to any parameter perturbation with
    ||delta||_2 <= R = sigma * Phi^{-1}(p_A_lower), the Cohen et al. binary bound
    with p_A_lower a Clopper-Pearson lower confidence bound.

The adversary's reach: with FedAvg over N clients each clipped to rho, replacing
m honest vectors with malicious ones moves the aggregate by at most
Delta(m) = 2 * m * rho / N in a single round. A point is certified against m
malicious clients when R >= Delta(m). Delta is a per-round bound and therefore
GENEROUS to CRFL -- displacement can accumulate across rounds -- so any failure
it reports is a lower bound on the difficulty.
"""
import argparse, json, math, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import torch
from fedhomeguard import config as CFG, runner as R, fl as FL
from fedhomeguard.models import build_model
from fedhomeguard.fl import set_flat


def clopper_pearson_lower(k, n, alpha=0.001):
    """Lower confidence bound on a binomial proportion; no SciPy dependency."""
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):                      # bisect on the CP condition
        mid = (lo + hi) / 2
        # P[Bin(n, mid) >= k] = alpha  at the lower bound
        s = sum(math.comb(n, i) * mid**i * (1 - mid)**(n - i) for i in range(k, n + 1))
        if s > alpha:
            hi = mid
        else:
            lo = mid
    return lo


def norm_ppf(p):
    """Inverse standard normal CDF (Acklam), adequate at the precision we report."""
    if p <= 0: return -np.inf
    if p >= 1: return np.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage3_certification.yaml")
    ap.add_argument("--partition", default="device_derived")
    ap.add_argument("--pseed", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--betas", type=float, nargs="+", default=[0.0, 0.05, 0.10, 0.20])
    ap.add_argument("--rho", type=float, nargs="+", default=[5.0])
    ap.add_argument("--sigma", type=float, nargs="+", default=[0.01, 0.05, 0.1])
    ap.add_argument("--nsmooth", type=int, default=200)
    ap.add_argument("--attack", default="alie")
    ap.add_argument("--out", default="results/canonical/e18_crfl.jsonl")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    fh = open(a.out, "w")
    for pseed in a.pseed:
        cfg = CFG.load(a.config)
        cfg.partition.kind = a.partition
        cfg.partition.seed = pseed
        cfg.adversary.F3_knowledge = "white_box"
        t = R.prepare(cfg, verbose=False)
        N = cfg.partition.N
        ids = sorted(t["parts"])[:N]
        Xte, yte = t["Xte"], t["yte_np"]
        tau = t["tau"]
        print(f"[{a.partition} pseed={pseed}] tau={tau:.4f}", flush=True)
        for rho in a.rho:
            for sig in a.sigma:
                cfg.defense.name = "crfl"
                cfg.defense.observability = "L1"
                cfg.defense.clip_norm = rho
                cfg.defense.noise_sigma = sig
                for beta in a.betas:
                    m = int(round(beta * N))
                    mal = FL.A.select_malicious(N, beta, seed=0) if m else []
                    t0 = time.time()
                    g = FL.fl_run(cfg, ids, t["Xtr"], t["ytr"], t["parts"],
                                  malicious_ids=mal, attack=(a.attack if m else None),
                                  min_rows=16)
                    theta = FL.get_flat(g).clone()
                    # parameter smoothing
                    gen = torch.Generator(device=theta.device); gen.manual_seed(1234)
                    net = build_model(cfg, Xte.shape[1]).to(Xte.device).eval()
                    counts = np.zeros((len(yte), 2), dtype=np.int32)
                    with torch.no_grad():
                        for _ in range(a.nsmooth):
                            th = theta + torch.randn(theta.shape, generator=gen,
                                                     device=theta.device) * sig
                            set_flat(net, th)
                            counts[np.arange(len(yte)), net(Xte).argmax(1).cpu().numpy()] += 1
                    top = counts.argmax(1)
                    nA = counts.max(1)
                    # certified radius per point
                    pA = np.array([clopper_pearson_lower(int(k), a.nsmooth) for k in nA])
                    Rad = sig * np.array([norm_ppf(p) if p > 0.5 else -np.inf for p in pA])
                    delta = 2.0 * m * rho / N
                    cert = Rad >= delta if m else Rad > 0
                    acc = float((top == yte).mean())
                    ca = float(((top == yte) & cert).mean())
                    row = dict(family="crfl", partition_type=a.partition,
                               partition_seed=pseed, N=N, beta=beta, m=m, rho=rho,
                               sigma=sig, n_smooth=a.nsmooth, attack=(a.attack if m else None),
                               tau_triv=round(tau, 6), smoothed_acc=round(acc, 6),
                               CA=round(ca, 6), coverage=round(float(cert.mean()), 6),
                               delta_reach=round(delta, 6),
                               median_radius=round(float(np.median(Rad[np.isfinite(Rad)]))
                                                   if np.isfinite(Rad).any() else 0.0, 6),
                               max_radius=round(float(np.max(Rad[np.isfinite(Rad)]))
                                                if np.isfinite(Rad).any() else 0.0, 6),
                               secs=round(time.time() - t0, 1))
                    fh.write(json.dumps(row) + "\n"); fh.flush()
                    print(f"  rho={rho} sig={sig} b={beta:.2f} m={m}: acc={acc:.4f} "
                          f"CA={ca:.4f} cov={cert.mean():.4f} "
                          f"medR={row['median_radius']:.4f} vs reach={delta:.4f} "
                          f"[{row['secs']:.0f}s]", flush=True)
    fh.close()
    print(f"DONE -> {a.out}")


if __name__ == "__main__":
    main()
