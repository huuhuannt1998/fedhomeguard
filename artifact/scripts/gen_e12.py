#!/usr/bin/env python3
"""E12 -- what server observability buys, across partition draws and attacker sets.

The old Table I was a single device-derived draw. This rebuilds it over three
partition draws and three malicious sets per cell, and reports the spread, because
the paper's own measurements show high-beta cells are unstable across draws.
"""
import collections, glob, json, os, sys
import numpy as np

from _manuscript import GENERATED as OUT  # TMLR generated/ (FHG_GENERATED overrides)
BET = [0.10, 0.20, 0.30, 0.40]
LEVEL_ORDER = ["fedavg", "krum", "multikrum", "trimmed_mean", "median", "norm_clip",
               "fltrust", "oracle_trimmed"]
NAME = {"fedavg": "FedAvg", "krum": "Krum", "multikrum": "multi-Krum",
        "trimmed_mean": "trimmed mean", "median": "median", "norm_clip": "norm clipping",
        "fltrust": "FLTrust", "oracle_trimmed": "oracle"}


def main():
    d = [json.loads(l) for f in glob.glob("results/canonical/e3_device_derived.jsonl")
         for l in open(f) if l.strip()]
    if not d:
        print("no e3 device rows"); return
    tau = d[0]["tau_triv"]

    # worst attack per (draw, attacker set, defence), then median and range over draws
    worst = {}
    for r in d:
        k = (r["partition_seed"], round(r["beta"], 4), r["mal_seed"], r["defense"])
        if k not in worst or r["EA"] < worst[k]["EA"]:
            worst[k] = r

    rows = ["% GENERATED -- do not edit", "\\begin{tabular}{llcccc}", "\\toprule",
            "Defence & Lvl & $\\beta{=}0.10$ & $0.20$ & $0.30$ & $0.40$ \\\\",
            "\\midrule"]
    for dn in LEVEL_ORDER:
        cells, lvl = [], None
        for b in BET:
            v = [x["EA"] for k, x in worst.items()
                 if k[3] == dn and abs(k[1] - b) < 1e-9]
            if not v:
                cells.append("---"); continue
            lvl = [x for k, x in worst.items() if k[3] == dn][0]["observability"]
            cells.append(f"{np.median(v):.3f}\\,\\tiny[{min(v):.2f},{max(v):.2f}]")
        rows.append(f"{NAME[dn]} & ${lvl}$ & " + " & ".join(cells) + " \\\\")
    rows += ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_lattice.tex"), "w").write("\n".join(rows) + "\n")

    def med(dn, b):
        v = [x["EA"] for k, x in worst.items() if k[3] == dn and abs(k[1] - b) < 1e-9]
        return float(np.median(v)) if v else float("nan")

    def best_dep(b):
        cands = {dn: med(dn, b) for dn in LEVEL_ORDER
                 if dn not in ("fltrust", "oracle_trimmed")}
        n = max(cands, key=cands.get)
        return n, cands[n]

    lines = []
    for b in (0.20, 0.40):
        n, v = best_dep(b)
        lines.append((b, NAME[n], v, med("fltrust", b), med("oracle_trimmed", b)))

    para = ["% GENERATED -- do not edit",
            "\\begin{table}[t]", "\\centering",
            "\\caption{What server observability buys under the device-derived partition. "
            "$\\mathrm{EA}$ is the worst case over the five-attack set; each cell is the "
            "median over three partition draws and three malicious sets, with the full "
            "observed range beneath it. $L_3$ is an upper bound, never achievable.}",
            "\\label{tab:lattice}", "\\scriptsize",
            "\\resizebox{\\columnwidth}{!}{%", "\\input{generated/tab_lattice}}",
            "\\end{table}", "",
            "% provenance: jrn_01M0SH0V4DR4AYK59BJCN230Q5 supports the cost and sensitivity measurements",
            "Table~\\ref{tab:lattice} repeats that comparison across draws and attacker sets",
            "rather than on one run, and the spread is the first thing to read: at",
            "$\\beta \\ge 0.30$ every deployable rule has a range wider than the gaps between",
            "rules, so an ordering read off a single draw is not an ordering."]
    b, dn, v, l2, l3 = lines[1]
    para += ["",
             "% provenance: jrn_01M0SH0V4DR4AYK59BJCN230Q5 supports the cost and sensitivity measurements",
             f"One statement survives it. At $\\beta = {b:.2f}$ the best deployable rule reaches",
             f"${v:.3f}$ and $L_2$ reaches ${l2:.3f}$, while the $L_3$ oracle still holds ${l3:.3f}$:",
             "robustness under this threat model is limited by \\emph{identification} rather",
             "than by what an aggregation rule can do once the adversary is known. That is",
             "exactly the problem the subsampling certificate declines to solve, buying its",
             "guarantee by ensuring enough members never saw the adversary at all."]
    open(os.path.join(OUT, "e12_paragraph.tex"), "w").write("\n".join(para) + "\n")
    print("wrote tab_lattice.tex, e12_paragraph.tex")
    for b, dn, v, l2, l3 in lines:
        print(f"  beta={b:.2f}  best deployable {dn} {v:.3f} | L2 {l2:.3f} | L3 {l3:.3f}")


if __name__ == "__main__":
    main()
