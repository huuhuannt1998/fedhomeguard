#!/usr/bin/env python3
"""PB06 (preregistered, predeclarations/tmlr_PB06_class_conditional_prior.md): class-conditional
certified detection (CTR_mal), certified benign rate (CTR_ben), prior re-weighting and prior-free
breakdown points. POST HOC: re-weighting assumes the class-conditional certified rates do not change
with the prior. Rows only. Writes results/pb06_prior.json and results/pb06_prior_table.csv."""
import argparse, collections, csv, glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

PIS = (0.5, 0.1, 0.01, 0.001)


def q(x):
    x = np.asarray(x, float)
    return dict(median=float(np.median(x)), q25=float(np.percentile(x, 25)), q75=float(np.percentile(x, 75)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    srcs = {"e5f (30 draws)": [r for p in ("iid", "device_derived") for r in C.load_rows(f"e5f_{p}.jsonl")],
            "e2 corrected (3 draws x 3 sets)": [r for f in sorted(glob.glob(os.path.join(
                C.REPO, "results/r6_nan_fix/corrected/e2_*.jsonl"))) for r in C.load_rows(f)]}
    if a.dry_run:
        for k, v in srcs.items():
            print(k, len(v), "rows")
        return
    out, table = {}, []
    for name, rows in srcs.items():
        cells = collections.defaultdict(list)
        for r in rows:
            cells[(r["partition_type"], r["k"], round(r["beta"], 4))].append(r)
        res = {}
        for (p, k, b), v in sorted(cells.items()):
            void = not any(r["combinatorially_possible"] for r in v)
            e = dict(n_rows=len(v), void=void, CTR_mal=q([r["CTR_mal"] for r in v]),
                     CTR_ben=q([r["CTR_ben"] for r in v]), CA=q([r["CA"] for r in v]))
            for pi in PIS:
                cap = [pi * r["CTR_mal"] + (1 - pi) * r["CTR_ben"] for r in v]
                e[f"CA_pi{pi}"] = q(cap)
                e[f"beats_floor_pi{pi}"] = bool(np.median(cap) > max(pi, 1 - pi) + 1e-12)
            res[f"{p}|k{k}|b{b:g}"] = e
            table.append(dict(source=name, partition=p, k=k, beta=b, void=void, n=len(v),
                              CTR_mal=round(e["CTR_mal"]["median"], 4), CTR_ben=round(e["CTR_ben"]["median"], 4),
                              CA=round(e["CA"]["median"], 4),
                              **{f"CA_pi{pi}": round(e[f"CA_pi{pi}"]["median"], 4) for pi in PIS}))
        cnt = {}
        for pi in PIS:
            nv = [e for e in res.values() if not e["void"]]
            cnt[str(pi)] = dict(cells=len(res), nonvoid=len(nv),
                                beats_floor_nonvoid=sum(e[f"beats_floor_pi{pi}"] for e in nv))
        # prior-free breakdown points per draw
        draws = collections.defaultdict(list)
        for r in rows:
            draws[(r["partition_type"], r["partition_seed"], r["k"])].append(r)
        bp = collections.defaultdict(lambda: collections.defaultdict(list))
        for (p, s, k), v in draws.items():
            def bstar(ok):
                g = [r["beta"] for r in v if ok(r)]
                return max(g) if g else 0.0
            bp[(p, k)]["beta_star"].append(bstar(lambda r: r["CA"] > r["tau_triv"]))
            bp[(p, k)]["beta_star_bal"].append(bstar(lambda r: 0.5 * (r["CTR_mal"] + r["CTR_ben"]) > 0.5))
            for pi in (0.1, 0.01):
                bp[(p, k)][f"beta_star_pi{pi}"].append(
                    bstar(lambda r, pi=pi: pi * r["CTR_mal"] + (1 - pi) * r["CTR_ben"] > max(pi, 1 - pi)))
        out[name] = dict(cells=res, floor_counts=cnt,
                         breakdown={f"{p}|k{k}": {kk: dict(median=float(np.median(vv)), n=len(vv),
                                                           values=sorted(vv)) for kk, vv in d.items()}
                                    for (p, k), d in bp.items()})
    out["note"] = "POST HOC re-weighting; assumes class-conditional certified rates are prior-invariant"
    C.dump("pb06_prior.json", out)
    with open(os.path.join(C.OUTDIR, "pb06_prior_table.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys())); w.writeheader(); w.writerows(table)
    for name in srcs:
        print(name, out[name]["floor_counts"])
        for kk, v in out[name]["breakdown"].items():
            print("  ", kk, {a: b["median"] for a, b in v.items()})


if __name__ == "__main__":
    main()
