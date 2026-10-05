#!/usr/bin/env python3
"""E3 -- empirical robust-aggregation defences on the SAME partitions and malicious
sets as E2, plus E12 (observability across draws) and E13 (attack strength).

E3's quantity is the CERTIFICATION COST, not certificate slack:

    G_method = EA_best_robust_defence  -  EA_certifiable_ensemble

i.e. how much empirical robustness an operator gives up by moving to a construction
that admits a certificate at all. The review is explicit that this must not be
conflated with certificate slack (sec 33, Gap B).

The best-defence figure is a best-in-hindsight ORACLE ENVELOPE: the defence is
chosen after observing test outcomes. It is labelled as such everywhere, and a
deployable variant selected on a clean validation split is reported alongside.
"""
from __future__ import annotations
import argparse, json, os, sys, time
import numpy as np
import torch
torch.set_num_threads(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import config as CFG, runner as R, fl as FL, defenses as D

ATTACKS = ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]
DEFENSES = ["fedavg", "krum", "multikrum", "trimmed_mean", "median", "norm_clip",
            "fltrust", "oracle_trimmed"]


def load_done(path):
    done = set()
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                r = json.loads(line)
                done.add((r["partition_type"], r["partition_seed"], round(r["beta"], 4),
                          r["mal_seed"], r["defense"], r["attack"], r["scale"]))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage3_certification.yaml")
    ap.add_argument("--partition", default="device_derived")
    ap.add_argument("--pseed", type=int, nargs="+", default=[0])
    ap.add_argument("--betas", type=float, nargs="+",
                    default=[0.0, 0.05, 0.10, 0.20, 0.30, 0.40])
    ap.add_argument("--mal-seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--attacks", nargs="+", default=ATTACKS)
    ap.add_argument("--defenses", nargs="+", default=DEFENSES)
    ap.add_argument("--scales", type=float, nargs="+", default=[1.0],
                    help="E13 attack-strength sweep, e.g. 0.5 1.0 5.0")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default="results/canonical/e3.jsonl")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = load_done(a.out)
    fh = open(a.out, "a")
    t_start = time.time()

    for pseed in a.pseed:
        cfg = CFG.load(a.config)
        cfg.device = a.device
        cfg.partition.kind = a.partition
        cfg.partition.seed = pseed
        cfg.adversary.F3_knowledge = "white_box"
        t = R.prepare(cfg, verbose=False)
        N = cfg.partition.N
        root = None
        print(f"[{a.partition} pseed={pseed}] S_JS={t['pmeta']['S_JS']:.4f}", flush=True)

        for b in a.betas:
            m = int(round(b * N))
            for ms in ([0] if m == 0 else a.mal_seeds):
                B = ([] if m == 0 else
                     sorted(np.random.default_rng(1000 + ms)
                            .choice(N, size=m, replace=False).tolist()))
                for defn in a.defenses:
                    cfg.defense.name = defn
                    cfg.defense.observability = D.LEVEL[defn]
                    if defn == "fltrust" and root is None:
                        # L2 root set: a clean labelled server-side sample. Drawn from
                        # the training pool, which is the most favourable case for the
                        # defence and is reported as such.
                        rng = np.random.default_rng(7)
                        root = rng.choice(len(t["ytr_np"]),
                                          size=cfg.defense.root_size, replace=False)
                        root_t = torch.tensor(root, device=t["dev"])
                    for atk in (["none"] if m == 0 else a.attacks):
                        for sc in ([1.0] if atk in ("none", "label_flip") else a.scales):
                            key = (a.partition, pseed, round(b, 4), ms, defn, atk, sc)
                            if key in done:
                                continue
                            cfg.adversary.beta = b
                            cfg.adversary.scale = sc
                            t0 = time.time()
                            sr = (FL.server_root_update(cfg, t["Xtr"], t["ytr"], root_t)
                                  if defn == "fltrust" else None)
                            g = FL.fl_run(cfg, list(range(N)), t["Xtr"], t["ytr"],
                                          t["parts"], malicious_ids=B,
                                          attack=None if atk == "none" else atk,
                                          server_root=sr)
                            pred = FL.predict(g, t["Xte"])
                            y = t["yte_np"]
                            acc = float((pred == y).mean())
                            P = (y == 1); Nn = ~P
                            tpr = float(((pred == 1) & P).sum()) / max(int(P.sum()), 1)
                            tnr = float(((pred == 0) & Nn).sum()) / max(int(Nn.sum()), 1)
                            row = dict(
                                schema="fedhomeguard.canonical-defense/v1",
                                partition_type=a.partition, partition_seed=pseed,
                                S_JS=t["pmeta"]["S_JS"], N=N, beta=float(b), m=m,
                                mal_seed=ms, mal_members=B, defense=defn,
                                observability=D.LEVEL[defn],
                                is_upper_bound=defn in D.IS_UPPER_BOUND,
                                requires_clean_server_data=defn in D.REQUIRES_CLEAN_SERVER_DATA,
                                attack=atk, scale=sc,
                                EA=round(acc, 6), tau_triv=round(t["tau"], 6),
                                TPR=round(tpr, 6), FNR=round(1 - tpr, 6),
                                FPR=round(1 - tnr, 6),
                                balanced_acc=round(0.5 * (tpr + tnr), 6),
                                secs=round(time.time() - t0, 2))
                            fh.write(json.dumps(row) + "\n"); fh.flush()
                    print(f"  b={b:.2f} ms={ms} {defn:15s} done [{time.time()-t_start:.0f}s]",
                          flush=True)
    fh.close()
    print(f"DONE in {(time.time()-t_start)/60:.1f} min -> {a.out}")


if __name__ == "__main__":
    main()
