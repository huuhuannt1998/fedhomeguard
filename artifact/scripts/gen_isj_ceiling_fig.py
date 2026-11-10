#!/usr/bin/env python3
"""ISJ-GP figure fig:ceiling (round isj2a plan, O-001@5): certified accuracy against the number of malicious clients m
for plurality (P), abstention (A), the max-flow certified decoder (D) and the oracle ceiling (MAX), median and
interquartile range over the 30 fresh IoT-23 draws of predeclarations/maxflow_decoder_2026-11-03.md.

Reads results/novelty/maxflow_decoder_iot23.jsonl only. Writes, in the ISJ-GP folder:
  figures/fig_ceiling.pdf and figures/fig_ceiling.eps (T&F accepts PS/EPS, not PDF, for figure files)
  generated/fig_ceiling_numbers.json (the plotted medians and quartiles, for traceability)

    python3 scripts/gen_isj_ceiling_fig.py
"""
import hashlib, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# round isj3 r1 (2026-11-07): serif text as in the other figures; legend below the axes, off the plurality band
plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "cm", "font.size": 9})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "results", "novelty", "maxflow_decoder_iot23.jsonl")
OUT = os.environ.get("FHG_OUT") or os.path.join(ROOT, "out")  # artifact: writes out/generated, out/figures
ARMS = [("CA_P", "Plurality", "#7f7f7f", "o"), ("CA_A", "Abstention", "#1f77b4", "s"),
        ("CA_D", "Max-flow certified decoder", "#d62728", "^"), ("CA_MAX", "Competence ceiling (oracle)", "#000000", None)]  # round isj4: the locked term


def main():
    rows = [json.loads(l) for l in open(SRC) if l.strip()]
    ms = sorted(int(m) for m in rows[0]["by_m"])
    tau = float(np.median([r["tau"] for r in rows]))
    nums = {"source": os.path.relpath(SRC, ROOT), "source_sha256": hashlib.sha256(open(SRC, "rb").read()).hexdigest(),
            "n_draws": len(rows), "m": ms, "tau_median": tau, "arms": {}}
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    for key, label, colour, marker in ARMS:
        v = np.array([[r["by_m"][str(m)][key] for m in ms] for r in rows])
        med, q1, q3 = np.median(v, 0), np.percentile(v, 25, 0), np.percentile(v, 75, 0)
        nums["arms"][key] = {"median": med.round(4).tolist(), "q1": q1.round(4).tolist(), "q3": q3.round(4).tolist()}
        if marker is None:
            ax.plot(ms, med, color=colour, ls="--", lw=1.2, label=label)
        else:
            ax.plot(ms, med, color=colour, marker=marker, ms=4, lw=1.4, label=label)
            rgb = np.array(matplotlib.colors.to_rgb(colour))
            ax.fill_between(ms, q1, q3, color=tuple(1 - 0.12 * (1 - rgb)), lw=0, zorder=0)  # opaque tint: EPS has no alpha
    ax.axhline(tau, color="#999999", ls=":", lw=1.0)
    ax.text(ms[0] + 0.05, tau - 0.02, r"trivial floor $\tau_{\mathrm{triv}}$", ha="left", va="top", fontsize=8, color="#666666")
    ax.set_xlabel("malicious clients $m$ (of $N = 20$)")
    ax.set_ylabel("certified accuracy")
    ax.set_xticks(ms)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    fig.tight_layout()
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "generated"), exist_ok=True)
    for ext in ("pdf", "eps"):
        fig.savefig(os.path.join(OUT, "figures", f"fig_ceiling.{ext}"))
    json.dump(nums, open(os.path.join(OUT, "generated", "fig_ceiling_numbers.json"), "w"), indent=1)
    print("fig_ceiling:", {k: v["median"] for k, v in nums["arms"].items()}, "tau", tau)


if __name__ == "__main__":
    main()
