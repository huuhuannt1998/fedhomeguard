#!/usr/bin/env python3
"""Simulation counterpart to the real-stack arm.

Runs the SAME configuration the containers run -- one global FedAvg over all twenty
households, same partition, same seeds, same rounds -- inside the single-process
harness, so the two arms differ only in how the update reaches the server. Any
divergence is the cost of the simulation, which is what the cross-validation is for.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
import numpy as np
from fedhomeguard import config as CFG, runner as R, fl as FL

MAL = {0: [], 2: [3, 7], 4: [3, 7, 11, 15], 8: [1, 3, 5, 7, 9, 11, 13, 15]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage3_certification.yaml")
    ap.add_argument("--out", default="results/realstack/sim_counterpart.json")
    a = ap.parse_args()
    rows = []
    for part, dph in (("device_derived", [1, 3]), ("iid", None)):
        cfg = CFG.load(a.config)
        cfg.device = "cpu"; cfg.partition.kind = part; cfg.partition.seed = 0
        cfg.partition.N = 20; cfg.fl.seed = 0
        if dph:
            cfg.partition.devices_per_household = dph
        cfg.defense.name = "fedavg"
        cfg.adversary.F3_knowledge = "white_box"
        t = R.prepare(cfg, verbose=False)
        ids = sorted(t["parts_np"])
        for attack in ("none", "label_flip", "sign_flip", "gaussian", "ipm", "alie"):
            for m in ([0] if attack == "none" else [2, 4, 8]):
                model = FL.fl_run(cfg, ids, t["Xtr"], t["ytr"], t["parts_np"],
                                  malicious_ids=tuple(MAL[m]),
                                  attack=None if attack == "none" else attack)
                acc = FL.accuracy(model, t["Xte"], t["yte_np"])
                rows.append(dict(partition=part, attack=attack, m=m,
                                 beta=round(m / 20, 3), accuracy=round(float(acc), 6)))
                print(f"  {part:15s} {attack:11s} m={m}  acc={acc:.4f}", flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(rows, fh, indent=2)
    print(f"wrote {a.out}: {len(rows)} cells")


if __name__ == "__main__":
    main()
