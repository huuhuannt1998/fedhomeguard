#!/usr/bin/env python3
"""The one definition of the certified breakdown point.

Two generators computed beta* two different ways and the paper printed both:
gen_paper_numbers took the per-draw breakdown point and then the median across
draws; gen_richness took the median accuracy across draws and then the
breakdown point of that. Those are different statistics (median-of-X vs
X-of-medians -- the same mismatch that broke the CA decomposition), and they
disagreed by a grid step on the paper's headline setting.

beta*(draw) = max{ beta : median_over_malicious_sets CA(draw, beta) > tau_triv }
beta*       = median over draws of beta*(draw)

The per-draw quantity is the deployer's question ("for this federation, how
much hostility does the certificate survive?"), so the aggregation is over
draws, last. Import this; do not re-derive it.
"""
import statistics as st
from collections import defaultdict

__all__ = ["bstar_per_draw", "bstar", "TOL"]
TOL = 1e-9


def bstar_per_draw(rows, tau=None):
    """{partition_seed: beta*} for one (partition_type, k) slice of result rows."""
    if not rows:
        return {}
    if tau is None:
        tau = rows[0]["tau_triv"]
    g = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get("CA") is None:
            continue
        g[r["partition_seed"]][round(r["beta"], 6)].append(r["CA"])
    return {s: max([b for b, ca in gg.items() if st.median(ca) > tau], default=0.0)
            for s, gg in g.items()}


def bstar(rows, tau=None):
    """(median beta*, mean, n, sorted per-draw values) for one slice."""
    per = bstar_per_draw(rows, tau)
    if not per:
        return None, None, 0, []
    v = sorted(per.values())
    return st.median(v), st.mean(v), len(v), v
