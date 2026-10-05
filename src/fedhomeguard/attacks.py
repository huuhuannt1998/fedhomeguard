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
            "backdoor": "gray_box", "adaptive": "white_box",
            "vote_shape": "black_box", "rand_flip": "black_box",
            "replace_invert": "white_box"}
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
                     scale: float, gen: torch.Generator | None = None, *,
                     honest_w: list[float] | None = None,
                     mal_w: float | None = None,
                     pop_std: bool = False,
                     single_honest_zero_sd: bool = True) -> torch.Tensor:
    """Return the malicious update given the round's honest updates (may be empty).

    honest_w / mal_w are the FedAvg sample weights. They are only consumed by the
    `adaptive` attack, which solves for the post-aggregation model rather than
    perturbing its own contribution; every other attack ignores them, so callers
    that omit them keep their existing behaviour bit-for-bit.

    single_honest_zero_sd (review r6, DEFAULT since the correction): alie and gaussian
    estimate the honest spread with the unbiased std, which is NaN for a single honest
    update, so a member holding exactly one honest client used to receive a non-finite
    malicious update. The spread is now 0 in that case -- the attacks' published
    behaviour with one benign peer -- and the unbiased std is kept whenever there are
    two or more honest updates, so every member that never hit the NaN path is
    bit-for-bit unchanged. single_honest_zero_sd=False reproduces the frozen
    pre-correction results in results/canonical/e2_*. pop_std (review r5) instead uses
    the population std throughout; it is a comparison arm, not the paper's setting.
    """
    if attack in (None, "none"):
        return theta.clone()
    if honest:
        H = torch.stack(honest); mu = H.mean(0)
        if pop_std:
            sd = H.std(0, unbiased=False) + 1e-12
        elif single_honest_zero_sd and len(honest) == 1:
            sd = torch.zeros_like(mu) + 1e-12
        else:
            sd = H.std(0) + 1e-12
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
    if attack == "adaptive":
        # Adaptive, vote-targeting attack (this work).
        #
        # The five published attacks above all perturb the adversary's OWN
        # contribution, so FedAvg dilutes them by m/N and their effect shrinks as the
        # federation grows. An adversary that can see the round's honest updates does
        # not have to accept that dilution: it can solve for the update whose
        # aggregate IS its chosen target.
        #
        #   FedAvg:  theta' = (sum_h w_h u_h + W_m u_mal) / (sum_h w_h + W_m)
        #   solve :  u_mal  = (target * (W_h + W_m) - H) / W_m
        #
        # The target is the reflection of the honest consensus through the current
        # global model: the direction honest training is moving AWAY from, which for
        # a plurality-vote ensemble is the direction that flips the most member
        # predictions per unit of parameter movement.
        #
        # This is strictly stronger than ipm/sign_flip -- it attains the target drift
        # for ANY m >= 1 -- and it is the same manoeuvre the containerised attacker in
        # docker/fl_client_malicious.py performs against the real stack.
        if not honest:
            return theta - scale * torch.ones_like(theta)
        w = honest_w if honest_w else [1.0] * len(honest)
        W_h = float(sum(w))
        W_m = float(mal_w) if mal_w else W_h / max(len(honest), 1)
        H = torch.stack([u * float(wi) for u, wi in zip(honest, w)]).sum(0)
        mu_h = H / W_h
        target = theta - scale * (mu_h - theta)
        return (target * (W_h + W_m) - H) / W_m
    if attack in ("label_flip", "backdoor"):
        return mu                            # realized in the data, not the update
    raise ValueError(f"unknown attack {attack!r}")


def invert_output(model, flat: torch.Tensor) -> torch.Tensor:
    """Return `flat` with the rows of the model's final linear layer rolled by one.

    At n_class=2 this swaps the two logits, so the returned model predicts the other
    class on every input the original model classifies; on a wider label space it is
    the cyclic shift poison_labels uses. `model` is scratch space: it is overwritten."""
    from .models import get_flat, set_flat
    set_flat(model, flat)
    last = [m for m in model.modules() if isinstance(m, torch.nn.Linear)][-1]
    with torch.no_grad():
        last.weight.copy_(torch.roll(last.weight, 1, 0))
        last.bias.copy_(torch.roll(last.bias, 1, 0))
    return get_flat(model).clone()


def replace_to_target(target: torch.Tensor, honest: list[torch.Tensor],
                      honest_w: list[float], mal_w: float) -> torch.Tensor:
    """replace_invert (review r4, A-W1): the update whose FedAvg aggregate IS `target`.

    Model replacement: the malicious client scales its contribution by the inverse of
    its aggregation weight, so FedAvg's dilution by W_m/(W_h+W_m) no longer applies
    and one client decides the member whatever its data volume. Same solve as the
    `adaptive` attack; only the target differs. Every malicious client in a member
    sends this same vector, so the aggregate is exact for any m >= 1."""
    W_h = float(sum(honest_w)) if honest else 0.0
    H = (torch.stack([u * float(wi) for u, wi in zip(honest, honest_w)]).sum(0)
         if honest else torch.zeros_like(target))
    return (target * (W_h + float(mal_w)) - H) / float(mal_w)


def poison_labels(y: torch.Tensor, n_class: int = 2) -> torch.Tensor:
    """label_flip: flip labels on the malicious client's local data.

    A cyclic shift by one class. At n_class=2 this is exactly 1-y, so the binary
    attack is unchanged; on a wider label space it sends every row to a wrong class,
    which is what "1-y" was doing and what a flip is supposed to mean. Writing the
    binary form on a multi-class label space instead produces negative targets and
    the loss raises IndexError."""
    return (y + 1) % int(n_class)


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


def poison_labels_vote_shaping(model, X: torch.Tensor, y: torch.Tensor,
                               frac: float = 0.5) -> torch.Tensor:
    """vote_shape: flip labels only where the current model is least confident.

    Review W8/E6. Every attack in the evaluated set moves the parameter vector:
    they compete on displacement, and Appendix~B.8 measures that they saturate at
    ALIE. But a plurality certificate is bound by ensemble *agreement*, not by
    displacement -- a certified point cannot be flipped by construction, so the
    reachable damage is in the uncertified region and in the certified-but-wrong
    fraction. This attack targets that axis directly: it spends the malicious
    client's whole label budget on the samples whose margin under the current
    global model is smallest, which are exactly the ones where a member's vote is
    cheapest to move and where the ensemble margin is thinnest.

    Returns y with the lowest-margin `frac` of entries flipped. frac=1.0 degenerates
    to the existing label_flip, which is the right sanity check: vote shaping should
    do at least as much damage per flipped label, or the targeting is not working.
    """
    if frac >= 1.0:
        return 1 - y
    n = int(y.numel())
    k = max(1, int(round(frac * n)))
    was = model.training
    model.eval()
    try:
        with torch.no_grad():
            logits = model(X)
            # margin between the two logits; small margin == cheapest vote to move
            margin = (logits[:, 1] - logits[:, 0]).abs()
    finally:
        if was:
            model.train()
    idx = torch.argsort(margin)[:k]
    out = y.clone()
    n_class = int(model(X[:1]).shape[1]) if len(X) else 2
    out[idx] = (out[idx] + 1) % n_class
    return out


def poison_labels_random(y: torch.Tensor, frac: float = 0.5,
                         gen: torch.Generator | None = None,
                         n_class: int = 2) -> torch.Tensor:
    """rand_flip: flip a RANDOM `frac` of local labels -- the budget-matched control.

    vote_shape spends its label budget on the lowest-margin samples. Comparing it to
    label_flip would compare 50% of labels against 100% and say nothing about
    targeting, so this control flips the same NUMBER of labels uniformly at random.
    Any advantage vote_shape shows over this control is attributable to where the
    flips land, not how many there are.
    """
    n = int(y.numel())
    k = max(1, int(round(frac * n)))
    perm = torch.randperm(n, generator=gen, device=y.device)[:k]
    out = y.clone()
    out[perm] = (out[perm] + 1) % int(n_class)   # 1-y when n_class == 2
    return out
