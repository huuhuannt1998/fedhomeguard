#!/usr/bin/env python3
"""P0 audit: seeds, partition draws and their overlap across result families, malicious-set
selection, train/test separation (row disjointness, exact duplicate feature vectors), feature
processing, raw-data truncation, and the determinism of rebuilt ensembles (from the member bank).

Writes results/p0_audit.json.
"""
import collections, glob, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C


def seeds_inventory():
    inv = {}
    for f in sorted(glob.glob(os.path.join(C.CANON, "*.jsonl"))):
        rs = C.load_rows(f)
        if not rs or rs[0].get("partition_seed") is None:
            continue
        ds = "n-baiot" if abs(rs[0]["tau_triv"] - 0.900147) < 1e-4 else "iot-23"
        inv[os.path.basename(f)] = dict(
            dataset=ds, partition=sorted({r["partition_type"] for r in rs}),
            seeds=sorted({r["partition_seed"] for r in rs}),
            dph=sorted({tuple(r.get("devices_per_household") or ()) for r in rs}),
            alpha=sorted({r.get("dirichlet_alpha") for r in rs}, key=str),
            k=sorted({r.get("k") for r in rs}, key=str), N=sorted({r.get("N") for r in rs}, key=str),
            mal_seeds=sorted({r.get("mal_seed") for r in rs}, key=str),
            mal_modes=sorted({r.get("mal_mode") for r in rs}, key=str), n_rows=len(rs))
    return inv


def overlap(inv):
    """Draw identity = (dataset, partition kind, seed, dph, alpha, N): identical partitions."""
    ids = collections.defaultdict(set)
    for f, v in inv.items():
        for p in v["partition"]:
            for s in v["seeds"]:
                for d in v["dph"]:
                    for a in v["alpha"]:
                        for N in v["N"]:
                            # dph only matters for device_derived; alpha only for dirichlet/volume
                            key = (v["dataset"], p, s, d if p == "device_derived" else (),
                                   a if p in ("dirichlet", "dirichlet_device", "volume") else None, N)
                            ids[key].add(f)
    shared = {str(k): sorted(v) for k, v in ids.items() if len(v) > 1}
    return dict(n_distinct_draws=len(ids), n_draws_in_more_than_one_file=len(shared),
                examples=dict(list(shared.items())[:25]))


def malicious_sets():
    """Rows' mal_members against default_rng(1000 + mal_seed).choice(N, m) (exp_e2.malicious_set)."""
    bad, n = 0, 0
    same_across_draws = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(C.CANON, "e2_*.jsonl"))) + \
            sorted(glob.glob(os.path.join(C.REPO, "results/r6_nan_fix/corrected/e2_*.jsonl"))) + \
            [os.path.join(C.CANON, "e24_slack30_iid.jsonl")]:
        for r in C.load_rows(f):
            if r["m"] == 0 or r.get("mal_mode") != "random":
                continue
            n += 1
            exp = sorted(np.random.default_rng(1000 + r["mal_seed"]).choice(r["N"], size=r["m"],
                                                                            replace=False).tolist())
            bad += exp != r["mal_members"]
            same_across_draws[(r["m"], r["mal_seed"])].add(tuple(r["mal_members"]))
    return dict(
        rows_checked=n, mismatches=bad,
        max_distinct_B_per_m_and_malseed_across_draws=max(len(v) for v in same_across_draws.values()),
        note="B depends only on (N, m, mal_seed): the same three malicious sets are reused for every "
             "partition draw; certified accuracy does not depend on B")


def split_and_duplicates():
    out = {}
    for ds in ("iot-23", "n-baiot"):
        tb = C.prepare_base(ds)
        cwd = os.getcwd(); os.chdir(C.REPO)
        b = C.DATA.load_dataset(C.base_cfg(ds, "iid", 0), verbose=False)
        os.chdir(cwd)
        tr, te = C.DATA.time_split_within_device(b["y"], b["device"], 0.8, block=b.get("block"))
        X = b["X"]
        y = b["y"]
        # exact duplicate feature vectors (raw features, before standardisation)
        Xtr, Xte = X[tr], X[te]
        def keys(A):
            A = np.ascontiguousarray(A)
            return A.view(np.dtype((np.void, A.dtype.itemsize * A.shape[1]))).ravel()
        ktr, kte = keys(Xtr), keys(Xte)
        trset = set(ktr.tolist())
        dup = np.array([k in trset for k in kte.tolist()])
        # label of the same vector in train (majority) vs test label
        lab_tr = collections.defaultdict(lambda: [0, 0])
        for k_, yy in zip(ktr.tolist(), y[tr].tolist()):
            lab_tr[k_][yy] += 1
        agree = np.array([(lab_tr[k_][yy] > lab_tr[k_][1 - yy]) if d else False
                          for k_, yy, d in zip(kte.tolist(), y[te].tolist(), dup)])
        ambiguous = sum(1 for v in lab_tr.values() if v[0] > 0 and v[1] > 0)
        out[ds] = dict(
            n_train=int(tr.sum()), n_test=int(te.sum()), rows_disjoint=bool(not (tr & te).any()),
            test_rows_with_exact_train_duplicate=int(dup.sum()),
            frac_test_dup=float(dup.mean()),
            frac_test_dup_by_class={"benign": float(dup[y[te] == 0].mean()),
                                    "malicious": float(dup[y[te] == 1].mean())},
            frac_test_dup_label_matches_train_majority=float(agree[dup].mean()) if dup.any() else None,
            n_unique_train_vectors=len(trset), n_train_vectors_with_both_labels=ambiguous,
            frac_test_rows_unique_vectors=float(len(set(kte.tolist())) / len(kte)),
            devices_in_test_also_in_train=bool(set(np.unique(b["device"][te])) <=
                                               set(np.unique(b["device"][tr]))))
    return out


def iot23_truncation():
    """load_iot23 reads at most 400,000 lines per capture, then keeps 60,000 evenly spaced rows."""
    out = {}
    for f in sorted(glob.glob(os.path.join(C.REPO, "data/raw/iot23/*.labeled"))):
        n = sum(1 for l in open(f, "rb") if not l.startswith(b"#"))
        out[os.path.basename(f).split(".conn")[0]] = dict(
            data_lines=n, read=min(n, 400_000), kept_cap=60_000,
            frac_of_capture_read=round(min(n, 400_000) / n, 4))
    return out


def bank_determinism():
    res = []
    for f in sorted(glob.glob(os.path.join(C.OUTDIR, "member_bank", "*.json"))):
        m = json.load(open(f))
        res.append(dict(id=m["id"], n_rows=m["check"]["n_rows"], maxdiff=m["check"]["max_abs_diff"],
                        reproduced=m["check"]["reproduced"], train_secs=m["train_secs"]))
    return dict(n_ensembles=len(res), n_reproduced=sum(r["reproduced"] for r in res),
                n_rows_compared=sum(r["n_rows"] for r in res),
                max_abs_diff=max([r["maxdiff"] for r in res], default=None),
                not_reproduced=[r for r in res if not r["reproduced"]])


def main():
    inv = seeds_inventory()
    out = dict(seeds=inv, draw_overlap=overlap(inv), malicious_sets=malicious_sets(),
               split=split_and_duplicates(), iot23_truncation=iot23_truncation(),
               determinism=bank_determinism(),
               fixed_seeds=dict(fl_seed="cfg.fl.seed = 0 for every member (exp_e2.py)",
                                subset_sample_seed="default_rng(10000 + 97*partition_seed + k)",
                                malicious_set_seed="default_rng(1000 + mal_seed), mal_seed in {0,1,2}",
                                partition_seed="partition_seed (per draw)"),
               feature_processing=dict(
                   iot23="9 log-signed numeric fields incl. resp_p (destination port); one-hot of the "
                         "top 4 proto / 12 conn_state / 8 service values, vocabulary taken from ALL rows "
                         "(train+test); no IP addresses, no timestamp, no uid",
                   standardisation="mean/sd of the pooled training rows of all households (a server-"
                                   "side statistic in a real federation), applied to test rows",
                   split="time-ordered tail (last 20%) within each capture (IoT-23) / within each "
                         "capture x traffic-type file (N-BaIoT): every test capture is also a training "
                         "capture"))
    C.dump("p0_audit.json", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("seeds",)}, indent=1, default=str)[:5000])


if __name__ == "__main__":
    main()
