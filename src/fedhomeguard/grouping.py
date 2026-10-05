"""Diversity-maximising client grouping at k=2 (review E3 / F11).

WHY THIS EXISTS
---------------
The paper's finding is that small-k certification fails under device-derived
partitions because a member trained on one household sees essentially one class and
cannot cast an informative vote, and that the lever a deployer has is the device
inventory: households owning more device types produce members that see both classes.
CARVY-FL (arXiv 2608.28992) proposes the other lever for the same failure -- leave the
inventory alone and choose the GROUPS so that each member spans several client types.
This module builds that arm.

THE COMPARISON HAS TO BE ABOUT MARGINS, NOT GEOMETRY
----------------------------------------------------
Proposition 1's threshold is 2 c_max(m)/K, and c_max is a pure property of which
subsets were realised. Compare a diversity-chosen set of pairs against an arbitrary
one and you change the vote margins AND the certificate threshold at the same time,
and cannot say which moved the result.

Both arms here are therefore 2-REGULAR: K = N pairs in which every household appears
in exactly two, so the degree sequence -- the only thing c_max reads -- is identical
by construction. A 2-regular graph on N nodes with N edges is a disjoint union of
cycles, and the simplest such family is the single Hamiltonian cycle, so each arm is
a cyclic ordering of the N households:

    random arm        a uniformly random cyclic order
    anticlustered arm a cyclic order chosen to maximise the device-type span of the
                      adjacent pairs

Same k, same K, same degrees, different pairing. What differs between the arms is
which households are put together, which is exactly the lever under test.

c_max is still computed exactly on the realised pairs by exactcert, never assumed
from the degree sequence: two 2-regular graphs can differ in c_max at a given m, and
the certificate has to be the one the realised ensemble earns. The measured c_max of
both arms is reported alongside the result so a reader can confirm the geometry did
not move.
"""
from __future__ import annotations
import numpy as np


def household_device_sets(parts, device: np.ndarray) -> dict[int, set]:
    """Device types each household holds training rows for."""
    return {i: set(np.unique(device[np.asarray(idx)]).tolist()) if len(idx) else set()
            for i, idx in parts.items()}


def _span(a: set, b: set) -> int:
    """Device types the pair spans. The quantity E3 asks to maximise."""
    return len(a | b)


def _score(order, dsets) -> tuple[int, int]:
    """(total span, total disjointness) of the cycle's N adjacent pairs.

    Disjointness breaks ties between orders of equal span: two households holding
    {0,1} and {1,2} span three types and share one; {0,1} and {2,3} span four and
    share none. The second is the more anticlustered pairing at equal span.
    """
    n = len(order)
    tot = sum(_span(dsets[order[i]], dsets[order[(i + 1) % n]]) for i in range(n))
    dis = sum(len(dsets[order[i]] ^ dsets[order[(i + 1) % n]]) for i in range(n))
    return tot, dis


def cycle_pairs(order) -> list[tuple[int, int]]:
    n = len(order)
    return [tuple(sorted((int(order[i]), int(order[(i + 1) % n])))) for i in range(n)]


def random_cycle(N: int, seed: int) -> list[int]:
    rng = np.random.default_rng(seed)
    o = list(range(N))
    rng.shuffle(o)
    return o


def anticluster_cycle(parts, device: np.ndarray, N: int, seed: int,
                      restarts: int = 12, sweeps: int = 60) -> list[int]:
    """Cyclic order maximising the device-type span of adjacent pairs.

    Maximising over cyclic orders is a travelling-salesman problem with the sign
    flipped, so this is a heuristic and is labelled as one: multi-start greedy
    followed by 2-opt to a local optimum. It is not claimed to be the best pairing,
    only a markedly more diverse one than chance, and the realised pairs it returns
    are certified exactly whatever their quality -- a worse pairing yields a worse
    vote margin, never an unsound certificate.
    """
    dsets = household_device_sets(parts, device)
    best, best_sc = None, (-1, -1)
    for r in range(restarts):
        rng = np.random.default_rng(seed * 1000 + r)
        # greedy: from a random start, repeatedly append the unused household that
        # spans the most new device types against the current tail
        start = int(rng.integers(0, N))
        order = [start]
        left = set(range(N)) - {start}
        while left:
            tail = order[-1]
            cand = sorted(left, key=lambda j: (-_span(dsets[tail], dsets[j]),
                                               -len(dsets[tail] ^ dsets[j]), j))
            # sample among the equally best to give the restarts something to explore
            top = [j for j in cand
                   if (_span(dsets[tail], dsets[j]), len(dsets[tail] ^ dsets[j]))
                   == (_span(dsets[tail], dsets[cand[0]]),
                       len(dsets[tail] ^ dsets[cand[0]]))]
            nxt = int(top[int(rng.integers(0, len(top)))])
            order.append(nxt)
            left.discard(nxt)
        # 2-opt: reversing a segment changes exactly two adjacencies
        sc = _score(order, dsets)
        for _ in range(sweeps):
            improved = False
            for a in range(N):
                for b in range(a + 2, N):
                    cand = order[:a + 1] + order[a + 1:b + 1][::-1] + order[b + 1:]
                    csc = _score(cand, dsets)
                    if csc > sc:
                        order, sc, improved = cand, csc, True
            if not improved:
                break
        if sc > best_sc:
            best, best_sc = order, sc
    return best


def pairing_report(pairs, parts, device: np.ndarray) -> dict:
    """Descriptive statistics of a realised pairing, for the results table."""
    dsets = household_device_sets(parts, device)
    spans = [_span(dsets[i], dsets[j]) for i, j in pairs]
    deg = {}
    for i, j in pairs:
        deg[i] = deg.get(i, 0) + 1
        deg[j] = deg.get(j, 0) + 1
    return dict(K=len(pairs),
                mean_span=round(float(np.mean(spans)), 4),
                frac_span_ge2=round(float(np.mean([s >= 2 for s in spans])), 4),
                min_span=int(min(spans)), max_span=int(max(spans)),
                degree_min=int(min(deg.values())), degree_max=int(max(deg.values())))


def build_pairs(mode: str, parts, device: np.ndarray, N: int, seed: int):
    """Realised k=2 ensemble under the named pairing rule."""
    if mode == "random":
        order = random_cycle(N, seed)
    elif mode == "anticluster":
        order = anticluster_cycle(parts, device, N, seed)
    else:
        raise ValueError(f"unknown pairing mode {mode!r}")
    return cycle_pairs(order)
