#!/usr/bin/env python3
"""PB21b (round tmlr6, post hoc; existing rows only): which class the one-class households hold.

Reads results/pb03_cvm_draws.jsonl (per-draw count of one-class members at k=1: n_B households under 5%
malicious, n_M over 95% malicious, from pb03_cvm.py) and reports, per IoT-23 device-derived level and for the
main 1-3-type grid (e5f, seeds 10-39), the distribution of n_ben and n_mal, how many draws hold more benign-only
than malicious-only households, the draws with 9 or more benign-only households and their observed beta*.

  python3 pb21_oneclass_classes.py RESULTS_DIR OUT_JSON
"""
import json, os, statistics as st, sys

RES, OUT = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(os.path.join(RES, "pb03_cvm_draws.jsonl"))]
out = {}
for s in sorted({r["set"] for r in rows}):
    rs = [r for r in rows if r["set"] == s and r["k"] == 1]
    if not rs:
        continue
    nB = [r["n_B"] for r in rs]; nM = [r["n_M"] for r in rs]
    ge9 = [r for r in rs if r["n_B"] >= 9]
    out[s] = dict(
        draws=len(rs), n_ben_median=st.median(nB), n_ben_mean=st.mean(nB), n_ben_min=min(nB), n_ben_max=max(nB),
        n_mal_median=st.median(nM), n_mal_mean=st.mean(nM), n_mal_min=min(nM), n_mal_max=max(nM),
        draws_ben_more=sum(b > m for b, m in zip(nB, nM)), draws_mal_more=sum(m > b for b, m in zip(nB, nM)),
        one_class_total=sum(nB) + sum(nM), one_class_benign=sum(nB),
        draws_nben_ge9=len(ge9), bstar_obs_nben_ge9=sorted(r["bstar_obs"] for r in ge9),
        bstar_obs_median=st.median(r["bstar_obs"] for r in rs),
        bstar_pred_median=st.median(r["bstar_pred"] for r in rs),
        collapse02_obs=sum(bool(r["collapse02_obs"]) for r in rs))
json.dump(dict(sets=out, rule="one-class: a household's trainable records under 5% (benign-only) or over 95% "
               "(malicious-only) malicious; k=1, N=20", note="post hoc (round tmlr6); no training"),
          open(OUT, "w"), indent=1)
for s, v in out.items():
    if "device" in s and "iot23" in s:
        print(s, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items()})
