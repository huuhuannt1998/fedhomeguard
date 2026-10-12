#!/usr/bin/env python3
"""Figure: class coverage per member, not partition divergence, tells the k=1 regimes apart.

Figure fig:coverage of the TMLR manuscript (added 2026-10-07).
One marker per partition draw at k=1, read from the 318-cell instrument audit
(results/analysis/instruments.jsonl, written by scripts/gen_instruments.py; the same rows behind
Table tab:instruments and the pooled rank correlations in Section 6). The figure computes nothing
new: x is a pre-training statistic the audit stored for the draw (S_JS on the left, fracDegen on
the right), y is the draw's certified breakdown point beta* at k=1 as the audit stored it. No
number is printed in the figure except axis ticks.

  FHG_FIGURES=<dir> python3 scripts/gen_fig_coverage.py      (run from the repository root)

Writes <dir>/fig_coverage.pdf (vector; text set by LaTeX in Latin Modern, the paper's font) and
prints the group summaries the caption quotes, so they can be checked against it (mean S_JS
0.8503 / 0.8509, mean beta* 0.063 / 0.450, mean fracDegen 0.400 / 0.000).
Coincident markers are offset horizontally by group (the last GROUPS field) so that every group
stays visible. Every offset is non-negative and below half a grid step (0.025): no marker sits left
of its true share, none reaches the next grid value, and nothing is jittered vertically.
"""
import collections
import json
import os
import sys

import numpy as np
# Reproducible bytes: pdfTeX (run by the pgf backend) takes its dates from SOURCE_DATE_EPOCH.
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
os.environ.setdefault("FORCE_SOURCE_DATE", "1")
import matplotlib
matplotlib.use("pgf")   # pdflatex sets every label in Latin Modern, as in the paper
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "results", "analysis", "instruments.jsonl")
from _manuscript import FIGURES as FIG  # TMLR figures/ (FHG_FIGURES overrides)

# Paper palette (scripts/gen_teaser.py): IID blue and device-derived orange as in Figure 1; a third
# validated categorical slot for N-BaIoT; the three Dirichlet-style families in ink with distinct
# hollow shapes (identity is never colour alone).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, AXIS = "#3d3c39", "#898781", "#e1e0d9", "#c3c2b7"
BETA_GEO_K1 = 0.450          # exact ceiling beta_geo(20,1) (Table tab:ceiling)

# (key, legend label, colour, marker, filled, marker area, dodge in x units of the right panel).
# IID is drawn first and largest so the markers that coincide with it stay visible on top of it.
GROUPS = [
    (("iid", None), r"IID, both corpora", BLUE, "o", True, 30, 0.0),
    (("iot23", "device_derived"), r"IoT-23 device-derived", ORANGE, "s", True, 16, 0.0),
    (("nbaiot", "device_derived"), r"N-BaIoT device-derived", AQUA, "D", True, 14, 0.024),
    (("iot23", "dirichlet"), r"label-Dirichlet", INK, "^", False, 18, 0.0),
    (("iot23", "dirichlet_device"), r"device-Dirichlet", INK, "v", False, 18, 0.008),
    (("iot23", "volume"), r"volume skew", MUTED, "x", True, 18, 0.016),
]

plt.rcParams.update({
    "pgf.texsystem": "pdflatex", "pgf.rcfonts": False,
    "pgf.preamble": r"\pdftrailerid{}\usepackage[T1]{fontenc}\usepackage{lmodern}\usepackage{amsmath}",
    "font.family": "serif", "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.linewidth": 0.6,
    "legend.handletextpad": 0.2, "legend.columnspacing": 1.6, "legend.labelspacing": 0.25,
})


def group_of(r):
    if r["family"] == "iid":
        return ("iid", None)
    return (r["dataset"], r["family"])


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.grid(True, axis="y", color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=3, width=0.6)


def main():
    rows = [json.loads(l) for l in open(SRC) if l.strip().startswith("{")]
    rows = [r for r in rows if int(r["k"]) == 1]
    by = collections.defaultdict(list)
    for r in rows:
        by[group_of(r)].append(r)
    missing = [g for g, *_ in GROUPS if g not in by]
    if missing or sum(len(v) for v in by.values()) != len(rows):
        sys.exit(f"unexpected groups in {SRC}: missing {missing}, have {sorted(by, key=str)}")

    # Exactly the TMLR text width (6.5in), so the figure is included at scale 1 and its 8-9pt
    # labels print at that size beside the 10pt body text.
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(6.5, 2.1), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.995, bottom=0.19, top=0.815, wspace=0.07)
    for ax in (axl, axr):
        style(ax)
        ax.axhline(BETA_GEO_K1, color=MUTED, linewidth=2.6, alpha=0.35, zorder=1,
                   solid_capstyle="butt")
    handles = []
    assert all(0 <= d < 0.025 for *_, d in GROUPS), "offsets must be non-negative and below half a grid step"
    for g, label, col, mk, filled, area, dodge in GROUPS:
        rr = by[g]
        y = np.array([r["beta_star"] for r in rr])
        for ax, key, dx in ((axl, "S_JS", 0.0), (axr, "frac_degenerate", dodge)):
            x = np.array([r[key] for r in rr]) + dx
            kw = dict(marker=mk, s=area, linewidths=0.8, zorder=3)
            if mk == "x":
                h = ax.scatter(x, y, color=col, **kw)
            elif filled:
                h = ax.scatter(x, y, color=col, edgecolors="#fcfcfb", **kw)
            else:
                h = ax.scatter(x, y, facecolors="none", edgecolors=col, **kw)
        handles.append((h, label))

    axl.set_xlabel(r"partition divergence $S_{\mathrm{JS}}$")
    axr.set_xlabel(r"share of nearly one-class clients, $\mathrm{fracDegen}$")
    axl.set_ylabel(r"$\beta^{*}$ at $k=1$")
    axl.set_ylim(-0.025, 0.49)
    axl.set_yticks([0, 0.1, 0.2, 0.3, 0.4])
    axl.set_yticklabels(["0", "0.1", "0.2", "0.3", "0.4"])
    for ax in (axl, axr):
        ax.set_xlim(-0.06, 0.95)
        ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8])
        ax.set_xticklabels(["0", "0.2", "0.4", "0.6", "0.8"])
    axr.text(0.93, BETA_GEO_K1 + 0.01, r"ceiling", color=MUTED, fontsize=8, ha="right", va="bottom")
    # The one contrast the figure exists to show, direct-labelled: same divergence, opposite outcome.
    axl.annotate(r"N-BaIoT", xy=(0.79, BETA_GEO_K1 - 0.008), xytext=(0.64, 0.37), fontsize=8, color=INK,
                 ha="center", arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.6, shrinkB=2))
    axl.annotate(r"IoT-23", xy=(0.785, 0.075), xytext=(0.66, 0.075), fontsize=8, color=INK,
                 ha="center", va="center",
                 arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.6, shrinkB=2))
    fig.legend([h for h, _ in handles], [l for _, l in handles], loc="upper center",
               ncol=3, frameon=False, bbox_to_anchor=(0.535, 1.0), borderaxespad=0.2)
    out = os.path.join(FIG, "fig_coverage.pdf")
    fig.savefig(out, metadata={"Creator": None, "Producer": None})  # no tool URL in the embedded Info dict
    plt.close(fig)
    print(f"wrote {out}")

    # Group summaries (k=1), for checking the caption against the accepted evidence.
    for g, label, *_ in GROUPS:
        rr = by[g]
        f = lambda key: float(np.mean([r[key] for r in rr]))  # noqa: E731
        print(f"  {label:26s} n={len(rr):3d}  mean S_JS {f('S_JS'):.4f}  mean fracDegen "
              f"{f('frac_degenerate'):.3f}  mean beta* {f('beta_star'):.3f}")


if __name__ == "__main__":
    main()
