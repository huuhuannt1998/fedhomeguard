#!/usr/bin/env python3
"""Score the JISA training round against its predeclarations (no training):
  predeclarations/jisa_X1_X2_X4_seeds_budget_multiclass.md   X1 member seeds, X2 step budget, X4 8-class grid
  predeclarations/jisa_JS02_JS03_size_capacity.md             JS02 federation size, JS03 member capacity
Writes results/jisa/score.json and score.md. Collapse at (k, beta): certified accuracy at or below tau_triv.
beta*: the largest grid beta whose certified accuracy exceeds tau_triv (0 if none).
"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from aggregate import src  # noqa: E402

J = os.path.join(REPO, "results", "jisa")
PB04 = "<artifact-root>/results/tmlr_rev/pb04_rows.jsonl"
res, md = {}, ["# JISA training round: predeclared predictions scored", ""]


def rows(path):
    return [json.loads(l) for l in open(path) if l.startswith("{")]


def per_draw(rr, k):
    """partition_seed -> {beta: row} for clean rows at k (malicious-set seed 0)."""
    d = defaultdict(dict)
    for r in rr:
        if r["k"] == k and r.get("mal_seed", 0) == 0:
            d[r["partition_seed"]][round(r["beta"], 4)] = r
    return d


def bstar(bmap):
    ok = [b for b, r in bmap.items() if r["CA"] > r["tau_triv"] + 1e-12]
    return max(ok) if ok else 0.0


def collapse(bmap, b=0.2):
    r = bmap[round(b, 4)]
    return r["CA"] <= r["tau_triv"] + 1e-12


def mcnemar(a, b):
    """Exact two-sided McNemar on paired booleans a, b."""
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n10 + n01
    if n == 0:
        return n10, n01, 1.0
    lo = min(n10, n01)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(lo + 1)) / 2 ** n)
    return n10, n01, p


def wilson(x, n, z=1.959963984540054):
    p = x / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def verdict(ok):
    return "HOLDS" if ok else "FAILS"


SEEDS = range(10, 40)

# ================================================================== X1: member seeds
main = {0: {p: rows(os.path.join(REPO, "results", "canonical", f"e5f_{p}.jsonl")) for p in ("iid", "device_derived")}}
for s in (1, 2, 3, 4):
    main[s] = {p: rows(os.path.join(J, f"x1_main_{p}_s{s}.jsonl")) for p in ("iid", "device_derived")}
xr = rows(os.path.join(J, "x_runs.jsonl"))
rep = {0: {r["seed"]: r for r in (json.loads(l) for l in open(PB04) if l.strip()) if r["arm"] == "a" and r["k"] == 1}}
for s in (1, 2, 3, 4):
    rep[s] = {r["pseed"]: r for r in xr if r["arm"] == "repair" and r["member_seed"] == s}


def rep_collapse(r):
    g = next(g for g in r["grid"] if abs(g["beta"] - 0.2) < 1e-9)
    return g["CA"] <= r.get("tau", 0.7300) + 1e-12


x1 = {}
status = defaultdict(list)
for s in range(5):
    dd1, dd2 = per_draw(main[s]["device_derived"], 1), per_draw(main[s]["device_derived"], 2)
    ii1, ii2 = per_draw(main[s]["iid"], 1), per_draw(main[s]["iid"], 2)
    assert set(dd1) == set(SEEDS) and set(ii2) == set(SEEDS), (s, len(dd1), len(ii2))
    mc = [collapse(dd1[p]) for p in SEEDS]
    rc = [rep_collapse(rep[s][p]) for p in SEEDS]
    for p, c in zip(SEEDS, mc):
        status[p].append(c)
    n10, n01, pval = mcnemar(mc, rc)
    x1[s] = dict(main_collapse=sum(mc), repair_collapse=sum(rc), mcnemar_main_only=n10, mcnemar_repair_only=n01,
                 mcnemar_p=pval,
                 iid_at_ceiling_k1=sum(bstar(ii1[p]) == 0.45 for p in SEEDS),
                 iid_at_ceiling_k2=sum(bstar(ii2[p]) == 0.25 for p in SEEDS),
                 dd_median_bstar_k1=st.median(bstar(dd1[p]) for p in SEEDS),
                 dd_median_bstar_k2=st.median(bstar(dd2[p]) for p in SEEDS),
                 dd_median_margin_k1=st.median(dd1[p][0.0]["mean_vote_margin"] for p in SEEDS))
new = (1, 2, 3, 4)
pred = dict(
    X1a=all(x1[s]["main_collapse"] >= 23 for s in new),
    X1b=all(x1[s]["repair_collapse"] <= 4 and x1[s]["mcnemar_p"] < 0.001 for s in new),
    X1c=all(x1[s]["iid_at_ceiling_k1"] >= 28 and x1[s]["iid_at_ceiling_k2"] >= 28 for s in new),
    X1d=all(abs(x1[s]["dd_median_bstar_k1"] - 0.05) <= 0.05 + 1e-9 and abs(x1[s]["dd_median_bstar_k2"] - 0.15)
            <= 0.05 + 1e-9 for s in new))
stable = sum(len(set(v)) == 1 for v in status.values())
res["X1"] = dict(per_seed=x1, predictions=pred, stable_collapse_status_all_5_seeds=stable,
                 main_collapse_range=[min(x1[s]["main_collapse"] for s in range(5)),
                                      max(x1[s]["main_collapse"] for s in range(5))],
                 repair_collapse_range=[min(x1[s]["repair_collapse"] for s in range(5)),
                                        max(x1[s]["repair_collapse"] for s in range(5))])
md += ["## X1: member seeds 0-4 (seed 0 = the paper)", "",
       "| seed | main collapse | repair collapse | McNemar (main only / repair only, p) | IID at ceiling k=1, k=2 | "
       "dd median beta* k=1, k=2 | dd median margin k=1 |", "|---|---|---|---|---|---|---|"]
for s in range(5):
    v = x1[s]
    md.append(f"| {s} | {v['main_collapse']}/30 | {v['repair_collapse']}/30 | {v['mcnemar_main_only']} / "
              f"{v['mcnemar_repair_only']}, {v['mcnemar_p']:.2e} | {v['iid_at_ceiling_k1']}, {v['iid_at_ceiling_k2']} | "
              f"{v['dd_median_bstar_k1']:.3f}, {v['dd_median_bstar_k2']:.3f} | {v['dd_median_margin_k1']:.4f} |")
md += ["", f"- Same collapse status at all five seeds: {stable} of 30 device-derived draws.",
       f"- Main-grid collapse range over seeds: {res['X1']['main_collapse_range']}; repair: "
       f"{res['X1']['repair_collapse_range']}."] + [f"- {k}: {verdict(v)}" for k, v in pred.items()] + [""]

# ================================================================== X2: step-budget-scaled arms
mb = {r["pseed"]: r for r in xr if r["arm"] == "main_budget"}
rb = {r["pseed"]: r for r in xr if r["arm"] == "repair_budget"}
mcb = [mb[p]["collapse20"] for p in SEEDS]
rcb = [rb[p]["collapse20"] for p in SEEDS]
n10, n01, pval = mcnemar(mcb, rcb)


def small_share(rr):
    sizes = [v for r in rr for v in r["sizes"].values()]
    return sum(v < 1000 for v in sizes) / len(sizes), len(sizes)


x2 = dict(main_budget_collapse=sum(mcb), repair_budget_collapse=sum(rcb), mcnemar_main_only=n10,
          mcnemar_repair_only=n01, mcnemar_p=pval,
          main_budget_median_bstar=st.median(mb[p]["beta_star"] for p in SEEDS),
          repair_budget_median_bstar=st.median(rb[p]["beta_star"] for p in SEEDS),
          main_budget_median_margin=st.median(mb[p]["mean_margin"] for p in SEEDS),
          repair_budget_median_margin=st.median(rb[p]["mean_margin"] for p in SEEDS),
          main_share_households_under_1000_rows=small_share(mb.values()),
          repair_share_households_under_1000_rows=small_share(rb.values()),
          main_max_epochs=max(max(r["epochs"].values()) for r in mb.values()),
          repair_max_epochs=max(max(r["epochs"].values()) for r in rb.values()))
pred2 = dict(X2a=x2["main_budget_collapse"] >= 20, X2a_falsifier_fired=x2["main_budget_collapse"] <= 10,
             X2b=x2["repair_budget_collapse"] <= 4, X2c=x2["mcnemar_p"] < 0.001)
res["X2"] = dict(**x2, predictions=pred2)
md += ["## X2: step-budget-scaled main grid and repair (member seed 0, k = 1)", "",
       f"- Collapse at beta = 0.20: main_budget {x2['main_budget_collapse']}/30, repair_budget "
       f"{x2['repair_budget_collapse']}/30; McNemar {n10} / {n01}, p = {pval:.2e}.",
       f"- Median beta*: {x2['main_budget_median_bstar']:.3f} and {x2['repair_budget_median_bstar']:.3f}; median "
       f"margin {x2['main_budget_median_margin']:.4f} and {x2['repair_budget_median_margin']:.4f}.",
       f"- Households under 1,000 rows: main {x2['main_share_households_under_1000_rows'][0]:.3f}, repair "
       f"{x2['repair_share_households_under_1000_rows'][0]:.3f}; max epochs per round {x2['main_max_epochs']} and "
       f"{x2['repair_max_epochs']}."] + [f"- {k}: {verdict(v) if not k.endswith('fired') else v}"
                                         for k, v in pred2.items()] + [""]

# ================================================================== X4: 8-class grid
mc_rows = {p: rows(src(f"e25_multiclass_{p}.jsonl")) for p in ("iid", "device_derived")}
x4 = {}
for p in ("iid", "device_derived"):
    d1 = per_draw(mc_rows[p], 1)
    x4[p] = dict(median_bstar_k1=st.median(bstar(d1[s]) for s in SEEDS),
                 collapse20_k1=sum(collapse(d1[s]) for s in SEEDS))
rer = {p: per_draw(rows(os.path.join(J, f"x4_multiclass_k1_{p}.jsonl")), 1) for p in ("iid", "device_derived")}
ctrl = max(abs(rer[p][s][b]["CA"] - per_draw(mc_rows[p], 1)[s][b]["CA"])
           for p in rer for s in SEEDS for b in rer[p][s])
fam = {}
for p in ("iid", "device_derived"):
    by = defaultdict(list)
    for s in SEEDS:
        for f, v in (rer[p][s][0.0].get("CTR_mal_by_family") or {}).items():
            by[f].append(v)
    fam[p] = {f: st.median(v) for f, v in by.items()}
fams = sorted(set(fam["iid"]) & set(fam["device_derived"]))
pred4 = dict(X4a=x4["device_derived"]["median_bstar_k1"] <= x4["iid"]["median_bstar_k1"] - 0.05 + 1e-9,
             X4b=x4["device_derived"]["collapse20_k1"] >= 20,
             X4c=all(fam["device_derived"][f] < fam["iid"][f] for f in fams))
res["X4"] = dict(stored=x4, rerun_control_max_abs_CA_diff=ctrl, per_family_detection_k1_beta0=fam,
                 predictions=pred4)
md += ["## X4: 8-class grid (stored rows; per-family detection from the k = 1 re-run)", "",
       f"- Re-run control: max |CA difference| against the stored rows {ctrl:.2e} (must be 0).",
       f"- Median beta* at k = 1: IID {x4['iid']['median_bstar_k1']:.3f}, device-derived "
       f"{x4['device_derived']['median_bstar_k1']:.3f}; device-derived collapse at beta = 0.20: "
       f"{x4['device_derived']['collapse20_k1']}/30 (IID {x4['iid']['collapse20_k1']}/30).",
       "- Median certified detection per family at k = 1, beta = 0 (IID / device-derived): " +
       "; ".join(f"{f} {fam['iid'][f]:.3f} / {fam['device_derived'][f]:.3f}" for f in fams)] + \
    [f"- {k}: {verdict(v)}" for k, v in pred4.items()] + [""]

# ================================================================== JS02: federation size
js2 = {}
for N in (10, 50):
    d = {p: per_draw(rows(os.path.join(J, f"js02_N{N}_{p}.jsonl")), 1) for p in ("iid", "device_derived")}
    any_iid = next(iter(d["iid"].values()))
    # the ceiling read on the grid: the largest grid beta whose m (as exp_e2 sets it) keeps p_clean > 1/2
    ceil_grid = max(b for b, r in any_iid.items() if (N - r["m"]) / N > 0.5)
    js2[N] = dict(ceiling_on_grid=ceil_grid,
                  iid_at_ceiling=sum(bstar(d["iid"][s]) == ceil_grid for s in SEEDS),
                  dd_median_bstar=st.median(bstar(d["device_derived"][s]) for s in SEEDS),
                  dd_median_margin=st.median(d["device_derived"][s][0.0]["mean_vote_margin"] for s in SEEDS),
                  dd_collapse20=sum(collapse(d["device_derived"][s]) for s in SEEDS))
d20 = per_draw(main[0]["device_derived"], 1)
js2[20] = dict(dd_median_bstar=st.median(bstar(d20[s]) for s in SEEDS),
               dd_median_margin=st.median(d20[s][0.0]["mean_vote_margin"] for s in SEEDS),
               dd_collapse20=sum(collapse(d20[s]) for s in SEEDS))
lo, hi = wilson(27, 30)
pred_js2 = dict(J2a=all(js2[N]["iid_at_ceiling"] >= 28 for N in (10, 50)),
                J2b=all(abs(js2[N]["dd_median_bstar"] - 0.05) <= 0.05 + 1e-9 for N in (10, 50))
                and js2[50]["dd_median_margin"] <= js2[10]["dd_median_margin"] + 1e-12,
                J2c=all(lo <= js2[N]["dd_collapse20"] / 30 <= hi for N in (10, 50)))
res["JS02"] = dict(per_N=js2, wilson_27_of_30=[lo, hi], predictions=pred_js2)
md += ["## JS02: federation size (k = 1)", "",
       "| N | IID at ceiling (grid value) | dd median beta* | dd median margin | dd collapse at 0.20 |",
       "|---|---|---|---|---|"]
for N in (10, 20, 50):
    v = js2[N]
    md.append(f"| {N} | {v.get('iid_at_ceiling', '-')} ({v.get('ceiling_on_grid', '-')}) | {v['dd_median_bstar']:.3f} | "
              f"{v['dd_median_margin']:.4f} | {v['dd_collapse20']}/30 |")
md += [""] + [f"- {k}: {verdict(v)}" for k, v in pred_js2.items()] + [""]

# ================================================================== JS03: member capacity
L = {p: per_draw(rows(os.path.join(J, f"js03_large_{p}.jsonl")), 1) for p in ("iid", "device_derived")}
S20 = {p: per_draw(main[0][p], 1) for p in ("iid", "device_derived")}
same = sum(bstar(L["device_derived"][s]) == bstar(S20["device_derived"][s]) for s in SEEDS)
dacc = [L["device_derived"][s][0.0]["clean_ensemble_acc"] - S20["device_derived"][s][0.0]["clean_ensemble_acc"]
        for s in SEEDS]
dmar = [L["device_derived"][s][0.0]["mean_vote_margin"] - S20["device_derived"][s][0.0]["mean_vote_margin"]
        for s in SEEDS]
iid_ceil = sum(bstar(L["iid"][s]) == 0.45 for s in SEEDS)
pred_js3 = dict(J3a=same >= 25, J3b=st.median(dacc) > 0 and st.median(dmar) <= 0.05, J3c=iid_ceil >= 28)
res["JS03"] = dict(dd_bstar_unchanged=same, median_paired_acc_gain=st.median(dacc),
                   median_paired_margin_gain=st.median(dmar), iid_at_ceiling=iid_ceil,
                   dd_median_bstar_large=st.median(bstar(L["device_derived"][s]) for s in SEEDS),
                   predictions=pred_js3)
md += ["## JS03: member capacity (128-64-32 against 32-16, k = 1, paired by draw)", "",
       f"- Device-derived beta* unchanged on {same}/30 draws; median paired gain in clean ensemble accuracy "
       f"{st.median(dacc):+.4f}, in vote margin {st.median(dmar):+.4f}; IID at the ceiling {iid_ceil}/30."] + \
    [f"- {k}: {verdict(v)}" for k, v in pred_js3.items()] + [""]

json.dump(res, open(os.path.join(J, "score.json"), "w"), indent=1, default=float)
open(os.path.join(J, "score.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
