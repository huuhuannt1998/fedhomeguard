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


def fl_run(cfg, client_ids, Xtr, ytr, parts, *, malicious_ids=(), attack=None,
           server_root=None, backdoor_feat=None, min_rows: int = 16, verbose=False):
    """Run federated training over `client_ids`. Returns the trained global model."""
    dev = Xtr.device
    d = Xtr.shape[1]
    gen = torch.Generator(device=dev); gen.manual_seed(cfg.fl.seed)
    agen = torch.Generator(device=dev); agen.manual_seed(cfg.adversary.seed)

    if attack:
        A.check_capability(attack, cfg.adversary.F3_knowledge)
    D.check_observability(cfg.defense.name, cfg.defense.observability)
    agg = D.get(cfg.defense.name)

    g = build_model(cfg, d).to(dev)
    theta = get_flat(g).clone()
    local = build_model(cfg, d).to(dev)
    mal = set(malicious_ids)
    active = [i for i in client_ids if len(parts[i]) >= min_rows]
    if not active:
        raise ValueError("no client in this subset has enough rows; lower min_rows or N")

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
        if verbose:
            print(f"    round {t+1}/{cfg.fl.rounds_T}")

    set_flat(g, theta)
    g.eval()
    return g


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
