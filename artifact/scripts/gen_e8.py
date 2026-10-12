#!/usr/bin/env python3
"""E8 -- the certifiable frontier with its uncertainty (review sec 13).

beta*(S) is rebuilt from every partition draw we have rather than one curve per skew
level, because the draw-to-draw spread at small k is comparable to the effect. We
plot the measured points and the median; we draw no phase boundary, because the data
do not support one.
"""
import collections, glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from aggregate import load                                             # noqa: E402

from _manuscript import FIGURES as FIG, GENERATED as OUT  # TMLR figures/ and generated/ (FHG_* override)
BLUE, ORANGE, MUTED, GRID = "#2a78d6", "#eb6834", "#898781", "#e1e0d9"

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8,
    "legend.fontsize": 7, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.linewidth": 0.6, "lines.linewidth": 1.4, "figure.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02})


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.grid(True, axis="y", color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=3, width=0.6)
    for l in ax.get_xticklabels() + ax.get_yticklabels():
        l.set_color("#52514e")


def points(paths, k, full_only=False):
    """One (S_JS, beta*) per partition draw at this subsample size.

    full_only drops draws whose ensemble lost starved members: K shrinks there, which
    raises the certification threshold independently of skew, so those draws are a
    different predictor and must not be pooled with full-enumeration ones.
    """
    import math
    rows = [r for p in paths for r in load(p) if r["k"] == k
            and (not full_only or r["K"] == math.comb(r["N"], k))]
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["partition_type"], r.get("dirichlet_alpha"), r["partition_seed"])].append(r)
    out = []
    for _, v in by.items():
        good = [x["beta"] for x in v if x["CA"] > x["tau_triv"]]
        out.append((float(np.mean([x["S_JS"] for x in v])), max(good) if good else 0.0))
    return sorted(out)


def main():
    # ONLY the decensored sweeps. The earlier grid stopped at beta = 0.40 and so
    # right-censored beta* at k=1, whose ceiling is 0.450; mixing censored draws with
    # uncensored ones would bias the frontier downward exactly where it matters.
    src = sorted(glob.glob(os.path.join(ROOT, "results/canonical/e5f_*.jsonl"))
                 + glob.glob(os.path.join(ROOT, "results/canonical/e7f_*.jsonl")))
    vol = sorted(glob.glob(os.path.join(ROOT, "results/canonical/e7_volskew.jsonl")))
    nb = sorted(glob.glob(os.path.join(ROOT, "results/canonical/nb9_cert_device_derived.jsonl")))
    if not src:
        print("no decensored sweeps yet; skipping frontier"); return
    fig, ax = plt.subplots(figsize=(3.4, 2.35))
    style(ax)
    stats = {}
    for k, col, mk, ls in ((1, BLUE, "o", "-"), (2, ORANGE, "s", "--")):
        pts = points(src, k)
        if not pts:
            continue
        xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
        ax.scatter(xs, ys, s=9, color=col, marker=mk, alpha=0.45, linewidths=0, zorder=2)
        # median within skew deciles, drawn only where a bin has >= 3 draws
        edges = np.array([0, .05, .12, .22, .32, .45, .60, .78, 1.01])
        mx, my = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (xs >= lo) & (xs < hi)
            if m.sum() >= 3:
                mx.append(float(np.median(xs[m]))); my.append(float(np.median(ys[m])))
        ax.plot(mx, my, color=col, marker=mk, markersize=4, linestyle=ls, zorder=3,
                label=f"median, $k={k}$")
        ax.axhline({1: 0.450, 2: 0.250}[k], color=col, linewidth=0.7, linestyle=":",
                   alpha=0.6, zorder=1)
        stats[k] = dict(n=len(pts),
                        lo=[float(np.median(ys[xs < 0.12])) if (xs < 0.12).any() else None],
                        hi=[float(np.median(ys[xs > 0.60])) if (xs > 0.60).any() else None])
    # Volume-skew draws are plotted separately because they are the counterexample:
    # they lose breakdown point at S_JS near zero, so beta* is not a function of S_JS.
    vstat = {}
    if vol:
        vp = [p for p in points(vol, 1, full_only=True) if p[0] < 0.02]
        # the plotted diamonds themselves (review r6 item 5): the prose quotes these,
        # not Table 10's per-level means, which also average the starved draws
        if vp:
            vstat = dict(n=len(vp), sjs=max(p[0] for p in vp),
                         bhi=max(p[1] for p in vp), blo=min(p[1] for p in vp))
        if vp:
            vx = np.array([p[0] for p in vp]); vy = np.array([p[1] for p in vp])
            ax.scatter(vx, vy, s=26, facecolors="none", edgecolors="#52514e",
                       linewidths=0.9, marker="D", zorder=4,
                       label="data-volume skew, $k=1$")
    # The other counterexample, and the one that matters more: N-BaIoT device-derived
    # partitions sit at the SAME measured skew as IoT-23's and certify at the ceiling.
    # With the volume points below, the figure shows beta* failing to be a function of
    # S_JS in both directions at once.
    if nb:
        np_ = points(nb, 1)
        if np_:
            nx = np.array([p[0] for p in np_]); ny = np.array([p[1] for p in np_])
            ax.scatter(nx, ny, s=30, facecolors="none", edgecolors="#52514e",
                       linewidths=0.9, marker="^", zorder=4,
                       label="N-BaIoT device-derived, $k=1$")
            ax.annotate("same skew,\nceiling $\\beta^{*}$",
                        (float(np.median(nx)), float(np.median(ny))),
                        textcoords="offset points", xytext=(-74, -18),
                        color="#52514e", fontsize=6.5, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color="#898781",
                                        linewidth=0.6, shrinkA=2, shrinkB=3))
    ax.set_xlabel(r"measured skew $S_{\mathrm{JS}}$")
    ax.set_ylabel(r"certified breakdown point $\beta^{*}$")
    ax.set_ylim(-0.02, 0.52); ax.set_xlim(-0.02, 0.92)
    ax.annotate(r"$\beta_{\mathrm{geo}}(20,1)$", (0.60, 0.462), color=BLUE, fontsize=6.5)
    ax.annotate(r"$\beta_{\mathrm{geo}}(20,2)$", (0.60, 0.262), color=ORANGE, fontsize=6.5)
    ax.legend(frameon=False, loc="lower left")
    fig.savefig(os.path.join(FIG, "fig_frontier.pdf"))
    plt.close(fig)

    n1 = stats.get(1, {}).get("n", 0); n2 = stats.get(2, {}).get("n", 0)
    tex = f"""% GENERATED -- do not edit
% provenance: jrn_01M0SH05VQQZV4NQA53GCYPW99 supports the collapse and margin measurements
Figure~\\ref{{fig:frontier}} plots the largest certifiable fraction against measured
skew, one marker per partition draw over {n1} draws at $k=1$ and {n2} at $k=2$, pooled
across the device-derived, IID, device-Dirichlet and label-Dirichlet families; the volume
and N-BaIoT draws are the two open series below. Two features are visible that a single
curve would hide. The breakdown point sits \\emph{{on}} the geometric ceiling across
the whole low-skew range and falls only as skew grows, so combinatorics rather than
data binds there. The fall is not a clean boundary: at intermediate skew the same nominal
partition family yields draws that certify at the ceiling and draws that certify
nothing, which is why we plot the draws and a binned median and decline to draw a
phase transition through them.

% provenance: jrn_01M0WANCPPMEWGWW0J4JKT6SKA supports the volume-skew counterexample
The open diamonds are the counterexample that keeps this figure from being a curve.
They are data-volume-skewed partitions: every client draws from the same
pool, so their distributions are near-identical. As in the paired test, only draws that
kept every member are plotted: those {vstat['n']} never exceed
$S_{{\\mathrm{{JS}}}} = {vstat['sjs']:.3f}$, yet their breakdown point runs from
${vstat['bhi']:.3f}$ down to ${vstat['blo']:.3f}$. The draws that lost members to starved
clients reach higher $S_{{\\mathrm{{JS}}}}$ and lift Table~\\ref{{tab:ablation}}'s volume means.

% provenance: jrn_01M0WPYA144JWHAV4FACAQFD8R supports the N-BaIoT counterexample
The open triangles are the counterexample in the other direction. They are N-BaIoT
device-derived partitions, built by the identical construction that collapses on
IoT-23 and landing at the same measured skew, and they certify at the ceiling. Taken
together the two open series show that measured skew is neither sufficient nor
necessary for certifiability, and that $\\beta^{{*}}$ is not a function of it. A
federation can look homogeneous by $S_{{\\mathrm{{JS}}}}$ and still be uncertifiable,
because a client holding few rows trains a weak member whatever its distribution
looks like.

\\begin{{figure}}[t]
\\centering
\\includegraphics[width=\\columnwidth]{{figures/fig_frontier.pdf}}
\\caption{{Certified breakdown point against measured skew, one marker per partition
draw, pooled over the device-derived, IID, device-Dirichlet and label-Dirichlet
families. Dotted lines are the geometric ceilings $\\beta_{{\\mathrm{{geo}}}}(20,k)$; the
solid line is a median within skew bins holding at least three draws. The vertices
are measurements and nothing is interpolated between them. The two open series break
$\\beta^{{*}}$ as a function of $S_{{\\mathrm{{JS}}}}$ in opposite directions: volume-skewed
partitions lose breakdown point at $S_{{\\mathrm{{JS}}}}$ near zero, and N-BaIoT
device-derived partitions certify at the ceiling at the same $S_{{\\mathrm{{JS}}}}$ where
IoT-23's collapse.}}
\\label{{fig:frontier}}
\\end{{figure}}
"""
    open(os.path.join(OUT, "e8_paragraph.tex"), "w").write(tex)
    print(f"wrote fig_frontier.pdf and e8_paragraph.tex  (k=1: {n1} draws, k=2: {n2})")


if __name__ == "__main__":
    main()
