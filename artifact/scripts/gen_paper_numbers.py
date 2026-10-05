#!/usr/bin/env python3
"""Generate every number, table and macro the manuscript uses, from the canonical
result files. Nothing in the paper is hand-maintained.

Emits into <manuscript>/generated/:
  numbers.tex   \newcommand macros used by the prose (abstract, intro, conclusion)
  numbers.json  the same values, for auditing
  tab_*.tex     the result tables

Exits non-zero if any consistency assertion fails, so a broken build cannot ship.
"""
from __future__ import annotations
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load, gap_table, collapse_stats, assertions, med_iqr, src

MAN = ("manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP")
OUT = os.environ.get("FHG_GENERATED", os.path.join(MAN, "generated"))
BETAS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]


def fmt(x, n=4):
    return "---" if x is None else f"{x:.{n}f}"


def macro(name, val):
    return f"\\newcommand{{\\{name}}}{{{val}}}\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = load(src("e2_*.jsonl"))     # review r6: corrected rows unless FHG_FROZEN=1
    e5 = load("results/canonical/e5_*.jsonl")
    if not rows:
        print("no canonical rows yet"); return 1
    gt = gap_table(rows)
    checks = assertions(rows, gt)
    for c in checks:
        print(f"  {c['verdict']:5s} {c['check']:44s} {c['detail']}")
    if any(c["verdict"] == "FAIL" for c in checks):
        print("ASSERTION FAILURE -- refusing to generate paper numbers")
        return 1

    ks = sorted({r["k"] for r in rows})
    tau = rows[0]["tau_triv"]
    N = rows[0]["N"]
    num, tex = {}, ""

    # ---------------------------------------------------------------- headline macros
    def g(p, k, b, field, stat="median"):
        e = gt.get((p, k, round(b, 4)))
        return None if e is None else e[field][stat] if isinstance(e[field], dict) else e[field]

    iid_slack = [gt[key]["G_cert"]["max"] for key in gt
                 if key[0] == "iid" and gt[key]["possible"] and gt[key]["G_cert"]["n"]]
    dev_slack = [gt[key]["G_cert"]["median"] for key in gt
                 if key[0] == "device_derived" and gt[key]["possible"]
                 and gt[key]["G_cert"]["n"]]
    dev_slack_worst = [gt[key]["G_cert"]["max"] for key in gt
                       if key[0] == "device_derived" and gt[key]["possible"]
                       and gt[key]["G_cert"]["n"]]
    num["GcertIIDmax"] = round(max(iid_slack), 4) if iid_slack else None
    num["GcertDevMedMax"] = round(max(dev_slack), 4) if dev_slack else None
    num["GcertDevWorst"] = round(max(dev_slack_worst), 4) if dev_slack_worst else None
    num["tauTriv"] = round(tau, 4)
    num["Nclients"] = N

    # Indexed values. LaTeX control sequences cannot contain digits, so these are
    # stored under \csname keys and reached through two-argument wrappers, which
    # keeps the prose readable: \CAIID{1}{40}.
    idx = {}
    FIELDS = [("CA", "CA"), ("EA", "EA_ens"), ("G", "G_cert"),
              ("COV", "coverage"), ("CTR", "CTR_mal")]
    for (p_, sfx) in (("iid", "IID"), ("device_derived", "DEV")):
        for k in ks:
            mg = gt.get((p_, k, 0.0))
            if mg:
                idx[f"MARG{sfx}k{k}"] = f"{mg['margin']['median']:.4f}"
            for b in BETAS:
                e = gt.get((p_, k, round(b, 4)))
                if e is None:
                    continue
                bb = int(round(b * 100))
                for pre, fld in FIELDS:
                    v = e[fld]["median"]
                    idx[f"{pre}{sfx}k{k}b{bb}"] = "---" if v is None else f"{v:.4f}"
                idx[f"COLL{sfx}k{k}b{bb}"] = f"{e['collapse_rate']:.2f}"
                idx[f"POSS{sfx}k{k}b{bb}"] = "yes" if e["possible"] else "no"
    num["indexed"] = idx

    # collapse statistics from the wide replication sweep
    coll = {}
    if e5:
        for p_ in ("iid", "device_derived"):
            for k in sorted({r["k"] for r in e5}):
                for b in BETAS:
                    s = collapse_stats(e5, p_, k, b)
                    if s.get("n"):
                        coll[f"{p_}|{k}|{b}"] = s
    num["collapse"] = coll
    # Draws PER PARTITION, not summed across them. Counting (partition_type, seed)
    # pairs double-counted the 30 seeds into 60 and contradicted tab_collapse, whose
    # denominator is 30, and Sec. V, which says "thirty".
    # Measured beta* by k. MUST come from the fine grid: e2_* stops at beta=0.40, so
    # beta* there is right-censored and reports 0.400 for IID where the true value is
    # 0.450 -- one grid step short at every k, contradicting tab_crossdataset and the
    # teaser caption. e5f_* runs to 0.50 over 30 partition draws.
    import statistics as _st
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from bstar import bstar_per_draw as _bstar_per_draw
    # k=1,2 come from e5f (30 draws); k=3 from e2k3full and k=5,8 from e2k58_cert
    # (3 draws each). All four arms run the fine beta grid to 0.50, so none is censored.
    _e5f = (load("results/canonical/e5f_*.jsonl")
            + load("results/canonical/e2k3full_*.jsonl")
            + load("results/canonical/e2k58_cert_*.jsonl"))
    if _e5f:
        _tau = _e5f[0]["tau_triv"]
        # canonical estimator lives in scripts/bstar.py -- one definition, so a
        # second consumer cannot silently compute a different statistic.
        import collections as _c
        _slices = _c.defaultdict(list)
        for r in _e5f:
            _slices[(r["partition_type"], r["k"])].append(r)
        _bs = {}
        for (pp, kk), rs in _slices.items():
            for s_, v_ in _bstar_per_draw(rs, _tau).items():
                _bs[(pp, s_, kk)] = v_
        for p_, tag_ in (("iid", "IID"), ("device_derived", "DEV")):
            for k_ in sorted({k for (pp, _s, k) in _bs if pp == p_}):
                v = [_bs[(pp, s_, kk)] for (pp, s_, kk) in _bs if pp == p_ and kk == k_]
                idx[f"BSTAR{tag_}k{k_}"] = f"{_st.median(v):.3f}"
                idx[f"BSTARMEAN{tag_}k{k_}"] = f"{_st.mean(v):.3f}"
                idx[f"BSTARN{tag_}k{k_}"] = str(len(v))
        # The denominator and the win/loss counts MUST come from one set. e5f numbers
        # its device draws 10..39 while e2k3full and e2k58_cert use 0..2, so the pooled
        # seed union is 33 while the paired k=1-vs-k=2 comparison only exists on e5f's
        # 30. Counting the union here reported "23 of 33" beside a table saying 30.
        _sd = sorted({s_ for (pp, s_, k_) in _bs if pp == "device_derived" and k_ == 1}
                     & {s_ for (pp, s_, k_) in _bs if pp == "device_derived" and k_ == 2})
        _w = sum(1 for s_ in _sd if _bs[("device_derived", s_, 2)]
                                  > _bs[("device_derived", s_, 1)])
        _l = sum(1 for s_ in _sd if _bs[("device_derived", s_, 2)]
                                  < _bs[("device_derived", s_, 1)])
        num["NdrawsFine"] = len(_sd)
        num["BstarPairWin"] = _w
        num["BstarPairTie"] = len(_sd) - _w - _l
        num["BstarPairLoss"] = _l

    num["NdrawsE"] = (max(len({r["partition_seed"] for r in e5
                               if r["partition_type"] == p_})
                          for p_ in {r["partition_type"] for r in e5})
                      if e5 else 0)

    # ------------------------------------------------------------------- numbers.tex
    tex += "% GENERATED by scripts/gen_paper_numbers.py -- do not edit.\n"
    tex += "% Every number the prose quotes is defined here and produced from\n"
    tex += "% results/canonical/*.jsonl through one code path.\n"
    for kk, vv in num.items():
        if isinstance(vv, (int, float)) and not isinstance(vv, bool):
            tex += macro(kk, f"{vv:.4f}" if isinstance(vv, float) else str(vv))
    # certification thresholds 2c_max(m)/K at the fraction Sec. VII discusses, so the
    # margin-vs-threshold comparison there quotes macros rather than typed numbers.
    for r in rows:
        if abs(r["beta"] - 0.20) < 1e-9 and r.get("cert_threshold") is not None:
            tag_ = "IID" if r["partition_type"] == "iid" else "DEV"
            idx.setdefault(f"THR{tag_}k{r['k']}", f"{r['cert_threshold']:.3f}")

    # Decomposition of the device-vs-IID certified-accuracy loss. Because
    # CA = EA - G identically, the loss splits exactly into a competence term
    # (how much worse the predictor is under skew) and a slack term (how much more
    # conservative the certificate is). One estimator throughout, so the rows close.
    import statistics as _s2
    def _md(p_, k_, b_, f_):
        sl = [r for r in rows if r["partition_type"] == p_ and r["k"] == k_
              and abs(r["beta"] - b_) < 1e-9]
        v = ([min(r["EA_final_round"].values()) for r in sl if r.get("EA_final_round")]
             if f_ == "EA" else [r[f_] for r in sl if r.get(f_) is not None])
        return _s2.median(v) if v else None
    def _poss(p_, k_, b_):
        sl = [r for r in rows if r["partition_type"] == p_ and r["k"] == k_
              and abs(r["beta"] - b_) < 1e-9]
        return bool(sl) and all(r.get("combinatorially_possible") for r in sl)
    _tau = rows[0]["tau_triv"]
    _dec, _live, _liveslack, _liveslackG = [], 0, 0, 0
    for k_ in (1, 2, 3):
        for b_ in (0.05, 0.1, 0.2, 0.3, 0.4):
            if not (_poss("iid", k_, b_) and _poss("device_derived", k_, b_)):
                continue
            cai, cad = _md("iid", k_, b_, "CA"), _md("device_derived", k_, b_, "CA")
            eai, ead = _md("iid", k_, b_, "EA"), _md("device_derived", k_, b_, "EA")
            if None in (cai, cad, eai, ead):
                continue
            comp, slack = eai - ead, (ead - cad) - (eai - cai)
            _dec.append((k_, b_, cai - cad, comp, slack, ead))
            idx[f"DECOMPCOMPk{k_}b{int(round(b_*100))}"] = f"{comp:.4f}"
            idx[f"DECOMPSLACKk{k_}b{int(round(b_*100))}"] = f"{slack:.4f}"
            if ead > _tau:                      # the predictor is still informative here
                _live += 1
                _liveslack += slack > comp
                # review r6 item 7: the same count read off Table 2's G column (median of
                # per-draw differences) instead of differences of medians
                _gd = _md("device_derived", k_, b_, "G_cert"); _gi = _md("iid", k_, b_, "G_cert")
                _liveslackG += (_gd - _gi) > comp
    # emitted directly: the scalar loop above has already run by this point
    tex += macro("DecompLive", str(_live))
    tex += macro("DecompLiveSlack", str(_liveslack))
    tex += macro("DecompLiveSlackG", str(_liveslackG))
    tex += macro("DecompCells", str(len(_dec)))

    tex += "\n% indexed values, reached through the wrappers below\n"
    # A cell where certification is combinatorially impossible has CA identically 0,
    # so its "slack" is just the attacked accuracy and means nothing. tab_gap prints
    # such cells as void; the G macro used to hand back a plausible number instead.
    for kk, vv in sorted(idx.items()):
        if kk.startswith("G") and idx.get("POSS" + kk[1:]) == "no":
            vv = "\\textit{void}"
        tex += "\\expandafter\\newcommand\\csname %s\\endcsname{%s}\n" % (kk, vv)
    tex += ("\n% Two-argument wrappers. LaTeX control sequences cannot contain\n"
            "% digits, so indexed values live under \\csname keys and are reached\n"
            "% like \\CAIID{1}{40}: certified accuracy, IID, k=1, beta=0.40.\n"
            "% A cell with no data expands to a visible ?? rather than nothing.\n")
    for pre in ("BSTAR", "BSTARMEAN", "BSTARN", "THR"):
        pass
    for pre in ("DECOMPCOMP", "DECOMPSLACK"):
        tex += ("\\newcommand{\\%s}[2]{\\ifcsname %sk#1b#2\\endcsname"
                "\\csname %sk#1b#2\\endcsname\\else\\textbf{??}\\fi}\n"
                % (pre, pre, pre))
    for pre in ("BSTAR", "BSTARMEAN", "BSTARN", "THR"):
        for sfx in ("IID", "DEV"):
            tex += ("\\newcommand{\\%s%s}[1]{\\ifcsname %s%sk#1\\endcsname"
                    "\\csname %s%sk#1\\endcsname\\else\\textbf{??}\\fi}\n"
                    % (pre, sfx, pre, sfx, pre, sfx))
    for pre in ("CA", "EA", "G", "COV", "CTR", "COLL", "POSS"):
        for sfx in ("IID", "DEV"):
            tex += ("\\newcommand{\\%s%s}[2]{\\ifcsname %s%sk#1b#2\\endcsname"
                    "\\csname %s%sk#1b#2\\endcsname\\else\\textbf{??}\\fi}\n"
                    % (pre, sfx, pre, sfx, pre, sfx))
    for sfx in ("IID", "DEV"):
        tex += ("\\newcommand{\\MARG%s}[1]{\\ifcsname MARG%sk#1\\endcsname"
                "\\csname MARG%sk#1\\endcsname\\else\\textbf{??}\\fi}\n"
                % (sfx, sfx, sfx))
    # Sampling fractions for the k>3 lattice cells. Appendix B states these as
    # percentages; percentages were outside gate2's 0.XXX regex, so they were
    # hand-written and could go stale if a k-cap ever changed -- the same C6
    # shape as a stale number in a generator template. Computed here from the
    # K actually used in the arm each sentence describes.
    import math as _math, glob as _glob
    _json = json
    _fr = {}
    for _k, _pat in ((3, "e2_*"), (5, "e2k58_*"), (8, "e2k58_*")):
        _Ks = set()
        for _f in _glob.glob(src(_pat + ".jsonl") if _pat == "e2_*"
                             else "results/canonical/" + _pat + ".jsonl"):
            for _l in open(_f):
                if not _l.startswith("{"):
                    continue
                _r = _json.loads(_l)
                if _r.get("k") == _k and _r.get("K"):
                    _Ks.add(_r["K"])
        _Ks = {K for K in _Ks if K < _math.comb(20, _k)}   # sampled, not full enum
        if len(_Ks) == 1:
            _pct = 100.0 * _Ks.pop() / _math.comb(20, _k)
            _fr[_k] = f"{_pct:.2g}"   # 2 s.f. matches the register Appendix B reads in
    for _k, _nm in ((3, "sampFracThree"), (5, "sampFracFive"), (8, "sampFracEight")):
        if _k in _fr:
            tex += macro(_nm, _fr[_k])
        else:
            print(f"  WARNING: no unique sampled K at k={_k}; {_nm} not emitted")

    with open(os.path.join(OUT, "numbers.tex"), "w") as f:
        f.write(tex)


    # ------------------------------------------------------------------- gap table
    t = ["% GENERATED -- do not edit", "\\begin{tabular}{@{}l@{\\;}l@{\\;\\;}" + "c@{\\;}" * 6 + "@{}}", "\\toprule",
         "& & \\multicolumn{3}{c}{IID} & \\multicolumn{3}{c}{Device-derived} \\\\",
         "\\cmidrule(lr){3-5}\\cmidrule(lr){6-8}",
         "$k$ & $\\beta$ & CA & EA & $G$ & CA & EA & $G$ \\\\", "\\midrule"]
    for k in ks:
        for b in BETAS:
            cells = []
            any_row = False
            for p in ("iid", "device_derived"):
                e = gt.get((p, k, round(b, 4)))
                if e is None:
                    cells += ["---", "---", "---"]; continue
                any_row = True
                ca = fmt(e["CA"]["median"])
                ea = fmt(e["EA_ens"]["median"])
                gc = ("\\textit{void}" if not e["possible"]
                      else fmt(e["G_cert"]["median"]))
                if not e["possible"]:
                    ca = "0.0000"
                cells += [ca, ea, gc]
            if any_row:
                t.append(f"{k} & {b:.2f} & " + " & ".join(cells) + " \\\\")
        t.append("\\midrule" if k != ks[-1] else "")
    t += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(OUT, "tab_gap.tex"), "w") as f:
        f.write("\n".join(x for x in t if x) + "\n")

    # ------------------------------------------------------- failure decomposition
    d = ["% GENERATED -- do not edit", "\\begin{tabular}{llcccc}", "\\toprule",
         "Partition & $\\beta$ & correct & cert.\\ wrong & geometric & margin \\\\",
         "& & \\& certified & & impossible & limited \\\\", "\\midrule"]
    kk = 2 if 2 in ks else ks[0]
    for p, lab in (("iid", "IID"), ("device_derived", "Device")):
        for b in BETAS:
            sel = [r for r in rows if r["partition_type"] == p and r["k"] == kk
                   and abs(r["beta"] - b) < 1e-9]
            if not sel:
                continue
            f4 = [float(np.median([r[x] for r in sel])) for x in
                  ("frac_correct_certified", "frac_certified_wrong",
                   "frac_geometric_impossible", "frac_margin_limited")]
            d.append(f"{lab} & {b:.2f} & " + " & ".join(f"{v:.3f}" for v in f4) + " \\\\")
        d.append("\\midrule")
    d = d[:-1] + ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(OUT, "tab_decomp.tex"), "w") as f:
        f.write("\n".join(d) + "\n")
    num["decomp_k"] = kk

    # --------------------------------------------------------------- collapse table
    if coll:
        c = ["% GENERATED -- do not edit", "\\begin{tabular}{llcccc}", "\\toprule",
             "Partition & $\\beta$ & $k$ & collapsed / draws & $P(\\text{collapse})$ "
             "& 95\\% CI \\\\", "\\midrule"]
        # IID never collapses below its geometric ceiling and the prose says so in one
        # sentence; tabulating those zeros costs a third of a column for no information.
        for p, lab in (("device_derived", "Device"), ("iid", "IID")):
            for k in sorted({int(x.split("|")[1]) for x in coll}):
                for b in BETAS:
                    s = coll.get(f"{p}|{k}|{b}")
                    if not s:
                        continue
                    if p == "iid" and s["n_collapsed"] == 0:
                        continue
                    c.append(f"{lab} & {b:.2f} & {k} & {s['n_collapsed']} / {s['n']} & "
                             f"{s['p_collapse']:.2f} & [{s['ci95'][0]:.2f}, {s['ci95'][1]:.2f}] \\\\")
            c.append("\\midrule")
        c = c[:-1] + ["\\bottomrule", "\\end{tabular}"]
        with open(os.path.join(OUT, "tab_collapse.tex"), "w") as f:
            f.write("\n".join(c) + "\n")

    # ------------------------------------------------- certified IDS metric panel
    # Overall accuracy is a weak instrument when a constant predictor attains 0.73,
    # so this is the class-conditional view the review asks for (sec 11, sec 46).
    kk2 = 2 if 2 in ks else ks[0]
    ids = ["% GENERATED -- do not edit", "\\begin{tabular}{llcccc}", "\\toprule",
           "Partition & $\\beta$ & coverage & $\\mathrm{CTR}_{\\mathrm{mal}}$ & "
           "$\\mathrm{CTR}_{\\mathrm{ben}}$ & cert.\\ wrong \\\\", "\\midrule"]
    for p_, lab in (("iid", "IID"), ("device_derived", "Device")):
        for b in BETAS:
            e = gt.get((p_, kk2, round(b, 4)))
            if e is None:
                continue
            ids.append(f"{lab} & {b:.2f} & {e['coverage']['median']:.3f} & "
                       f"{e['CTR_mal']['median']:.3f} & {e['CTR_ben']['median']:.3f} & "
                       f"{e['cert_wrong']['median']:.4f} \\\\")
        ids.append("\\midrule")
    ids = ids[:-1] + ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(OUT, "tab_ids.tex"), "w") as f:
        f.write("\n".join(ids) + "\n")
    # The ensemble's own detection quality does not vary with beta -- it is one
    # predictor -- so it belongs in the caption rather than as a constant column.
    ti = gt[("iid", kk2, 0.0)]; td = gt[("device_derived", kk2, 0.0)]
    os.makedirs(os.path.join(OUT, "floats"), exist_ok=True)
    cap = (
        "% Float wrapper; the caption is generated with the table so its numbers\n"
        "% cannot drift from it.\n"
        "\\begin{table}[t]\n\\centering\n"
        "\\caption{Certified detection at $k=" + str(kk2) + "$. Coverage and the\n"
        "certified true-rate per class are what move with the adversary budget; the\n"
        "underlying ensemble is a single predictor whose clean detection quality does\n"
        "not (TPR " + f"${ti['TPR']['median']:.3f}$" + ", FPR "
        + f"${ti['FPR']['median']:.3f}$" + " under IID; "
        + f"${td['TPR']['median']:.3f}$" + " and " + f"${td['FPR']['median']:.3f}$"
        + " under device-derived skew). Zero rows are cells the geometric ceiling\n"
        "forbids.}\n"
        "\\label{tab:ids}\n\\scriptsize\n"
        "\\resizebox{\\columnwidth}{!}{" + "%" + "\n\\input{generated/tab_ids}}\n"
        "\\end{table}\n")
    with open(os.path.join(OUT, "floats", "tab_ids.tex"), "w") as f:
        f.write(cap)

    # ------------------------------------------------------- E14 certification cost
    import math as _m, re as _re, glob as _glob
    T = 15
    wall = {}
    # Only the six same-predictor runs (stage C, 2026-10-02): "logs/e2_*.log" also pooled
    # logs/e2_classbal.log, whose k=2 passes were served from the member cache (16-17 s) and
    # pulled the k=2 median to 88 s; the six clean logs give 95 s, as Core E14 records.
    for f_ in sorted(_glob.glob("logs/e2_iid_s*.log") + _glob.glob("logs/e2_device_derived_s*.log")):
        for line in open(f_):
            mm = _re.search(r"k=(\d+) K=(\d+)/(\d+) full_enum=(\w+).*\[(\d+)s\]", line)
            if mm:
                wall.setdefault(int(mm.group(1)), []).append(int(mm.group(5)))
    o = ["% GENERATED -- do not edit", "\\begin{tabular}{lrrrrr}", "\\toprule",
         "$k$ & $\\binom{N}{k}$ & $K$ & client-rounds & vs.\\ FedAvg & clean pass \\\\",
         "\\midrule"]
    grp = lambda v: f"{v:,}".replace(",", "{,}")
    for k in ks:
        K = [r["K"] for r in rows if r["k"] == k][0]
        cr = K * k * T
        w = wall.get(k)
        ws = f"{int(np.median(w))}\\,s" if w else "---"
        # The k=3 same-predictor arm is a sample of the 1,140 subsets; say so in
        # the row rather than leaving the reader to compare K against C(N,k).
        Klab = f"{grp(K)} (sampled arm)" if K < _m.comb(N, k) else grp(K)
        o.append(f"{k} & {grp(_m.comb(N, k))} & {Klab} & {grp(cr)} & "
                 f"{cr / (N * T):.0f}$\\times$ & {ws} \\\\")
    # The configuration the certified k=3 arm (Table 1) actually ran is the full
    # enumeration, so the cost curve must price it too. Wall-clock comes from the
    # enumeration's own log; every other column is arithmetic on K.
    _full3 = load("results/canonical/e2k3full_*.jsonl")
    if _full3 and 3 in ks:
        K3 = max(r["K"] for r in _full3 if r["k"] == 3)
        cr3 = K3 * 3 * T
        # No wall-clock for this row: the enumeration run served its members from
        # the member cache, so its logged time is not a clean pass and would read
        # as faster than the 500-member sample. Client-rounds are the honest cost.
        ws3 = "---"
        o.append(f"3 & {grp(_m.comb(N, 3))} & {grp(K3)} (full) & {grp(cr3)} & "
                 f"{cr3 / (N * T):.0f}$\\times$ & {ws3} \\\\")
    o += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(OUT, "tab_cost.tex"), "w") as f:
        f.write("\n".join(o) + "\n")
    num["costKone"] = 1

    # ------------------------------------------------- E4 malicious-set sensitivity
    import collections as _c
    v = ["% GENERATED -- do not edit", "\\begin{tabular}{llcc}", "\\toprule",
         "Partition & $\\beta$ & malicious-set spread & partition-draw spread \\\\",
         "\\midrule"]
    kv = 1 if 1 in ks else ks[0]
    for p_, lab in (("iid", "IID"), ("device_derived", "Device")):
        for b in BETAS[1:]:
            sel = [r for r in rows if r["partition_type"] == p_ and r["k"] == kv
                   and abs(r["beta"] - b) < 1e-9 and r["EA_ensemble"] is not None]
            if len(sel) < 4:
                continue
            byp = _c.defaultdict(list)
            for r in sel:
                byp[r["partition_seed"]].append(r["EA_ensemble"])
            within = [max(x) - min(x) for x in byp.values() if len(x) > 1]
            permed = [float(np.median(x)) for x in byp.values()]
            across = (max(permed) - min(permed)) if len(permed) > 1 else 0.0
            v.append(f"{lab} & {b:.2f} & {float(np.mean(within)):.4f} & {across:.4f} \\\\")
        v.append("\\midrule")
    v = v[:-1] + ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(OUT, "tab_malset.tex"), "w") as f:
        f.write("\n".join(v) + "\n")
    num["malsetK"] = kv

    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(dict(numbers=num, assertions=checks,
                       gap={f"{p}|{k}|{b}": v for (p, k, b), v in gt.items()}),
                  f, indent=2, default=str)
    print(f"\ngenerated -> {OUT}")
    print(f"  IID max certificate slack   {num['GcertIIDmax']}")
    print(f"  Device max certificate slack {num["GcertDevMedMax"]}")
    print(f"  partition draws in E5: {num["NdrawsE"]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
