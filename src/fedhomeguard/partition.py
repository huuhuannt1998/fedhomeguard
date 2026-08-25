"""Client partitions and the skew instrument.

D1: the partition IS the experiment. `device_derived` is the substrate; `dirichlet`
exists ONLY as the matched-skew control (Algorithm 4) that tests whether device
STRUCTURE, or merely skew MAGNITUDE, drives the effect. It is never a fallback.
"""
from __future__ import annotations
import numpy as np

Partition = dict[int, np.ndarray]


# ------------------------------------------------------------------ skew instrument
def _hist(idx: np.ndarray, y: np.ndarray, device: np.ndarray, n_dev: int) -> np.ndarray:
    if len(idx) == 0:
        return np.ones(n_dev * 2) / (n_dev * 2)
    key = device[idx].astype(int) * 2 + y[idx].astype(int)
    h = np.bincount(key, minlength=n_dev * 2).astype(float)
    return h / h.sum()


def _jsd(p: np.ndarray, q: np.ndarray) -> float:
    m = 0.5 * (p + q)
    def kl(u, v):
        msk = u > 0
        return float(np.sum(u[msk] * np.log2(u[msk] / np.maximum(v[msk], 1e-12))))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def skew_js(parts: Partition, y: np.ndarray, device: np.ndarray) -> float:
    """S_JS: mean pairwise Jensen-Shannon divergence over (device x label) histograms.

    JSD (not KL) because smart-home clients routinely have disjoint support.

    EMPTY CLIENTS ARE EXCLUDED. A client holding no data is not a participant, and
    counting it would inject an artificial uniform histogram that drags the mean
    divergence DOWN -- which made S_JS non-monotone in the Dirichlet alpha (measured:
    alpha=1e-3 scored *lower* than alpha=1e-1 purely because most clients went empty)
    and would have broken the Algorithm-4 search. Use `count_empty` to reject such
    partitions rather than silently scoring them.
    """
    n_dev = int(device.max()) + 1
    live = [i for i in sorted(parts) if len(parts[i]) > 0]
    H = [_hist(np.asarray(parts[i]), y, device, n_dev) for i in live]
    N = len(H)
    if N < 2:
        return 0.0
    tot = sum(_jsd(H[a], H[b]) for a in range(N) for b in range(a + 1, N))
    return float(tot / (N * (N - 1) / 2))


def count_empty(parts: Partition, min_rows: int = 1) -> int:
    return int(sum(len(parts[i]) < min_rows for i in parts))


def skew_device(parts: Partition, device: np.ndarray) -> float:
    """S_dev = 1 - mean pairwise Jaccard similarity of client device sets."""
    sets = [set(np.unique(device[np.asarray(parts[i])]).tolist()) if len(parts[i]) else set()
            for i in sorted(parts)]
    N = len(sets); sims = []
    for a in range(N):
        for b in range(a + 1, N):
            u = sets[a] | sets[b]
            sims.append(len(sets[a] & sets[b]) / len(u) if u else 1.0)
    return float(1.0 - np.mean(sims)) if sims else 0.0


def skew_label(parts: Partition, y: np.ndarray) -> float:
    """S_lab = mean pairwise JS divergence over client LABEL marginals alone.

    S_JS is a joint device-by-label divergence, so it stays high whenever clients
    hold different devices even if every client sees the same label mix. S_lab
    isolates the label component, which is what the N-BaIoT natural experiment
    showed is the part that actually bears on certifiability."""
    ps = []
    for i in sorted(parts):
        ix = np.asarray(parts[i])
        if len(ix) == 0:
            ps.append(np.array([0.5, 0.5])); continue
        p1 = float(np.mean(y[ix]))
        ps.append(np.array([1.0 - p1, p1]))
    N = len(ps); tot = 0.0
    for a in range(N):
        for b in range(a + 1, N):
            tot += _jsd(ps[a], ps[b])
    return float(tot / (N * (N - 1) / 2)) if N > 1 else 0.0


def min_minority_share(parts: Partition, y: np.ndarray) -> float:
    """Smallest minority-class share held by any client, min_j min(p_j, 1-p_j).

    A client at 0 contributes an ensemble member that has never seen one of the
    classes; such a member cannot vote informatively however large it is."""
    out = []
    for i in sorted(parts):
        ix = np.asarray(parts[i])
        if len(ix) == 0:
            return 0.0
        p1 = float(np.mean(y[ix])); out.append(min(p1, 1.0 - p1))
    return float(min(out)) if out else 0.0


def frac_degenerate(parts: Partition, y: np.ndarray, thresh: float = 0.95) -> float:
    """Fraction of clients that are more than `thresh` one class -- the label
    degeneracy the certified predictor actually fails on."""
    n = 0; tot = 0
    for i in sorted(parts):
        ix = np.asarray(parts[i]); tot += 1
        if len(ix) == 0:
            n += 1; continue
        p1 = float(np.mean(y[ix]))
        if max(p1, 1.0 - p1) > thresh:
            n += 1
    return float(n / tot) if tot else 0.0


def min_class_support(parts: Partition, y: np.ndarray, q: float = 0.05) -> float:
    """Smallest fraction of clients able to speak for either class.

    Derived from the voting rule rather than from a divergence. At k=1 a member is
    one client, and a client whose training data is all one class votes that class
    on every input: it is correct on that class and wrong on the other, whatever
    its size. The plurality margin on class c therefore tracks the FRACTION of
    clients carrying usable class-c data, and the binding constraint is the worse
    of the two classes.

    This is deliberately a fraction, not a minimum. min_minority_share is a min
    over clients, so one degenerate client pins it near zero and it cannot
    discriminate between partitions that all contain at least one -- which is
    every device-derived draw on IoT-23, and is why that instrument is flat
    exactly where the paper most needs a signal."""
    n = len(parts)
    if n == 0:
        return 0.0
    have = [0, 0]
    for i in sorted(parts):
        ix = np.asarray(parts[i])
        if len(ix) == 0:
            continue
        p1 = float(np.mean(y[ix]))
        if p1 >= q:
            have[1] += 1
        if 1.0 - p1 >= q:
            have[0] += 1
    return float(min(have) / n)


def min_size_share(parts: Partition) -> float:
    """Smallest client's share of the data -- the volume-skew instrument, which is
    invisible to S_JS because every client draws from the same pool."""
    sizes = [len(parts[i]) for i in sorted(parts)]
    tot = sum(sizes)
    return float(min(sizes) / tot) if tot else 0.0


def measure_skew(parts: Partition, y: np.ndarray, device: np.ndarray) -> dict:
    sizes = [len(parts[i]) for i in sorted(parts)]
    return dict(S_JS=round(skew_js(parts, y, device), 6),
                S_dev=round(skew_device(parts, device), 6),
                S_lab=round(skew_label(parts, y), 6),
                min_minority=round(min_minority_share(parts, y), 6),
                frac_degenerate=round(frac_degenerate(parts, y), 6),
                min_class_support=round(min_class_support(parts, y), 6),
                min_size_share=round(min_size_share(parts), 6),
                size_min=int(min(sizes)), size_med=int(np.median(sizes)),
                size_max=int(max(sizes)), n_empty=int(sum(s == 0 for s in sizes)))


# ---------------------------------------------------------------------- constructors
def iid_partition(n: int, N: int, seed: int = 0) -> Partition:
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    return {i: np.sort(perm[i::N]) for i in range(N)}


def device_derived_partition(device: np.ndarray, N: int, seed: int = 0,
                             devices_per_household: tuple[int, int] = (1, 3),
                             drop_device: int | None = None) -> Partition:
    """Households own 1-3 real device types; each device's rows are split among owners."""
    rng = np.random.default_rng(seed)
    devs = [d for d in np.unique(device) if d != drop_device]
    owners: dict[int, list[int]] = {int(d): [] for d in devs}
    lo, hi = devices_per_household
    for i in range(N):
        ndev = int(rng.integers(lo, hi + 1))
        own = rng.choice(devs, size=min(ndev, len(devs)), replace=False)
        for d in own:
            owners[int(d)].append(i)
    for d in devs:                       # no orphaned device type
        if not owners[int(d)]:
            owners[int(d)].append(int(rng.integers(0, N)))
    buckets: dict[int, list[np.ndarray]] = {i: [] for i in range(N)}
    for d in devs:
        idx = np.where(device == d)[0].copy()
        rng.shuffle(idx)
        for chunk, i in zip(np.array_split(idx, len(owners[int(d)])), owners[int(d)]):
            buckets[i].append(chunk)
    return {i: (np.sort(np.concatenate(v)) if v else np.array([], dtype=int))
            for i, v in buckets.items()}


def volume_skew_partition(y: np.ndarray, N: int, alpha: float, seed: int = 0) -> Partition:
    """Data-VOLUME skew (review sec 12, Experiment C).

    Every client draws from the same pool uniformly at random, so device and label
    composition are preserved in expectation; only how MUCH each client holds varies,
    by a Dirichlet draw over client sizes. This isolates the third component of
    heterogeneity from the device-support and label components.
    """
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    w = rng.dirichlet(np.full(N, alpha))
    cuts = (np.cumsum(w) * len(idx)).astype(int)[:-1]
    parts = np.split(idx, cuts)
    return {i: np.sort(parts[i]) for i in range(N)}


def dirichlet_partition(y: np.ndarray, N: int, alpha: float, seed: int = 0) -> Partition:
    """Standard label-Dirichlet split. CONTROL ONLY (Algorithm 4)."""
    rng = np.random.default_rng(seed)
    buckets: dict[int, list[np.ndarray]] = {i: [] for i in range(N)}
    for c in np.unique(y):
        idx = np.where(y == c)[0].copy()
        rng.shuffle(idx)
        p = rng.dirichlet(np.repeat(alpha, N))
        cuts = (np.cumsum(p)[:-1] * len(idx)).astype(int)
        for i, chunk in enumerate(np.split(idx, cuts)):
            buckets[i].append(chunk)
    return {i: (np.sort(np.concatenate(v)) if v else np.array([], dtype=int))
            for i, v in buckets.items()}


def dirichlet_device_partition(device: np.ndarray, N: int, alpha: float,
                               seed: int = 0) -> Partition:
    """Dirichlet over the DEVICE->client allocation. The correct Algorithm-4 control.

    Label-Dirichlet skews only the label marginal: every client still sees every
    device, so it reaches high (device x label) S_JS only by concentrating LABELS,
    which is a different kind of skew from the one device-derived partitions create.
    Allocating each device's rows by Dirichlet moves the device dimension directly,
    matching skew MAGNITUDE while carrying none of the household co-ownership
    STRUCTURE -- exactly the contrast the necessity test needs to isolate.
    """
    rng = np.random.default_rng(seed)
    buckets: dict[int, list[np.ndarray]] = {i: [] for i in range(N)}
    for d in np.unique(device):
        idx = np.where(device == d)[0].copy()
        rng.shuffle(idx)
        p = rng.dirichlet(np.repeat(alpha, N))
        cuts = (np.cumsum(p)[:-1] * len(idx)).astype(int)
        for i, chunk in enumerate(np.split(idx, cuts)):
            buckets[i].append(chunk)
    return {i: (np.sort(np.concatenate(v)) if v else np.array([], dtype=int))
            for i, v in buckets.items()}


def dirichlet_matched(y, device, N, target_S_JS, seed=0, tol=0.01, max_iter=40,
                      lo=1e-3, hi=1e3, mode: str = "device",
                      min_client_rows: int = 1) -> tuple[Partition, float, float]:
    """ALGORITHM 4 -- the necessity / anti-triviality control.

    Binary-search Dirichlet alpha so the CONTROL partition matches the device-derived
    partition's measured S_JS. Only then is a CA difference attributable to device
    STRUCTURE rather than skew MAGNITUDE. S_JS decreases monotonically in alpha.

    mode='device' (default) allocates each DEVICE's rows by Dirichlet and so moves the
    device axis directly. mode='label' is the classic label-Dirichlet, retained as a
    secondary control: it leaves every device visible to every client.

    Partitions that starve a client below `min_client_rows` are REJECTED, not scored.
    A federation with empty clients is degenerate, and including such clients also made
    S_JS non-monotone in alpha (an empty client contributes an artificial uniform
    histogram that pulls the mean divergence down), which would silently break any
    monotone search.
    """
    make = (dirichlet_device_partition if mode == "device"
            else (lambda _arg, _N, _a, _s: dirichlet_partition(y, _N, _a, _s)))
    arg0 = device if mode == "device" else y

    def score(alpha: float):
        p = make(arg0, N, float(alpha), seed)
        return p, skew_js(p, y, device), count_empty(p, min_client_rows)

    grid = np.geomspace(lo, hi, 25)
    cands = [(abs(sj - target_S_JS), float(a), p, sj)
             for a in grid
             for p, sj, ne in [score(a)] if ne == 0]
    if not cands:
        mid = float(np.sqrt(lo * hi))
        p, sj, _ = score(mid)
        print(f"  WARNING: no Dirichlet alpha in [{lo}, {hi}] keeps every client at "
              f">= {min_client_rows} rows; the matched control is unreliable and the "
              f"necessity test must not be reported from it.")
        return p, mid, sj

    cands.sort(key=lambda t: t[0])
    _, best_a, best_p, best_s = cands[0]
    if abs(best_s - target_S_JS) <= tol:
        return best_p, best_a, best_s
    for a in np.geomspace(best_a / 3.0, best_a * 3.0, max_iter):
        p, sj, ne = score(a)
        if ne == 0 and abs(sj - target_S_JS) < abs(best_s - target_S_JS):
            best_p, best_a, best_s = p, float(a), sj
        if abs(best_s - target_S_JS) <= tol:
            break
    return best_p, best_a, best_s


def leave_one_device_out(device: np.ndarray, N: int, drop: int, seed: int = 0,
                         devices_per_household=(1, 3)) -> Partition:
    """ALGORITHM 5 -- counterfactual necessity over device types."""
    return device_derived_partition(device, N, seed, devices_per_household, drop_device=drop)


def build(cfg, y: np.ndarray, device: np.ndarray) -> tuple[Partition, dict]:
    """Construct the partition named by cfg.partition.kind and measure its skew."""
    pc = cfg.partition
    kind, N, seed = pc.kind, pc.N, pc.seed
    meta: dict = {"kind": kind, "N": N, "seed": seed}
    if kind == "iid":
        parts = iid_partition(len(y), N, seed)
    elif kind == "device_derived":
        drop = None
        if pc.drop_device is not None:
            drop = int(pc.drop_device)
        parts = device_derived_partition(device, N, seed, tuple(pc.devices_per_household), drop)
        meta["drop_device"] = drop
    elif kind == "volume":
        parts = volume_skew_partition(y, N, cfg.partition.dirichlet_alpha, seed)
    elif kind == "dirichlet":
        if pc.dirichlet_alpha is None:
            raise ValueError("dirichlet partition requires partition.dirichlet_alpha")
        parts = dirichlet_partition(y, N, pc.dirichlet_alpha, seed)
        meta["alpha"] = pc.dirichlet_alpha
    elif kind == "dirichlet_device":
        if pc.dirichlet_alpha is None:
            raise ValueError("dirichlet_device partition requires partition.dirichlet_alpha")
        parts = dirichlet_device_partition(device, N, pc.dirichlet_alpha, seed)
        meta["alpha"] = pc.dirichlet_alpha
    elif kind == "dirichlet_matched":
        if pc.match_target_S_JS is None:
            raise ValueError("dirichlet_matched requires partition.match_target_S_JS "
                             "(measure it from the device_derived run first)")
        parts, alpha, s = dirichlet_matched(y, device, N, pc.match_target_S_JS, seed,
                                            pc.match_tol, mode=getattr(pc, "match_mode", "device"),
                                            min_client_rows=getattr(pc, "min_client_rows", 16))
        meta.update(alpha=alpha, matched_S_JS=s, target_S_JS=pc.match_target_S_JS,
                    match_mode=getattr(pc, "match_mode", "device"),
                    matched_within_tol=bool(abs(s - pc.match_target_S_JS) <= pc.match_tol))
        if not meta["matched_within_tol"]:
            print(f"  WARNING: matched control reached S_JS={s:.4f} vs target "
                  f"{pc.match_target_S_JS:.4f}; the necessity test is NOT valid until "
                  f"these match (design Algorithm 4).")
    else:
        raise ValueError(f"unknown partition kind {kind!r}")
    meta.update(measure_skew(parts, y, device))
    # A client below the trainable minimum breaks any ensemble member that draws it
    # (at k=1 that client IS the member). Surface it here rather than as a crash
    # deep inside FLRun.
    mcr = getattr(pc, "min_client_rows", 16)
    starved = count_empty(parts, mcr)
    meta["min_client_rows"] = mcr
    meta["n_starved"] = starved
    if starved:
        print(f"  WARNING: {starved}/{N} clients hold < {mcr} rows under partition "
              f"'{kind}'. Small-k ensembles will be unreliable or fail.")
    return parts, meta
