#!/usr/bin/env python3
"""Figure 3 (fig_main.pdf): certified and attacked accuracy of the SAME ensemble.

Replaces the lost `manuscripts/.../charts/make_figures_v2.py`, which drew this figure
until 2026-09-01 and did not survive the move of the manuscript folder (no copy in git
history, in any committed prism bundle, or on disk). Layout, series, labels and colours
follow that PDF: two panels (IID, device-derived), certified (blue) and attacked
(orange) accuracy against the malicious fraction, k = 1 solid circles, k = 2 dashed
squares, the trivial floor dotted.

Plots the medians Table 2 prints -- CA and the final-round attacked accuracy (min over
the five published attacks) from aggregate.gap_table -- so the figure cannot disagree
with the table. Reads the corrected rows by default (aggregate.src); FHG_FROZEN=1
reproduces the pre-correction figure.

    python3 scripts/make_fig_main.py --out "<manuscript>/figures/fig_main.pdf"
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregate import load, gap_table, src

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE = "#2A78D6", "#EB6834"
GRID, FLOOR = "#E1E0D9", "#898781"
BETAS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = load(src("e2_*.jsonl"))
    gt = gap_table(rows)
    tau = rows[0]["tau_triv"]

    plt.rcParams.update({"font.family": "serif", "font.size": 8,
                         "axes.titlesize": 9, "axes.labelsize": 8,
                         "legend.fontsize": 7, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(5.884, 2.65), sharey=True)
    for ax, (p, title) in zip(axes, (("iid", "IID partition"),
                                      ("device_derived", "Device-derived partition"))):
        for k, ls, mk in ((1, "-", "o"), (2, "--", "s")):
            bs = [b for b in BETAS if (p, k, round(b, 4)) in gt]
            ca = [gt[(p, k, round(b, 4))]["CA"]["median"] for b in bs]
            ea = [gt[(p, k, round(b, 4))]["EA_ens"]["median"] for b in bs]
            ax.plot(bs, ca, ls, marker=mk, ms=3.2, lw=1.4, color=BLUE,
                    label=f"certified, $k={k}$")
            ax.plot(bs, ea, ls, marker=mk, ms=3.2, lw=1.4, color=ORANGE,
                    label=f"attacked, $k={k}$")
        ax.axhline(tau, ls=":", lw=0.8, color=FLOOR, zorder=0)
        ax.set_title(title)
        ax.set_xlabel(r"malicious fraction $\beta$")
        ax.set_xticks([0.0, 0.1, 0.2, 0.3, 0.4])
        ax.set_ylim(-0.02, 1.03)
        ax.yaxis.grid(True, color=GRID, lw=0.7); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color("#A5A5A5")
        ax.tick_params(colors="#595959", length=2.5)
    axes[0].set_ylabel("accuracy")
    axes[0].text(0.0, tau + 0.025, r"$\tau_{\mathrm{triv}}$", fontsize=7, color="#595959")
    # review D2 (F-35): the legend sat inside the IID panel, where the k=2 curves fall between
    # beta=0.2 and 0.3; it now sits below both panels, outside the axes, in one row.
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="lower center", frameon=False, handlelength=2.2,
               columnspacing=1.2, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(pad=0.3, w_pad=1.2, rect=(0, 0.08, 1, 1))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    fig.savefig(a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
