#!/usr/bin/env python3
"""Evaluate the deployable k-selection rule against the oracle choice (review sec 14).

The rule uses only pre-attack, LABEL-FREE information: the declared budget m, the
geometric feasibility 2*c_max(m)/K < 1, and the ensemble's clean COVERAGE at that
budget -- the fraction of points whose vote margin clears the threshold -- which the
server computes on its own unlabelled traffic with no adversary present.

Coverage is the right screen rather than the mean margin, because CA <= Coverage by
construction: a point can only contribute to certified accuracy if it is certified at
all. So Coverage <= tau_triv is a SUFFICIENT condition for the certificate to be
uninformative, and the operator can check it without a single test label. It needs
only the class prior, which a deployer knows.

The oracle picks the k that maximises CA after the fact.
"""
import collections, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load, src

from _manuscript import GENERATED as OUT  # TMLR generated/ (FHG_GENERATED overrides)
SAFETY = 1.05          # coverage must clear the trivial floor by 5%, fixed in advance


def main():
    rows = load(src("e2_*.jsonl"))
    tau = rows[0]["tau_triv"]
    idx = collections.defaultdict(dict)
    for r in rows:
        idx[(r["partition_type"], r["partition_seed"], round(r["beta"], 4))][r["k"]] = r

    out, agree, refuse_ok, refuse_bad = [], 0, 0, 0
    for (p, s, b), byk in sorted(idx.items()):
        feasible = [k for k, r in byk.items()
                    if r["combinatorially_possible"]
                    and r["coverage"] > SAFETY * tau]
        pick = max(feasible) if feasible else None
        # oracle: the k with the highest CA, only counting cells above the floor
        good = {k: r["CA"] for k, r in byk.items() if r["CA"] > tau}
        oracle = max(good, key=good.get) if good else None
        ca_rule = byk[pick]["CA"] if pick else 0.0
        ca_orc = good[oracle] if oracle else 0.0
        if pick is None and oracle is None:
            refuse_ok += 1
        elif pick is None and oracle is not None:
            refuse_bad += 1
        elif pick == oracle or ca_rule > tau:
            agree += 1
        out.append(dict(partition=p, seed=s, beta=b, rule_k=pick, oracle_k=oracle,
                        CA_rule=round(ca_rule, 4), CA_oracle=round(ca_orc, 4),
                        regret=round(ca_orc - ca_rule, 4)))

    n = len(out)
    reg = [o["regret"] for o in out]
    # never certify below the floor: the rule must not pick a k whose CA <= tau
    unsafe = [o for o in out if o["rule_k"] is not None and o["CA_rule"] <= tau]
    summary = dict(
        n_cells=n, rule_matches_or_clears=agree,
        correct_refusals=refuse_ok, missed_opportunities=refuse_bad,
        unsafe_selections=len(unsafe),
        mean_regret=round(float(np.mean(reg)), 4),
        max_regret=round(float(np.max(reg)), 4), safety_factor=SAFETY)
    print(json.dumps(summary, indent=1))
    print()
    print(f"{'partition':16s} {'seed':>4} {'beta':>5} {'rule k':>7} {'oracle k':>8} "
          f"{'CA rule':>8} {'CA orc':>8} {'regret':>7}")
    for o in out:
        print(f"{o['partition']:16s} {o['seed']:>4} {o['beta']:>5.2f} "
              f"{str(o['rule_k']):>7} {str(o['oracle_k']):>8} "
              f"{o['CA_rule']:>8.4f} {o['CA_oracle']:>8.4f} {o['regret']:>7.4f}")
    json.dump(dict(summary=summary, cells=out),
              open(os.path.join(OUT, "deployable_k.json"), "w"), indent=1)
    return summary


if __name__ == "__main__":
    main()
