"""EXACT finite-ensemble certification (replaces the sampled + Clopper-Pearson path).

WHY THIS EXISTS
---------------
FLCert-style certification samples K subsets from the C(N,k) population and then
needs a confidence correction, because it certifies the *idealised* population
ensemble from a sample of it. That construction has two costs the review flagged
(P0 items 6 and 7): the confidence semantics are never pinned down (per test point?
simultaneous?), and the guarantee is probabilistic.

Neither cost is necessary. The predictor an operator actually deploys IS the
realised K-member ensemble. For that predictor the counting argument is exact:

    a member j is corrupted  <=>  S_j intersects B

so the number of members the adversary can touch, for a worst-case malicious set,
is a purely combinatorial quantity over the REALISED subsets:

    c_max(m) = max_{|B| = m} |{ j : S_j ∩ B != {} }|

and the certification condition is

    margin > 2 * c_max(m) / K.

Three consequences:

1. No sampling error and no confidence interval. The statement is exact.
2. SOUND EVEN AGAINST A SEED-AWARE ADVERSARY. c_max takes the maximum over B given
   the realised subsets, so an adversary who knows which subsets were drawn and
   picks B to maximise corruption gains nothing. The private-seed assumption is
   NOT load-bearing here; it is load-bearing for the population certificate.
3. It is never weaker than the corrected sampled certificate at the same K, and we
   assert exactly that in the E1 validation suite.

c_max is a max-coverage quantity and NP-hard in general; at N <= 20 we enumerate
every B exactly, so nothing here is approximate.
"""
from __future__ import annotations
import math
from itertools import combinations
import numpy as np


def subset_masks(subsets, N: int) -> np.ndarray:
    """Bitmask per ensemble member over the client index space."""
    out = np.zeros(len(subsets), dtype=np.int64)
    for j, S in enumerate(subsets):
        b = 0
        for i in S:
            b |= (1 << int(i))
        out[j] = b
    return out


def c_max_exact(masks: np.ndarray, N: int, m: int, chunk: int = 4096) -> tuple[int, tuple]:
    """max_{|B|=m} #{members whose subset meets B}. Exact enumeration over B.

    Returns (c_max, one attaining B). m=0 gives 0.
    """
    K = len(masks)
    if m <= 0:
        return 0, ()
    if m >= N:
        return K, tuple(range(N))
    best, best_B = -1, ()
    buf_masks, buf_B = [], []

    def flush():
        nonlocal best, best_B, buf_masks, buf_B
        if not buf_masks:
            return
        Bs = np.array(buf_masks, dtype=np.int64)
        hits = ((masks[None, :] & Bs[:, None]) != 0).sum(1)
        j = int(hits.argmax())
        if hits[j] > best:
            best, best_B = int(hits[j]), buf_B[j]
        buf_masks, buf_B = [], []

    for B in combinations(range(N), m):
        b = 0
        for i in B:
            b |= (1 << i)
        buf_masks.append(b); buf_B.append(B)
        if len(buf_masks) >= chunk:
            flush()
    flush()
    return best, best_B


def c_max_upper(masks: np.ndarray, N: int, m: int) -> int:
    """Sound UPPER bound on c_max when enumerating every B is infeasible.

    A malicious set of size m touches at most the sum of the m largest member
    degrees, where deg(i) counts the members whose subset contains client i, because
    a union is never larger than the sum of its parts. Overstating c_max only ever
    raises the certification threshold, so the resulting certificate stays sound; it
    is simply more conservative than exact enumeration.
    """
    if m <= 0:
        return 0
    deg = np.array([int(((masks & (1 << i)) != 0).sum()) for i in range(N)])
    return int(min(len(masks), deg[np.argsort(-deg)[:m]].sum()))


def c_max_bounded(masks: np.ndarray, N: int, m: int,
                  enum_cap: int = 200_000) -> tuple[int, str, tuple]:
    """Exact c_max when the enumeration over B is affordable, otherwise the sound
    upper bound. Returns (value, mode, attaining_B)."""
    if m <= 0:
        return 0, "exact", ()
    if m >= N:
        return len(masks), "exact", tuple(range(N))
    if math.comb(N, m) <= enum_cap:
        c, B = c_max_exact(masks, N, m)
        return c, "exact", B
    return c_max_upper(masks, N, m), "degree_upper_bound", ()


def c_max_table(subsets, N: int, ms) -> dict:
    """c_max for each m, plus the population comparison 1 - p_clean."""
    masks = subset_masks(subsets, N)
    K = len(masks)
    out = {}
    for m in sorted(set(int(x) for x in ms)):
        c, mode, B = c_max_bounded(masks, N, m)
        pop = 1.0 - (math.comb(N - m, len(subsets[0])) / math.comb(N, len(subsets[0]))
                     if N - m >= len(subsets[0]) else 0.0)
        out[m] = dict(c_max=c, K=K, corrupt_frac=c / K, threshold=2.0 * c / K,
                      c_max_mode=mode, worst_B=list(B),
                      population_corrupt_frac=pop, population_threshold=2.0 * pop,
                      certifiable=bool(2.0 * c / K < 1.0))
    return out


def certify_exact(votes: np.ndarray, y_true: np.ndarray, subsets, N: int, k: int,
                  betas, tau_triv: float | None = None,
                  mal_label: int = 1) -> dict:
    """Exact certification of the realised ensemble + the full IDS metric panel.

    votes[i, c] = number of members predicting class c for test point i.
    """
    K = int(votes[0].sum())
    assert K == len(subsets), f"votes sum to {K} but there are {len(subsets)} members"
    srt = np.sort(votes, 1)
    margin = (srt[:, -1] - srt[:, -2]) / K
    top = votes.argmax(1)
    correct = (top == y_true)
    if tau_triv is None:
        tau_triv = float(max(y_true.mean(), 1 - y_true.mean()))

    ms = [int(round(b * N)) for b in betas]
    ctab = c_max_table(subsets, N, ms)
    thr0 = ctab[0]["threshold"] if 0 in ctab else 0.0
    cert0 = margin > thr0                      # certifiable with NO adversary at all

    grid = []
    for b in betas:
        m = int(round(b * N))
        e = ctab[m]
        thr = e["threshold"]
        cert = margin > thr
        CA = float((cert & correct).mean())
        # Certification failure decomposition (review sec 29): every test point lands
        # in exactly one of four classes.
        geometric = bool(thr >= 1.0)
        cls_ok = cert & correct
        cls_certwrong = cert & ~correct
        cls_geo = (~cert) & np.full(len(margin), geometric)
        cls_margin = (~cert) & ~cls_geo
        grid.append(dict(
            beta=float(b), m=m, K=K,
            c_max=e["c_max"], c_max_mode=e["c_max_mode"],
            corrupt_frac=round(e["corrupt_frac"], 6),
            threshold=round(thr, 6), combinatorially_possible=bool(thr < 1.0),
            population_threshold=round(2.0 * e["population_corrupt_frac"], 6),
            CA=round(CA, 6), tau_triv=round(tau_triv, 6),
            CA_minus_tau=round(CA - tau_triv, 6),
            coverage=round(float(cert.mean()), 6),
            cert_wrong=round(float(cls_certwrong.mean()), 6),
            # four-way decomposition, sums to 1
            frac_correct_certified=round(float(cls_ok.mean()), 6),
            frac_certified_wrong=round(float(cls_certwrong.mean()), 6),
            frac_geometric_impossible=round(float(cls_geo.mean()), 6),
            frac_margin_limited=round(float(cls_margin.mean()), 6),
            # legacy abstention split, kept for continuity with the old tables
            abstain_het=round(float((~cert & ~cert0).mean()), 6),
            abstain_adv=round(float((~cert & cert0).mean()), 6),
            **_ids_panel(top, y_true, cert, mal_label),
        ))
    beta_star = max([g["beta"] for g in grid if g["CA"] > tau_triv], default=0.0)
    return dict(mode="exact_finite_ensemble", K=K, k=k, N=N,
                tau_triv=round(tau_triv, 6),
                ensemble_acc=round(float(correct.mean()), 6),
                mean_margin=round(float(margin.mean()), 6),
                median_margin=round(float(np.median(margin)), 6),
                MC_het=round(1.0 - float(margin.mean()), 6),
                beta_star=beta_star, grid=grid,
                c_max_table={str(m): v for m, v in ctab.items()})


def _ids_panel(top: np.ndarray, y: np.ndarray, cert: np.ndarray, mal: int) -> dict:
    """Class-conditional IDS metrics, clean and certified (review sec 11)."""
    ben = 1 - mal
    P = (y == mal); Nn = (y == ben)
    tp = int(((top == mal) & P).sum()); fn = int(((top == ben) & P).sum())
    fp = int(((top == mal) & Nn).sum()); tn = int(((top == ben) & Nn).sum())
    tpr = tp / max(P.sum(), 1); fpr = fp / max(Nn.sum(), 1)
    tnr = tn / max(Nn.sum(), 1)
    prec = tp / max(tp + fp, 1)
    f1m = 2 * prec * tpr / max(prec + tpr, 1e-12)
    prec_b = tn / max(tn + fn, 1); rec_b = tnr
    f1b = 2 * prec_b * rec_b / max(prec_b + rec_b, 1e-12)
    # certified-and-correct, per class -- the security-relevant quantity
    ctr_mal = float(((top == mal) & P & cert).sum()) / max(int(P.sum()), 1)
    ctr_ben = float(((top == ben) & Nn & cert).sum()) / max(int(Nn.sum()), 1)
    return dict(
        TPR=round(float(tpr), 6), FNR=round(float(1 - tpr), 6),
        FPR=round(float(fpr), 6), precision=round(float(prec), 6),
        balanced_acc=round(float(0.5 * (tpr + tnr)), 6),
        macro_F1=round(float(0.5 * (f1m + f1b)), 6),
        CTR_mal=round(ctr_mal, 6), CTR_ben=round(ctr_ben, 6),
        n_mal_test=int(P.sum()), n_ben_test=int(Nn.sum()))
