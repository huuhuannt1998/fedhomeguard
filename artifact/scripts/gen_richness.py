#!/usr/bin/env python3
"""Macros and table for the household device-richness sweep (review W2 / E1).

The paper's headline collapse was measured at 1-3 device types per household. That
choice is arbitrary, and the sweep shows the collapse is confined to it: at 2-5 types
the partition is still strongly skewed (S_JS 0.67) yet beta* triples and the collapse
rate goes to zero. Reported as a function of richness rather than asserted at a point.
"""
import glob, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bstar import bstar as _bstar
from aggregate import src as _src   # review r6: corrected same-predictor rows

from _manuscript import GENERATED as OUT  # TMLR generated/ (FHG_GENERATED overrides)
ARMS = [("1", "1", "results/canonical/e11b_dph1_1.jsonl"),
        ("13", "1--3", "results/canonical/e11b_dph1_3.jsonl"),
        ("25", "2--5", "results/canonical/e11b_dph2_5.jsonl"),
        ("38", "3--8", "results/canonical/e11b_dph3_8.jsonl"),
        ("510", "5--10", "results/canonical/e11b_dph5_10.jsonl")]

# k=2 and N-BaIoT arms of the same sweep, keyed like ARMS (N-BaIoT's top level is 5-9 types).
K2ARMS = {"1": "results/canonical/e22_k2rich_1_1.jsonl", "13": "results/canonical/e22_k2rich_1_3.jsonl",
          "25": "results/canonical/e22_k2rich_2_5.jsonl", "38": "results/canonical/e22_k2rich_3_8.jsonl",
          "510": "results/canonical/e22_k2rich_5_10.jsonl"}
NBARMS = {"1": "results/canonical/e21_nbrich_1_1.jsonl", "13": "results/canonical/e21_nbrich_1_3.jsonl",
          "25": "results/canonical/e21_nbrich_2_5.jsonl", "38": "results/canonical/e21_nbrich_3_8.jsonl",
          "510": "results/canonical/e21_nbrich_5_9.jsonl"}


# review D1 (F-09): the share of nearly one-class clients per level, from the rebuilt
# partitions (scripts/gen_richness_instruments.py checks S_JS against these rows).
RICH_AUDIT = "results/analysis/richness_instruments.jsonl"
LEVEL = {"1": "1_1", "13": "1_3", "25": "2_5", "38": "3_8", "510": "5_10"}
NB_LEVEL = dict(LEVEL, **{"510": "5_9"})


def _frac_degen(ds, level):
    v = [r["frac_degenerate"] for r in (json.loads(l) for l in open(RICH_AUDIT))
         if r["dataset"] == ds and r["level"] == level]
    return "%.3f" % st.median(v) if v else "---"


def _arm_bstar(pat):
    rs = load(pat) if pat else []
    if not rs:
        return "---"
    b, _m, _n, _v = _bstar(rs, rs[0]["tau_triv"])
    return "%.3f" % (0.0 if b is None else b)


def load(pat):
    r = []
    for f in glob.glob(pat):
        for l in open(f):
            if l.startswith("{"):
                x = json.loads(l)
                if x["partition_type"] == "device_derived":
                    r.append(x)
    return r

mac, rows, tau = [], [], None
for key, lab, pat in ARMS:
    rs = load(pat)
    if not rs:
        continue
    tau = rs[0]["tau_triv"]
    sjs = st.median([r["S_JS"] for r in rs])
    cells = []
    for k in (1, 2):
        s = [r for r in rs if r["k"] == k]
        if not s:
            continue
        marg = st.median([r["mean_vote_margin"] for r in s])
        # canonical estimator (scripts/bstar.py): per-draw breakdown point first,
        # median across draws last. Previously this file took the median accuracy
        # first, which is a different statistic and disagreed with Table 1.
        bstar, _bmean, _bn, _bvals = _bstar(s, tau)
        bstar = 0.0 if bstar is None else bstar
        b20 = [r for r in s if abs(r["beta"] - 0.20) < 1e-9]
        coll = sum(1 for r in b20 if r["CA"] <= tau) / len(b20) if b20 else float("nan")
        cells.append((k, marg, bstar, coll))
        mac.append(("\\expandafter\\newcommand\\csname RICHMARGd%sk%d\\endcsname{%.3f}" % (key, k, marg)))
        mac.append(("\\expandafter\\newcommand\\csname RICHBSTARd%sk%d\\endcsname{%.3f}" % (key, k, bstar)))
        mac.append(("\\expandafter\\newcommand\\csname RICHCOLLd%sk%d\\endcsname{%.2f}" % (key, k, coll)))
    mac.append("\\expandafter\\newcommand\\csname RICHSJSd%s\\endcsname{%.3f}" % (key, sjs))
    c1 = next((c for c in cells if c[0] == 1), None)
    # Stage C (2026-10-02): the e11b arms hold k=1 only, so the old "if c1 and c2" left the
    # table body empty. k=2 comes from its own arm (e22_k2rich_*) and N-BaIoT's k=1 from
    # e21_nbrich_*, both through the same estimator (scripts/bstar.py). Macros are unchanged.
    if c1:
        rows.append("%s & %.3f & %s & %.3f & %.3f & %.2f & %s & %s & %s \\\\"
                    % (lab, sjs, _frac_degen("iot23", LEVEL[key]), c1[1], c1[2], c1[3],
                       _arm_bstar(K2ARMS.get(key)), _frac_degen("nbaiot", NB_LEVEL[key]),
                       _arm_bstar(NBARMS.get(key))))

for name, wrap in (("RICHMARG", 2), ("RICHBSTAR", 2), ("RICHCOLL", 2)):
    mac.append("\\newcommand{\\%s}[2]{\\ifcsname %sd#1k#2\\endcsname"
               "\\csname %sd#1k#2\\endcsname\\else\\textbf{??}\\fi}" % (name, name, name))
# IID reference, so the body can contrast without a hand-typed number
iid = load(_src("e2_iid_*.jsonl"))
if True:
    import glob as _g, json as _j
    vals = []
    for f in _g.glob(_src("e2_iid_*.jsonl")):
        for l in open(f):
            if l.startswith("{"):
                vals.append(_j.loads(l)["S_JS"])
    if vals:
        mac.append("\\newcommand{\\RICHSJSiid}{%.3f}" % st.median(vals))
# second model family: the logistic-regression margin the body quotes
_lg = load("results/canonical/e9_logreg_device_derived.jsonl")
if _lg:
    mac.append("\\newcommand{\\LGMARGONE}{%.3f}"
               % st.median([r["mean_vote_margin"] for r in _lg if r["k"] == 1]))
mac.append("\\newcommand{\\RICHSJS}[1]{\\ifcsname RICHSJSd#1\\endcsname"
           "\\csname RICHSJSd#1\\endcsname\\else\\textbf{??}\\fi}")

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "richness_macros.tex"), "w").write(
    "% GENERATED by scripts/gen_richness.py -- do not edit.\n" + "\n".join(mac) + "\n")
open(os.path.join(OUT, "tab_richness.tex"), "w").write(
    "% GENERATED -- do not edit\n"
    "\\begin{tabular}{lcccccccc}\n\\toprule\n"
    "& \\multicolumn{6}{c}{IoT-23} & \\multicolumn{2}{c}{N-BaIoT} \\\\\n\\cmidrule(lr){2-7}\\cmidrule(lr){8-9}\n"
    "device types & $S_{\\mathrm{JS}}$ & $\\mathrm{fracDegen}$ & margin & $\\beta^{*}$ & collapse & $\\beta^{*}$, $k=2$ & $\\mathrm{fracDegen}$ & $\\beta^{*}$ \\\\\n"
    "\\midrule\n"
    + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
print("wrote richness_macros.tex, tab_richness.tex")
for r in rows:
    print("  " + r.replace("\\\\", ""))
