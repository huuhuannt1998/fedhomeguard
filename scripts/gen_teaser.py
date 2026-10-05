#!/usr/bin/env python3
"""Introduction teaser: the pincer in the units a security reader already owns.

The paper's first figure previously appeared on page 7. This one carries the whole
finding on page 1 without needing any definition from Section IV: the y-axis is the
malicious client fraction that can actually be certified.

Design follows the paper's existing charts: validated categorical slots 1-2,
grayscale carried by line style and marker rather than hue, one axis, no
interpolation between measured k.
"""
import collections, glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "/Users/huanbui/Research/FedHomeGuard-P10"
FIG = os.environ.get("FHG_FIGURES", os.path.join(ROOT, "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/figures"))
OUT = os.environ.get("FHG_GENERATED", os.path.join(ROOT, "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bstar import bstar as _bstar  # the one definition of beta* (per-draw, then median over draws)
BLUE, ORANGE, MUTED, GRID = "#2a78d6", "#eb6834", "#898781", "#e1e0d9"
BETA_GEO = {1: 0.450, 2: 0.250, 3: 0.150, 5: 0.100, 8: 0.050}
# k=1,2 fully enumerated; k=3 full C(20,3); k=5,8 sampled, so those two are LOWER
# BOUNDS on the population breakdown point and are drawn open to say so.
SRC = ["e5f_*", "e2k3full_*", "e2k58_cert_*"]

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8,
    "legend.fontsize": 7, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.linewidth": 0.6, "lines.linewidth": 1.4,
    "figure.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.grid(True, axis="y", color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=3, width=0.6)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_color("#52514e")


def beta_star():
    """Median over partition draws of the per-draw beta* (scripts/bstar.py), per (partition, k).

    Stage C (2026-10-02): this figure used to plot the MEAN over draws of a min-over-malicious-sets
    beta*, while the text and tables print the canonical median; it now uses the canonical
    estimator so the plotted values are the printed ones."""
    rows = collections.defaultdict(list)
    for pat in SRC:
        for f in glob.glob(os.path.join(ROOT, "results/canonical", pat + ".jsonl")):
            for line in open(f):
                if not line.startswith("{"):
                    continue
                r = json.loads(line)
                rows[(r["partition_type"], int(r["k"]))].append(r)
    out = {}
    for key, rs in rows.items():
        med, _mean, _n, _v = _bstar(rs, rs[0]["tau_triv"])
        out[key] = float(med)
    return out


def main():
    bs = beta_star()
    ks = [k for k in (1, 2, 3, 5, 8) if ("iid", k) in bs and ("device_derived", k) in bs]
    if not ks:
        print("teaser: no data"); return
    ceil = [BETA_GEO[k] for k in ks]
    iid = [bs[("iid", k)] for k in ks]
    dev = [bs[("device_derived", k)] for k in ks]
    x = np.arange(len(ks))                      # even spacing: k is ordinal here

    fig, ax = plt.subplots(figsize=(3.4, 2.05))
    style(ax)
    ax.plot(x, ceil, color=MUTED, linewidth=3.2, alpha=0.45, solid_capstyle="round",
            zorder=1, label=r"ceiling $\beta_{\mathrm{geo}}(20,k)$")
    ax.plot(x, iid, color=BLUE, marker="o", markersize=5, linestyle="-",
            markeredgecolor="#fcfcfb", markeredgewidth=0.8, zorder=3,
            label=r"IID partition")
    ax.plot(x, dev, color=ORANGE, marker="s", markersize=4.5, linestyle="--",
            markeredgecolor="#fcfcfb", markeredgewidth=0.8, zorder=4,
            label=r"device-derived partition")

    # The two facts the figure exists to carry, direct-labelled; nothing else.
    i1 = ks.index(1)
    ax.annotate("", xy=(i1, ceil[i1]), xytext=(i1, dev[i1]),
                arrowprops=dict(arrowstyle="<->", color="#898781", linewidth=0.7,
                                shrinkA=1.5, shrinkB=1.5))
    # No in-plot text. The curve sweeps diagonally across a small single-column
    # panel and every candidate position for a label puts it on a line; the caption
    # sits directly beneath the figure and can carry the same sentence safely.

    ax.set_xticks(x); ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel(r"subsample size $k$")
    ax.set_ylabel("certified breakdown\npoint $\\beta^{*}$")
    ax.set_ylim(0, 0.52); ax.set_xlim(-0.25, len(ks) - 0.55)
    ax.legend(frameon=False, loc="upper right", handlelength=2.0,
              borderaxespad=0.2, labelspacing=0.35)
    fig.savefig(os.path.join(FIG, "fig_teaser.pdf"))
    plt.close(fig)

    open(os.path.join(OUT, "floats", "fig_teaser.tex"), "w").write(
        "% Float wrapper; caption authored, figure generated by scripts/gen_teaser.py.\n"
        "\\begin{figure}[t]\n\\centering\n"
        "\\includegraphics[width=\\columnwidth]{figures/fig_teaser.pdf}\n"
        "\\caption{The whole finding. Certification against a bounded number of\n"
        "malicious clients has a ceiling that falls as the subsample size $k$ grows,\n"
        "and IID clients reach it at every $k$. Partitioning by device --- how a real\n"
        "smart-home federation is actually split --- keeps the certified predictor far\n"
        "below it, so what binds is the data, not the combinatorics: the arrow marks that\n"
        "gap at $k=1$. The two\n"
        "constraints move in opposite directions in $k$, which is why the best choice\n"
        "is interior and why enlarging the federation does not help. Markers at\n"
        "$k \\ge 5$ are sampled ensembles and bound $\\beta^{*}$ from below.}\n"
        "\\label{fig:teaser}\n\\end{figure}\n")
    print("wrote fig_teaser.pdf")
    for k, a, b, c in zip(ks, ceil, iid, dev):
        print(f"   k={k}  ceiling {a:.3f}  iid {b:.3f}  device {c:.3f}")


if __name__ == "__main__":
    main()
