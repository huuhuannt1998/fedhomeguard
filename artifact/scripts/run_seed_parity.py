#!/usr/bin/env python3
"""Stage 2 across the same partition seeds the certified arm uses.

The review flagged that the empirical arm was single-seed while the certified
arm was a median over three, which is what produced the -0.0005 gap entry at
IID beta=0.10. This removes the mismatch.
"""
import copy, json, sys, time, collections
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, fl as FL, attacks as A, defenses as D

base = yaml.safe_load(open("configs/stage2_empirical.yaml"))
ATTACKS = ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]
DEFENSES = ["fedavg", "krum", "trimmed_mean", "median", "norm_clip"]
rows = []
t0 = time.time()
for kind in ("device_derived", "iid"):
    for seed in (1, 2):                      # seed 0 already measured
        d = copy.deepcopy(base)
        d["partition"]["kind"] = kind; d["partition"]["seed"] = seed
        d["adversary"]["F3_knowledge"] = "white_box"
        cfg = CFG.from_dict(d)
        t = R.prepare(cfg, verbose=False)
        for defn in DEFENSES:
            cfg.defense.name = defn
            cfg.defense.observability = D.LEVEL[defn]
            for b in cfg.betas:
                mal = A.select_malicious(cfg.partition.N, b, cfg.adversary.seed)
                for atk in (["none"] if b == 0 else ATTACKS):
                    cfg.adversary.beta = b
                    g = FL.fl_run(cfg, list(range(cfg.partition.N)), t["Xtr"], t["ytr"],
                                  t["parts"], malicious_ids=mal,
                                  attack=None if atk == "none" else atk)
                    rows.append(dict(kind=kind, seed=seed, defense=defn, attack=atk,
                                     beta=b, EA=round(FL.accuracy(g, t["Xte"], t["yte_np"]), 6)))
            json.dump(rows, open("results/stage2_seeds.json", "w"), indent=2)
        print(f"  {kind} seed={seed} done [{time.time()-t0:.0f}s] rows={len(rows)}", flush=True)
print("DONE")
