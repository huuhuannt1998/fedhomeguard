"""ALGORITHM 1 -- FLRun, the deterministic execution primitive everything calls.

Determinism given (partition_seed, train_seed) is a REQUIREMENT, not a nicety:
CertifySubsample calls FLRun K times and the soundness argument assumes members
differ only through their client subset.
"""
from __future__ import annotations
import numpy as np, torch, torch.nn as nn

from . import attacks as A, defenses as D
from .models import build_model, get_flat, set_flat


def local_train(model, Xc, yc, epochs, lr, momentum, bs, gen):
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=momentum)
    lossf = nn.CrossEntropyLoss()
    n = len(yc)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=gen, device=yc.device)
        for s in range(0, n, bs):
            idx = perm[s:s + bs]
            if len(idx) < 2:
                continue
            opt.zero_grad()
            lossf(model(Xc[idx]), yc[idx]).backward()
            opt.step()
    return get_flat(model)


# Attacked accuracy is read from a window of rounds, not the final round. Under
# label-flip the global model oscillates with a period of about two rounds --
# measured swings from 0.27 to 0.98 between adjacent rounds -- so a final-round
# readout samples an arbitrary phase, and two faithful implementations of the same
# experiment differed by 0.16 for that reason alone. Eight rounds is the smallest
# window that always straddles a trough (mean sensitivity to the stopping round
# 0.0010, against 0.0234 for the final round and 0.0231 for a five-round window),
# and at T=15 every round in it is past convergence, which is reached by round 4.
EA_WINDOW = 8


def fl_run(cfg, client_ids, Xtr, ytr, parts, *, malicious_ids=(), attack=None,
           server_root=None, backdoor_feat=None, min_rows: int = 16, verbose=False,
           snapshot_last: int = 0):
    """Run federated training over `client_ids`. Returns the trained global model, or
    (model, [flat parameters for each of the last `snapshot_last` rounds]) when
    snapshot_last > 0, so a caller can read a statistic over a window of rounds."""
    dev = Xtr.device
    d = Xtr.shape[1]
    gen = torch.Generator(device=dev); gen.manual_seed(cfg.fl.seed)
    agen = torch.Generator(device=dev); agen.manual_seed(cfg.adversary.seed)

    if attack:
        A.check_capability(attack, cfg.adversary.F3_knowledge)
    D.check_observability(cfg.defense.name, cfg.defense.observability)
    agg = D.get(cfg.defense.name)

    # build_model draws initial weights from the GLOBAL torch RNG, so before this
    # fix two identical calls to fl_run started from different weights and the run
    # was not reproducible -- which the artifact claims it is. Seed the global RNG
    # from the run's own seed and restore the caller's state on the way out, so the
    # determinism is local to fl_run and nothing outside it sees a changed stream.
    _rng_state = torch.random.get_rng_state()
    torch.manual_seed(cfg.fl.seed)
    try:
        g = build_model(cfg, d).to(dev)
        local = build_model(cfg, d).to(dev)
    finally:
        torch.random.set_rng_state(_rng_state)
    theta = get_flat(g).clone()
    mal = set(malicious_ids)
    active = [i for i in client_ids if len(parts[i]) >= min_rows]
    if not active:
        raise ValueError("no client in this subset has enough rows; lower min_rows or N")

    snaps: list = []
    for t in range(cfg.fl.rounds_T):
        honest_u, updates, weights = [], {}, {}
        for i in active:                                   # honest clients first
            if i in mal:
                continue
            idx = parts[i]
            set_flat(local, theta)
            u = local_train(local, Xtr[idx], ytr[idx], cfg.fl.local_epochs_E,
                            cfg.fl.lr, cfg.fl.momentum, cfg.fl.batch_size, gen)
            updates[i] = u; weights[i] = len(idx); honest_u.append(u)

        for i in active:                                   # then the adversary
            if i not in mal:
                continue
            idx = parts[i]
            if attack == "label_flip":
                set_flat(local, theta)
                u = local_train(local, Xtr[idx], A.poison_labels(ytr[idx]),
                                cfg.fl.local_epochs_E, cfg.fl.lr, cfg.fl.momentum,
                                cfg.fl.batch_size, gen)
            elif attack == "backdoor":
                if backdoor_feat is None:
                    raise ValueError("backdoor attack requires backdoor_feat indices")
                Xp, yp, _ = A.apply_backdoor(Xtr[idx], ytr[idx], backdoor_feat, gen=agen)
                set_flat(local, theta)
                u = local_train(local, Xp, yp, cfg.fl.local_epochs_E, cfg.fl.lr,
                                cfg.fl.momentum, cfg.fl.batch_size, gen)
            else:
                u = A.malicious_update(attack, theta, honest_u, cfg.adversary.scale, agen)
            u = A.project(u, cfg.adversary.F2_update_space, cfg.adversary.F2_rho)
            updates[i] = u; weights[i] = len(idx)

        kw = dict(weights=weights, n_mal=len(mal), trim_frac=cfg.defense.trim_frac or 0.2,
                  clip_norm=cfg.defense.clip_norm or 5.0, malicious_ids=tuple(mal),
                  server_update=server_root)
        theta = agg(updates, **kw)
        if snapshot_last and t >= cfg.fl.rounds_T - snapshot_last:
            snaps.append(theta.clone())
        if verbose:
            print(f"    round {t+1}/{cfg.fl.rounds_T}")

    set_flat(g, theta)
    g.eval()
    return (g, snaps) if snapshot_last else g


@torch.no_grad()
def predict(model, X, bs: int = 65536) -> np.ndarray:
    out = []
    for s in range(0, len(X), bs):
        out.append(model(X[s:s + bs]).argmax(1).cpu().numpy())
    return np.concatenate(out) if out else np.array([], dtype=int)


@torch.no_grad()
def accuracy(model, X, y_np: np.ndarray) -> float:
    return float((predict(model, X) == y_np).mean())


def server_root_update(cfg, Xtr, ytr, root_idx):
    """L2 only: FLTrust's clean server root update. Fails loudly if not authorized."""
    if cfg.defense.observability != "L2":
        raise ValueError("server root update is an L2 capability; declare it explicitly")
    dev = Xtr.device
    gen = torch.Generator(device=dev); gen.manual_seed(cfg.fl.seed)
    m = build_model(cfg, Xtr.shape[1]).to(dev)
    return local_train(m, Xtr[root_idx], ytr[root_idx], cfg.fl.local_epochs_E,
                       cfg.fl.lr, cfg.fl.momentum, cfg.fl.batch_size, gen)
