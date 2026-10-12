#!/usr/bin/env python3
"""E7 -- which component of heterogeneity breaks small-k certification.

Two controlled families sweep the same concentration grid: device-Dirichlet
allocates each DEVICE's records across clients, label-Dirichlet allocates each
CLASS's records. Comparing them at matched realised skew isolates the component.

Round tmlr4 (2026-10-10): the device and label rows come from the predeclared PB13 runs
(results/tmlr_rev/pb13_15_rows.jsonl; predeclarations/tmlr_PB13_dirichlet_30draws.md), 30
independent draws per family and concentration at k=1; the volume rows stay the 3-draw e7 runs.
A column gives the number of draws per row.
"""
import collections, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load

from _manuscript import GENERATED as OUT  # TMLR generated/ (FHG_GENERATED overrides)
# review D1 (F-09): the share of nearly one-class clients per partition, read from the
# instrument audit, which rebuilt these same partitions (S_JS identical per draw).
FAMILY_IN_AUDIT = {"device": "dirichlet_device", "label": "dirichlet", "volume": "volume"}


def frac_degen_median(fam, alpha, path="results/analysis/instruments.jsonl"):
    v = [r["frac_degenerate"] for r in (json.loads(l) for l in open(path))
         if r["dataset"] == "iot23" and r["family"] == FAMILY_IN_AUDIT[fam]
         and r["k"] == 1 and r["alpha"] == alpha]
    return float(np.median(v)) if v else float("nan")


def summarise(path, k=1):
    r = [x for x in load(path) if x["k"] == k]
    by = collections.defaultdict(list)
    for x in r:
        by[x["dirichlet_alpha"]].append(x)
    out = []
    for a, v in sorted(by.items(), key=lambda z: -(z[0] or 0)):
        seeds = {x["partition_seed"] for x in v}
        bstar = np.median([max([y["beta"] for y in v
                                if y["partition_seed"] == s and y["CA"] > y["tau_triv"]] + [0.0])
                           for s in seeds])
        out.append(dict(alpha=a,
                        S_JS=float(np.mean([x["S_JS"] for x in v])),
                        S_dev=float(np.mean([x["S_dev"] or 0.0 for x in v])),
                        margin=float(np.median([x["mean_vote_margin"] for x in v])),
                        ens=float(np.median([x["clean_ensemble_acc"] for x in v])),
                        bstar=float(bstar),
                        # round tmlr2 (2026-10-10): members of clients with fewer than 16 training
                        # rows are not trained, so K can fall below N; the table shows its range.
                        K=sorted({int(x["K"]) for x in v})))
    return out


def summarise_pb13(family, path="results/tmlr_rev/pb13_15_rows.jsonl"):
    """PB13 rows of one family ('dirichlet' = label, 'dirichlet_device' = device), per alpha."""
    rows = [r for r in (json.loads(l) for l in open(path) if l.strip()) if r["pb"] == 13 and r["family"] == family]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["alpha"]].append(r)
    out = []
    for a, v in sorted(by.items(), key=lambda z: -z[0]):
        out.append(dict(alpha=a, n=len(v),
                        S_JS=float(np.mean([r["partition"]["S_JS"] for r in v])),
                        S_dev=float(np.mean([r["partition"]["S_dev"] for r in v])),
                        fd=float(np.median([r["partition"]["frac_degenerate"] for r in v])),
                        margin=float(np.median([r["mean_margin"] for r in v])),
                        ens=float("nan"),
                        bstar=float(np.median([r["beta_star"] for r in v])),
                        K=sorted({int(r["K"]) for r in v})))
    return out


def main():
    # review D2 (N-02): the device and label families come from the fine-grid re-run of the
    # same partitions (e7f_*: beta 0 to 0.50 in steps of 0.05, as the volume family and every
    # other beta* in the paper). The coarse e7_* grid stopped at 0.40, below the 0.450 ceiling,
    # so a draw at the ceiling printed as 0.400. S_JS, S_dev and margin are identical in both.
    dev = summarise_pb13("dirichlet_device")
    lab = summarise_pb13("dirichlet")
    vol = (summarise("results/canonical/e7_volskew.jsonl")
           if os.path.exists("results/canonical/e7_volskew.jsonl") else [])
    if not dev or not lab:
        print("e7 incomplete"); return
    for e in vol:
        e["n"] = len({x["partition_seed"] for x in load("results/canonical/e7_volskew.jsonl")
                      if x["k"] == 1 and x["dirichlet_alpha"] == e["alpha"]})
        e["fd"] = frac_degen_median("volume", e["alpha"])

    rows = ["% GENERATED -- do not edit", "\\begin{tabular}{lcccccccc}", "\\toprule",
            "Family & $\\alpha$ & draws & $K$ & $S_{\\mathrm{JS}}$ & $S_{\\mathrm{dev}}$ & "
            "$\\mathrm{fracDegen}$ & margin & $\\beta^{*}$ \\\\", "\\midrule"]
    # concentrations at or above 3 are near-uniform in both families and add nothing
    KEEP = {1.0, 0.5, 0.2, 0.1}
    fams = [("device", dev), ("label", lab)] + ([("volume", vol)] if vol else [])
    for lab_name, tab in fams:
        for e in [x for x in tab if x["alpha"] in KEEP]:
            kr = e["K"]
            kcol = f"{kr[0]}" if len(kr) == 1 else f"{kr[0]}--{kr[-1]}"
            rows.append(f"{lab_name} & {e['alpha']:g} & {e['n']} & {kcol} & {e['S_JS']:.3f} & "
                        f"{e['S_dev']:.3f} & {e['fd']:.2f} & "
                        f"{e['margin']:.3f} & {e['bstar']:.3f} \\\\")
        rows.append("\\midrule")
    rows = rows[:-1] + ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_ablation.tex"), "w").write("\n".join(rows) + "\n")

    # closest matched pair on S_JS, and the highest-skew device point
    pair = min(((d, l) for d in dev for l in lab),
               key=lambda p: abs(p[0]["S_JS"] - p[1]["S_JS"]) - 0.5 * min(p[0]["S_JS"], p[1]["S_JS"]))
    best = max((d for d in dev), key=lambda d: d["S_JS"])
    worst = min((l for l in lab), key=lambda l: l["margin"])
    if vol:
        vlo = min(vol, key=lambda e: e["margin"])
        m_vol = dict(abVolWorstSJS=f"{vlo['S_JS']:.3f}",
                     abVolWorstMargin=f"{vlo['margin']:.3f}",
                     abVolWorstBstar=f"{vlo['bstar']:.3f}",
                     abVolMinMargin=f"{min(e['margin'] for e in vol):.3f}")
    else:
        m_vol = {}
    m = dict(abDevSJS=f"{pair[0]['S_JS']:.3f}", abLabSJS=f"{pair[1]['S_JS']:.3f}",
             abDevMargin=f"{pair[0]['margin']:.3f}", abLabMargin=f"{pair[1]['margin']:.3f}",
             abDevBstar=f"{pair[0]['bstar']:.3f}", abLabBstar=f"{pair[1]['bstar']:.3f}",
             abDevTopSJS=f"{best['S_JS']:.3f}", abDevTopMargin=f"{best['margin']:.3f}",
             abDevTopBstar=f"{best['bstar']:.3f}",
             abLabWorstSJS=f"{worst['S_JS']:.3f}", abLabWorstMargin=f"{worst['margin']:.3f}",
             **m_vol)
    mac = ["% GENERATED -- do not edit"] + \
          [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in m.items()]
    open(os.path.join(OUT, "ablation_macros.tex"), "w").write("\n".join(mac) + "\n")
    print("wrote tab_ablation.tex, ablation_macros.tex")
    print(f"  matched pair: device S_JS={m['abDevSJS']} margin={m['abDevMargin']} "
          f"| label S_JS={m['abLabSJS']} margin={m['abLabMargin']}")


if __name__ == "__main__":
    main()
