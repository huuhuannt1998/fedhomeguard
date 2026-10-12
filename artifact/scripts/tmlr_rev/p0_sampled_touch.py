#!/usr/bin/env python3
"""Re-derive the appendix claim 'at k=5, m=2, K=200 the touched fraction averages 0.539 (0.488 at
K=1000), population 0.447' by simulation over 40 random draws per K (the original script is lost)."""
import math, sys, os, json
from itertools import combinations
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
N, k, m = 20, 5, 2
allc = np.array(list(combinations(range(N), k)))
pairs = list(combinations(range(N), m))
out = {}
for K in (200, 500, 1000):
    vals = []
    for d in range(40):
        sel = allc[np.random.default_rng(d).choice(len(allc), K, replace=False)]
        inc = np.zeros((K, N), bool); np.put_along_axis(inc, sel, True, axis=1)
        best = max(int((inc[:, list(p)].any(1)).sum()) for p in pairs)
        vals.append(best / K)
    out[K] = dict(mean=float(np.mean(vals)), min=float(np.min(vals)), max=float(np.max(vals)),
                  frac_above_population=float(np.mean(np.array(vals) > 1 - math.comb(18, 5) / math.comb(20, 5))))
out["population"] = 1 - math.comb(18, 5) / math.comb(20, 5)
C.dump("p0_sampled_touch.json", out); print(json.dumps(out, indent=1))
