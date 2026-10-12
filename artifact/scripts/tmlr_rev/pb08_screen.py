#!/usr/bin/env python3
"""PB08 (preregistered, predeclarations/tmlr_PB08_screen_baselines.md): the paper's label-free
coverage screen against simple alternatives on the 660 e5f decision cells, with parameters fitted on
even seeds (development) and scored on odd seeds (held out). Rows + per-draw partition statistics
from results/analysis/instruments.jsonl (same draws, seeds 10-39). Writes results/pb08_screen.json."""
import argparse, collections, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

FACTORS = [1.00, 1.02, 1.05, 1.08, 1.10, 1.15, 1.20]


def load():
    rows = [r for p in ("iid", "device_derived") for r in C.load_rows(f"e5f_{p}.jsonl")]
    tau = rows[0]["tau_triv"]
    idx = collections.defaultdict(dict)
    for r in rows:
        idx[(r["partition_type"], r["partition_seed"], round(r["beta"], 4))][r["k"]] = r
    st = {}
    for l in open(os.path.join(C.REPO, "results/analysis/instruments.jsonl")):
        c = json.loads(l)
        if c["dataset"] == "iot23" and c["family"] in ("iid", "device_derived") and c["k"] == 1:
            st[(c["family"], c["pseed"])] = c
    for (p, s, b), byk in idx.items():
        assert abs(st[(p, s)]["S_JS"] - next(iter(byk.values()))["S_JS"]) < 1e-5
    return idx, st, tau


def screen_rule(name, thr=None):
    """Returns accept(partition, seed, k, row, stats) -> bool, applied on top of feasibility."""
    if name == "cov":
        return lambda r, s, tau: r["coverage"] > thr * tau
    if name == "geo":
        return lambda r, s, tau: True
    if name == "refuse":
        return lambda r, s, tau: False
    if name == "div":
        return lambda r, s, tau: s["S_JS"] <= thr
    if name == "vol":
        return lambda r, s, tau: s["min_size_share"] >= thr
    if name == "labsup":
        return lambda r, s, tau: s["min_class_support"] >= thr
    if name == "labdeg":
        return lambda r, s, tau: s["frac_degenerate"] <= thr
    raise ValueError(name)


def evaluate(idx, st, tau, accept, seeds, floor=None):
    floor = tau if floor is None else floor
    n = commit = unsafe = ref_ok = ref_bad = agree = 0
    reg, unsafe_draws, cells = [], set(), []
    for (p, s, b), byk in idx.items():
        if s not in seeds:
            continue
        n += 1
        feas = [k for k, r in byk.items() if r["combinatorially_possible"] and accept(r, st[(p, s)], tau)]
        pick = max(feas) if feas else None
        good = {k: r["CA"] for k, r in byk.items() if r["CA"] > floor}
        orc = max(good, key=good.get) if good else None
        if pick is None:
            ref_ok += orc is None; ref_bad += orc is not None
            if orc is not None:
                reg.append(good[orc])
            agree += orc is None
        else:
            commit += 1
            if byk[pick]["CA"] <= floor:
                unsafe += 1; unsafe_draws.add((p, s))
                cells.append(dict(partition=p, seed=s, beta=b, k=pick, CA=byk[pick]["CA"],
                                  coverage=byk[pick]["coverage"]))
            else:
                agree += 1
                reg.append(good[orc] - byk[pick]["CA"])
    draws = {(p, s) for (p, s, _) in idx if s in seeds}
    return dict(cells=n, commitments=commit, unsafe=unsafe, correct_refusals=ref_ok,
                missed_opportunities=ref_bad, agree=agree,
                max_regret=(max(reg) if reg else 0.0), mean_regret=(float(np.mean(reg)) if reg else 0.0),
                draws=len(draws), draws_with_unsafe=len(unsafe_draws),
                unsafe_rate_cp95=(list(C.cp_interval(unsafe, commit)) if commit else None),
                draw_unsafe_cp95=list(C.cp_interval(len(unsafe_draws), len(draws))),
                unsafe_cells=cells)


def fit(idx, st, tau, name, grid, dev):
    best, bkey = None, None
    for t in grid:
        e = evaluate(idx, st, tau, screen_rule(name, t), dev)
        key = (e["unsafe"] == 0, e["agree"], -e["mean_regret"])
        if bkey is None or key > bkey:
            best, bkey = t, key
    return best


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    idx, st, tau = load()
    seeds = sorted({s for (_, s, _) in idx})
    dev = {s for s in seeds if s % 2 == 0}; test = {s for s in seeds if s % 2 == 1}
    if a.dry_run:
        print(f"{len(idx)} cells, seeds {seeds[0]}-{seeds[-1]}, dev {len(dev)} / held-out {len(test)} draws"); return
    vals = lambda key: sorted({c[key] for c in st.values()})
    grids = dict(cov=FACTORS, div=vals("S_JS") + [0.0, 1.0], vol=vals("min_size_share") + [0.0, 1.0],
                 labsup=vals("min_class_support") + [0.0, 1.01], labdeg=vals("frac_degenerate") + [-0.01, 1.0])
    out = dict(tau=tau, n_cells=len(idx), dev_seeds=sorted(dev), heldout_seeds=sorted(test), screens={})
    specs = [("cov_paper_1.05", "cov", 1.05), ("cov_1.00", "cov", 1.00), ("geo", "geo", None),
             ("refuse", "refuse", None)]
    for nm in ("cov", "div", "vol", "labsup", "labdeg"):
        specs.append((f"{nm}_fitted", nm, fit(idx, st, tau, nm, grids[nm], dev)))
    for label, nm, thr in specs:
        rule = screen_rule(nm, thr)
        out["screens"][label] = dict(rule=nm, threshold=thr, label_free=nm not in ("labsup", "labdeg"),
                                     heldout=evaluate(idx, st, tau, rule, test),
                                     development=evaluate(idx, st, tau, rule, dev),
                                     all=evaluate(idx, st, tau, rule, set(seeds)),
                                     by_partition={p: evaluate({k: v for k, v in idx.items() if k[0] == p}, st, tau,
                                                               rule, set(seeds)) for p in ("iid", "device_derived")})
    # prior dependence: the paper screen at the floor of a 1% attack prior, ground truth = CA_pi
    pi = 0.01
    idx_pi = {k: {kk: dict(r, CA=pi * r["CTR_mal"] + (1 - pi) * r["CTR_ben"]) for kk, r in v.items()}
              for k, v in idx.items()}
    out["prior_1pct"] = evaluate(idx_pi, st, 0.99, screen_rule("cov", 1.05), set(seeds), floor=0.99)
    hc, sc = out["screens"]["cov_paper_1.05"]["heldout"], None
    fired = []
    for nm in ("div_fitted", "vol_fitted"):
        h = out["screens"][nm]["heldout"]
        if h["unsafe"] <= hc["unsafe"] and h["missed_opportunities"] <= hc["missed_opportunities"]:
            fired.append(nm)
    out["falsifier"] = dict(fired=bool(fired), by=fired)
    C.dump("pb08_screen.json", out)
    for k, v in out["screens"].items():
        h, al = v["heldout"], v["all"]
        print(f"{k:16s} thr={v['threshold']}  held-out: commit={h['commitments']} unsafe={h['unsafe']} "
              f"missed={h['missed_opportunities']} | all: commit={al['commitments']} unsafe={al['unsafe']} "
              f"missed={al['missed_opportunities']} unsafe draws={al['draws_with_unsafe']}/{al['draws']}")
    print("1% prior:", {k: out["prior_1pct"][k] for k in ("commitments", "unsafe", "correct_refusals")})
    print("falsifier:", out["falsifier"])


if __name__ == "__main__":
    main()
