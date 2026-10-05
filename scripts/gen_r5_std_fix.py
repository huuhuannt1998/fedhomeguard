#!/usr/bin/env python3
"""Review r5: impact of the alie/gaussian single-honest-update NaN on the paper.

Reads the canonical same-predictor rows (results/canonical/e2_*.jsonl) and the rerun of
alie and gaussian with the population std (results/r5_std_fix/e2pop_*.jsonl, written by
scripts/run_r5_std_fix.sh). Builds CORRECTED rows: the canonical row with the two
attacks' EA replaced, EA = min over all five attacks recomputed, and G_cert recomputed the
way exp_e2.py computes it. Nothing in results/canonical is modified.

Then regenerates every artifact that reads e2_* EA twice, in two scratch mirrors of the
repository that differ ONLY in results/canonical/e2_*.jsonl (baseline: the canonical
files; corrected: the corrected rows), and diffs the outputs. Both mirrors write their
manuscript files under the scratch directory, never into the real manuscript.

Usage: python3 scripts/gen_r5_std_fix.py SCRATCH_DIR
       python3 scripts/gen_r5_std_fix.py SCRATCH_DIR --rerun-dir results/r6_nan_fix \
           --pattern 'e2fix_*.jsonl' --check-unaffected
--check-unaffected (for the minimal r6 fix) rebuilds each row's subsets, malicious set
and active clients, finds the members that hit the one-honest-update NaN path, and
refuses to continue unless every row with none of them reproduces the canonical alie
and gaussian values exactly.
Writes: results/r5_std_fix/corrected/e2_*.jsonl (corrected copies of the canonical
        rows) and results/r5_std_fix/comparison.json (per-cell medians and the diff of
        every regenerated file)
"""
from __future__ import annotations
import copy, difflib, glob, json, os, shutil, statistics as st, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXED = ("alie", "gaussian")
GENS = ["scripts/gen_paper_numbers.py", "scripts/gen_e3.py", "scripts/gen_gapspread.py",
        "scripts/gen_e9.py"]
MANGEN = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"


def key(r):
    return (r["partition_type"], r["partition_seed"], r["k"], round(r["beta"], 4), r["mal_seed"])


def load(pat):
    out = {}
    for f in sorted(glob.glob(os.path.join(REPO, pat))):
        for line in open(f):
            if line.startswith("{"):
                r = json.loads(line); out[key(r)] = (os.path.basename(f), r)
    return out


def correct(canon, new):
    fixed, notes = {}, dict(ca_mismatch=0, replaced=0)
    for kk, (fname, r) in canon.items():
        c = copy.deepcopy(r)
        if kk in new and r["m"] > 0 and r["k"] in (2, 3):
            n = new[kk][1]
            notes["ca_mismatch"] += abs(n["CA"] - r["CA"]) > 1e-9
            for a in FIXED:
                c["EA_per_attack"][a] = n["EA_per_attack"][a]
                c["EA_final_round"][a] = n["EA_final_round"][a]
                c["EA_window_spread"][a] = n["EA_window_spread"][a]
            c["worst_attack"] = min(c["EA_per_attack"], key=c["EA_per_attack"].get)
            c["EA_ensemble"] = c["EA_per_attack"][c["worst_attack"]]
            c["G_cert"] = round(min(c["EA_final_round"].values()) - c["CA"], 6)
            c["G_cert_windowmin"] = round(c["EA_ensemble"] - c["CA"], 6)
            c["std_estimator_alie_gaussian"] = "population (r5 rerun)"
            notes["replaced"] += 1
        fixed.setdefault(fname, []).append(c)
    return fixed, notes


def mirror(dst, e2files):
    """Symlink the repo into dst, except results/canonical/e2_*.jsonl and manuscripts."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.join(dst, "results", "canonical"))
    for e in os.listdir(REPO):
        if e in ("results", "manuscripts", ".git") or e.startswith("[READY]"):
            continue
        os.symlink(os.path.join(REPO, e), os.path.join(dst, e))
    for e in os.listdir(os.path.join(REPO, "results")):
        if e != "canonical":
            os.symlink(os.path.join(REPO, "results", e), os.path.join(dst, "results", e))
    for f in glob.glob(os.path.join(REPO, "results", "canonical", "*")):
        b = os.path.basename(f)
        if not (b.startswith("e2_") and b.endswith(".jsonl")):
            os.symlink(f, os.path.join(dst, "results", "canonical", b))
    for b, src in e2files.items():
        shutil.copy(src, os.path.join(dst, "results", "canonical", b))
    os.makedirs(os.path.join(dst, MANGEN, "floats"), exist_ok=True)
    logs = []
    for g in GENS:
        # FHG_FROZEN=1: the generators read this mirror's results/canonical, which holds
        # whichever e2 rows this mirror is testing (frozen or corrected)
        env = dict(os.environ, FHG_FROZEN="1", FHG_GENERATED=os.path.join(dst, MANGEN))
        p = subprocess.run([sys.executable, g], cwd=dst, capture_output=True, text=True,
                           env=env)
        logs.append(f"$ {g} (exit {p.returncode})\n{p.stdout[-3000:]}{p.stderr[-2000:]}")
    return "\n".join(logs)


def cells(rows):
    out = {}
    for r in rows:
        if r["m"] == 0:
            continue
        c = out.setdefault((r["partition_type"], r["k"], round(r["beta"], 4)),
                           dict(EA=[], G=[], CA=[], worst=[], possible=r["combinatorially_possible"]))
        c["EA"].append(min(r["EA_final_round"].values()))
        c["G"].append(r["G_cert"]); c["CA"].append(r["CA"])
        c["worst"].append(min(r["EA_final_round"], key=r["EA_final_round"].get))
    return out


def correct_family(pattern, canon, new):
    """Other result families whose members are the SAME trainings as the e2 grid (same
    partition, subset, malicious set and seeds): substitute the corrected alie/gaussian
    values, but only after checking that every frozen value equals the frozen e2 value
    at the same key -- which is what shows the members are the same. Refuses otherwise."""
    out, bad = {}, []
    for f in sorted(glob.glob(os.path.join(REPO, pattern))):
        rows = []
        for line in open(f):
            if not line.startswith("{"):
                continue
            r = json.loads(line); kk = key(r)
            present = [a for a in FIXED if a in (r.get("EA_per_attack") or {})]
            if r.get("m", 0) > 0 and r["k"] in (2, 3) and present:
                c0 = canon[kk][1]
                for a in present:
                    for fld in ("EA_per_attack", "EA_final_round", "EA_window_spread"):
                        if r[fld][a] != c0[fld][a]:
                            bad.append((os.path.basename(f), kk, a, fld))
                n = new[kk][1]
                for a in present:
                    for fld in ("EA_per_attack", "EA_final_round", "EA_window_spread"):
                        r[fld][a] = n[fld][a]
                r["worst_attack"] = min(r["EA_per_attack"], key=r["EA_per_attack"].get)
                r["EA_ensemble"] = r["EA_per_attack"][r["worst_attack"]]
                r["G_cert"] = round(min(r["EA_final_round"].values()) - r["CA"], 6)
                r["G_cert_windowmin"] = round(r["EA_ensemble"] - r["CA"], 6)
                r["std_estimator_alie_gaussian"] = "single_honest_zero (r6, from e2 rerun)"
            rows.append(r)
        out[os.path.basename(f)] = rows
    return out, bad


def nan_members(canon):
    """Per canonical row, the members whose alie/gaussian update is NaN under the
    committed code: exactly one ACTIVE honest client (fl.py min_rows = 16) and at least
    one active malicious one. Reproduces each row's K and members_touched."""
    sys.path.insert(0, os.path.join(REPO, "src")); sys.path.insert(0, os.path.join(REPO, "scripts"))
    from fedhomeguard import config as CFG, runner as R
    from exp_e2 import build_subsets, malicious_set
    caps, tc, out = {1: 20, 2: 190, 3: 500}, {}, {}
    for kk, (_, r) in canon.items():
        if r["m"] == 0:
            continue
        pk = (r["partition_type"], r["partition_seed"])
        if pk not in tc:
            cfg = CFG.load(os.path.join(REPO, "configs/stage3_certification.yaml"))
            cfg.device = "cpu"; cfg.partition.kind, cfg.partition.seed = pk; cfg.fl.seed = 0
            cwd = os.getcwd(); os.chdir(REPO)
            try:
                tc[pk] = R.prepare(cfg, verbose=False)
            finally:
                os.chdir(cwd)
        t = tc[pk]
        subsets, _, _ = build_subsets(20, r["k"], caps[r["k"]], r["partition_seed"])
        B = set(malicious_set("random", 20, r["m"], 1000 + r["mal_seed"], t))
        act = lambda i: len(t["parts_np"][i]) >= 16
        kept = [S for S in subsets if any(act(i) for i in S)]
        assert len(kept) == r["K"] and sum(bool(B & set(S)) for S in kept) == r["members_touched"], kk
        out[kk] = sum(1 for S in kept if sum(act(i) and i not in B for i in S) == 1
                      and any(act(i) and i in B for i in S))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--rerun-dir", default="results/r5_std_fix")
    ap.add_argument("--pattern", default="e2pop_*.jsonl")
    ap.add_argument("--check-unaffected", action="store_true")
    a = ap.parse_args()
    scratch, rdir = a.scratch, a.rerun_dir
    canon = load("results/canonical/e2_*.jsonl")
    new = load(os.path.join(rdir, a.pattern))
    want = [k for k, (_, r) in canon.items() if r["m"] > 0 and r["k"] in (2, 3)]
    missing = [k for k in want if k not in new]
    if missing:
        print(f"{len(missing)} canonical k=2,3 attacked rows have no rerun yet -- refusing")
        return 1
    if a.check_unaffected:
        nm = nan_members(canon)
        same = diff = 0; bad = []
        for kk in want:
            ident = all(new[kk][1][f][x] == canon[kk][1][f][x]
                        for f in ("EA_per_attack", "EA_final_round", "EA_window_spread")
                        for x in FIXED)
            if nm[kk] == 0:
                same += ident
                if not ident:
                    bad.append(kk)
            else:
                diff += not ident
        print(f"rows with no NaN member: {sum(1 for k in want if nm[k] == 0)}, "
              f"bit-identical {same}; rows with NaN members: {sum(1 for k in want if nm[k])}, "
              f"changed {diff}")
        if bad:
            print(f"UNAFFECTED ROWS DIFFER: {bad[:10]} -- refusing"); return 1
        gdir = os.environ.get("FHG_GENERATED")
        if gdir:     # the counts the artifact appendix states, so no prose integer is typed
            n_nan = sum(1 for k in want if nm[k])
            mac = dict(nfRerun=len(want), nfWithNaN=n_nan, nfChanged=diff,
                       nfWithout=len(want) - n_nan, nfIdentical=same)
            with open(os.path.join(gdir, "nanfix_macros.tex"), "w") as fh:
                fh.write("% GENERATED by scripts/gen_r5_std_fix.py --check-unaffected -- do not edit\n")
                for k_, v_ in mac.items():
                    fh.write("\\newcommand{\\%s}{%d}\n" % (k_, v_))
            print(f"wrote {gdir}/nanfix_macros.tex {mac}")
    fixed, notes = correct(canon, new)
    cdir = os.path.join(REPO, rdir, "corrected")
    os.makedirs(cdir, exist_ok=True)
    for fname, rs in fixed.items():
        with open(os.path.join(cdir, fname), "w") as fh:
            for r in rs:
                fh.write(json.dumps(r) + "\n")
    print(f"replaced {notes['replaced']} rows, CA mismatches {notes['ca_mismatch']}")
    if a.check_unaffected:        # the r6 promotion also corrects the adaptive family
        fam, bad = correct_family("results/canonical/adaptive_*.jsonl", canon, new)
        if bad:
            print(f"adaptive rows do not share the e2 members: {bad[:5]} -- refusing")
            return 1
        for fname, rs in fam.items():
            with open(os.path.join(cdir, fname), "w") as fh:
                for r in rs:
                    fh.write(json.dumps(r) + "\n")
        print(f"corrected adaptive family: {sorted(fam)}")

    base_files = {os.path.basename(f): f for f in glob.glob(os.path.join(REPO, "results/canonical/e2_*.jsonl"))}
    corr_files = {b: os.path.join(cdir, b) for b in base_files}
    lb = mirror(os.path.join(scratch, "base"), base_files)
    lc = mirror(os.path.join(scratch, "corr"), corr_files)
    open(os.path.join(scratch, "gen_logs.txt"), "w").write("BASE\n" + lb + "\n\nCORRECTED\n" + lc)

    # cell comparison
    cb = cells([r for _, r in canon.values()]); cc = cells([r for rs in fixed.values() for r in rs])
    comp = []
    for kk in sorted(cb):
        b, c = cb[kk], cc[kk]
        comp.append(dict(partition=kk[0], k=kk[1], beta=kk[2], void=not b["possible"],
                         EA_canon=round(st.median(b["EA"]), 4), EA_corr=round(st.median(c["EA"]), 4),
                         G_canon=round(st.median(b["G"]), 4), G_corr=round(st.median(c["G"]), 4),
                         CA_canon=round(st.median(b["CA"]), 4), CA_corr=round(st.median(c["CA"]), 4),
                         worst_canon_alie_gauss=sum(w in FIXED for w in b["worst"]),
                         worst_corr_alie_gauss=sum(w in FIXED for w in c["worst"]), n=len(b["EA"])))

    # diff every generated file between the two mirrors
    diffs = {}
    bdir = os.path.join(scratch, "base", MANGEN); cdir2 = os.path.join(scratch, "corr", MANGEN)
    for f in sorted(set(os.listdir(bdir)) | set(os.listdir(cdir2))):
        pb, pc = os.path.join(bdir, f), os.path.join(cdir2, f)
        if os.path.isdir(pb) or os.path.isdir(pc):
            continue
        a = open(pb).read().splitlines() if os.path.exists(pb) else []
        b = open(pc).read().splitlines() if os.path.exists(pc) else []
        if a != b:
            diffs[f] = [l for l in difflib.unified_diff(a, b, "baseline", "corrected", lineterm="", n=0)]
    json.dump(dict(notes=notes, cells=comp, diffs=diffs),
              open(os.path.join(REPO, rdir, "comparison.json"), "w"), indent=1)
    print(f"{len(diffs)} generated files differ: {sorted(diffs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
