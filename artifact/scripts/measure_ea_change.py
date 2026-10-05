#!/usr/bin/env python3
"""Separate the two effects on empirical accuracy, so each can be reported honestly.

EFFECT A -- reproducibility. Before the fix, fl_run drew its initial weights from the
global RNG, so two identical calls disagreed. Varying fl.seed now reproduces exactly
that spread, which is the run-to-run noise every previously published EA carried.

EFFECT B -- the statistic. With the seed pinned, EA read as the worst round in the
window versus EA read at the final round, on the SAME runs.
"""
from __future__ import annotations
import argparse, json, os, statistics as st, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from fedhomeguard import config as CFG, runner as R, ensemble as EN, fl as FL

ATTACKS = ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--out", default="results/analysis/ea_change.json")
    a = ap.parse_args()

    rows = []
    for part in ("device_derived", "iid"):
        for beta, m in ((0.10, 2), (0.20, 4), (0.40, 8)):
            for seed in range(a.seeds):
                cfg = CFG.load("configs/stage3_certification.yaml")
                cfg.device = "cpu"; cfg.partition.kind = part; cfg.partition.seed = 0
                cfg.partition.N = 20; cfg.fl.seed = seed
                cfg.defense.name = "fedavg"; cfg.adversary.F3_knowledge = "white_box"
                t = R.prepare(cfg, verbose=False)
                subsets = [(i,) for i in sorted(t["parts_np"])][: cfg.partition.N]
                B = tuple(sorted(t["parts_np"]))[:m]
                r = EN.attacked_ensemble_accuracy(cfg, t, subsets, B, ATTACKS,
                                                  EN.MemberCache())
                for atk, d in r["per_attack"].items():
                    rows.append(dict(partition=part, beta=beta, m=m, seed=seed,
                                     attack=atk, EA_window=d["EA"],
                                     EA_final=d["EA_final_round"],
                                     spread=d["EA_window_spread"]))
                print(f"  {part:15s} b={beta:.2f} seed={seed} "
                      f"worst={r['worst_attack']} EA={r['EA_ensemble']:.4f}", flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rows, open(a.out, "w"), indent=2)

    print("\n" + "=" * 70)
    print("EFFECT A -- run-to-run spread of EA under the OLD unseeded init")
    print("=" * 70)
    by = {}
    for r in rows:
        by.setdefault((r["partition"], r["beta"], r["attack"]), []).append(r["EA_final"])
    sp = [max(v) - min(v) for v in by.values() if len(v) > 1]
    print(f"  cells={len(sp)}  mean spread {st.mean(sp):.4f}  median {st.median(sp):.4f}"
          f"  max {max(sp):.4f}")
    worst = max(by.items(), key=lambda kv: max(kv[1]) - min(kv[1]))
    print(f"  worst cell: {worst[0]} -> {[round(x,4) for x in worst[1]]}")

    print("\n" + "=" * 70)
    print("EFFECT B -- worst-round vs final-round EA, same runs (seed pinned)")
    print("=" * 70)
    d = [r["EA_final"] - r["EA_window"] for r in rows]
    print(f"  n={len(d)}  mean {st.mean(d):+.4f}  median {st.median(d):+.4f}  max {max(d):+.4f}")
    byatk = {}
    for r in rows:
        byatk.setdefault(r["attack"], []).append(r["EA_final"] - r["EA_window"])
    for k, v in sorted(byatk.items(), key=lambda kv: -st.mean(kv[1])):
        print(f"    {k:11s} mean final-minus-window {st.mean(v):+.4f}  max {max(v):+.4f}")
    print(f"\n  wrote {a.out}")


if __name__ == "__main__":
    main()
