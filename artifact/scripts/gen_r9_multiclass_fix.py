#!/usr/bin/env python3
"""F10 port: correct the multi-class control's alie/gaussian values (r6 NaN fix).

results/canonical/e25_multiclass_{iid,device_derived}.jsonl were run on 2026-09-08,
before the r6 correction. At k=2 a member holding exactly one honest and one malicious
client estimated the honest spread with the unbiased std of one update, which is NaN,
so alie and gaussian sent it a non-finite update. scripts/run_r9_mc_nanfix.sh re-ran
those two attacks, and only at k=2, with the corrected default code into
results/r9_mc_nanfix/e25fix_*.jsonl. This script:

  1. refuses unless every canonical attacked k=2 row has a rerun, and the rerun's CA
     equals the canonical CA exactly (same clean ensemble);
  2. rebuilds each row's subsets, malicious set and active clients and counts the
     members that take the NaN path (gen_r5_std_fix.nan_members), and refuses unless
     every row with none reproduces the canonical alie/gaussian values bit for bit;
  3. writes corrected copies of the whole canonical files, alie/gaussian replaced and
     EA_ensemble, worst_attack, G_cert and G_cert_windowmin recomputed exactly as
     gen_r5_std_fix.correct() does, to results/r6_nan_fix/corrected/ -- where
     aggregate.src() already points -- plus results/r9_mc_nanfix/comparison.json.

Nothing in results/canonical is modified. k=1 rows are copied unchanged: a touched k=1
member holds no honest client, so the NaN path cannot fire there.
"""
import copy, glob, json, os, statistics as st, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from gen_r5_std_fix import nan_members, key, FIXED          # noqa: E402

RERUN = "results/r9_mc_nanfix"
CORR = "results/r6_nan_fix/corrected"
FIELDS = ("EA_per_attack", "EA_final_round", "EA_window_spread")


def rows(path):
    return [json.loads(l) for l in open(os.path.join(REPO, path)) if l.startswith("{")]


def main():
    new = {}
    for f in sorted(glob.glob(os.path.join(REPO, RERUN, "e25fix_*.jsonl"))):
        for r in rows(os.path.relpath(f, REPO)):
            new[key(r)] = r
    report = {}
    for part in ("iid", "device_derived"):
        canon_rows = rows(f"results/canonical/e25_multiclass_{part}.jsonl")
        canon = {key(r): (f"e25_multiclass_{part}.jsonl", r) for r in canon_rows}
        want = [kk for kk, (_, r) in canon.items() if r["m"] > 0 and r["k"] == 2]
        miss = [kk for kk in want if kk not in new]
        if miss:
            print(f"{part}: {len(miss)} attacked k=2 rows have no rerun -- refusing"); return 1
        ca_bad = [kk for kk in want if new[kk]["CA"] != canon[kk][1]["CA"]]
        if ca_bad:
            print(f"{part}: rerun CA differs on {ca_bad[:5]} -- refusing"); return 1
        nm = nan_members({kk: canon[kk] for kk in want})
        same = changed = 0; bad = []
        for kk in want:
            ident = all(new[kk][f][a] == canon[kk][1][f][a] for f in FIELDS for a in FIXED)
            if nm[kk] == 0:
                same += ident
                if not ident:
                    bad.append(kk)
            else:
                changed += not ident
        if bad:
            print(f"{part}: rows with no NaN member differ: {bad[:5]} -- refusing"); return 1
        out = []
        for r0 in canon_rows:
            r = copy.deepcopy(r0); kk = key(r)
            if kk in want:
                n = new[kk]
                for a in FIXED:
                    for f in FIELDS:
                        r[f][a] = n[f][a]
                r["worst_attack"] = min(r["EA_per_attack"], key=r["EA_per_attack"].get)
                r["EA_ensemble"] = r["EA_per_attack"][r["worst_attack"]]
                r["G_cert"] = round(min(r["EA_final_round"].values()) - r["CA"], 6)
                r["G_cert_windowmin"] = round(r["EA_ensemble"] - r["CA"], 6)
                r["std_estimator_alie_gaussian"] = "single_honest_zero (r9 rerun of e25)"
            out.append(r)
        os.makedirs(os.path.join(REPO, CORR), exist_ok=True)
        with open(os.path.join(REPO, CORR, f"e25_multiclass_{part}.jsonl"), "w") as fh:
            for r in out:
                fh.write(json.dumps(r) + "\n")
        # per-(k, beta) medians and the max slack over possible cells, before and after
        def summ(rs):
            cells = {}
            for r in rs:
                cells.setdefault((r["k"], r["beta"]), []).append(r)
            poss = [max(r["G_cert"] for r in c) for c in cells.values()
                    if any(r["combinatorially_possible"] for r in c)]
            return dict(max_slack_possible=max(poss),
                        cells={f"k{k}_b{b:.2f}": dict(
                            EA=round(st.median(r["EA_ensemble"] for r in c), 4),
                            G=round(st.median(r["G_cert"] for r in c), 4),
                            worst_alie_gauss=sum(r["worst_attack"] in FIXED for r in c))
                               for (k, b), c in sorted(cells.items()) if k == 2})
        report[part] = dict(rows_rerun=len(want), rows_with_nan_member=sum(1 for k in want if nm[k]),
                            rows_changed=changed, rows_without_identical=same,
                            before=summ(canon_rows), after=summ(out))
        print(f"{part}: rerun {len(want)} rows; {report[part]['rows_with_nan_member']} with a NaN "
              f"member, {changed} of those changed; {same} without one, all identical")
        print(f"   max slack over possible cells: {report[part]['before']['max_slack_possible']:.4f}"
              f" -> {report[part]['after']['max_slack_possible']:.4f}")
    json.dump(report, open(os.path.join(REPO, RERUN, "comparison.json"), "w"), indent=1)
    print(f"wrote {CORR}/e25_multiclass_{{iid,device_derived}}.jsonl and {RERUN}/comparison.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
