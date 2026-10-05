#!/usr/bin/env python3
"""F10 / review E2: is "the certificate is nearly exact under IID" a saturated-task
artefact?

The review's Sec. 5 Finding C: the base model is an MLP(32,16) on 31 flow features and
under IID a single household's data already reaches ~0.98 accuracy, so every member is
near-perfect, every vote near-unanimous, and the certificate has nothing to withhold.
On that reading the IID tightness result is a property of the benchmark rather than of
the certificate.

The control is a harder label space on the same corpus, the same partitions and the
same ensemble: relabel IoT-23 from benign-versus-malicious to benign plus one class per
attack family. The trivial floor falls from 0.7300 to 0.5330 and the ensemble is no
longer saturated. If the slack stays tiny there, the tightness result generalises; if it
grows, the claim narrows to the binary task.

Slack is computed with the SAME definition as the binary arm in gen_paper_numbers.py:
the maximum of G_cert over rows in geometrically possible cells. A cell the geometry
forbids has CA identically 0, so its "slack" is the whole attacked accuracy and is not
slack at all; including those cells would manufacture a large number and invert the
conclusion.

Reads : aggregate.src("e25_multiclass_{iid,device_derived}.jsonl") -- corrected rows
        by default, results/canonical with FHG_FROZEN=1
        generated/numbers.json  (the binary arm, for the side-by-side)
Writes: generated/multiclass_macros.tex, generated/tab_multiclass.tex
"""
import json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregate import src                                    # noqa: E402

OUT = os.environ.get("FHG_GENERATED",
                     "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated")
BETAS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]
KS = [1, 2]


def load(part):
    # F10 port: the corrected rows (alie/gaussian re-run at k=2 with the r6 spread fix,
    # scripts/gen_r9_multiclass_fix.py) unless FHG_FROZEN=1 selects the frozen canonical
    # file -- the same selector every same-predictor generator uses.
    return [json.loads(l) for l in open(src(f"e25_multiclass_{part}.jsonl"))
            if l.strip()]


def cells(rows):
    out = {}
    for k in KS:
        for b in BETAS:
            c = [r for r in rows if r["k"] == k and abs(r["beta"] - b) < 1e-9]
            if c:
                out[(k, b)] = c
    return out


def main():
    data = {p: cells(load(p)) for p in ("iid", "device_derived")}

    ndraw = set()
    for p, d in data.items():
        for key, c in d.items():
            ndraw.add(len({r["partition_seed"] for r in c}))
    if len(ndraw) != 1:
        sys.exit(f"FAIL: cells hold differing draw counts {sorted(ndraw)}; "
                 "refusing to emit a table that claims one number of draws")
    N_DRAW = ndraw.pop()

    any_row = next(iter(data["iid"].values()))[0]
    n_class = int(any_row["n_class"])
    class_names = any_row["class_names"]
    tau_mc = float(any_row["tau_triv"])
    if n_class < 3:
        sys.exit("FAIL: this is not the multi-class arm")

    def max_slack(part):
        """Max G_cert over geometrically possible cells -- gen_paper_numbers' rule."""
        vals = []
        for key, c in data[part].items():
            if not any(r["combinatorially_possible"] for r in c):
                continue
            v = [r["G_cert"] for r in c if r["G_cert"] is not None]
            if v:
                vals.append((max(v), key))
        return max(vals) if vals else (None, None)

    s_iid, at_iid = max_slack("iid")
    s_dev, _ = max_slack("device_derived")

    # r7 item 3: compare like with like. The paper's binary 0.0040 is a maximum over the
    # three-draw grid (three malicious sets) at k <= 3; this arm is thirty draws, one
    # malicious set, k <= 2. The binary thirty-draw IID arm (results/canonical/
    # e24_slack30_iid.jsonl, k = 1, three malicious sets, never touched by the r6 NaN
    # path because a touched k=1 member holds no honest client) gives the same-k,
    # same-draw-count comparison.
    def max_at(part, k):
        v = [r["G_cert"] for (kk, _), c in data[part].items() if kk == k
             and any(x["combinatorially_possible"] for x in c) for r in c
             if r["G_cert"] is not None]
        return max(v)
    mal_sets = len({r["mal_seed"] for c in data["iid"].values() for r in c})
    b30 = [json.loads(l) for l in open("results/canonical/e24_slack30_iid.jsonl") if l.strip()]
    b30_g = max(r["G_cert"] for r in b30 if r["combinatorially_possible"] and r["m"] > 0)
    b30_draws = len({r["partition_seed"] for r in b30})
    b30_mal = len({r["mal_seed"] for r in b30 if r["m"] > 0})
    assert {r["k"] for r in b30} == {1}

    # clean ensemble accuracy under IID, and CA at the headline cell
    ens_iid = st.median([r["clean_ensemble_acc"]
                         for r in data["iid"][(1, 0.0)]])
    ca_iid_40 = st.median([r["CA"] for r in data["iid"][(1, 0.40)]])
    cov_iid_40 = st.median([r["coverage"] for r in data["iid"][(1, 0.40)]])

    # the binary arm, so the comparison is not eyeballed
    binary = json.load(open(f"{OUT}/numbers.json"))["numbers"]
    tau_bin = float(binary["tauTriv"]) if "tauTriv" in binary else None
    s_bin = float(binary["GcertIIDmax"])

    # Per-class certified-correct rate under IID at the headline cell. Classes with
    # no test rows are absent from the record and are not invented here.
    per = {}
    for r in data["iid"][(1, 0.40)]:
        for nm, d in (r.get("per_class_certified") or {}).items():
            per.setdefault(nm, []).append(d)
    rows_t = []
    for nm in class_names:
        if nm not in per:
            continue
        share = st.median([d["share"] for d in per[nm]])
        cc = st.median([d["certified_correct"] for d in per[nm]])
        n = int(st.median([d["n"] for d in per[nm]]))
        rows_t.append((nm, n, share, cc))

    lines = ["% GENERATED by scripts/gen_multiclass.py -- do not edit",
             r"\begin{tabular}{@{}l@{\;\;}r@{\;\;}c@{\;\;}c@{}}",
             r"\toprule",
             r"class & $n$ & share & certified-correct \\",
             r"\midrule"]
    for nm, n, share, cc in rows_t:
        safe = nm.replace("&", r"\&").replace("_", r"\_")
        lines.append(f"{safe} & {n} & {share:.4f} & {cc:.4f} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/tab_multiclass.tex", "w").write("\n".join(lines) + "\n")

    # The class the trivial predictor would name, and how the certified ensemble does
    # on it, is the whole point: tau_triv is that class's share.
    top = max(rows_t, key=lambda t: t[2])
    # F10 port: "the rare families far below" was not what the rows say -- the 1.4%
    # Attack family certifies at 0.98 -- so name the weakest class instead, among
    # classes holding at least 1% of test rows (C&C-Torii has three rows and would make
    # any rate a coin flip).
    LOW_SHARE = 0.01
    low = min((t for t in rows_t if t[2] >= LOW_SHARE), key=lambda t: t[3])
    mac = [
        f"\\newcommand{{\\McClasses}}{{{n_class}}}",
        f"\\newcommand{{\\McDraws}}{{{N_DRAW}}}",
        f"\\newcommand{{\\McTau}}{{{tau_mc:.4f}}}",
        f"\\newcommand{{\\McEnsIID}}{{{ens_iid:.4f}}}",
        f"\\newcommand{{\\McCAIID}}{{{ca_iid_40:.4f}}}",
        f"\\newcommand{{\\McCovIID}}{{{cov_iid_40:.4f}}}",
        f"\\newcommand{{\\McSlackIID}}{{{s_iid:.4f}}}",
        f"\\newcommand{{\\McSlackIIDk}}{{{at_iid[0]}}}",
        f"\\newcommand{{\\McSlackIIDbeta}}{{{at_iid[1]:.2f}}}",
        f"\\newcommand{{\\McSlackDev}}{{{s_dev:.4f}}}",
        f"\\newcommand{{\\McTopClassShare}}{{{top[2]:.4f}}}",
        f"\\newcommand{{\\McTopClassCert}}{{{top[3]:.4f}}}",
        f"\\newcommand{{\\McClassesCertified}}{{"
        f"{sum(1 for _, _, _, cc in rows_t if cc > 0.5)}}}",
        f"\\newcommand{{\\McClassesReported}}{{{len(rows_t)}}}",
        f"\\newcommand{{\\McLowName}}{{{low[0].replace('&', chr(92) + '&')}}}",
        f"\\newcommand{{\\McLowShare}}{{{low[2]:.4f}}}",
        f"\\newcommand{{\\McLowCert}}{{{low[3]:.4f}}}",
        f"\\newcommand{{\\McLowMinShare}}{{{100 * LOW_SHARE:g}}}",
        f"\\newcommand{{\\McSlackIIDkOne}}{{{max_at('iid', 1):.4f}}}",
        f"\\newcommand{{\\McSlackIIDkTwo}}{{{max_at('iid', 2):.4f}}}",
        f"\\newcommand{{\\McMalSets}}{{{mal_sets}}}",
        f"\\newcommand{{\\BinThirtySlack}}{{{b30_g:.4f}}}",
        f"\\newcommand{{\\BinThirtyDraws}}{{{b30_draws}}}",
        f"\\newcommand{{\\BinThirtyMalSets}}{{{b30_mal}}}",
    ]
    open(f"{OUT}/multiclass_macros.tex", "w").write(
        "% GENERATED by scripts/gen_multiclass.py -- do not edit\n"
        + "\n".join(mac) + "\n")

    print(f"wrote multiclass_macros.tex ({len(mac)} macros), tab_multiclass.tex")
    print(f"  {n_class}-class IoT-23, tau_triv {tau_mc:.4f} (binary arm 0.7300), "
          f"{N_DRAW} draws")
    print(f"  IID clean ensemble {ens_iid:.4f}; CA at k=1 beta=0.40 {ca_iid_40:.4f}")
    print(f"  MAX IID SLACK  multi-class {s_iid:.4f} at k={at_iid[0]} "
          f"beta={at_iid[1]:.2f}   |   binary {s_bin:.4f}")
    print(f"  max device-derived slack {s_dev:.4f}")
    print(f"  IID max by k: k=1 {max_at('iid', 1):.4f}, k=2 {max_at('iid', 2):.4f}; "
          f"binary thirty-draw k=1 arm (e24): {b30_g:.4f} over {b30_draws} draws x {b30_mal} sets")
    print("  VERDICT: " + ("slack does NOT grow on the harder task -- the IID "
                           "tightness claim generalises"
                           if s_iid <= 2 * s_bin else
                           "slack GROWS on the harder task -- narrow the claim to "
                           "the binary task"))
    for nm, n, share, cc in rows_t:
        print(f"    {nm[:34]:34s} n={n:6d} share={share:.4f} cert-correct={cc:.4f}")


if __name__ == "__main__":
    main()
