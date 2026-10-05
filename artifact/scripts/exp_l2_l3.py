#!/usr/bin/env python3
"""FLTrust (L2), multi-Krum (L1) and the oracle ceiling (L3).

Section 3 argues that L2 defenses buy accuracy with knowledge a household
federation cannot supply. That argument is currently asserted rather than
measured. This quantifies it: same attacks and fractions, differing only in what
the server is allowed to see.
"""
import copy, json, sys, time
import numpy as np, yaml
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, fl as FL, attacks as A, defenses as D

base = yaml.safe_load(open("configs/stage2_empirical.yaml"))
ATTACKS = ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]
BETAS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]
PLAN = [("multikrum", "L1"), ("fltrust", "L2"), ("oracle_trimmed", "L3")]
rows, t0 = [], time.time()

for kind in ("device_derived", "iid"):
    for defn, lvl in PLAN:
        for b in BETAS:
            for atk in (["none"] if b == 0 else ATTACKS):
                d = copy.deepcopy(base)
                d["partition"].update(kind=kind, seed=0, N=20)
                d["adversary"].update(beta=b, F3_knowledge="white_box")
                d["defense"].update(name=defn, observability=lvl, root_size=200)
                d["name"] = f"l2_{kind}_{defn}_b{b}_{atk}"
                cfg = CFG.from_dict(d)
                t = R.prepare(cfg, verbose=False)
                mal = A.select_malicious(20, b, cfg.adversary.seed)
                root = None
                if defn == "fltrust":
                    # L2 capability: a clean labelled server-side root set.
                    rng = np.random.default_rng(0)
                    idx = rng.choice(len(t["ytr_np"]), size=cfg.defense.root_size,
                                     replace=False)
                    root = FL.server_root_update(
                        cfg, t["Xtr"], t["ytr"],
                        __import__("torch").tensor(np.sort(idx), device=t["dev"]))
                try:
                    g = FL.fl_run(cfg, list(range(20)), t["Xtr"], t["ytr"], t["parts"],
                                  malicious_ids=mal,
                                  attack=None if atk == "none" else atk,
                                  server_root=root)
                except Exception as e:
                    print(f"  ERR {kind} {defn} b={b} {atk}: {type(e).__name__}: {e}",
                          flush=True); continue
                ea = FL.accuracy(g, t["Xte"], t["yte_np"])
                rows.append(dict(kind=kind, defense=defn, level=lvl, beta=b,
                                 attack=atk, EA=round(ea, 6),
                                 is_upper_bound=defn in D.IS_UPPER_BOUND,
                                 requires_clean_server_data=defn in D.REQUIRES_CLEAN_SERVER_DATA))
                print(f"  {kind:15s} {defn:15s}[{lvl}] beta={b:.2f} {atk:11s} "
                      f"EA={ea:.4f} [{time.time()-t0:.0f}s]", flush=True)
                json.dump(rows, open("results/l2_l3_defenses.json", "w"), indent=2)
print(f"L2/L3 DONE {len(rows)} rows")
