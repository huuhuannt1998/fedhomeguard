#!/usr/bin/env python3
"""Review r4 (A-W1, meta item 1): attacks that one client per member cannot dilute.

Reads results/r4_normscaled/e2ns_*.jsonl, written by scripts/run_r4_normscaled.sh,
which re-runs the same-predictor grid of results/canonical/e2_* (same partition,
malicious-set and subset-sample seeds, same ensemble sizes) with two attacks the
canonical five do not include:

  replace_invert  model replacement toward the round's clean aggregate with its output
                  inverted; the malicious client scales its update by the inverse of
                  its FedAvg weight, so one client decides its member
  sign_flip       the canonical attack at scale 100 instead of 1

Emits generated/r4ns_macros.tex into the manuscript and a JSON summary next to the
results. Three checks gate the output, and the script exits non-zero if one fails:

  * reproduction  every clean certified quantity (CA) equals the canonical row's,
                  so the new rows describe the same ensembles as Table 2
  * soundness     wherever certification is possible, the attacked final-round
                  accuracy under the new attacks never falls below CA (Prop. 1)
  * coverage      every canonical (partition, draw, k, beta, malicious set) cell is
                  present in the new files
"""
from __future__ import annotations
import glob, json, os, statistics as st, sys

RES = "results/r4_normscaled"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregate import src as _src
CANON = _src("e2_*.jsonl")   # review r6: the corrected rows the paper prints
OUT = os.environ.get("FHG_GENERATED",
                     "[READY] (S&P 2027) FedHomeGuard - P10/generated")
NEW = ("replace_invert", "sign_flip")


def rows(pat):
    out = {}
    for f in sorted(glob.glob(pat)):
        for line in open(f):
            if line.startswith("{"):
                r = json.loads(line)
                out[(r["partition_type"], r["partition_seed"], r["k"],
                     round(r["beta"], 4), r["mal_seed"])] = r
    return out


def half_counts(new, canon, minority, tau):
    """Review r6. Per partition and k, over the void draws on which the drawn malicious
    set touches more than half the members: how many collapse to the minority-class rate
    under model replacement, and under ANY finite attack (the five published attacks as
    corrected, plus replace_invert; the x100 sign flip is excluded because its members
    go non-finite)."""
    PUB = ("label_flip", "sign_flip", "gaussian", "ipm", "alie")
    out = {}
    for p, P in (("iid", "IID"), ("device_derived", "Dev")):
        for k, K in ((2, "Two"), (3, "Three")):
            half = [kk for kk, r in new.items()
                    if kk[0] == p and kk[2] == k and r["m"] > 0
                    and not r["combinatorially_possible"] and r["members_touched"] > r["K"] / 2]
            fin = lambda kk: min([canon[kk]["EA_final_round"][a] for a in PUB]
                                 + [new[kk]["EA_final_round"]["replace_invert"]])
            ri = lambda kk: new[kk]["EA_final_round"]["replace_invert"]
            out[f"ns{P}{K}Half"] = str(len(half))
            out[f"ns{P}{K}RIColl"] = str(sum(ri(kk) <= minority + 1e-3 for kk in half))
            out[f"ns{P}{K}FinColl"] = str(sum(fin(kk) <= minority + 1e-3 for kk in half))
            out[f"ns{P}{K}FinBelow"] = str(sum(fin(kk) <= tau for kk in half))
    return out


def main():
    new, canon = rows(f"{RES}/e2ns_*.jsonl"), rows(CANON)
    missing = sorted(set(canon) - set(new))
    repro_bad = [k for k in canon if k in new and abs(new[k]["CA"] - canon[k]["CA"]) > 1e-9]
    unsound, cells = [], {}
    for key, r in new.items():
        p, s, k, b, ms = key
        if r["m"] == 0:
            continue
        ea_new = min(r["EA_per_attack"][a] for a in NEW)             # window minimum
        ea_new_final = min(r["EA_final_round"][a] for a in NEW)      # deployed round
        if r["combinatorially_possible"] and ea_new_final < r["CA"] - 1e-9:
            unsound.append(key)
        # Table 2 prints the FINAL-ROUND attacked accuracy (min over attacks), the
        # same estimator as CA, so the macros use it too; the 8-round window minimum
        # is kept in the JSON summary for reference.
        cf = canon[key]["EA_final_round"]
        c = cells.setdefault((p, k, b), dict(new=[], ri=[], sf=[], canon=[], ca=[],
                                             new_w=[], canon_w=[],
                                             possible=r["combinatorially_possible"]))
        c["new"].append(ea_new_final)
        c["ri"].append(r["EA_final_round"]["replace_invert"])
        c["sf"].append(r["EA_final_round"]["sign_flip"])
        c["canon"].append(min(cf.values()) if cf else canon[key]["EA_ensemble"])
        c["new_w"].append(ea_new)
        c["canon_w"].append(canon[key]["EA_ensemble"])
        c["ca"].append(r["CA"])

    print(f"rows {len(new)}  canonical {len(canon)}  missing {len(missing)}  "
          f"CA mismatches {len(repro_bad)}  soundness violations {len(unsound)}")
    print("final-round EA (the estimator Table 2 prints); window minimum in [brackets]")
    print(f"{'part':15s} k  beta  void  EA canon  EA new  (replace_invert  sign_flip x100)  CA")
    summ = {}
    for (p, k, b), c in sorted(cells.items()):
        m = lambda v: round(st.median(v), 4)
        summ[f"{p}|{k}|{b}"] = dict(void=not c["possible"], n=len(c["new"]),
                                    EA_canonical=m(c["canon"]), EA_new=m(c["new"]),
                                    EA_new_max=round(max(c["new"]), 4),
                                    EA_replace_invert=m(c["ri"]), EA_sign_flip_x100=m(c["sf"]),
                                    EA_new_windowmin=m(c["new_w"]),
                                    EA_canonical_windowmin=m(c["canon_w"]),
                                    CA=m(c["ca"]))
        print(f"{p:15s} {k}  {b:.2f}  {'void' if not c['possible'] else '    '}  "
              f"{m(c['canon']):.4f}  {m(c['new']):.4f}  ({m(c['ri']):.4f}  {m(c['sf']):.4f})  "
              f"{m(c['ca']):.4f}  [{m(c['canon_w']):.4f} {m(c['new_w']):.4f}]")

    voidk3 = {kk: v for kk, v in summ.items() if v["void"] and kk.split("|")[1] == "3"}
    tau = next(iter(new.values()))["tau_triv"]
    # Per draw at the k=3 void cells: a void cell is one where SOME malicious set can
    # touch half the members; the drawn B may touch fewer. Count the draws where the
    # drawn B touches more than half, and how many of those collapse to the
    # minority-class rate (one class voted everywhere) under the new attacks.
    minority = 1 - tau
    half = [r for r in new.values()
            if r["k"] == 3 and r["m"] > 0 and not r["combinatorially_possible"]
            and r["members_touched"] > r["K"] / 2]
    coll = lambda r, atks: min(r["EA_final_round"][a] for a in atks) <= minority + 1e-3
    half_iid = [r for r in half if r["partition_type"] == "iid"]
    mac = {
        "nsRows": str(len([r for r in new.values() if r["m"] > 0])),
        "nsUnsound": str(len(unsound)),
        "nsVoidCells": str(len(voidk3)),
        # largest median, and largest single draw, of attacked accuracy at the k=3
        # void cells under the new attacks
        "nsVoidMedMax": f"{max(v['EA_new'] for v in voidk3.values()):.4f}",
        "nsVoidDrawMax": f"{max(v['EA_new_max'] for v in voidk3.values()):.4f}",
        "nsVoidCanonMin": f"{min(v['EA_canonical'] for v in voidk3.values()):.4f}",
        "nsVoidCanonMax": f"{max(v['EA_canonical'] for v in voidk3.values()):.4f}",
        # the same range restricted to IID, for the sentence whose subject is IID
        # (review r6 item 8: the pooled minimum is a device-derived cell)
        "nsVoidCanonIIDMin": f"{min(v['EA_canonical'] for kk, v in voidk3.items() if kk.startswith('iid|')):.4f}",
        "nsVoidCanonIIDMax": f"{max(v['EA_canonical'] for kk, v in voidk3.items() if kk.startswith('iid|')):.4f}",
        "nsMinority": f"{1 - tau:.4f}",
        "nsHalfN": str(len(half)),
        "nsHalfCollapsed": str(sum(coll(r, NEW) for r in half)),
        "nsHalfNIID": str(len(half_iid)),
        "nsHalfRIIID": str(sum(coll(r, ("replace_invert",)) for r in half_iid)),
        **half_counts(new, canon, minority, tau),
        "nsRIDevVoidMed": f"{st.median([r['EA_final_round']['replace_invert'] for r in new.values() if r['k'] == 3 and r['m'] > 0 and not r['combinatorially_possible'] and r['partition_type'] == 'device_derived']):.4f}",
    }
    idx = {}
    for kk, v in summ.items():
        p, k, b = kk.split("|")
        sfx = "IID" if p == "iid" else "DEV"
        idx[f"NSEA{sfx}k{k}b{int(round(float(b) * 100))}"] = f"{v['EA_new']:.4f}"
    tex = "% GENERATED by scripts/gen_r4_normscaled.py -- do not edit\n"
    tex += "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(mac.items()))
    tex += "".join("\\expandafter\\newcommand\\csname %s\\endcsname{%s}\n" % (k, v)
                   for k, v in sorted(idx.items()))
    tex += ("\\newcommand{\\NSEAIID}[2]{\\csname NSEAIIDk#1b#2\\endcsname}\n"
            "\\newcommand{\\NSEADEV}[2]{\\csname NSEADEVk#1b#2\\endcsname}\n")
    json.dump(dict(cells=summ, macros=mac, missing=[list(x) for x in missing],
                   ca_mismatch=[list(x) for x in repro_bad],
                   unsound=[list(x) for x in unsound]),
              open(f"{RES}/summary.json", "w"), indent=1)
    if missing or repro_bad or unsound:
        print("CHECK FAILED -- refusing to write macros"); return 1
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "r4ns_macros.tex"), "w").write(tex)
    print(f"wrote {OUT}/r4ns_macros.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
