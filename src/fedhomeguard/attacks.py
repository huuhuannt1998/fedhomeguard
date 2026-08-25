"""Attack suite (the finite set 𝒜tk).

EA_min = min over this set is an UPPER bound on true empirical robustness, so the
measured gap Γ is a LOWER bound on the true gap -- conservative, and stated as such
(design C5). Every attack declares the capability level (F3) it requires.
"""
from __future__ import annotations
import numpy as np, torch

# attack -> minimum knowledge level required
REQUIRES = {"none": "black_box", "label_flip": "black_box", "sign_flip": "gray_box",
            "gaussian": "black_box", "ipm": "white_box", "alie": "white_box",
            "backdoor": "gray_box"}
_ORDER = {"black_box": 0, "gray_box": 1, "white_box": 2}


def check_capability(attack: str, knowledge: str) -> None:
    need = REQUIRES.get(attack)
    if need is None:
        raise ValueError(f"unknown attack {attack!r}")
    if _ORDER[knowledge] < _ORDER[need]:
        raise ValueError(f"attack {attack!r} needs F3>={need}, capability record says {knowledge}")


def select_malicious(N: int, beta: float, seed: int = 0) -> list[int]:
    m = int(round(beta * N))
    if m == 0:
        return []
    return sorted(np.random.default_rng(seed).choice(N, size=m, replace=False).tolist())


def project(u: torch.Tensor, space: str, rho: float | None) -> torch.Tensor:
    """Enforce F2. byzantine_unbounded is the identity; l2_ball projects onto ||u||<=rho."""
    if space == "byzantine_unbounded":
        return u
    if space == "l2_ball":
        if rho is None:
            raise ValueError("F2_update_space='l2_ball' requires F2_rho")
        n = u.norm()
        return u if n <= rho else u * (rho / (n + 1e-12))
    raise ValueError(f"unknown update space {space!r}")


def malicious_update(attack: str, theta: torch.Tensor, honest: list[torch.Tensor],
                     scale: float, gen: torch.Generator | None = None) -> torch.Tensor:
    """Return the malicious update given the round's honest updates (may be empty)."""
    if attack in (None, "none"):
        return theta.clone()
    if honest:
        H = torch.stack(honest); mu = H.mean(0); sd = H.std(0) + 1e-12
    else:
        mu, sd = theta.clone(), torch.ones_like(theta)

    if attack == "sign_flip":
        return theta - scale * (mu - theta)
    if attack == "gaussian":
        noise = torch.randn(theta.shape, generator=gen, device=theta.device, dtype=theta.dtype)
        return mu + scale * noise * sd
    if attack == "ipm":                      # inner-product manipulation (Xie et al.)
        return theta - scale * (mu - theta)
    if attack == "alie":                     # a little is enough (Baruch et al.)
        return mu - scale * sd
    if attack in ("label_flip", "backdoor"):
        return mu                            # realized in the data, not the update
    raise ValueError(f"unknown attack {attack!r}")


def poison_labels(y: torch.Tensor) -> torch.Tensor:
    """label_flip: flip binary labels on the malicious client's local data."""
    return 1 - y


def apply_backdoor(X: torch.Tensor, y: torch.Tensor, feat_idx: list[int],
                   value: float = 3.0, target: int = 0, frac: float = 0.5,
                   gen: torch.Generator | None = None):
    """Stamp a trigger on a fraction of rows and relabel to `target`."""
    n = len(y)
    k = max(1, int(frac * n))
    idx = torch.randperm(n, generator=gen, device=X.device)[:k]
    Xp, yp = X.clone(), y.clone()
    Xp[idx[:, None], torch.tensor(feat_idx, device=X.device)] = value
    yp[idx] = target
    return Xp, yp, idx


def trigger_test_set(X: torch.Tensor, feat_idx: list[int], value: float = 3.0):
    Xb = X.clone()
    Xb[:, torch.tensor(feat_idx, device=X.device)] = value
    return Xb


REGISTRY = list(REQUIRES)
