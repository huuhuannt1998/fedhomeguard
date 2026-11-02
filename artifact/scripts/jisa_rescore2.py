#!/usr/bin/env python3
"""JISA round jisa4 re-scoring (2026-10-16): no training, stored result rows only.

  C5   The count rule (coverage-vote model) per device-type level of the IoT-23 device-derived draws: how many draws
       sit at each level, and how often the predicted beta* is exact and within one 0.05 grid step (k = 1 and 2).
       Same rows and the same scoring as Table C.6 (gen_tmlr2_tables.cvm_groups, dev_unique).
  C10  How fragile the 1% attack-prior result is: for each (partition, k, beta) cell, the smallest attack prior pi at
       which the median certified accuracy re-weighted to pi, pi * CTR_mal + (1 - pi) * CTR_ben, beats the constant
       benign predictor's 1 - pi. On the 36 cells of the same-predictor rows the paper's 1% statement uses
       (gen_r8_prior.py; 3 draws each) and on the 30-draw main grid (results/canonical/e5f_*.jsonl, k = 1 and 2).
  A4   A prior-free beta*: the largest grid beta at which certified balanced accuracy, (CTR_mal + CTR_ben) / 2,
       exceeds 0.5, per draw of the 30-draw main grid, beside the paper's beta* (certified accuracy above tau_triv);
       and the IoT-23 against N-BaIoT contrast on that common floor (rows and the per-(draw, beta) minimum over
       malicious sets as gen_crossdataset.cert_cells; added after AutoResearchClaw follow-up f3).

Writes results/jisa/rescore2.json and rescore2.md. Leaves results/jisa/rescore.json (round jisa2) unchanged.
"""
import json
import os
import statistics as st
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aggregate import load, src  # noqa: E402

REPO = os.path.dirname(HERE)
RES = os.path.join(REPO, "results", "tmlr_rev")
OUTD = os.path.join(REPO, "results", "jisa")
STEP = 0.05
res, md = {}, ["# JISA re-scoring, round jisa4 (no training)", ""]

# ----------------------------------------------------------------- C5: the count rule per device-type level
draws = [json.loads(l) for l in open(os.path.join(RES, "pb03_cvm_draws.jsonl")) if l.strip()]
md += ["## C5: count rule per device-type level (IoT-23 device-derived; each (level, seed) draw counted once)", ""]
res["C5"] = {}
for k in (1, 2):
    seen, lv = set(), defaultdict(list)
    for r in draws:
        if r["dataset"] == "iot-23" and r["kind"] == "device_derived" and r["k"] == k:
            key = (tuple(r["dph"]), r["seed"])
            if key not in seen:
                seen.add(key)
                lv[tuple(r["dph"])].append((r["bstar_pred"], r["bstar_obs"]))
    allerr, rows = [], {}
    for L in sorted(lv):
        p = np.array(lv[L])
        e = np.round((p[:, 0] - p[:, 1]) / STEP)
        allerr += list(e)
        rows[f"{L[0]}-{L[1]}"] = dict(draws=len(p), exact=int((e == 0).sum()), within_one=int((abs(e) <= 1).sum()),
                                      mean_error_steps=float(e.mean()),
                                      both_zero=int(((p[:, 0] == 0) & (p[:, 1] == 0)).sum()))
    allerr = np.array(allerr)
    res["C5"][f"k={k}"] = dict(levels=rows, draws=int(len(allerr)), within_one=int((abs(allerr) <= 1).sum()))
    md.append(f"- k = {k}: {int((abs(allerr) <= 1).sum())} of {len(allerr)} within one step overall")
    for L, v in rows.items():
        md.append(f"  - {L} types: {v['within_one']} of {v['draws']} within one step, {v['exact']} exact, mean error "
                  f"{v['mean_error_steps']:+.2f} steps, {v['both_zero']} with predicted and observed beta* both 0")
md.append("")
c5 = res["C5"]["k=1"]
assert c5["draws"] == 160 and c5["within_one"] == 135, c5      # 84.4% of 160, as printed (Table C.6)

# ----------------------------------------------------------------- C10: break-even attack prior per cell
rows = load(src("e2_*.jsonl"))
assert not [r for r in rows
            if abs(r["CA"] - (r["tau_triv"] * r["CTR_mal"] + (1 - r["tau_triv"]) * r["CTR_ben"])) > 1e-5]
cells = defaultdict(list)
for r in rows:
    cells[(r["partition_type"], r["k"], round(r["beta"], 4))].append(r)
GRID = [i / 10000 for i in range(1, 5001)]                      # attack priors 0.0001 .. 0.5


def breakeven(v):
    for pi in GRID:
        if st.median([pi * r["CTR_mal"] + (1 - pi) * r["CTR_ben"] for r in v]) > 1 - pi + 1e-12:
            return pi
    return None


be = {(p, k, b): breakeven(v) for (p, k, b), v in sorted(cells.items())}
some = {kk for kk, v in cells.items() if st.median([r["CA"] for r in v]) > 0}
reach = {kk: v for kk, v in be.items() if v is not None}
reach2 = {kk: v for kk, v in reach.items() if kk[1] <= 2}
assert len(cells) == 36                                          # \prCells
res["C10"] = dict(cells=len(cells), cells_median_ca_positive=len(some), cells_beating_at_some_prior_le_0_5=len(reach),
                  min_breakeven_prior=min(reach.values()), min_breakeven_prior_k_le_2=min(reach2.values()),
                  iid_k1_beta0=be[("iid", 1, 0.0)], iid_k1_beta04=be[("iid", 1, 0.4)],
                  per_cell={f"{p}|k={k}|beta={b}": v for (p, k, b), v in be.items()})
md += ["## C10: smallest attack prior at which a cell's median re-weighted certified accuracy beats 1 - pi", "",
       f"- {len(cells)} cells ({len(some)} with median certified accuracy above 0); {len(reach)} beat the constant "
       f"benign predictor at some prior up to 0.5; the smallest such prior is {min(reach.values())} "
       f"({min(reach2.values())} at k <= 2)",
       f"- IID, k = 1: {be[('iid', 1, 0.0)]} at beta = 0, {be[('iid', 1, 0.4)]} at beta = 0.4", ""]
for (p, k, b), v in be.items():
    md.append(f"  - {p}, k = {k}, beta = {b}: {v}")


# ----------------------------------------------------------------- C10 and A4 on the 30-draw main grid
def first_prior(v):
    for pi in GRID:
        if st.median([pi * r["CTR_mal"] + (1 - pi) * r["CTR_ben"] for r in v]) > 1 - pi + 1e-12:
            return pi
    return None


main = {}
for kind in ("iid", "device_derived"):
    rr = [json.loads(l) for l in open(os.path.join(REPO, "results", "canonical", f"e5f_{kind}.jsonl")) if l.strip()]
    assert not [r for r in rr if abs(r["CA"] - (r["tau_triv"] * r["CTR_mal"] + (1 - r["tau_triv"]) * r["CTR_ben"])) > 1e-5]
    for k in (1, 2):
        by_beta, by_seed = defaultdict(list), defaultdict(dict)
        for r in rr:
            if r["k"] == k:
                by_beta[round(r["beta"], 4)].append(r)
                by_seed[r["partition_seed"]][round(r["beta"], 4)] = r
        assert len(by_seed) == 30
        bt, bb = [], []
        for m in by_seed.values():
            ok_t = [b for b, r in m.items() if r["CA"] > r["tau_triv"] + 1e-12]
            ok_b = [b for b, r in m.items() if (r["CTR_mal"] + r["CTR_ben"]) / 2 > 0.5 + 1e-12]
            bt.append(max(ok_t) if ok_t else 0.0)
            bb.append(max(ok_b) if ok_b else 0.0)
        main[f"{kind}|k={k}"] = dict(
            draws=30, beta_star_median=st.median(bt), beta_star_mean=st.mean(bt),
            beta_star_balanced_median=st.median(bb), beta_star_balanced_mean=st.mean(bb),
            breakeven_prior={str(b): first_prior(v) for b, v in sorted(by_beta.items())})
reach30 = [x for v in main.values() for x in v["breakeven_prior"].values() if x is not None]
res["C10_main_grid"] = dict(min_breakeven_prior=min(reach30), cells={kk: v["breakeven_prior"] for kk, v in main.items()})
res["A4_main_grid"] = {kk: {x: v[x] for x in ("draws", "beta_star_median", "beta_star_mean", "beta_star_balanced_median",
                                              "beta_star_balanced_mean")} for kk, v in main.items()}
md += ["", "## C10 on the 30-draw main grid (k = 1 and 2)", "",
       f"- smallest attack prior at which any cell's median beats 1 - pi: {min(reach30)}"]
for kk, v in main.items():
    md.append(f"  - {kk}: " + ", ".join(f"beta {b}: {x}" for b, x in v["breakeven_prior"].items()))
md += ["", "## A4: prior-free beta* (certified balanced accuracy above 0.5) on the 30-draw main grid", ""]
for kk, v in main.items():
    md.append(f"- {kk}: beta* median {v['beta_star_median']:.3f} (mean {v['beta_star_mean']:.3f}); balanced "
              f"median {v['beta_star_balanced_median']:.3f} (mean {v['beta_star_balanced_mean']:.3f})")


# ----------------------------------------------------------------- A4: the cross-corpus contrast on a common floor
import glob  # noqa: E402


def cross(pattern):
    ca, bal, tau = defaultdict(dict), defaultdict(dict), {}
    for f in glob.glob(os.path.join(REPO, pattern)):
        for line in open(f):
            if not line.startswith("{"):
                continue
            r = json.loads(line)
            key = (r["partition_type"], int(r["k"]), int(r["partition_seed"]))
            b = round(float(r["beta"]), 4)
            ca[key][b] = min(ca[key].get(b, r["CA"]), r["CA"])
            bb = (r["CTR_mal"] + r["CTR_ben"]) / 2
            bal[key][b] = min(bal[key].get(b, bb), bb)
            tau[key] = r["tau_triv"]
    out = defaultdict(lambda: ([], []))
    for key in ca:
        ok = [b for b, v in ca[key].items() if v > tau[key] + 1e-9]
        okb = [b for b, v in bal[key].items() if v > 0.5 + 1e-9]
        out[f"{key[0]}|k={key[1]}"][0].append(max(ok) if ok else 0.0)
        out[f"{key[0]}|k={key[1]}"][1].append(max(okb) if okb else 0.0)
    return {kk: dict(draws=len(a), beta_star_mean=st.mean(a), beta_star_balanced_mean=st.mean(b))
            for kk, (a, b) in out.items()}


res["A4_cross_corpus"] = {"N-BaIoT": cross("results/canonical/nb9_cert_*.jsonl"),
                          "IoT-23": cross("results/canonical/e5f_*.jsonl")}
md += ["", "## A4: IoT-23 against N-BaIoT, mean beta* on the paper's floors and on a common prior-free floor", ""]
for corpus, d in res["A4_cross_corpus"].items():
    for kk, v in sorted(d.items()):
        md.append(f"- {corpus} {kk}: {v['draws']} draws, mean beta* {v['beta_star_mean']:.3f} (tau floor), "
                  f"{v['beta_star_balanced_mean']:.3f} (balanced accuracy above 0.5)")

os.makedirs(OUTD, exist_ok=True)
json.dump(res, open(os.path.join(OUTD, "rescore2.json"), "w"), indent=1, default=float)
open(os.path.join(OUTD, "rescore2.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md[-12:]))
