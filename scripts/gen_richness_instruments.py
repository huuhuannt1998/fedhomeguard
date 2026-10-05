#!/usr/bin/env python3
"""Class coverage at each device-types-per-household level (review D1, F-09).

The richness tables report beta*, vote margin and collapse per level, but not the
quantity the paper's mechanism names: how many members see essentially one class.
This script rebuilds every partition the richness sweeps used -- same config, same
data split, same seeds, same devices_per_household -- and records the partition's
pre-training statistics (fracDegen, minClassSup, S_JS, ...). No training happens.

A rebuilt partition is accepted only if its S_JS equals the S_JS stored in the result
row of the same (config, level, seed) to six decimals; otherwise the script stops, so
the statistics cannot drift from the partitions the runs saw.

Writes results/analysis/richness_instruments.jsonl, one row per (corpus, level, seed).
"""
from __future__ import annotations
import glob, json, os, sys
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, data as DATA, partition as P

SWEEPS = [  # (corpus, config, result-file pattern for the stored S_JS, levels)
    ("iot23", "configs/stage3_certification.yaml", "results/canonical/e11b_dph{t}.jsonl",
     [(1, 1), (1, 3), (2, 5), (3, 8), (5, 10)]),
    ("nbaiot", "configs/stage3_nbaiot.yaml", "results/canonical/e21_nbrich_{t}.jsonl",
     [(1, 1), (1, 3), (2, 5), (3, 8), (5, 9)]),
]
SEEDS = range(30)
KEEP = ["S_JS", "S_dev", "S_lab", "min_minority", "frac_degenerate",
        "min_class_support", "min_size_share"]


def stored_sjs(path):
    out = {}
    for line in open(path):
        if line.startswith("{"):
            r = json.loads(line)
            out[int(r["partition_seed"])] = float(r["S_JS"])
    return out


def main():
    rows = []
    for corpus, cfgpath, pat, levels in SWEEPS:
        cfg = CFG.load(cfgpath)
        cfg.device = "cpu"
        bundle = DATA.load_dataset(cfg, verbose=False)
        y, device = bundle["y"], bundle["device"]
        tr, _ = DATA.time_split_within_device(y, device, cfg.data.train_frac,
                                              block=bundle.get("block"))
        ytr, dtr = y[tr], device[tr]
        for lo, hi in levels:
            tag = f"{lo}_{hi}"
            ref = stored_sjs(pat.format(t=tag))
            for s in SEEDS:
                cfg.partition.kind = "device_derived"
                cfg.partition.seed = s
                cfg.partition.devices_per_household = [lo, hi]
                _, pm = P.build(cfg, ytr, dtr)
                if round(pm["S_JS"], 6) != round(ref[s], 6):
                    sys.exit(f"{corpus} {tag} seed {s}: rebuilt S_JS {pm['S_JS']} != stored {ref[s]}")
                rows.append(dict(dataset=corpus, family="device_derived", level=tag, pseed=s,
                                 **{k: pm.get(k) for k in KEEP}))
            print(f"  {corpus} {tag}: 30 partitions rebuilt, S_JS matches the result rows", flush=True)
    os.makedirs("results/analysis", exist_ok=True)
    with open("results/analysis/richness_instruments.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} rows to results/analysis/richness_instruments.jsonl")


if __name__ == "__main__":
    main()
