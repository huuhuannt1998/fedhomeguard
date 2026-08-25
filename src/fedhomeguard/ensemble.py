"""Same-predictor ensemble machinery (review E2/E3/E4).

The old pipeline compared the certified ENSEMBLE against the best single-model
robust-aggregation DEFENCE. Those are different predictors, so their difference
could never have been certificate slack. This module builds the attacked version of
the *same* ensemble, so that

    G_cert(k, beta) = EA_ensemble(k, beta) - CA_ensemble(k, beta)

is a statement about one predictor.

The only member models that change when the adversary appears are those whose
client subset intersects B; a member trained on a subset disjoint from B is
bit-identical to its clean counterpart because FLRun is deterministic given
(partition_seed, train_seed). We exploit that, and cache on
(subset, subset-intersect-B, attack), which is what makes the full grid affordable.
"""
from __future__ import annotations
import numpy as np

from . import fl as FL


class MemberCache:
    """Maps (subset, malicious-within-subset, attack) -> test-set predictions."""

    def __init__(self):
        self.store: dict[tuple, np.ndarray] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(S, mal_in_S, attack) -> tuple:
        return (tuple(sorted(int(i) for i in S)),
                tuple(sorted(int(i) for i in mal_in_S)),
                attack if mal_in_S else None)

    def get_or_train(self, cfg, t, S, mal_in_S, attack):
        """Test-set predictions of one member, or None if its subset is untrainable.

        Under strong Dirichlet concentration some clients hold fewer rows than the
        trainable minimum, and a subset made entirely of those has no member to
        train. Returning None lets the caller drop that member rather than abort the
        sweep. Dropping is sound: which subsets are trainable depends on the
        partition alone, never on B, so the adversary cannot influence the surviving
        ensemble, and c_max is then computed over exactly the members that remain.
        """
        kk = self.key(S, mal_in_S, attack)
        if kk in self.store:
            self.hits += 1
            return self.store[kk]
        self.misses += 1
        try:
            g = FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"],
                          malicious_ids=tuple(mal_in_S),
                          attack=None if not mal_in_S else attack)
        except ValueError as e:
            if "enough rows" not in str(e):
                raise
            self.store[kk] = None
            return None
        pred = FL.predict(g, t["Xte"])
        self.store[kk] = pred
        return pred

    def stats(self) -> dict:
        n = self.hits + self.misses
        return dict(trainings=self.misses, cache_hits=self.hits,
                    hit_rate=round(self.hits / n, 4) if n else 0.0)


def votes_from_preds(preds: list[np.ndarray], n_test: int, n_class: int = 2) -> np.ndarray:
    v = np.zeros((n_test, n_class), np.int32)
    ar = np.arange(n_test)
    for p in preds:
        v[ar, p] += 1
    return v


def ensemble_votes(cfg, t, subsets, B=(), attack=None, cache: MemberCache | None = None,
                   progress: int = 0):
    """Votes of the K-member ensemble when the clients in B run `attack`.

    B=() reproduces the clean ensemble exactly, which is the certificate's predictor.
    """
    cache = cache if cache is not None else MemberCache()
    Bs = set(int(i) for i in B)
    n_test = len(t["yte_np"])
    preds, kept, n_touched = [], [], 0
    for j, S in enumerate(subsets):
        inter = sorted(Bs.intersection(int(i) for i in S))
        pred = cache.get_or_train(cfg, t, S, inter, attack)
        if pred is None:                      # untrainable subset; drop the member
            continue
        n_touched += bool(inter)
        preds.append(pred); kept.append(S)
        if progress and (j + 1) % progress == 0:
            print(f"      member {j+1}/{len(subsets)}", flush=True)
    return votes_from_preds(preds, n_test), n_touched, kept


def attacked_ensemble_accuracy(cfg, t, subsets, B, attacks, cache=None) -> dict:
    """EA of the SAME ensemble under each attack, and the worst case over them."""
    cache = cache if cache is not None else MemberCache()
    y = t["yte_np"]
    per = {}
    for a in attacks:
        v, touched, _ = ensemble_votes(cfg, t, subsets, B, a, cache)
        top = v.argmax(1)
        per[a] = dict(EA=round(float((top == y).mean()), 6),
                      members_touched=touched)
    worst = min(per, key=lambda a: per[a]["EA"]) if per else None
    return dict(per_attack=per, worst_attack=worst,
                EA_ensemble=per[worst]["EA"] if worst else None,
                members_touched=per[worst]["members_touched"] if worst else 0)
