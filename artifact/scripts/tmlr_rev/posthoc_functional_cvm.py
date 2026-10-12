#!/usr/bin/env python3
"""POST HOC (not preregistered; written after PB03/PB04 results): 'functional' coverage-vote model.
A member counts as one-class if its clean predictions are one class on >= 99% of test flows,
whatever its training labels. Same vote arithmetic as the CVM (k = 1, K members, c_max = m).
Scored on banked IoT-23 k = 1 ensembles (banks A, B, D) and, via member accuracy, on PB04 rows.
Writes results/posthoc_functional_cvm.json."""
import glob, json, os, sys
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from build_member_bank import load_bank
BF = [round(0.05 * i, 2) for i in range(11)]

def pred(nM, nB, K, tau, grid=BF, N=20):
    best = 0.0
    for b in grid:
        m = int(round(b * N)); c = min(m, K)
        ca = tau * ((K - 2 * nB) > 2 * c) + (1 - tau) * ((K - 2 * nM) > 2 * c)
        if ca > tau + 1e-12: best = max(best, b)
    return best

tb = C.prepare_base("iot-23"); tau = tb["tau"]
out = []
for mf in sorted(glob.glob(os.path.join(C.OUTDIR, "member_bank", "iot-23_*_k1_K20.json"))):
    m = json.load(open(mf)); j = m["job"]
    preds, subs, _ = load_bank(m["id"])
    share = preds.mean(1)
    nM, nB = int((share >= 0.99).sum()), int((share <= 0.01).sum())
    out.append(dict(id=m["id"], kind=j["kind"], dph=j["dph"], alpha=j["alpha"], seed=j["seed"],
                    observed=m["beta_star"], functional_pred=pred(nM, nB, len(subs), tau), nM_f=nM, nB_f=nB))
def score(rs):
    e = np.array([(r["functional_pred"] - r["observed"]) / 0.05 for r in rs]).round()
    o = [r["observed"] for r in rs]; p = [r["functional_pred"] for r in rs]
    return dict(n=len(rs), exact=float((e == 0).mean()), within1=float((abs(e) <= 1).mean()),
                mae_steps=float(abs(e).mean()), spearman=(float(spearmanr(p, o).statistic) if len(set(o)) > 1 and len(set(p)) > 1 else None))
groups = {}
for r in out:
    key = r["kind"] if r["kind"] in ("iid",) else f"{r['kind']}|{r['dph']}|{r['alpha']}"
    groups.setdefault(key, []).append(r)
summary = {k: score(v) for k, v in sorted(groups.items())}
dev = {}
for r in out:
    if r["kind"] == "device_derived":
        dev[(tuple(r["dph"]), r["seed"])] = r
summary["ALL iot23 device-derived k=1 (unique draws)"] = score(list(dev.values()))
# PB04 rows via member accuracy (constant-malicious acc == tau, constant-benign == 1 - tau)
pb = [json.loads(l) for l in open(os.path.join(C.OUTDIR, "pb04_rows.jsonl"))]
pr = []
for r in pb:
    if r["k"] != 1 or not r.get("member_acc"):
        continue
    acc = np.array(list(r["member_acc"].values()))
    nM, nB = int((abs(acc - tau) < 0.003).sum()), int((abs(acc - (1 - tau)) < 0.003).sum())
    pr.append(dict(arm=r["arm"], variant=r["variant"], level=str(r["level"]), observed=r["beta_star"],
                   functional_pred=pred(nM, nB, r["K"], tau), cvm_pred=r["cvm_pred"]))
pbs = {}
for r in pr:
    pbs.setdefault(f"{r['arm']}|{r['variant']}|{r['level']}", []).append(r)
summary_pb04 = {k: dict(score(v), cvm_exact=float(np.mean([x["cvm_pred"] == x["observed"] for x in v])))
                for k, v in sorted(pbs.items())}
C.dump("posthoc_functional_cvm.json", dict(note="POST HOC, not preregistered", bank=summary, pb04=summary_pb04, rows=out))
for k, v in summary.items(): print(k, v)
for k, v in summary_pb04.items(): print("PB04", k, v)
