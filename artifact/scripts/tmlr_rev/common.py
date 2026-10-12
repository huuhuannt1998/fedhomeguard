"""Shared helpers for the paper2 (FedHomeGuard) TMLR-revision analyses.

Read-only with respect to the FedHomeGuard repository: it imports the project's own
modules (src/fedhomeguard) so that every partition, member and certificate is built by
exactly the code that produced the submitted results, and it never writes into the repo.
Outputs go to TMLR_Revision/paper2/results/.
"""
from __future__ import annotations
import copy, hashlib, json, math, os, sys, time
import numpy as np

REPO = "<artifact-root>"
OUTDIR = "<artifact-root>/results/tmlr_rev"
sys.path.insert(0, os.path.join(REPO, "src"))

import torch  # noqa: E402
torch.set_num_threads(1)

from fedhomeguard import config as CFG, runner as R, exactcert as XC  # noqa: E402
from fedhomeguard import ensemble as EN, partition as P, data as DATA, metrics as M  # noqa: E402
from fedhomeguard import defenses as D  # noqa: E402

CANON = os.path.join(REPO, "results", "canonical")


def load_rows(name):
    path = name if os.path.isabs(name) else os.path.join(CANON, name)
    return [json.loads(l) for l in open(path) if l.strip()]


def base_cfg(dataset="iot-23", kind="device_derived", seed=0, dph=(1, 3), alpha=None,
             N=20):
    """The exact configuration exp_e2.py builds for one partition draw."""
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        cfg = CFG.load("configs/stage3_certification.yaml")
    finally:
        os.chdir(cwd)
    cfg.device = "cpu"
    cfg.data.root = os.path.join(REPO, "data", "raw")
    cfg.data.dataset = dataset
    cfg.partition.kind = kind
    cfg.partition.seed = seed
    cfg.partition.N = N
    cfg.partition.devices_per_household = list(dph)
    if alpha is not None:
        cfg.partition.dirichlet_alpha = alpha
    cfg.fl.seed = 0
    cfg.defense.name = "fedavg"
    cfg.defense.observability = D.LEVEL["fedavg"]
    cfg.adversary.F3_knowledge = "white_box"
    return cfg


_DATA_CACHE: dict = {}


def prepare_base(dataset="iot-23", verbose=False):
    """Dataset, split and standardisation are independent of the partition draw, so
    they are built once (with runner.prepare, the same function exp_e2.py calls)."""
    if dataset in _DATA_CACHE:
        return _DATA_CACHE[dataset]
    cfg = base_cfg(dataset, "iid", 0)
    t0 = time.time()
    cwd = os.getcwd(); os.chdir(REPO)
    try:
        t = R.prepare(cfg, verbose=verbose)
    finally:
        os.chdir(cwd)
    t["_load_secs"] = time.time() - t0
    _DATA_CACHE[dataset] = t
    return t


def with_partition(t_base, cfg):
    """A copy of the prepared bundle with the partition named by cfg (P.build, exactly
    as runner.prepare does it)."""
    parts, pmeta = P.build(cfg, t_base["ytr_np"], t_base["dtr"])
    t = dict(t_base)
    t["parts"] = {i: torch.tensor(v, device="cpu") for i, v in parts.items()}
    t["parts_np"] = parts
    t["pmeta"] = pmeta
    return t


def build_subsets(N, k, K_cap, seed):
    """Identical to scripts/exp_e2.py:build_subsets."""
    from itertools import combinations
    tot = math.comb(N, k)
    allc = list(combinations(range(N), k))
    if tot <= K_cap:
        return allc, True, tot
    rng = np.random.default_rng(10_000 + seed * 97 + k)
    sel = rng.choice(tot, size=K_cap, replace=False)
    return [allc[j] for j in sorted(sel)], False, tot


def member_predictions(cfg, t, subsets):
    """Clean final-round test predictions of every trainable member, shape (K, n_test),
    plus the kept subsets. Same code path as exp_e2.py (MemberCache / fl_run)."""
    cache = EN.MemberCache()
    preds, kept = [], []
    for S in subsets:
        p = cache.get_or_train(cfg, t, S, [], None)
        if p is None:
            continue
        preds.append(p[-1].astype(np.int8))
        kept.append(tuple(int(i) for i in S))
    return (np.stack(preds) if preds else np.zeros((0, len(t["yte_np"])), np.int8)), kept


def votes_from_member_preds(mp, n_class=2):
    K, n = mp.shape
    v = np.zeros((n, n_class), np.int32)
    for c in range(n_class):
        v[:, c] = (mp == c).sum(0)
    return v


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def wilson(x, n, z=1.959963984540054):
    if n == 0:
        return (0.0, 1.0)
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def cp_interval(x, n, alpha=0.05):
    from scipy.stats import beta
    lo = 0.0 if x == 0 else float(beta.ppf(alpha / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1 - alpha / 2, x + 1, n - x))
    return lo, hi


def dump(name, obj):
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return path
