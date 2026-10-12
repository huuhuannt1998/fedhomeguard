#!/usr/bin/env python3
"""P0 (part 2): independent recomputation of the appendix numbers (Tables 8-10, LOCO, 8-class,
purpose-built attack, sampled touched fraction, cost arithmetic). Writes results/p0_recompute2.json."""
import collections, glob, json, math, os, statistics as st, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
CORR = os.path.join(C.REPO, "results/r6_nan_fix/corrected")
def rows(p, base=C.CANON):
    return [r for f in sorted(glob.glob(os.path.join(base, p))) for r in C.load_rows(f)]
med = lambda x: float(np.median(x)) if len(x) else None
res = {}
e2 = rows("e2_*.jsonl", CORR)
t9 = {}
for p in ("iid", "device_derived"):
    for k in (1, 2, 3):
        for b in (0, .05, .1, .2, .3, .4):
            v = [r for r in e2 if r["partition_type"] == p and r["k"] == k and abs(r["beta"] - b) < 1e-9]
            eaf = [min(r["EA_final_round"].values()) if r["EA_final_round"] else r["EA_ensemble"] for r in v]
            t9[f"{p}|k{k}|b{b:g}"] = dict(CA=med([r["CA"] for r in v]), EA_final=med(eaf),
                                          EA_window=med([r["EA_ensemble"] for r in v]),
                                          G=med([r["G_cert"] for r in v]), n=len(v),
                                          row_max_G=max(r["G_cert"] for r in v))
res["table9"] = t9
# Table 8: predictor loss = EA_iid - EA_dev (medians), added slack = (EA-CA)_dev - (EA-CA)_iid
t8 = {}
for k, b in ((1, .05), (1, .1), (2, .05), (2, .1), (2, .2), (3, .05), (3, .1)):
    i, d = t9[f"iid|k{k}|b{b:g}"], t9[f"device_derived|k{k}|b{b:g}"]
    t8[f"k{k}|b{b:g}"] = dict(pred_loss=i["EA_final"] - d["EA_final"],
                              added_slack=(d["EA_final"] - d["CA"]) - (i["EA_final"] - i["CA"]),
                              drop=i["CA"] - d["CA"])
res["table8"] = t8
res["table8_added_slack_larger"] = sum(v["added_slack"] > v["pred_loss"] for v in t8.values())
res["largest_single_row_slack_dev"] = max(r["G_cert"] for r in e2 if r["partition_type"] == "device_derived"
                                          and r["combinatorially_possible"] and r["G_cert"] is not None)
# Table 10: k = 2 detection metrics, which source matches
for name, src in (("e2_corrected", e2), ("e5f", rows("e5f_*.jsonl"))):
    t10 = {}
    for p in ("iid", "device_derived"):
        for b in (0, .05, .1, .2, .3, .4):
            v = [r for r in src if r["partition_type"] == p and r["k"] == 2 and abs(r["beta"] - b) < 1e-9]
            t10[f"{p}|b{b:g}"] = [round(med([r[f] for r in v]), 4) for f in ("coverage", "CTR_mal", "CTR_ben", "cert_wrong")] + [len(v)]
    res[f"table10_{name}"] = t10
# LOCO
lo = [r for r in rows("e16_lodo.jsonl") if r["beta"] == 0]
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in lo:
    by[r["tag"]][r["partition_type"]].append(r)
folds = []
for tag, d in by.items():
    tau = next(iter(d.values()))[0]["tau_triv"]
    ca = {p: med([x["CA"] for x in v]) for p, v in d.items()}
    folds.append(dict(fold=tag, tau=tau, ca=ca, beats=max(ca.values()) > tau,
                      diff=abs(ca["iid"] - ca["device_derived"])))
res["loco"] = dict(n=len(folds), tau_min=min(f["tau"] for f in folds), tau_max=max(f["tau"] for f in folds),
                   n_beats=sum(f["beats"] for f in folds),
                   n_tau_ge_099=sum(f["tau"] >= 0.99 for f in folds),
                   med_diff=med([f["diff"] for f in folds]), max_diff=max(f["diff"] for f in folds),
                   max_diff_in_beating=max([f["diff"] for f in folds if f["beats"]], default=None),
                   folds=folds)
# 8-class control
mc = rows("e25_multiclass_*.jsonl", CORR)
mci = [r for r in mc if r["partition_type"] == "iid"]
g1 = [r["G_cert"] for r in mci if r["k"] == 1 and r["combinatorially_possible"] and r["G_cert"] is not None]
g2 = [r["G_cert"] for r in mci if r["k"] == 2 and r["combinatorially_possible"] and r["G_cert"] is not None]
r04 = [r for r in mci if r["k"] == 1 and abs(r["beta"] - 0.4) < 1e-9]
pc = collections.defaultdict(list)
for r in r04:
    for c, v in (r["per_class_certified"] or {}).items():
        pc[c].append(v["certified_correct"])
res["multiclass"] = dict(tau=mci[0]["tau_triv"], n_draws=len({r["partition_seed"] for r in mci}),
                         max_G_k1=max(g1), max_G_k2=max(g2),
                         clean_acc=med([r["clean_ensemble_acc"] for r in mci if r["k"] == 1 and r["beta"] == 0]),
                         k1_b04_coverage=med([r["coverage"] for r in r04]), k1_b04_CA=med([r["CA"] for r in r04]),
                         per_class_certified_median={c: med(v) for c, v in pc.items()},
                         n_classes_with_rows=len(pc),
                         n_classes_over_half=sum(med(v) > 0.5 for v in pc.values()),
                         dev_max_G_k2_b02=max(r["G_cert"] for r in mc if r["partition_type"] == "device_derived"
                                              and r["k"] == 2 and abs(r["beta"] - .2) < 1e-9))
# purpose-built (adaptive) attack: cells where it beats the five published attacks
ad = rows("adaptive_*.jsonl", CORR)
ad = [r for r in ad if r.get("partition_type") in ("iid", "device_derived") and r.get("EA_per_attack")]
res["adaptive_rows"] = len(ad)
res["adaptive_keys_example"] = sorted(ad[0].keys())[:60] if ad else None
# touched fraction of the sampled k=5 ensembles at m=2
cm = json.load(open(os.path.join(C.OUTDIR, "p0_cmax_audit.json")))["rows"]
res["k5_m2_touched"] = [(a["file"], a["seed"], a["touched_frac"], a["population_touched"]) for a in cm
                        if a.get("k") == 5 and a.get("m") == 2 and a.get("N") == 20]
res["k5_m2_population"] = 1 - math.comb(18, 5) / math.comb(20, 5)
# cost arithmetic
res["cost"] = {k: dict(K=min(math.comb(20, k), {1: 20, 2: 190, 3: 1140, 5: 200, 8: 200}[k]),
                       client_rounds=min(math.comb(20, k), {1: 20, 2: 190, 3: 1140, 5: 200, 8: 200}[k]) * k * 15)
               for k in (1, 2, 3, 5, 8)}
res["cost"]["3_sampled"] = dict(K=500, client_rounds=500 * 3 * 15)
C.dump("p0_recompute2.json", res)
for k in ("table8", "table8_added_slack_larger", "largest_single_row_slack_dev", "table10_e2_corrected", "table10_e5f", "multiclass", "k5_m2_touched", "k5_m2_population", "cost"):
    print(k, json.dumps(res[k], default=str)[:900])
print("loco", {k: v for k, v in res["loco"].items() if k != "folds"})
print("table9 IID k1 b0.05", res["table9"]["iid|k1|b0.05"], "dev k1 b0.4", res["table9"]["device_derived|k1|b0.4"], "dev k2 b0.4", res["table9"]["device_derived|k2|b0.4"])
print(res["adaptive_rows"], res["adaptive_keys_example"])
