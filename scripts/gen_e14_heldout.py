#!/usr/bin/env python3
"""Held-out validation of the deployable k-selection rule (review W4).

The rule has one free parameter, the safety factor by which clean coverage must
clear the trivial floor, and its performance was reported on the same partition
draws that the factor could have been chosen on. That is the criticism: a rule
tuned and scored on one sample is optimistic by construction.

This splits the partition draws into a development half and a held-out half by
seed parity (fixed before looking at any result -- even seeds develop, odd seeds
test), sweeps the safety factor on development only, and reports the selected
factor's performance on the held-out draws it never saw. The gap between the two
is the quantity the review asked for.
"""
import collections, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregate import load

OUT = os.environ.get("FHG_GENERATED",
                     "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated")
GRID = [1.00, 1.02, 1.05, 1.08, 1.10, 1.15, 1.20]


def evaluate(idx, tau, safety, seeds, detail=False):
    """Return (n, agree, unsafe, mean_regret) for the rule at this safety factor.

    With detail=True also returns refusals, missed opportunities and max regret."""
    n = agree = unsafe = refuse_ok = refuse_bad = 0
    reg = []
    for (p, s, b), byk in idx.items():
        if s not in seeds:
            continue
        n += 1
        feasible = [k for k, r in byk.items()
                    if r["combinatorially_possible"] and r["coverage"] > safety * tau]
        pick = max(feasible) if feasible else None
        good = {k: r["CA"] for k, r in byk.items() if r["CA"] > tau}
        oracle = max(good, key=good.get) if good else None
        ca_rule = byk[pick]["CA"] if pick else 0.0
        ca_orc = good[oracle] if oracle else 0.0
        if pick is not None and ca_rule <= tau:
            unsafe += 1
        if pick is None and oracle is None:
            refuse_ok += 1
        elif pick is None and oracle is not None:
            refuse_bad += 1
        if (pick is None and oracle is None) or pick == oracle or ca_rule > tau:
            agree += 1
        reg.append(ca_orc - ca_rule)
    mr = float(np.mean(reg)) if reg else float("nan")
    if detail:
        return n, agree, unsafe, mr, refuse_ok, refuse_bad, (max(reg) if reg else float("nan"))
    return n, agree, unsafe, mr


def main():
    # e5f carries 30 partition draws (k in {1,2}); e2_* has only 3, which cannot
    # support a held-out split. The k range is stated with the result.
    rows = load("results/canonical/e5f_*.jsonl")
    tau = rows[0]["tau_triv"]
    idx = collections.defaultdict(dict)
    for r in rows:
        idx[(r["partition_type"], r["partition_seed"], round(r["beta"], 4))][r["k"]] = r
    seeds = sorted({s for (_, s, _) in idx})
    dev = {s for s in seeds if s % 2 == 0}
    test = {s for s in seeds if s % 2 == 1}
    if not dev or not test:
        raise SystemExit(f"gen_e14_heldout: need both parities, got seeds {seeds}")

    print(f"  seeds {seeds}  dev={sorted(dev)}  held-out={sorted(test)}")
    print(f"  {'safety':>7}{'dev n':>7}{'dev agree':>11}{'dev unsafe':>11}{'dev regret':>12}")
    best, best_key = None, None
    for sf in GRID:
        n, ag, un, mr = evaluate(idx, tau, sf, dev)
        print(f"  {sf:>7.2f}{n:>7}{ag:>11}{un:>11}{mr:>12.4f}")
        # selection rule fixed in advance: no unsafe selection first, then max agreement,
        # then lowest mean regret. Ties broken toward the smaller (more conservative) factor.
        key = (un == 0, ag, -mr)
        if best_key is None or key > best_key:
            best, best_key = sf, key
    PAPER = 1.05   # the factor the manuscript fixed in advance, not tuned here
    n_p, ag_p, un_p, mr_p = evaluate(idx, tau, PAPER, test)
    print(f"\n  the manuscript's PRE-FIXED safety = {PAPER:.2f}, on held-out draws:")
    print(f"    n={n_p} agree={ag_p} ({100*ag_p/n_p:.1f}%) unsafe={un_p} regret={mr_p:.4f}")
    n_d, ag_d, un_d, mr_d = evaluate(idx, tau, best, dev)
    n_t, ag_t, un_t, mr_t = evaluate(idx, tau, best, test)
    print(f"\n  selected on development: safety = {best:.2f}")
    print(f"    development : n={n_d} agree={ag_d} ({100*ag_d/n_d:.1f}%) unsafe={un_d} regret={mr_d:.4f}")
    print(f"    HELD OUT    : n={n_t} agree={ag_t} ({100*ag_t/n_t:.1f}%) unsafe={un_t} regret={mr_t:.4f}")
    print(f"    optimism    : {100*ag_d/n_d - 100*ag_t/n_t:+.1f} points of agreement")

    # coverage at the one unsafe selection, so the prose never hard-codes it
    unsafe_cov = None
    for (pp, ss, bb), byk in idx.items():
        feas = [k for k, r in byk.items()
                if r["combinatorially_possible"] and r["coverage"] > PAPER * tau]
        if not feas:
            continue
        pk = max(feas)
        if byk[pk]["CA"] <= tau:
            unsafe_cov = byk[pk]["coverage"]
    allseeds = set(dev) | set(test)
    n_all, ag_all, un_all, mr_all, d_ro, d_rb, d_mx = evaluate(
        idx, tau, PAPER, allseeds, detail=True)
    print(f"  full set at the pre-fixed {PAPER:.2f}: n={n_all} unsafe={un_all} "
          f"correct-refusals={d_ro} missed={d_rb} mean-regret={mr_all:.4f} max={d_mx:.4f}")

    mac = [f"\\newcommand{{\\hoSafety}}{{{best:.2f}}}",
           f"\\newcommand{{\\hoDevN}}{{{n_d}}}", f"\\newcommand{{\\hoDevAgree}}{{{ag_d}}}",
           f"\\newcommand{{\\hoTestN}}{{{n_t}}}", f"\\newcommand{{\\hoTestAgree}}{{{ag_t}}}",
           f"\\newcommand{{\\hoTestUnsafe}}{{{un_t}}}",
           f"\\newcommand{{\\hoDevPct}}{{{100*ag_d/n_d:.1f}}}",
           f"\\newcommand{{\\hoTestPct}}{{{100*ag_t/n_t:.1f}}}",
           f"\\newcommand{{\\hoTestRegret}}{{{mr_t:.4f}}}",
           f"\\newcommand{{\\hoPaperSafety}}{{{PAPER:.2f}}}",
           f"\\newcommand{{\\hoPaperTestAgree}}{{{ag_p}}}",
           f"\\newcommand{{\\hoPaperTestN}}{{{n_p}}}",
           f"\\newcommand{{\\hoPaperTestUnsafe}}{{{un_p}}}",
           f"\\newcommand{{\\hoPaperTestPct}}{{{100*ag_p/n_p:.1f}}}",
           f"\\newcommand{{\\hoRefuseOk}}{{{d_ro}}}",
           f"\\newcommand{{\\hoRefuseBad}}{{{d_rb}}}",
           f"\\newcommand{{\\hoMaxRegret}}{{{d_mx:.4f}}}",
           f"\\newcommand{{\\hoAllN}}{{{n_all}}}",
           f"\\newcommand{{\\hoAllUnsafe}}{{{un_all}}}",
           # review r4 (C-W3): the denominator the unsafe rate is read against is the
           # cells where the rule commits to a k, not every cell it was shown
           f"\\newcommand{{\\hoCommitN}}{{{n_all - d_ro - d_rb}}}",
           f"\\newcommand{{\\hoUnsafeCoverage}}{{{unsafe_cov:.4f}}}"]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "heldout_macros.tex"), "w") as fh:
        fh.write("% GENERATED by scripts/gen_e14_heldout.py -- do not edit\n")
        fh.write("\n".join(mac) + "\n")
    print(f"  -> {OUT}/heldout_macros.tex")


if __name__ == "__main__":
    main()
