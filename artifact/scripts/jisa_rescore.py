#!/usr/bin/env python3
"""JISA revision, no-training items (PI 2026-10-16: "Re-scoring now, training later"). Post hoc re-analysis of
stored result rows plus partition rebuilds and arithmetic; no member is trained.

  python3 scripts/jisa_rescore.py      ->  results/jisa/rescore.json, results/jisa/rescore.md

Items (feedback/JISA_triage_and_plan.md, section 4):
  X3  K-matched device- vs label-Dirichlet comparison (PB13 rows; referee C4): the predeclared test restricted to
      draws with K = 20 in both families.
  R4  Paired exact McNemar test, coverage repair vs main grid, collapse at beta = 0.20, k = 1, seeds 10-39 (C6).
  B2  Household row counts of the main device-derived grid (partition rebuilds), and how collapse relates to
      one-class households and to small households (descriptive, post hoc).
  R8  Tie-aware ceiling at N = 20 for k = 1, 2, 3, and the bound it puts on certified accuracy (A2).
  R9  Benign false alarms per device per day at IoT-23's honeypot flow rates (B5).
  R2  The device-derived draw count behind the coverage-vote-model row (160 vs 150; C5).
"""
import glob, json, math, os, sys
from collections import Counter

import numpy as np
from scipy.stats import binom, spearmanr

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P2 = "<artifact-root>"
sys.path.insert(0, os.path.join(P2, "scripts", "tmlr_rev"))
OUTD = os.path.join(REPO, "results", "jisa")
os.makedirs(OUTD, exist_ok=True)
res, md = {}, ["# JISA re-scoring (no training; post hoc)", ""]


def perm_test(a, b, reps=100_000, seed=0):
    """Same statistic and RNG as scripts/tmlr_rev/pb13_15_runs.py:perm_test."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b]); n = len(a)
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(reps):
        p = rng.permutation(pool)
        if abs(p[:n].mean() - p[n:].mean()) >= abs(obs) - 1e-12:
            cnt += 1
    return float(obs), (cnt + 1) / (reps + 1)


# ----------------------------------------------------------------- X3: K-matched Dirichlet comparison
rows13 = [json.loads(l) for l in open(os.path.join(P2, "results", "tmlr_rev", "pb13_15_rows.jsonl")) if l.strip()]
rows13 = [r for r in rows13 if r.get("pb") == 13 and r["k"] == 1]
cell = lambda f, a: [r for r in rows13 if r["family"] == f and abs(r["alpha"] - a) < 1e-9]  # noqa: E731
kd = {f"{f}|{a}": dict(Counter(r["K"] for r in cell(f, a))) for f in ("dirichlet_device", "dirichlet")
      for a in (1.0, 0.5, 0.2, 0.1)}
x3 = {"K_distribution": kd}
md += ["## X3: device- vs label-Dirichlet, restricted to K = 20 (PB13 rows, k = 1)", "",
       "K per draw (family|alpha: {K: draws}): " + json.dumps(kd), ""]
for name, (fa, aa), (fb, ab) in (("primary (device 0.5 vs label 0.2)", ("dirichlet_device", 0.5), ("dirichlet", 0.2)),
                                 ("S2 (device 0.1 vs label 0.2)", ("dirichlet_device", 0.1), ("dirichlet", 0.2))):
    A, B = cell(fa, aa), cell(fb, ab)
    out = {}
    for lab, keep in (("all draws", lambda r: True), ("K = 20 only", lambda r: r["K"] == 20)):
        a = [r for r in A if keep(r)]; b = [r for r in B if keep(r)]
        dm, pm = perm_test([r["mean_margin"] for r in a], [r["mean_margin"] for r in b])
        db, pb = perm_test([r["beta_star"] for r in a], [r["beta_star"] for r in b])
        out[lab] = dict(n_device=len(a), n_label=len(b), margin_diff=round(dm, 4), margin_p=pm,
                        bstar_diff=round(db, 4), bstar_p=pb,
                        median_bstar_device=float(np.median([r["beta_star"] for r in a])) if a else None,
                        median_bstar_label=float(np.median([r["beta_star"] for r in b])) if b else None)
        md.append(f"- {name}, {lab}: n = {len(a)} vs {len(b)}; mean margin difference {dm:+.4f} (p = {pm:.5f}); "
                  f"beta* difference {db:+.4f} (p = {pb:.5f})")
    x3[name] = out
res["X3"] = x3
md.append("")

# ----------------------------------------------------------------- R4: paired McNemar, repair vs main grid
main = [json.loads(l) for l in open(os.path.join(REPO, "results", "canonical", "e5f_device_derived.jsonl"))
        if l.startswith("{")]
main = [r for r in main if r["k"] == 1 and r["partition_type"] == "device_derived"]
tau = float(np.median([r["tau_triv"] for r in main]))
coll_main = {}
for r in main:
    if abs(r["beta"] - 0.2) < 1e-9:
        coll_main[r["partition_seed"]] = r["CA"] <= r["tau_triv"]
rep = [json.loads(l) for l in open(os.path.join(P2, "results", "tmlr_rev", "pb04_rows.jsonl")) if l.strip()]
rep = [r for r in rep if r["arm"] == "a" and r["k"] == 1]
coll_rep = {r["seed"]: [g for g in r["grid"] if abs(g["beta"] - 0.2) < 1e-9][0]["CA"] <= tau for r in rep}
seeds = sorted(set(coll_main) & set(coll_rep))
b = sum(coll_main[s] and not coll_rep[s] for s in seeds)
c = sum(coll_rep[s] and not coll_main[s] for s in seeds)
n = b + c
p_mcn = min(1.0, 2 * binom.cdf(min(b, c), n, 0.5)) if n else 1.0
res["R4"] = dict(seeds=len(seeds), tau=tau, collapse_main=sum(coll_main[s] for s in seeds),
                 collapse_repair=sum(coll_rep[s] for s in seeds), discordant_main_only=b,
                 discordant_repair_only=c, exact_mcnemar_p=p_mcn)
md += ["## R4: coverage repair vs main grid, collapse at beta = 0.20, k = 1, paired on seeds", "",
       f"- {len(seeds)} paired seeds (10-39); collapse {res['R4']['collapse_main']} (main) vs "
       f"{res['R4']['collapse_repair']} (repair); discordant pairs {b} (main only) and {c} (repair only); "
       f"exact two-sided McNemar p = {p_mcn:.2e}", ""]

# ----------------------------------------------------------------- B2: household sizes in the main grid
import common as C  # noqa: E402  (scripts/tmlr_rev/common.py: the exact exp_e2.py partition build)
tb = C.prepare_base("iot-23")
ytr, dtr = tb["ytr_np"], tb["dtr"]
per_draw = []
for s in range(10, 40):
    cfg = C.base_cfg("iot-23", "device_derived", s, (1, 3))
    parts, meta = C.P.build(cfg, ytr, dtr)
    sizes = np.array([len(parts[i]) for i in range(20)])
    mal = np.array([ytr[parts[i]].mean() if len(parts[i]) else np.nan for i in range(20)])
    oneclass = (mal > 0.95) | (mal < 0.05)
    benign_only = mal < 0.05
    small = sizes < 1000
    per_draw.append(dict(seed=s, sizes=sizes.tolist(), n_small=int(small.sum()), n_oneclass=int(oneclass.sum()),
                         n_benign_only=int(benign_only.sum()), n_oneclass_small=int((oneclass & small).sum()),
                         n_oneclass_large=int((oneclass & ~small).sum()), frac_degenerate=meta["frac_degenerate"],
                         collapsed=bool(coll_main.get(s))))
allsizes = np.concatenate([d["sizes"] for d in per_draw])
q = np.percentile(allsizes, [0, 10, 25, 50, 75, 90, 100]).round(0).tolist()
coll = np.array([d["collapsed"] for d in per_draw])
ns = np.array([d["n_small"] for d in per_draw]); no = np.array([d["n_oneclass"] for d in per_draw])
nol = np.array([d["n_oneclass_large"] for d in per_draw])
rho_small = spearmanr(ns, coll).statistic if len(set(ns)) > 1 else None
rho_one = spearmanr(no, coll).statistic if len(set(no)) > 1 else None
res["B2"] = dict(size_percentiles_0_10_25_50_75_90_100=q, households=len(allsizes),
                 share_below_1000=float((allsizes < 1000).mean()),
                 oneclass_households=int(no.sum()), oneclass_small=int(sum(d["n_oneclass_small"] for d in per_draw)),
                 oneclass_large=int(nol.sum()), collapsed=int(coll.sum()),
                 spearman_collapse_vs_n_small=rho_small, spearman_collapse_vs_n_oneclass=rho_one,
                 collapsed_draws_with_oneclass_large_ge1=int(sum(c and d["n_oneclass_large"] >= 1
                                                                 for c, d in zip(coll, per_draw))),
                 per_draw=per_draw)
md += ["## B2: household row counts, main device-derived grid (seeds 10-39, 1-3 types, N = 20; rebuilt, no training)", "",
       f"- {len(allsizes)} households; row-count percentiles (0/10/25/50/75/90/100): {q}; "
       f"{100 * (allsizes < 1000).mean():.1f}% below 1,000 rows",
       f"- one-class households (>95% one class): {int(no.sum())} in total, {res['B2']['oneclass_small']} below 1,000 rows "
       f"and {int(nol.sum())} at or above; collapse at beta = 0.20 on {int(coll.sum())} of 30 draws",
       f"- collapsed draws with at least one one-class household of >= 1,000 rows: "
       f"{res['B2']['collapsed_draws_with_oneclass_large_ge1']} of {int(coll.sum())}",
       f"- Spearman, collapse vs number of small households {rho_small}; vs number of one-class households {rho_one}",
       ""]

# ----------------------------------------------------------------- R8: tie-aware ceiling
N = 20
r8 = {}
for k in (1, 2, 3):
    tot = math.comb(N, k)
    strict = max(m for m in range(N + 1) if math.comb(N - m, k) / tot > 0.5) / N
    tie = max(m for m in range(N + 1) if math.comb(N - m, k) / tot >= 0.5) / N
    r8[k] = dict(strict=strict, tie_aware=tie)
res["R8"] = dict(ceilings=r8, note="At k = 1 and m = 10 only a unanimous vote for the tie-winning class certifies; "
                 "ties break to benign, so certified accuracy is at most the benign share 1 - tau_triv = "
                 f"{1 - tau:.4f} < tau_triv = {tau:.4f}: the tie-aware rule cannot raise beta* above 0.45 here.")
md += ["## R8: tie-aware ceiling at N = 20", "",
       "- " + "; ".join(f"k = {k}: strict {v['strict']:.3f}, tie-aware {v['tie_aware']:.3f}" for k, v in r8.items()),
       "- " + res["R8"]["note"], ""]

# ----------------------------------------------------------------- R9: false alarms per device per day
iid = [json.loads(l) for l in open(os.path.join(REPO, "results", "canonical", "e5f_iid.jsonl")) if l.startswith("{")]
ben0 = [r["CTR_ben"] for r in iid if r["k"] == 1 and abs(r["beta"]) < 1e-9 and r.get("CTR_ben") is not None]
err = 1 - float(np.median(ben0)) if ben0 else None
r9 = dict(benign_error_iid_k1=err)
for cap in ("CTU-Honeypot-Capture-4-1", "CTU-Honeypot-Capture-5-1"):
    ts = []
    for line in open(os.path.join(REPO, "data", "raw", "iot23", f"{cap}.conn.log.labeled"), errors="replace"):
        if line.startswith("#"):
            continue
        try:
            ts.append(float(line.split("\t")[0].split()[0]))
        except ValueError:
            pass
    days = (max(ts) - min(ts)) / 86400 if len(ts) > 1 else None
    r9[cap] = dict(flows=len(ts), days=days, flows_per_day=(len(ts) / days if days else None),
                   alarms_per_day=(len(ts) / days * err if days and err is not None else None))
res["R9"] = r9
md += ["## R9: benign false alarms at IoT-23's honeypot flow rates (IID ensemble, k = 1, no adversary)", "",
       f"- benign error {err:.4f} (1 - median certified benign rate at beta = 0, which at m = 0 is the benign accuracy)"]
for cap in ("CTU-Honeypot-Capture-4-1", "CTU-Honeypot-Capture-5-1"):
    v = r9[cap]
    md.append(f"- {cap}: {v['flows']} flows over {v['days']:.2f} days = {v['flows_per_day']:.0f} flows/day -> "
              f"{v['alarms_per_day']:.1f} false alarms/day for that one device")
md.append("")

# ----------------------------------------------------------------- R2: 160 vs 150
cvm = json.load(open(os.path.join(P2, "results", "tmlr_rev", "pb03_cvm.json"))) if os.path.exists(
    os.path.join(P2, "results", "tmlr_rev", "pb03_cvm.json")) else {}
dd = [ln for ln in open(os.path.join(P2, "results", "tmlr_rev", "pb03_cvm_draws.jsonl"))] if os.path.exists(
    os.path.join(P2, "results", "tmlr_rev", "pb03_cvm_draws.jsonl")) else []
dd = [json.loads(l) for l in dd if l.strip()]
iot_dd = [r for r in dd if r["dataset"] == "iot-23" and r["kind"] == "device_derived" and r["k"] == 1]
uniq = {(tuple(r["dph"]), r["seed"]) for r in iot_dd}
by_level = Counter(tuple(r["dph"]) for r in {(tuple(r["dph"]), r["seed"]): r for r in iot_dd}.values())
res["R2"] = dict(unique_device_derived_k1_draws=len(uniq), by_level={str(k): v for k, v in by_level.items()})
md += ["## R2: device-derived draws behind the count rule's IoT-23 row (k = 1)", "",
       f"- {len(uniq)} unique (devices-per-household level, seed) draws; by level: {dict(by_level)}", ""]

json.dump(res, open(os.path.join(OUTD, "rescore.json"), "w"), indent=1, default=float)
open(os.path.join(OUTD, "rescore.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
