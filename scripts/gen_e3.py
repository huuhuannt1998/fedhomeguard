#!/usr/bin/env python3
"""Generate the E3 method-gap paragraph and table.

G_method = EA_best-in-hindsight robust aggregation  -  EA_certifiable ensemble.
Different predictors, so this is the COST OF CERTIFIABILITY, never certificate slack.
"""
import collections, glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load, gap_table

OUT = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"
BET = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]


def main():
    d = [json.loads(l) for f in glob.glob("results/canonical/e3_*.jsonl")
         for l in open(f) if l.strip()]
    if not d:
        print("no e3 rows yet"); return
    gt = gap_table(load("results/canonical/e2_*.jsonl"))
    ks = sorted({k for (_, k, _) in gt})

    worst = {}
    for r in d:
        key = (r["partition_type"], r["partition_seed"], round(r["beta"], 4),
               r["mal_seed"], r["defense"])
        if key not in worst or r["EA"] < worst[key]["EA"]:
            worst[key] = r

    rows = ["% GENERATED -- do not edit", "\\begin{tabular}{llccc}", "\\toprule",
            "Partition & $\\beta$ & oracle envelope & best certifiable & "
            "$G_{\\mathrm{method}}$ \\\\", "\\midrule"]
    lines, macros = [], {}
    for p, lab in (("iid", "IID"), ("device_derived", "Device")):
        for b in BET:
            dep = [v for k, v in worst.items()
                   if k[0] == p and abs(k[2] - b) < 1e-9 and v["observability"] in ("L0", "L1")]
            if not dep:
                continue
            by = collections.defaultdict(list)
            for v in dep:
                by[(v["partition_seed"], v["mal_seed"])].append(v["EA"])
            env = float(np.median([max(x) for x in by.values()]))
            # best certifiable ensemble over k, restricted to cells that certify
            cands = [gt[(p, k, round(b, 4))]["EA_ens"]["median"] for k in ks
                     if (p, k, round(b, 4)) in gt
                     and gt[(p, k, round(b, 4))]["possible"]
                     and gt[(p, k, round(b, 4))]["EA_ens"]["median"] is not None]
            if not cands:
                rows.append(f"{lab} & {b:.2f} & {env:.4f} & \\textit{{none certifies}} & --- \\\\")
                continue
            ens = max(cands)
            rows.append(f"{lab} & {b:.2f} & {env:.4f} & {ens:.4f} & {env - ens:+.4f} \\\\")
            macros[f"GM{'IID' if p == 'iid' else 'DEV'}b{int(round(b*100))}"] = f"{env-ens:+.4f}"
        rows.append("\\midrule")
    rows = rows[:-1] + ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_method.tex"), "w").write("\n".join(rows) + "\n")

    mac = ["% GENERATED -- do not edit"]
    for k, v in sorted(macros.items()):
        mac.append("\\expandafter\\newcommand\\csname %s\\endcsname{%s}" % (k, v))
    for sfx in ("IID", "DEV"):
        mac.append("\\newcommand{\\GM%s}[1]{\\ifcsname GM%sb#1\\endcsname"
                   "\\csname GM%sb#1\\endcsname\\else\\textbf{??}\\fi}" % (sfx, sfx, sfx))
    open(os.path.join(OUT, "method_macros.tex"), "w").write("\n".join(mac) + "\n")

    para = r"""% GENERATED -- do not edit
Table~\ref{tab:method} prices certifiability against that envelope. Under IID it
costs nothing: the best deployable aggregation rule and the best certifiable
ensemble are within a few ten-thousandths of each other at every fraction where
certification is possible, so an operator who switches to the certifiable
construction gives up no measurable empirical robustness and gains a guarantee.
Under device-derived skew the picture inverts. The certifiable construction is the
one that suffers from heterogeneity, so moving to it costs real accuracy, and the
cost grows with the malicious fraction because the subsample size that would restore
competence is the one the ceiling has already forbidden.

\begin{table}[t]
\centering
\caption{Cost of certifiability. The oracle envelope is the strongest deployable
$L_0$/$L_1$ rule per cell, selected after observing test outcomes; the certifiable
column is the best-performing ensemble over subsample sizes that still certify.
Positive $G_{\mathrm{method}}$ means certifiability costs empirical accuracy.}
\label{tab:method}
\footnotesize
\resizebox{\columnwidth}{!}{%
\input{generated/tab_method}}
\end{table}
"""
    open(os.path.join(OUT, "e3_paragraph.tex"), "w").write(para)
    print("wrote tab_method.tex, method_macros.tex, e3_paragraph.tex")
    for r in rows[5:]:
        if "&" in r:
            print("  " + r.replace("\\\\", "").replace("&", "|"))


if __name__ == "__main__":
    main()
