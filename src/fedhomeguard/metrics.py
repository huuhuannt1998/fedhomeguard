"""Metric instrument (design 1.5) and the gap analyzer (Algorithm 7)."""
from __future__ import annotations
import numpy as np


def tau_triv(y: np.ndarray) -> float:
    """The trivial certificate: a constant predictor is certifiably robust to EVERY
    beta. Any CA at or below this conveys zero information. It is the mandatory
    hardest baseline (design 11.2)."""
    return float(max(y.mean(), 1 - y.mean()))


def balanced_index(y: np.ndarray, seed: int = 0) -> np.ndarray:
    """Class-balanced test subsample (ablation A7) so a vacuity verdict is never an
    artifact of natural class imbalance."""
    rng = np.random.default_rng(seed)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    n = min(len(pos), len(neg))
    if n == 0:
        return np.arange(len(y))
    return np.concatenate([rng.choice(pos, n, replace=False), rng.choice(neg, n, replace=False)])


def ea_min(records: list[dict]) -> dict:
    """Empirical robustness, as the LITERATURE would state it.

    For each defense, its robustness is the worst case over the finite attack set:
        EA_min(defense) = min_{a in 𝒜tk} EA(defense, a)
    The field's claim is then the BEST such defense, because an operator gets to pick
    one:
        EA_min = max_{defense} min_{a} EA(defense, a)

    Taking a plain min over all (defense, attack) records instead would compare the
    certified ensemble against whichever defense happened to be weakest, which is not
    apples-to-apples and produces spurious Gamma < 0.

    𝒜tk is finite, so this is an UPPER bound on true empirical robustness, and Gamma
    is therefore a LOWER bound on the true gap -- conservative (design C5).
    """
    if not records:
        return dict(EA_min=None, argmin_attack=None, n_attacks=0, per_defense={})
    per: dict[str, dict] = {}
    for r in records:
        d = r.get("defense", "unknown")
        if d not in per or r["EA"] < per[d]["EA"]:
            per[d] = r
    # L3 oracle defenses are upper bounds and must never set the headline.
    admissible = {d: r for d, r in per.items() if d != "oracle_trimmed"} or per
    best_def = max(admissible, key=lambda d: admissible[d]["EA"])
    best = admissible[best_def]
    return dict(EA_min=round(float(best["EA"]), 6), best_defense=best_def,
                argmin_attack=best.get("attack"), n_attacks=len(records),
                per_defense={d: dict(EA_min=round(float(r["EA"]), 6),
                                     worst_attack=r.get("attack")) for d, r in per.items()},
                note="max over defenses of min over attacks; upper bound on empirical "
                     "robustness, so Gamma is a lower bound on the true gap")


def gap(EA_min_val: float | None, CA: float) -> dict:
    """Gamma = EA_min - CA. Gamma < 0 is a BUG SIGNAL (unsound certificate or an
    attack outside the declared threat class), never a finding (design C8)."""
    if EA_min_val is None:
        return dict(Gamma=None, bug=False, note="no empirical arm yet")
    g = EA_min_val - CA
    return dict(Gamma=round(float(g), 6), bug=bool(g < -1e-9),
                note=("BUG: certified accuracy exceeds observed worst-case accuracy. "
                      "Audit certificate soundness and whether the attack left the "
                      "declared threat class." if g < -1e-9 else "ok"))


def honest_region(cert_rows: list[dict]) -> list[dict]:
    """R_hon = {(beta,S) : CA > tau_triv}."""
    return [dict(beta=r["beta"], S_JS=r.get("S_JS"), CA=r["CA"], tau=r["tau_triv"])
            for r in cert_rows if r["CA"] > r["tau_triv"]]


def claim_gap_region(R_lit: list[dict], cert_rows: list[dict], tol: float = 1e-9) -> list[dict]:
    """R_lit \\ R_hon -- where the literature claims robustness and no certificate
    supports any. This is the paper's headline object (design 1.3)."""
    hon = {(round(r["beta"], 4), round(r.get("S_JS") or 0.0, 3))
           for r in cert_rows if r["CA"] > r["tau_triv"] + tol}
    out = []
    for c in R_lit:
        key = (round(c["beta"], 4), round(c.get("S_JS") or 0.0, 3))
        if key not in hon:
            out.append(dict(**c, certified_supported=False))
    return out


def summarize(cert: dict, empirical: list[dict] | None = None) -> dict:
    """Algorithm 7 -- join the certified and empirical arms into the gap surface."""
    rows = []
    by_beta: dict[float, list[dict]] = {}
    for r in (empirical or []):
        by_beta.setdefault(round(float(r["beta"]), 6), []).append(r)
    for g in cert["grid"]:
        e = ea_min(by_beta.get(round(g["beta"], 6), []))
        rows.append({**g, **{f"emp_{k}": v for k, v in e.items()},
                     **gap(e["EA_min"], g["CA"])})
    return dict(beta_star=cert["beta_star"], beta_geo=cert["beta_geo"],
                tau_triv=cert["tau_triv"], ensemble_acc=cert["ensemble_acc"],
                MC_het=cert["MC_het"], exact=cert["exact"], K=cert["K"],
                k=cert["k"], N=cert["N"], rows=rows,
                any_bug=any(r.get("bug") for r in rows))
