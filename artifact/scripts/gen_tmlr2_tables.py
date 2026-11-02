#!/usr/bin/env python3
"""Tables of the TMLR revision round tmlr2 (2026-10-10): exact worst case, screen baselines, coverage count.

Reads the revision's result files, copied into the repository as results/tmlr_rev/ (their analysis
scripts are in scripts/tmlr_rev/; protocols in predeclarations/tmlr_PB*.md):
  results/tmlr_rev/pb10/*.json          per-ensemble exact worst case (PB10): every touched member
                                        outputs the wrong class, minimised over every malicious set
  results/tmlr_rev/pb08_screen.json     coverage screen against baseline screens (PB08)
  results/tmlr_rev/pb03_cvm_draws.jsonl coverage-vote count against observed beta*, per draw (PB03)
  results/tmlr_rev/pb04_rows.jsonl      controlled partitions (PB04: coverage repair, coverage dial,
                                        volume dial), with the count's prediction per draw
  results/tmlr_rev/pb13_15_rows.jsonl   round tmlr4: PB13 (label- and device-Dirichlet, 30 draws per
                                        concentration, k = 1) and PB14 (coverage dial on N-BaIoT), each
                                        with the count's prediction per draw

Writes (FHG_GENERATED, as every generator; scripts/_manuscript.py):
  tab_worstcase.tex  median slack to the exact worst case per (partition, k, beta) and the largest
                     slack on a draw whose certified accuracy is above tau_triv (Appendix B)
  tab_screen.tex     held-out draws: commitments, unsafe commitments, missed configurations (Appendix C)
  tab_dedup.tex      round tmlr5: certified accuracy, certified detection and the benign certified rate on the
                     8,771 test flows with no identical training feature vector (results/tmlr_rev/pb07a_dedup.json),
                     IID and device-derived, k <= 2, medians over the 30 draws of Table tab:main (Appendix C)
  tab_captures.tex   round tmlr6: the ten IoT-23 captures as used (results/tmlr_rev/pb21_capture_table.json): labelled
                     rows in full and their malicious share, rows read (first 400,000 lines), rows kept (at most
                     60,000, thinned evenly in time order), benign and malicious rows kept, test rows (Appendix D)
  tab_runs.tex       round tmlr6: every draw set the paper reports, with its draws, k, where it is used and whether
                     its test was predeclared or post hoc (Appendix D); a fixed list, no result file
  tab_cvm.tex        accuracy of the coverage count per partition family, k = 1 and k = 2 (Appendix C);
                     round tmlr4 adds the PB13 and PB14 rows and the mean signed error in grid steps
                     (prediction minus observed beta*: positive = the count over-predicts, the unsafe side)

The printed numbers are formatted here only; a proposal that cites them reads them from these files.
"""
import glob
import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _manuscript import GENERATED as OUT  # TMLR generated/ (FHG_GENERATED overrides)

RES = os.path.join("results", "tmlr_rev")
BETAS = (0.05, 0.10, 0.20, 0.30, 0.40)
TAU = 0.729961          # IoT-23 test split's malicious share (tau_triv), as in every result row
STEP = 0.05             # beta grid step (1/N at N = 20)


def f4(x):
    """4 decimals; the 6-decimal rounding of certified accuracy can leave -0.0000, printed as 0.0000."""
    s = f"{x:.4f}"
    return "0.0000" if s == "-0.0000" else s


# ------------------------------------------------------------------ exact worst case (PB10)
WC_ROWS = [("IID", "iid", 1, 20), ("IID", "iid", 2, 190), ("IID", "iid", 3, 500),
           ("Device", "device_derived", 1, 20), ("Device", "device_derived", 2, 190),
           ("Device", "device_derived", 3, 500)]


def worstcase_cells():
    """{(kind, k, K): {"draws": n, "slack": {beta: [per-draw slack]}, "void": {beta}, "max_inf": x}}."""
    out = {}
    for _, kind, k, K in WC_ROWS:
        files = sorted(glob.glob(os.path.join(RES, "pb10", f"iot-23_{kind}_dph1-3_na_s*_k{k}_K{K}.json")))
        c = dict(draws=len(files), slack={b: [] for b in BETAS}, void=set(), max_inf=0.0)
        for f in files:
            d = json.load(open(f))
            for r in d["rows"]:
                b = round(r["beta"], 2)
                if b <= 0:
                    continue
                if not r["certifiable"]:
                    if b in c["slack"]:
                        c["void"].add(b)
                    continue
                s = r["M1_best"] - r["CA"]
                if b in c["slack"]:
                    c["slack"][b].append(s)
                if r["CA"] > TAU:
                    c["max_inf"] = max(c["max_inf"], s)
        out[(kind, k, K)] = c
    return out


def worstcase_three_draws(kind="device_derived", k=1, K=20, beta=0.20):
    """Medians over the three draws (seeds 0-2) of Table tab:gap: certified accuracy, exact worst case
    (every touched member wrong, over every malicious set) and, at k = 1, each malicious household
    flipping its own member's output."""
    rows = []
    for s in (0, 1, 2):
        d = json.load(open(os.path.join(RES, "pb10", f"iot-23_{kind}_dph1-3_na_s{s}_k{k}_K{K}.json")))
        rows += [r for r in d["rows"] if abs(r["beta"] - beta) < 1e-9]
    med = lambda key: float(np.median([r[key] for r in rows]))  # noqa: E731
    return dict(CA=med("CA"), worst=med("M1_best"), flip_own=med("M2_best") if "M2_best" in rows[0] else None)


def tab_worstcase():
    cells = worstcase_cells()
    t = ["% GENERATED by scripts/gen_tmlr2_tables.py -- do not edit",
         "\\begin{tabular}{llc" + "c" * len(BETAS) + "c}", "\\toprule",
         "& & & \\multicolumn{%d}{c}{median slack to the exact worst case, by $\\beta$} & \\\\" % len(BETAS),
         "\\cmidrule(lr){4-%d}" % (3 + len(BETAS)),
         "Partition & $k$ & draws & " + " & ".join(f"{b:.2f}" for b in BETAS) + " & max \\\\", "\\midrule"]
    for i, (lab, kind, k, K) in enumerate(WC_ROWS):
        c = cells[(kind, k, K)]
        vals = []
        for b in BETAS:
            if b in c["void"] and not c["slack"][b]:
                vals.append("\\textit{void}")
            else:
                vals.append(f4(float(np.median(c["slack"][b]))))
        t.append(f"{lab} & {k} & {c['draws']} & " + " & ".join(vals) + f" & {f4(c['max_inf'])} \\\\")
        if i == 2:
            t.append("\\midrule")
    t += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(t) + "\n"


# ------------------------------------------------------------------ screen baselines (PB08)
SCREENS = [  # (key in pb08_screen.json, label, uses labels?, threshold format)
    ("cov_paper_1.05", "coverage screen, factor fixed in advance", "no", "{:.2f}"),
    ("cov_fitted", "coverage screen, factor fitted", "no", "{:.2f}"),
    ("geo", "ceiling only", "no", None),
    ("div_fitted", "$S_{\\mathrm{JS}}$ at most a fitted threshold", "no", "{:.5f}"),
    ("vol_fitted", "$\\mathrm{minSizeShare}$ at least a fitted threshold", "no", "{:.2f}"),
    ("labsup_fitted", "$\\mathrm{minClassSup}$ at least a fitted threshold", "yes", "{:.2f}"),
    ("labdeg_fitted", "$\\mathrm{fracDegen}$ at most a fitted threshold", "yes", "{:.2f}"),
    ("refuse", "always refuse", "no", None),
]


def tab_screen():
    d = json.load(open(os.path.join(RES, "pb08_screen.json")))
    t = ["% GENERATED by scripts/gen_tmlr2_tables.py -- do not edit",
         "\\begin{tabular}{lcccccc}", "\\toprule",
         "Screen & labels & threshold & commitments & unsafe & missed & draws with unsafe \\\\", "\\midrule"]
    for key, lab, labels, fmt in SCREENS:
        s = d["screens"][key]
        h = s["heldout"]
        thr = "--" if fmt is None or s.get("threshold") is None else fmt.format(s["threshold"])
        t.append(f"{lab} & {labels} & {thr} & {h['commitments']} & {h['unsafe']} & "
                 f"{h['missed_opportunities']} & {h['draws_with_unsafe']} \\\\")
    t += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(t) + "\n"


def screen_heldout_summary():
    d = json.load(open(os.path.join(RES, "pb08_screen.json")))
    h = d["screens"]["cov_paper_1.05"]["heldout"]
    return dict(cells=h["cells"], draws=h["draws"], heldout_per_partition=len(d["heldout_seeds"]))


# ------------------------------------------------------------------ coverage count (PB03, PB04)
def _score(pairs):
    """pairs: [(predicted beta*, observed beta*)] -> (n, exact, within one step, mean signed error in steps,
    Spearman or None)."""
    if not pairs:
        return (0, None, None, None, None)
    pp = np.array([p for p, _ in pairs]); po = np.array([o for _, o in pairs])
    e = np.round((pp - po) / STEP)
    rho = float(spearmanr(pp, po).statistic) if len(set(po)) > 1 and len(set(pp)) > 1 else None
    return (len(pairs), float((e == 0).mean()), float((abs(e) <= 1).mean()), float(e.mean()), rho)


def cvm_groups():
    draws = [json.loads(l) for l in open(os.path.join(RES, "pb03_cvm_draws.jsonl")) if l.strip()]
    pb04 = [json.loads(l) for l in open(os.path.join(RES, "pb04_rows.jsonl")) if l.strip()]

    def sel(k, pred):
        return [(r["bstar_pred"], r["bstar_obs"]) for r in draws if r["k"] == k and pred(r)]

    def dev_unique(k):
        # the 1-3 level of the device-type sweep shares 20 draws with the main grid: count each once
        seen, out = set(), []
        for r in draws:
            if r["dataset"] == "iot-23" and r["kind"] == "device_derived" and r["k"] == k:
                key = (tuple(r["dph"]), r["seed"])
                if key not in seen:
                    seen.add(key); out.append((r["bstar_pred"], r["bstar_obs"]))
        return out

    def p4(arm, k):
        return [(r["cvm_pred"], r["beta_star"]) for r in pb04 if r["arm"] == arm and r["k"] == k]

    pb1314 = [json.loads(l) for l in open(os.path.join(RES, "pb13_15_rows.jsonl")) if l.strip()]

    def p13(family, k):
        return [(r["cvm_pred"], r["beta_star"]) for r in pb1314
                if r["pb"] == 13 and r["family"] == family and r["k"] == k]

    def p14(k):
        return [(r["cvm_pred"], r["beta_star"]) for r in pb1314 if r["pb"] == 14 and r["k"] == k]

    G = [
        ("IoT-23, IID", lambda k: sel(k, lambda r: r["set"] == "iot23 IID")),
        ("IoT-23, device-derived (five device-type levels)", dev_unique),
        ("IoT-23, label-Dirichlet, 3 draws per $\\alpha$", lambda k: sel(k, lambda r: r["set"] == "iot23 label-Dirichlet fine")),
        ("IoT-23, device-Dirichlet, 3 draws per $\\alpha$", lambda k: sel(k, lambda r: r["set"] == "iot23 device-Dirichlet fine")),
        ("IoT-23, label-Dirichlet, 30 draws per $\\alpha$", lambda k: p13("dirichlet", k)),
        ("IoT-23, device-Dirichlet, 30 draws per $\\alpha$", lambda k: p13("dirichlet_device", k)),
        ("IoT-23, Dirichlet with $\\alpha \\ge 3$", lambda k: sel(k, lambda r: "coarse" in r["set"])),
        ("IoT-23, volume skew", lambda k: sel(k, lambda r: r["set"] == "iot23 volume")),
        ("N-BaIoT, IID and device-derived", lambda k: sel(k, lambda r: r["dataset"] == "n-baiot")),
        ("controlled: coverage dial", lambda k: p4("b", k)),
        ("controlled: coverage dial, N-BaIoT", p14),
        ("controlled: coverage repair", lambda k: p4("a", k)),
        ("controlled: volume dial", lambda k: p4("c", k)),
    ]
    return [(lab, _score(fn(1)), _score(fn(2))) for lab, fn in G]


def tab_cvm():
    fx = lambda x: "--" if x is None else (f"$-${-x:.3f}" if x < 0 else f"{x:.3f}")  # noqa: E731
    fs = lambda x: "--" if x is None else (f"$-${-x:.2f}" if x < -0.005 else f"$+${x:.2f}")  # noqa: E731
    t = ["% GENERATED by scripts/gen_tmlr2_tables.py -- do not edit",
         "\\begin{tabular}{lcccccccccc}", "\\toprule",
         "& \\multicolumn{5}{c}{$k=1$} & \\multicolumn{5}{c}{$k=2$} \\\\",
         "\\cmidrule(lr){2-6}\\cmidrule(lr){7-11}",
         "Partitions & draws & exact & within one & error & $\\rho$ & draws & exact & within one & error & $\\rho$ \\\\",
         "\\midrule"]
    groups = cvm_groups()
    first_controlled = next(i for i, g in enumerate(groups) if g[0].startswith("controlled"))
    for i, (lab, s1, s2) in enumerate(groups):
        if i == first_controlled:
            t.append("\\midrule")
        cols = []
        for (n, ex, w1, err, rho) in (s1, s2):
            cols += ["--"] * 5 if n == 0 else [str(n), fx(ex), fx(w1), fs(err), fx(rho)]
        t.append(f"{lab} & " + " & ".join(cols) + " \\\\")
    t += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(t) + "\n"


# ------------------------------------------------------------------ deduplicated test subset (PB07a), round tmlr5
def tab_dedup():
    d = json.load(open(os.path.join(RES, "pb07a_dedup.json")))
    ens = [e for e in d["ensembles"] if e["k"] in (1, 2) and 10 <= e["seed"] <= 39]
    cell = {}
    for e in ens:
        for g in e["grid"]:
            cell.setdefault((e["kind"], e["k"], round(g["beta"], 2)), []).append(g)
    t = ["% GENERATED by scripts/gen_tmlr2_tables.py -- do not edit",
         "\\begin{tabular}{llcccccc}", "\\toprule",
         "& & \\multicolumn{2}{c}{certified accuracy} & \\multicolumn{2}{c}{certified detection} & "
         "\\multicolumn{2}{c}{benign certified rate} \\\\",
         "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\\cmidrule(lr){7-8}",
         "$k$ & $\\beta$ & IID & device-derived [IQR] & IID & device-derived & IID & device-derived \\\\", "\\midrule"]
    for i, k in enumerate((1, 2)):
        if i:
            t.append("\\midrule")
        for b in (0.0, 0.05, 0.10, 0.20, 0.30, 0.40):
            row = [str(k), f"{b:.2f}"]
            for kind in ("iid", "device_derived"):
                v = cell[(kind, k, b)]
                assert len(v) == 30, (kind, k, b, len(v))
            ca = {kind: np.array([g["CA_dedup"] for g in cell[(kind, k, b)]]) for kind in ("iid", "device_derived")}
            dv = ca["device_derived"]
            row += [f4(np.median(ca["iid"])),
                    f4(np.median(dv)) + ("" if np.median(dv) == 0 and np.percentile(dv, 75) == 0
                                         else f" [{np.percentile(dv, 25):.2f}, {np.percentile(dv, 75):.2f}]")]
            for key in ("CTR_mal_dedup", "CTR_ben_dedup"):
                row += [f4(np.median([g[key] for g in cell[(kind, k, b)]])) for kind in ("iid", "device_derived")]
            t.append(" & ".join(row) + " \\\\")
    t += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(t) + "\n"


def tab_captures():
    d = json.load(open(os.path.join(RES, "pb21_capture_table.json")))
    order = lambda r: (r["capture"].startswith("CTU-Honeypot"), int(r["capture"].split("-")[-2]))  # noqa: E731
    src = {"Philips-Hue-Bridge": "Philips Hue (honeypot)", "Amazon-Echo": "Amazon Echo (honeypot)"}
    n = lambda x: f"{x:,}"  # noqa: E731
    t = ["% GENERATED by scripts/gen_tmlr2_tables.py -- do not edit",
         "\\begin{tabular}{llrcrrrrr}", "\\toprule",
         "& & \\multicolumn{2}{c}{whole capture} & & \\multicolumn{3}{c}{kept} & \\\\",
         "\\cmidrule(lr){3-4}\\cmidrule(lr){6-8}",
         "Capture & source & rows & malicious & rows read & rows & benign & malicious & test rows \\\\", "\\midrule"]
    for r in sorted(d["captures"], key=order):
        name = r["capture"].replace("CTU-IoT-", "").replace("CTU-", "")
        t.append(" & ".join([name, src.get(r["device"], "malware run"), n(r["full_rows"]), f"{r['full_mal_share']:.3f}",
                             n(r["read_rows"]), n(r["kept_rows"]), n(r["kept_benign"]), n(r["kept_malicious"]),
                             n(r["test_rows"])]) + " \\\\")
    tot = d["totals"]
    t += ["\\midrule", f"all ten & & & & & {n(tot['kept'])} & & & {n(tot['test'])} \\\\", "\\bottomrule", "\\end{tabular}"]
    return "\n".join(t) + "\n"


T, F, S = "Table~\\ref{tab:%s}", "Figure~\\ref{fig:%s}", "Section~\\ref{sec:%s}"
RUNS = [  # (draw set, draws, k, where the paper uses it, status of its test); references resolve at build time
    ("Main grid: IoT-23 IID and device-derived (1--3 types)", "30 each (seeds 10--39)", "1, 2",
     "Tables~\\ref{tab:main}, \\ref{tab:collapse}, \\ref{tab:ids}, \\ref{tab:dedup}, \\ref{tab:screen}", "design"),
    ("Same-ensemble grid", "3 (seeds 0--2), 3 malicious sets each", "1, 2, 3 ($K=500$)",
     "Tables~\\ref{tab:slackdecomp}, \\ref{tab:gap}; " + F % "sameens", "design"),
    ("Exact worst case", "33 (the two above)", "1, 2; 3 over 3", T % "worstcase", "predeclared"),
    ("Larger $k$", "3", "3 ($K=1{,}140$); 5, 8 ($K=200$)", F % "teaser", "design"),
    ("Device types per household, IoT-23 and N-BaIoT", "30 per level, 5 levels", "1, 2",
     T % "richness" + "; " + S % "S7", "predeclared ($k=2$; N-BaIoT)"),
    ("N-BaIoT, IID and device-derived (1--2 types)", "30 each; earlier 5 each on five devices", "1, 2",
     T % "crossdataset" + "; " + F % "coverage", "predeclared ($k=1$)"),
    ("Dirichlet and volume-skew audit", "3 per $\\alpha$: 12 label, 12 device, 18 at $\\alpha \\ge 3$, 15 volume",
     "1, 2", "Tables~\\ref{tab:instruments}, \\ref{tab:cvm}", "design"),
    ("Dirichlet families, 30 draws", "30 per $\\alpha$, 4 $\\alpha$ per family (seeds 100--129)", "1",
     T % "ablation" + "; " + S % "S6", "predeclared; closest pair, clustered errors and $K=20$ restriction post hoc"),
    ("Coverage dial", "90 IoT-23 (45 at $k=2$), 30 N-BaIoT", "1, 2", S % "S6" + "; " + T % "cvm", "predeclared"),
    ("Coverage repair", "30 (seeds 10--39; 10 at $k=2$)", "1, 2", S % "S6" + "; " + T % "cvm",
     "predeclared; paired test post hoc"),
    ("Volume dial, fixed and scaled step budget", "70 each (7 sizes, seeds 0--9)", "1", S % "S6", "predeclared"),
    ("Standardization rerun", "10 per cell", "1, 2", S % "S3" + "; Appendix~\\ref{sec:D}",
     "predeclared; floored sample post hoc"),
    ("Statistic audit", "159 draws, 318 cells", "1, 2", T % "instruments" + "; " + S % "S6",
     "predeclared $R^2$; in-fold threshold post hoc"),
    ("Screen scoring", "660 cells (30 draws, 2 partitions, 11 budgets), split 15/15", "chosen from 1, 2",
     S % "S8" + "; " + T % "screen", "predeclared baselines"),
    ("Deduplicated test subset", "the 30 main-grid draws, re-scored", "1, 2", T % "dedup", "predeclared"),
    ("Pairing at $k=2$", "30 (seeds 10--39)", "2", "Appendix~\\ref{sec:C}", "predeclared"),
    ("8-class control", "30, one malicious set each", "1, 2", S % "S5" + "; Appendix~\\ref{sec:C}", "design"),
    ("1\\% prior re-weighting", "main grid and sampled $k=3$ arm", "1, 2, 3", S % "S5", "post hoc"),
    ("Brute-force check", "1,181 synthetic points; 36 trained ensembles", "1 to 8",
     S % "S3" + "; Appendix~\\ref{sec:A}", "design"),
    ("Leave one capture out", "10 folds", "1", S % "S10" + "; Appendix~\\ref{sec:C}", "design"),
    # JISA re-scoring of stored rows (rounds jisa2 and jisa4; AutoResearchClaw f1: keep the inventory level with the text)
    ("Re-scorings: sizes, count per level, priors, prior-free $\\beta^{*}$", "the draw sets above", "1, 2",
     S % "S5" + ", " + S % "S6", "post hoc"),
    # JISA training round (round jisa5, 2026-11-01): predeclared runs of 2026-10-20
    ("Member seeds 1--4: main grid and coverage repair", "30 per seed each (seeds 10--39)", "1, 2 (repair 1)",
     S % "S6" + ", " + S % "S10", "predeclared; all predictions held"),
    ("Equal step budget: main grid and coverage repair", "30 each (seeds 10--39)", "1", S % "S6", "predeclared; all predictions held"),
    ("8-class control, device-derived; per-family re-run", "30, one malicious set each", "1, 2 (re-run 1)",
     "Appendix~\\ref{sec:C}", "predeclared; one prediction failed"),
    ("Federation size $N=10$ and $N=50$", "30 each (seeds 10--39)", "1 (IID 2 at $N=10$)", S % "S10",
     "predeclared; one prediction failed"),
    ("Member with 9.1 times the parameters", "30 each (seeds 10--39)", "1", S % "S10", "predeclared; two predictions failed"),
    ("CIC IoT-IDAD 2024, victim side", "30 IID, 60 device-derived (seeds 10--39)", "1, 2",
     S % "S6" + "; Appendix~\\ref{sec:D}", "predeclared; the count's prediction failed"),
]


def tab_runs():
    rr = "\\raggedright "
    t = ["% GENERATED by scripts/gen_tmlr2_tables.py -- do not edit",
         "\\begin{tabular}{p{4.2cm}p{4.4cm}p{2.4cm}p{3.6cm}p{2.6cm}}", "\\toprule",
         "Draw set & draws & $k$ & used in & status \\tabularnewline", "\\midrule"]
    t += [" & ".join(rr + c for c in r) + " \\tabularnewline" for r in RUNS]
    t += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(t) + "\n"


def build():
    return {"tab_worstcase.tex": tab_worstcase(), "tab_screen.tex": tab_screen(), "tab_cvm.tex": tab_cvm(),
            "tab_dedup.tex": tab_dedup(), "tab_captures.tex": tab_captures(), "tab_runs.tex": tab_runs()}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, tex in build().items():
        with open(os.path.join(OUT, name), "w") as fh:
            fh.write(tex)
        print("wrote", name)


if __name__ == "__main__":
    main()
