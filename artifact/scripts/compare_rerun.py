#!/usr/bin/env python3
"""Compare the re-run against the pre-change results, so the correction is reported
as a measured delta rather than a silent replacement.

Two causes are separated where the data allows. The certified quantities (CA, and
beta* derived from it) can only have moved because initial weights are now seeded.
The empirical quantities (EA) moved for that reason AND because EA is now the worst
round in a window rather than the final round.
"""
from __future__ import annotations
import glob, json, os, statistics as st, sys

OLD, NEW = "results/pre_determinism_fix", "results/canonical"
KEY = ("partition_type", "k", "partition_seed", "beta", "dirichlet_alpha",
       "N", "mal_seed", "arch")


def load(d, name):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return {}
    out = {}
    for line in open(p):
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        out[tuple(str(r.get(k)) for k in KEY)] = r
    return out


def main() -> None:
    names = sorted(os.path.basename(p) for p in glob.glob(f"{NEW}/*.jsonl"))
    ca_d, ea_d, bs_moved, rows = [], [], 0, []
    for n in names:
        o, w = load(OLD, n), load(NEW, n)
        common = set(o) & set(w)
        if not common:
            continue
        ca = [abs(w[k]["CA"] - o[k]["CA"]) for k in common
              if w[k].get("CA") is not None and o[k].get("CA") is not None]
        ea = [abs(w[k]["EA_ensemble"] - o[k]["EA_ensemble"]) for k in common
              if w[k].get("EA_ensemble") is not None and o[k].get("EA_ensemble") is not None]
        ca_d += ca; ea_d += ea
        if ca or ea:
            rows.append((n, len(common), st.mean(ca) if ca else None,
                         max(ca) if ca else None, st.mean(ea) if ea else None,
                         max(ea) if ea else None))
    print(f"{'file':34s} {'cells':>6s} {'CA mean':>8s} {'CA max':>7s} {'EA mean':>8s} {'EA max':>7s}")
    for n, c, cm, cx, em, ex in rows:
        f = lambda v: f"{v:.4f}" if v is not None else "   --   "
        print(f"  {n:32s} {c:6d} {f(cm):>8s} {f(cx):>7s} {f(em):>8s} {f(ex):>7s}")
    print()
    if ca_d:
        print(f"CERTIFIED (CA), cause = seeded init only")
        print(f"  n={len(ca_d)}  mean |delta| {st.mean(ca_d):.4f}  median {st.median(ca_d):.4f}"
              f"  max {max(ca_d):.4f}   unchanged: {sum(1 for d in ca_d if d < 1e-9)}/{len(ca_d)}")
    if ea_d:
        print(f"EMPIRICAL (EA), cause = seeded init AND windowed statistic")
        print(f"  n={len(ea_d)}  mean |delta| {st.mean(ea_d):.4f}  median {st.median(ea_d):.4f}"
              f"  max {max(ea_d):.4f}")


if __name__ == "__main__":
    main()
