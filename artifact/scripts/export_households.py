#!/usr/bin/env python3
"""Export one household's data per file, plus the shared test set.

The real-stack arm must train on EXACTLY the partitions the simulation uses, or the
cross-validation compares two different experiments. So partitions come from
runner.prepare() -- the same code path, the same seeds -- and are written out
verbatim rather than reconstructed inside the containers.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
import numpy as np
from fedhomeguard import config as CFG, runner as R


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage3_certification.yaml")
    ap.add_argument("--partition", default="device_derived")
    ap.add_argument("--pseed", type=int, default=0)
    ap.add_argument("--N", type=int, default=20)
    ap.add_argument("--dph", type=int, nargs="+", default=None)
    ap.add_argument("--out", default="data/households")
    a = ap.parse_args()

    cfg = CFG.load(a.config)
    cfg.device = "cpu"
    cfg.partition.kind = a.partition
    cfg.partition.seed = a.pseed
    cfg.partition.N = a.N
    if a.dph:
        cfg.partition.devices_per_household = list(a.dph)
    t = R.prepare(cfg, verbose=False)

    Xtr = t["Xtr"].cpu().numpy(); ytr = t["ytr_np"]
    Xte = t["Xte"].cpu().numpy(); yte = t["yte_np"]
    out = os.path.join(a.out, f"{a.partition}_s{a.pseed}_N{a.N}")
    os.makedirs(out, exist_ok=True)

    sizes = {}
    for cid, idx in sorted(t["parts_np"].items()):
        idx = np.asarray(idx)
        np.savez_compressed(os.path.join(out, f"household_{cid:02d}.npz"),
                            X=Xtr[idx].astype(np.float32), y=ytr[idx].astype(np.int64))
        sizes[int(cid)] = int(len(idx))
    np.savez_compressed(os.path.join(out, "test.npz"),
                        X=Xte.astype(np.float32), y=yte.astype(np.int64))

    meta = dict(partition=a.partition, pseed=a.pseed, N=a.N,
                dim=int(Xtr.shape[1]), tau_triv=float(t["tau"]),
                n_train=int(len(ytr)), n_test=int(len(yte)),
                per_household_sizes=sizes,
                arch=cfg.model.arch, hidden=list(cfg.model.hidden),
                rounds_T=cfg.fl.rounds_T, local_epochs_E=cfg.fl.local_epochs_E,
                lr=cfg.fl.lr, momentum=cfg.fl.momentum, batch_size=cfg.fl.batch_size,
                skew=t["pmeta"])
    with open(os.path.join(out, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"wrote {out}: {len(sizes)} households, dim={meta['dim']}, "
          f"n_test={meta['n_test']}, tau_triv={meta['tau_triv']:.4f}")
    print(f"  household sizes: min={min(sizes.values())} med="
          f"{int(np.median(list(sizes.values())))} max={max(sizes.values())}")


if __name__ == "__main__":
    main()
