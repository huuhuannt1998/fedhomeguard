"""Certification engines.

ALGORITHM 2 -- CertifySubsample (FLCert / Cao et al. style). Certifies invariance to
  ANY behaviour of at most m malicious clients, by a counting argument that never
  mentions the adversary's update values.
ALGORITHM 3 -- CertifySmoothing (CRFL style). Certifies a bounded-MAGNITUDE radius.

These certify DIFFERENT threat classes and must never be merged into one column.

KEY STRUCTURAL FACT (measured in M1, jrn_01M0EH3187H0R085Y6Z24VHXXN):
  certification requires  margin > 2*(1 - p_clean)  and  margin <= 1  always,
  so it is IMPOSSIBLE whenever p_clean <= 1/2, giving the ceiling
        beta_cert  <  1 - 2^(-1/k)
  independent of N, the data and the model.
"""
from __future__ import annotations
import math
from itertools import combinations
import numpy as np

try:
    from scipy.stats import beta as _beta
except ImportError:
    _beta = None


# ------------------------------------------------------------ combinatorial geometry
def p_clean(N: int, m: int, k: int) -> float:
    """Minimum fraction of ensemble members trained on a subset disjoint from B."""
    if m < 0 or m > N or k > N:
        raise ValueError(f"bad (N,m,k)=({N},{m},{k})")
    if N - m < k:
        return 0.0
    return math.comb(N - m, k) / math.comb(N, k)


def cert_threshold(N: int, m: int, k: int) -> float:
    return 2.0 * (1.0 - p_clean(N, m, k))


def is_certifiable(N: int, m: int, k: int) -> bool:
    """False => NO model on NO dataset can certify here. Purely combinatorial."""
    return cert_threshold(N, m, k) < 1.0


def beta_geo(N: int, k: int) -> float:
    """Largest malicious fraction at which certification is combinatorially possible."""
    best = 0.0
    for m in range(N + 1):
        if p_clean(N, m, k) > 0.5:
            best = m / N
        else:
            break
    return best


def beta_geo_asymptotic(k: int) -> float:
    """Large-N limit of beta_geo: 1 - 2^(-1/k)."""
    return 1.0 - 2.0 ** (-1.0 / k)


# ---------------------------------------------------------------- Clopper-Pearson CI
def cp_lower(x: int, n: int, alpha: float) -> float:
    if n == 0: return 0.0
    if x == 0: return 0.0
    if _beta is None: return max(0.0, x / n - math.sqrt(math.log(1 / alpha) / (2 * n)))
    return float(_beta.ppf(alpha, x, n - x + 1))


def cp_upper(x: int, n: int, alpha: float) -> float:
    if n == 0: return 1.0
    if x == n: return 1.0
    if _beta is None: return min(1.0, x / n + math.sqrt(math.log(1 / alpha) / (2 * n)))
    return float(_beta.ppf(1 - alpha, x + 1, n - x))


# ------------------------------------------------------------------------ Algorithm 2
def choose_subsets(N: int, k: int, K: int, seed: int = 0, prefer_exact: bool = True,
                   exact_cap: int = 20_000):
    """Exact enumeration when affordable -- it is both CHEAPER and STRONGER than
    sampling (no confidence interval needed)."""
    total = math.comb(N, k)
    if prefer_exact and total <= min(K, exact_cap):
        return list(combinations(range(N), k)), True, total
    if prefer_exact and total <= exact_cap and total <= K:
        return list(combinations(range(N), k)), True, total
    allc = list(combinations(range(N), k))
    rng = np.random.default_rng(seed)
    sel = rng.choice(len(allc), size=min(K, len(allc)), replace=not (K <= len(allc)))
    return [allc[j] for j in sel], (len(sel) == total), total


def certify_from_votes(votes: np.ndarray, y_true: np.ndarray, N: int, k: int,
                       betas, exact: bool, confidence: float = 0.999,
                       tau_triv: float | None = None) -> dict:
    """Turn per-point ensemble votes into certified accuracy at each beta.

    votes[i, c] = number of ensemble members predicting class c for test point i.
    """
    K = int(votes[0].sum())
    srt = np.sort(votes, 1)
    n1, n2 = srt[:, -1].astype(int), srt[:, -2].astype(int)
    top = votes.argmax(1)
    alpha = 1.0 - confidence
    if exact:
        margin = (n1 - n2) / K
    else:
        margin = np.array([cp_lower(a, K, alpha) - cp_upper(b, K, alpha)
                           for a, b in zip(n1, n2)])
    if tau_triv is None:
        tau_triv = float(max(y_true.mean(), 1 - y_true.mean()))

    cert0 = margin > cert_threshold(N, 0, k)
    grid = []
    for b in betas:
        m = int(round(b * N))
        pc, thr = p_clean(N, m, k), cert_threshold(N, m, k)
        cert = margin > thr
        CA = float((cert & (top == y_true)).mean())
        grid.append(dict(
            beta=float(b), m=m, p_clean=round(pc, 6), threshold=round(thr, 6),
            combinatorially_possible=bool(thr < 1.0),
            CA=round(CA, 6), tau_triv=round(tau_triv, 6),
            CA_minus_tau=round(CA - tau_triv, 6),
            certified_frac=round(float(cert.mean()), 6),
            cert_wrong=round(float((cert & (top != y_true)).mean()), 6),
            abstain_het=round(float((~cert & ~cert0).mean()), 6),
            abstain_adv=round(float((~cert & cert0).mean()), 6),
            severity=severity(CA, tau_triv, float((cert & (top != y_true)).mean()),
                              b, float((cert0 & (top == y_true)).mean())),
        ))
    beta_star = max([g["beta"] for g in grid if g["CA"] > tau_triv], default=0.0)
    return dict(K=K, k=k, N=N, exact=bool(exact), tau_triv=round(tau_triv, 6),
                ensemble_acc=round(float((top == y_true).mean()), 6),
                mean_margin=round(float(margin.mean()), 6),
                # Clopper-Pearson margins can go negative at small K, so clip before
                # forming MC_het, which is defined as a fraction of margin in [0,1].
                MC_het=round(1.0 - float(np.clip(margin, 0.0, 1.0).mean()), 6),
                MC_adv={str(g["beta"]): g["threshold"] for g in grid},
                beta_star=beta_star, beta_geo=beta_geo(N, k), grid=grid)


def severity(CA: float, tau: float, cert_wrong: float, beta: float, CA0: float) -> str:
    """Predeclared severity classes (design 9.2). Fixed BEFORE any run."""
    if cert_wrong > 0.05:
        return "S4_certified_wrong"
    if beta == 0.0 and CA <= tau:
        return "S3_collapsed"            # heterogeneity alone killed it
    if CA <= tau:
        return "S2_vacuous"
    if CA <= tau + 0.10:
        return "S1_marginal"
    return "S0_informative"


def hicc_verdict(MC_het: float, threshold_at_m: float, EA_min: float | None,
                 ea_bar: float = 0.90) -> dict:
    """ALGORITHM 6 -- HICC holds iff heterogeneity + adversary budget exceed the
    available margin WHILE empirical defenses still look excellent."""
    exceeds = (MC_het + threshold_at_m) > 1.0
    holds = bool(exceeds and EA_min is not None and EA_min > ea_bar)
    return dict(MC_het=round(MC_het, 6), MC_adv=round(threshold_at_m, 6),
                sum=round(MC_het + threshold_at_m, 6), budget_exceeded=bool(exceeds),
                EA_min=EA_min, hicc_holds=holds)


# ------------------------------------------------------------------------ Algorithm 3
def certify_smoothing(pred_counts: np.ndarray, y_true: np.ndarray, n_smooth: int,
                      sigma: float, rho: float, confidence: float = 0.999) -> dict:
    """CRFL-style: certified radius sigma * Phi^-1(p_top) in parameter perturbation."""
    from scipy.stats import norm
    alpha = 1.0 - confidence
    top = pred_counts.argmax(1)
    ptop = np.array([cp_lower(int(pred_counts[i, top[i]]), n_smooth, alpha)
                     for i in range(len(top))])
    radius = np.where(ptop > 0.5, sigma * norm.ppf(np.clip(ptop, 1e-9, 1 - 1e-9)), 0.0)
    tau = float(max(y_true.mean(), 1 - y_true.mean()))
    CA = float(((radius >= rho) & (top == y_true)).mean())
    return dict(family="crfl_smoothing", sigma=sigma, rho=rho, n_smooth=n_smooth,
                tau_triv=round(tau, 6), CA_rho=round(CA, 6),
                median_radius=round(float(np.median(radius)), 6),
                frac_positive_radius=round(float((radius > 0).mean()), 6),
                note="bounded-MAGNITUDE class; NOT comparable to the client-count "
                     "certificate from Algorithm 2 and must not be merged with it.")
