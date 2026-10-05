"""Aggregation rules, each tagged with the observability level it consumes (design 2.2).

L0 sees only the aggregate. L1 sees individual updates. L2 additionally needs a CLEAN
labelled server-side validation set -- the recurring deployment assumption the
systematization targets. L3 knows the true malicious set and is an UPPER BOUND that
must never be reported as achievable.
"""
from __future__ import annotations
import torch

LEVEL = {"fedavg": "L0", "krum": "L1", "multikrum": "L1", "trimmed_mean": "L1",
         "crfl": "L1",   # clipping requires seeing each client update
         "median": "L1", "norm_clip": "L1", "fltrust": "L2", "oracle_trimmed": "L3"}
REQUIRES_CLEAN_SERVER_DATA = {"fltrust"}
IS_UPPER_BOUND = {"oracle_trimmed"}


def _stack(updates: dict[int, torch.Tensor]):
    ids = sorted(updates)
    return ids, torch.stack([updates[i] for i in ids])


def fedavg(updates, weights=None, **_):
    ids, U = _stack(updates)
    if weights is None:
        return U.mean(0)
    w = torch.tensor([weights[i] for i in ids], device=U.device, dtype=U.dtype)
    return (U * (w / w.sum()).unsqueeze(1)).sum(0)


def _krum_scores(U, n_mal):
    n = U.shape[0]
    d2 = torch.cdist(U, U) ** 2
    keep = max(1, n - n_mal - 2)
    return torch.stack([torch.sort(d2[i])[0][1:keep + 1].sum() for i in range(n)])


def krum(updates, n_mal=0, **_):
    _, U = _stack(updates)
    return U[int(torch.argmin(_krum_scores(U, n_mal)))].clone()


def multikrum(updates, n_mal=0, **_):
    _, U = _stack(updates)
    n = U.shape[0]
    m = max(1, n - n_mal)
    sel = torch.argsort(_krum_scores(U, n_mal))[:m]
    return U[sel].mean(0)


def trimmed_mean(updates, trim_frac=0.2, **_):
    _, U = _stack(updates)
    n = U.shape[0]
    t = int(trim_frac * n)
    if 2 * t >= n:
        t = max(0, (n - 1) // 2)
    S, _i = torch.sort(U, dim=0)
    return S[t:n - t].mean(0) if n - 2 * t > 0 else S.mean(0)


def median(updates, **_):
    _, U = _stack(updates)
    return U.median(0).values


def norm_clip(updates, clip_norm=5.0, **_):
    ids, U = _stack(updates)
    nrm = U.norm(dim=1, keepdim=True)
    return (U * torch.clamp(clip_norm / (nrm + 1e-12), max=1.0)).mean(0)


def fltrust(updates, server_update=None, **_):
    """L2. Requires a clean labelled server root dataset to produce `server_update`."""
    if server_update is None:
        raise ValueError("fltrust is an L2 defense: it requires a clean server root update. "
                         "Set defense.observability='L2' and provide root data.")
    ids, U = _stack(updates)
    g0 = server_update
    cos = torch.clamp((U @ g0) / (U.norm(dim=1) * g0.norm() + 1e-12), min=0.0)
    if cos.sum() <= 0:
        return g0.clone()
    Un = U * (g0.norm() / (U.norm(dim=1, keepdim=True) + 1e-12))
    return (Un * (cos / cos.sum()).unsqueeze(1)).sum(0)


def oracle_trimmed(updates, malicious_ids=(), **_):
    """L3 UPPER BOUND -- drops the true malicious set. Never achievable in deployment."""
    honest = {i: u for i, u in updates.items() if i not in set(malicious_ids)}
    if not honest:
        raise ValueError("oracle_trimmed: no honest clients remain")
    return fedavg(honest)


REGISTRY = {"fedavg": fedavg, "krum": krum, "multikrum": multikrum,
            "trimmed_mean": trimmed_mean, "median": median, "norm_clip": norm_clip,
            "fltrust": fltrust, "oracle_trimmed": oracle_trimmed}


def get(name: str):
    if name not in REGISTRY:
        raise ValueError(f"unknown defense {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name]


def check_observability(name: str, declared: str) -> None:
    need = LEVEL[name]
    order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
    if order[declared] < order[need]:
        raise ValueError(f"defense {name!r} consumes {need} but the capability record "
                         f"declares {declared}. Raise defense.observability or change defense.")


def crfl(updates, clip_norm=5.0, noise_sigma=0.0, gen=None, **_):
    """CRFL-style aggregation (Xie et al., ICML 2021): clip every update, then add
    isotropic Gaussian noise to the aggregate.

    This is the second certification family the review asks for (W6/E3), and it buys
    its guarantee differently from client subsampling. Clipping is what makes the
    bound hold against an UNBOUNDED Byzantine adversary: whatever a malicious client
    sends, the server truncates it to `clip_norm`, so m malicious clients displace the
    FedAvg aggregate by at most m*clip_norm/N. The noise then supports a
    randomised-smoothing certificate in parameter space.

    The cost is observability. Clipping requires the server to see each client's
    update, so CRFL sits at L1; the subsampling certificate operates at L0, seeing
    only aggregates. That difference is the point of comparing them here.
    """
    ids, U = _stack(updates)
    nrm = U.norm(dim=1, keepdim=True)
    agg = (U * torch.clamp(clip_norm / (nrm + 1e-12), max=1.0)).mean(0)
    if noise_sigma and noise_sigma > 0:
        noise = torch.randn(agg.shape, generator=gen, device=agg.device,
                            dtype=agg.dtype) * noise_sigma
        agg = agg + noise
    return agg


# registered after definition: crfl is appended below the original registry block
REGISTRY["crfl"] = crfl
