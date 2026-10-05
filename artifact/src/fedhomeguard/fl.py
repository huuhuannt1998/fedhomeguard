"""ALGORITHM 1 -- FLRun, the deterministic execution primitive everything calls.

Determinism given (partition_seed, train_seed) is a REQUIREMENT, not a nicety:
CertifySubsample calls FLRun K times and the soundness argument assumes members
differ only through their client subset.
"""
from __future__ import annotations
import numpy as np, torch, torch.nn as nn

from . import attacks as A, defenses as D
from .models import build_model, get_flat, set_flat


def local_train(model, Xc, yc, epochs, lr, momentum, bs, gen, class_balanced=False):
    """One client's local update.

    class_balanced weights the loss by inverse class frequency ON THIS CLIENT. Under
    device-derived partitioning a household can hold 97% one class, and unweighted
    cross-entropy then drives its member to a near-constant predictor -- which is a
    training choice, not a property of the data. Reviewers correctly asked whether the
    measured competence collapse survives the obvious fix; this flag is how we answer.
    """
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=momentum)
    if class_balanced:
        cnt = torch.bincount(yc, minlength=2).float()
        w = torch.where(cnt > 0, cnt.sum() / (2.0 * cnt.clamp(min=1)),
                        torch.ones_like(cnt))
        lossf = nn.CrossEntropyLoss(weight=w.to(Xc.device))
    else:
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
                            cfg.fl.lr, cfg.fl.momentum, cfg.fl.batch_size, gen,
                            class_balanced=getattr(cfg.fl, "class_balanced", False))
            updates[i] = u; weights[i] = len(idx); honest_u.append(u)

        ri_target = None                                   # replace_invert, per round
        for i in active:                                   # then the adversary
            if i not in mal:
                continue
            idx = parts[i]
            if attack == "replace_invert":
                # Review r4 (A-W1): model replacement toward an inverted member. The
                # target is this round's clean aggregate with its output inverted: the
                # weighted mean of the honest updates, or, in a member with no honest
                # client, the adversary's own honest training on its own data. It is
                # computed once per round so every malicious client sends the same
                # vector and the aggregate equals the target exactly.
                if ri_target is None:
                    if honest_u:
                        hw = [weights[j] for j in active if j not in mal and j in weights]
                        cons = (torch.stack([u_ * float(w_) for u_, w_ in zip(honest_u, hw)])
                                .sum(0) / float(sum(hw)))
                    else:
                        set_flat(local, theta)
                        cons = local_train(local, Xtr[idx], ytr[idx], cfg.fl.local_epochs_E,
                                           cfg.fl.lr, cfg.fl.momentum, cfg.fl.batch_size, gen)
                    ri_target = A.invert_output(local, cons)
                honest_w = [weights[j] for j in active if j not in mal and j in weights]
                mal_w = float(sum(len(parts[j]) for j in active if j in mal))
                u = A.replace_to_target(ri_target, honest_u, honest_w, mal_w)
            elif attack == "label_flip":
                set_flat(local, theta)
                u = local_train(local, Xtr[idx],
                                A.poison_labels(ytr[idx],
                                                getattr(cfg.model, "n_class", 2) or 2),
                                cfg.fl.local_epochs_E, cfg.fl.lr, cfg.fl.momentum,
                                cfg.fl.batch_size, gen,
                                class_balanced=getattr(cfg.fl, "class_balanced", False))
            elif attack == "rand_flip":
                # budget-matched control for vote_shape: same number of flipped
                # labels, placed at random instead of at the margin.
                set_flat(local, theta)
                yv = A.poison_labels_random(
                    ytr[idx], frac=float(getattr(cfg.adversary, "vote_shape_frac", 0.5)),
                    gen=agen, n_class=getattr(cfg.model, "n_class", 2) or 2)
                u = local_train(local, Xtr[idx], yv,
                                cfg.fl.local_epochs_E, cfg.fl.lr, cfg.fl.momentum,
                                cfg.fl.batch_size, gen,
                                class_balanced=getattr(cfg.fl, "class_balanced", False))
            elif attack == "vote_shape":
                # Review W8/E6: spend the label budget on the lowest-margin samples
                # under the CURRENT global model, so the flips land where a member's
                # vote is cheapest to move. Targets ensemble agreement rather than
                # parameter displacement, which is the axis the certificate binds.
                set_flat(local, theta)
                yv = A.poison_labels_vote_shaping(
                    local, Xtr[idx], ytr[idx],
                    frac=float(getattr(cfg.adversary, "vote_shape_frac", 0.5)))
                u = local_train(local, Xtr[idx], yv,
                                cfg.fl.local_epochs_E, cfg.fl.lr, cfg.fl.momentum,
                                cfg.fl.batch_size, gen,
                                class_balanced=getattr(cfg.fl, "class_balanced", False))
            elif attack == "backdoor":
                if backdoor_feat is None:
                    raise ValueError("backdoor attack requires backdoor_feat indices")
                Xp, yp, _ = A.apply_backdoor(Xtr[idx], ytr[idx], backdoor_feat, gen=agen)
                set_flat(local, theta)
                u = local_train(local, Xp, yp, cfg.fl.local_epochs_E, cfg.fl.lr,
                                cfg.fl.momentum, cfg.fl.batch_size, gen)
            else:
                # honest_w is built in the same order honest_u was appended, so the
                # adaptive attack can reconstruct the exact FedAvg aggregate.
                honest_w = [weights[j] for j in active if j not in mal and j in weights]
                mal_w = float(sum(len(parts[j]) for j in active if j in mal))
                u = A.malicious_update(attack, theta, honest_u, cfg.adversary.scale, agen,
                                       honest_w=honest_w, mal_w=mal_w,
                                       pop_std=bool(getattr(cfg.adversary, "pop_std", False)),
                                       # the r6 correction is the default;
                                       # legacy_nan_std reproduces the frozen results
                                       single_honest_zero_sd=not bool(getattr(
                                           cfg.adversary, "legacy_nan_std", False)))
            u = A.project(u, cfg.adversary.F2_update_space, cfg.adversary.F2_rho)
            updates[i] = u; weights[i] = len(idx)

        kw = dict(weights=weights, n_mal=len(mal), trim_frac=cfg.defense.trim_frac or 0.2,
                  clip_norm=cfg.defense.clip_norm or 5.0, malicious_ids=tuple(mal),
                  server_update=server_root,
                  # CRFL (review W6/E3): per-round noise on the aggregate. Drawn from
                  # the run's own generator so a run stays reproducible.
                  noise_sigma=getattr(cfg.defense, "noise_sigma", 0.0), gen=gen)
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
