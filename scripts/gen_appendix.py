#!/usr/bin/env python3
"""Appendix: the sensitivity analyses (review sections 17, 18, 20 / E10, E11, E13).

These are recommended rather than load-bearing, so they live in an appendix, which
IEEE S&P excludes from the page limit. Every number is generated from the canonical
files by the same code path as the body.
"""
import collections, glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from aggregate import load

OUT = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"


def summarise(paths, k=1):
    out = []
    for f in sorted(paths):
        r = [x for x in load(f) if x["k"] == k]
        if not r:
            continue
        seeds = {x["partition_seed"] for x in r}
        bs = float(np.median([max([y["beta"] for y in r
                                   if y["partition_seed"] == s and y["CA"] > y["tau_triv"]] + [0.0])
                              for s in seeds]))
        out.append(dict(
            f=os.path.basename(f), N=r[0]["N"],
            part=r[0]["partition_type"],
            dph=tuple(r[0].get("devices_per_household") or (1, 3)),
            S=float(np.mean([x["S_JS"] for x in r])),
            Sd=float(np.mean([x["S_dev"] or 0.0 for x in r])),
            margin=float(np.median([x["mean_vote_margin"] for x in r])),
            ens=float(np.median([x["clean_ensemble_acc"] for x in r])),
            bstar=bs,
            coll=float(np.mean([x["collapsed"] for x in r if abs(x["beta"] - 0.2) < 1e-9]))))
    return out


def main():
    e10 = summarise(glob.glob("results/canonical/e10_*.jsonl")
                    + glob.glob("results/canonical/e2_*_s0.jsonl"))
    e11 = summarise(glob.glob("results/canonical/e11_*.jsonl")
                    + ["results/canonical/e2_device_derived_s0.jsonl"])

    t10 = ["% GENERATED -- do not edit", "\\begin{tabular}{lrccccc}", "\\toprule",
           "Partition & $N$ & $S_{\\mathrm{JS}}$ & margin & ens.\\ acc & $\\beta^{*}$ & "
           "collapse \\\\", "\\midrule"]
    for e in sorted(e10, key=lambda x: (x["part"], x["N"])):
        nm = "device-derived" if e["part"] == "device_derived" else "IID"
        t10.append(f"{nm} & {e['N']} & {e['S']:.3f} & {e['margin']:.3f} & "
                   f"{e['ens']:.3f} & {e['bstar']:.3f} & {e['coll']:.2f} \\\\")
    t10 += ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_fedsize.tex"), "w").write("\n".join(t10) + "\n")

    t11 = ["% GENERATED -- do not edit", "\\begin{tabular}{lccccc}", "\\toprule",
           "Devices/household & $S_{\\mathrm{JS}}$ & $S_{\\mathrm{dev}}$ & margin & "
           "$\\beta^{*}$ & collapse \\\\", "\\midrule"]
    for e in sorted(e11, key=lambda x: x["dph"]):
        lo, hi = e["dph"]
        lab = f"{lo}" if lo == hi else f"{lo}--{hi}"
        t11.append(f"{lab} & {e['S']:.3f} & {e['Sd']:.3f} & {e['margin']:.3f} & "
                   f"{e['bstar']:.3f} & {e['coll']:.2f} \\\\")
    t11 += ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_devcount.tex"), "w").write("\n".join(t11) + "\n")

    d = [json.loads(l) for f in glob.glob("results/canonical/e13_*.jsonl")
         for l in open(f) if l.strip()]
    by = collections.defaultdict(list)
    for x in d:
        by[(x["partition_type"], x["defense"], x["scale"], round(x["beta"], 4))].append(x["EA"])
    t13 = ["% GENERATED -- do not edit", "\\begin{tabular}{llccc}", "\\toprule",
           "Partition & Defence & $\\lambda{=}0.5$ & $\\lambda{=}1$ & $\\lambda{=}5$ \\\\",
           "\\midrule"]
    for p, lab in (("device_derived", "device"), ("iid", "IID")):
        for dn in ("norm_clip", "multikrum", "median"):
            v = [by.get((p, dn, s, 0.2)) for s in (0.5, 1.0, 5.0)]
            if not all(v):
                continue
            t13.append(f"{lab} & {dn.replace('_',' ')} & "
                       + " & ".join(f"{min(x):.4f}" for x in v) + " \\\\")
        t13.append("\\midrule")
    t13 = t13[:-1] + ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_attackstrength.tex"), "w").write("\n".join(t13) + "\n")

    def get(lst, **kw):
        for e in lst:
            if all(e[k] == v for k, v in kw.items()):
                return e
        return None
    d11 = {e["dph"]: e for e in e11}
    poor, rich = d11.get((1, 1)), d11.get((2, 5))
    n10 = get(e10, part="device_derived", N=10); n50 = get(e10, part="device_derived", N=50)
    n20 = get(e10, part="device_derived", N=20)
    nc = min(min(by[(p, "norm_clip", 5.0, 0.2)]) for p in ("device_derived", "iid"))
    nw = max(min(by[(p, "norm_clip", 0.5, 0.2)]) for p in ("device_derived", "iid"))

    tex = f"""% GENERATED -- do not edit
\\appendices
\\section{{Sensitivity Analyses}}
\\label{{app:sensitivity}}

% provenance: jrn_01M0SH0V4DR4AYK59BJCN230Q5 supports the cost and sensitivity measurements
These three sweeps are recommended rather than load-bearing: no claim in the body
depends on them, and they are reported here so a reader can see what does and does
not move the result.

\\subsection{{Federation size}}
Corollary~\\ref{{cor:ceiling}} is independent of $N$, but ensemble competence need not
be. Table~\\ref{{tab:fedsize}} sweeps $N \\in \\{{10, 20, 50\\}}$. Under IID nothing moves.
Under device-derived skew, enlarging the federation does not rescue competence and
mildly hurts it: the mean vote margin is {n10['margin']:.3f} at $N=10$,
{n20['margin']:.3f} at $N=20$ and {n50['margin']:.3f} at $N=50$, because each household
holds proportionally less data as $N$ grows. Growth is not a way out of the pincer
from either side.

\\begin{{table}}[h]
\\centering
\\caption{{Federation-size sensitivity at $k=1$, three partition draws each.}}
\\label{{tab:fedsize}}
\\scriptsize
\\resizebox{{\\columnwidth}}{{!}}{{%
\\input{{generated/tab_fedsize}}}}
\\end{{table}}

\\subsection{{Household device richness}}
% provenance: jrn_01M0W6RR18X6MJY3X1JG07YTRN supports the device-versus-label ablation
This is the sharpest available test of the mechanism in Section~\\ref{{sec:skew}}, and
it agrees with it. Giving each household more device types raises the number of
labels its traffic contains, and the ensemble's agreement follows:
Table~\\ref{{tab:devcount}} shows the mean vote margin rising from
{poor['margin']:.3f} at one device per household to {rich['margin']:.3f} at two to
five, with the certified breakdown point moving from {poor['bstar']:.3f} to
{rich['bstar']:.3f} and the collapse rate at $\\beta = 0.20$ from {poor['coll']:.2f} to
{rich['coll']:.2f}. Note that $S_{{\\mathrm{{JS}}}}$ \\emph{{falls}} as richness rises, so
this is the mechanism operating in the direction the ablation predicts rather than an
independent effect. It is also the one actionable lever we can offer: a federation
whose households each hold at least two device types certifies where one whose
households hold a single device does not.

\\begin{{table}}[h]
\\centering
\\caption{{Household device richness, device-derived partitions at $k=1$.}}
\\label{{tab:devcount}}
\\scriptsize
\\resizebox{{\\columnwidth}}{{!}}{{%
\\input{{generated/tab_devcount}}}}
\\end{{table}}

\\subsection{{Attack strength}}
% provenance: jrn_01M0SH0V4DR4AYK59BJCN230Q5 supports the cost and sensitivity measurements
Every parameterised attack carries a strength $\\lambda$, and the review's question is
whether the empirical arm depends strongly on that arbitrary choice. It does, for one
rule. Table~\\ref{{tab:strength}} sweeps $\\lambda \\in \\{{0.5, 1, 5\\}}$ at
$\\beta = 0.20$: norm clipping falls from {nw:.4f} at $\\lambda = 0.5$ to {nc:.4f} at
$\\lambda = 5$, which is the minority-class rate, under both partitions, while
multi-Krum and coordinate-wise median are nearly flat. A robustness number for a
clipping rule is therefore only as meaningful as the attack magnitude it was measured
against. This cuts in the paper's conservative direction: a stronger attack lowers
$\\mathrm{{EA}}_{{\\mathrm{{finite}}}}$ and therefore \\emph{{tightens}} every slack we report.

\\begin{{table}}[h]
\\centering
\\caption{{Attack-strength sensitivity: worst-case accuracy over the attack set at
$\\beta = 0.20$, by attack magnitude $\\lambda$.}}
\\label{{tab:strength}}
\\scriptsize
\\resizebox{{\\columnwidth}}{{!}}{{%
\\input{{generated/tab_attackstrength}}}}
\\end{{table}}
"""
    # the observability measurement lives here rather than in the body, because no
    # result depends on it and IEEE S&P excludes appendices from the page limit
    e12p = os.path.join(OUT, "e12_paragraph.tex")
    if os.path.exists(e12p):
        e12 = "\n".join(l for l in open(e12p).read().split("\n")
                        if not l.startswith("% GENERATED"))
        tex += ("\n\\subsection{What server observability buys}\n"
                "\\label{app:observability}\n" + e12 + "\n")
    # Proofs relocated from Section IV: the body must fit 13 pages of text while
    # the CFP grants 5 for references and appendices, of which we were using 3.
    pf = os.path.join(OUT, "proofs_appendix.tex")
    if os.path.exists(pf):
        tex += "\n" + "\n".join(l for l in open(pf).read().split("\n")
                                 if not l.startswith("% HAND-AUTHORED")) + "\n"

    # Reference material moved out of the body, since IEEE S&P excludes appendices
    # from the page limit and the body prose already states every number these
    # tables carry that the argument depends on.
    for fname, heading in (("limitations_appendix.tex", None),
                           ("inventory_appendix.tex", None),
                           ("observability_appendix.tex", None),
                           ("ethics_appendix.tex", None),
                           ("floats/tab_cost.tex", "Cost of certifiability"),
                           ("floats/tab_ablation.tex", "Skew-component ablation"),
                           ("floats/fig_pincer.tex", "The pincer in vote-margin units"),
                           ("floats/tab_instruments.tex", "Partition-statistic ranking"),
                           ("config_table_appendix.tex", "Complete configuration"),
                           ("floats/tab_ids.tex", "Certified detection, per class"),
                           ("floats/tab_decomp.tex", "Where certification fails")):
        fp = os.path.join(OUT, fname)
        if os.path.exists(fp):
            body = "\n".join(l for l in open(fp).read().split("\n")
                             if not l.startswith(("% Moved", "% Float wrapper",
                                                  "% HAND-AUTHORED", "%")))
            # heading None means the file carries its own \subsection
            tex += ("\n" + body + "\n") if heading is None else \
                   ("\n\\subsection{" + heading + "}\n" + body + "\n")

    # The cost-of-certifiability table lives in the body (Section VIII, via
    # e3_paragraph.tex) and was ALSO being reprinted here from a stale
    # method_table_appendix.tex left over from an earlier reorganisation. That
    # duplicated a full float and defined \label{tab:method} twice, so the body's
    # own \ref resolved to the appendix copy. The appendix copy is dropped.
    esp = os.path.join(OUT, "ensemble_size_appendix.tex")
    if os.path.exists(esp):
        tex += "\n" + "\n".join(l for l in open(esp).read().split("\n")
                                 if not l.startswith("% GENERATED")) + "\n"
    open(os.path.join(OUT, "appendix.tex"), "w").write(tex)
    print("wrote appendix.tex, tab_fedsize.tex, tab_devcount.tex, tab_attackstrength.tex")
    print(f"  device richness margin {poor['margin']:.3f} -> {rich['margin']:.3f}, "
          f"beta* {poor['bstar']:.3f} -> {rich['bstar']:.3f}")


if __name__ == "__main__":
    main()
