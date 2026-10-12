#!/usr/bin/env python3
"""PB16 (post hoc, round tmlr4; mock review M4): split the same-ensemble slack of Table tab:gap into attack
strength, malicious-set selection and the certificate's own slack, from existing data only.

For every row of the same-ensemble grid (IoT-23, IID and device-derived, draws 0-2, k = 1, 2 and sampled
k = 3 with K = 500, three random malicious sets per budget; results/r6_nan_fix/corrected/e2_*.jsonl) and the
PB10 exact worst case of the same ensemble (results/pb10/*.json):
  EA5 - CA = (EA5 - W_set)   attack strength: five published attacks against the worst behaviour (every touched
                             member votes the wrong class) on the SAME random malicious set
           + (W_set - W_all) set selection: worst behaviour on that set against the worst set of the same size
           + (W_all - CA)    the certificate's slack against its exact worst case.
EA5 is the minimum over the five attacks at the final round, as in tab:gap. Writes results/pb16_slack_split.json."""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

rows = [r for f in sorted(glob.glob(os.path.join(C.REPO, "results/r6_nan_fix/corrected/e2_*.jsonl")))
        for r in C.load_rows(f)]
wc = {}
for f in glob.glob(os.path.join(C.OUTDIR, "pb10", "*.json")):
    d = json.load(open(f))
    if d["seed"] in (0, 1, 2) and (d["k"] in (1, 2) or d["K"] == 500):
        for r in d["rows"]:
            wc[(d["kind"], d["seed"], d["k"], round(r["beta"], 2))] = r
cells = {}
neg = 0
for r in rows:
    if not r.get("EA_final_round") or not r.get("combinatorially_possible"):
        continue
    key = (r["partition_type"], r["partition_seed"], r["k"], round(r["beta"], 2))
    w = wc.get(key)
    if w is None or r["mal_seed"] not in (0, 1, 2):
        continue
    ea5 = min(r["EA_final_round"].values())
    ws, wb, ca = w["M1_paperB"][r["mal_seed"]], w["M1_best"], r["CA"]
    if ea5 < ws - 1e-6:
        neg += 1
    c = cells.setdefault(f"{r['partition_type']}|k{r['k']}|b{round(r['beta'], 2):g}", dict(total=[], attack=[], set=[], cert=[]))
    c["total"].append(ea5 - ca); c["attack"].append(ea5 - ws); c["set"].append(ws - wb); c["cert"].append(wb - ca)
out = dict(note="post hoc; medians over the rows of each cell (3 draws x 3 malicious sets); medians need not add",
           rows_where_attacks_beat_worst_behaviour_on_the_same_set=neg, cells={})
for k, c in sorted(cells.items()):
    out["cells"][k] = dict(n=len(c["total"]), **{f"{x}_median": float(np.median(c[x])) for x in c},
                           **{f"{x}_mean": float(np.mean(c[x])) for x in c})
C.dump("pb16_slack_split.json", out)
for k, v in out["cells"].items():
    if v["n"]:
        print(f"{k:28s} n={v['n']} total {v['total_median']:.4f} = attack {v['attack_median']:.4f} + set {v['set_median']:.4f} + cert {v['cert_median']:.4f}   (means {v['total_mean']:.4f} = {v['attack_mean']:.4f}+{v['set_mean']:.4f}+{v['cert_mean']:.4f})")
print("rows where the published attacks went below the worst behaviour on the same set:", neg)
