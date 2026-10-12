#!/usr/bin/env python3
"""Rebuild clean ensembles (deterministic, same code path as scripts/exp_e2.py), store every
member's final-round test predictions, and check each rebuilt ensemble against the canonical rows
it reproduces.

    python3 build_member_bank.py --bank A --workers 8

Output: results/member_bank/<id>.npz (bit-packed binary member predictions, kept subsets) and
results/member_bank/<id>.json (timings, partition statistics, reproduction check).
"""
import argparse, json, math, os, sys, time
import multiprocessing as mp
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BANKDIR = "<artifact-root>/results/tmlr_rev/member_bank"
BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]


def jobs(bank):
    J = []
    if bank == "A":          # the 3-draw same-ensemble grid (Table 1, Table 9) and k=3/5/8 arms
        for kind in ("iid", "device_derived"):
            for s in (0, 1, 2):
                for k, K, f in ((1, 20, f"e2_{kind}_s{s}.jsonl"), (2, 190, f"e2_{kind}_s{s}.jsonl"),
                                (3, 500, f"e2_{kind}_s{s}.jsonl"),
                                (3, 1140, f"e2k3full_{kind}_s{s}.jsonl"),
                                (5, 200, f"e2k58_cert_{kind}_s{s}.jsonl"),
                                (8, 200, f"e2k58_cert_{kind}_s{s}.jsonl")):
                    J.append(dict(ds="iot-23", kind=kind, seed=s, dph=(1, 3), alpha=None,
                                  k=k, K=K, canon=f))
    elif bank == "B":        # the 30-draw grids (Tables 3, 4; coverage screen)
        for kind in ("iid", "device_derived"):
            for s in range(10, 40):
                for k, K in ((1, 20), (2, 190)):
                    J.append(dict(ds="iot-23", kind=kind, seed=s, dph=(1, 3), alpha=None,
                                  k=k, K=K, canon=f"e5f_{kind}.jsonl"))
    elif bank == "C":        # skew families (Table 2)
        for kind, f in (("dirichlet_device", "e7_devskew.jsonl"), ("dirichlet", "e7_labelskew.jsonl")):
            for a in (100.0, 10.0, 1.0, 0.5, 0.2, 0.1):
                for s in (0, 1, 2):
                    J.append(dict(ds="iot-23", kind=kind, seed=s, dph=(1, 3), alpha=a, k=1, K=20,
                                  canon=f))
        for a in (100.0, 10.0, 1.0, 0.5, 0.2):
            for s in (0, 1, 2):
                J.append(dict(ds="iot-23", kind="volume", seed=s, dph=(1, 3), alpha=a, k=1, K=20,
                              canon="e7_volskew.jsonl"))
    elif bank == "D":        # device-types-per-household sweep (Table 5), k = 1
        for lo, hi in ((1, 1), (1, 3), (2, 5), (3, 8), (5, 10)):
            for s in range(30):
                J.append(dict(ds="iot-23", kind="device_derived", seed=s, dph=(lo, hi), alpha=None,
                              k=1, K=20, canon=f"e11b_dph{lo}_{hi}.jsonl"))
    elif bank == "E":        # N-BaIoT, nine devices, k = 1 (Table 3)
        for kind in ("iid", "device_derived"):
            for s in range(30):
                J.append(dict(ds="n-baiot", kind=kind, seed=s, dph=(1, 2), alpha=None, k=1, K=20,
                              canon=f"nb9_cert_{kind}.jsonl"))
    else:
        raise SystemExit(f"unknown bank {bank}")
    return J


def job_id(j):
    a = "na" if j["alpha"] is None else f"a{j['alpha']:g}"
    return (f"{j['ds']}_{j['kind']}_dph{j['dph'][0]}-{j['dph'][1]}_{a}_s{j['seed']}"
            f"_k{j['k']}_K{j['K']}")


_TB = {}


def run_job(j):
    import common as C
    jid = job_id(j)
    out_npz = os.path.join(BANKDIR, jid + ".npz")
    out_js = os.path.join(BANKDIR, jid + ".json")
    if os.path.exists(out_npz) and os.path.exists(out_js):
        return jid, "cached", json.load(open(out_js))["check"]
    if j["ds"] not in _TB:
        _TB[j["ds"]] = C.prepare_base(j["ds"])
    tb = _TB[j["ds"]]
    cfg = C.base_cfg(j["ds"], j["kind"], j["seed"], j["dph"], j["alpha"])
    t = C.with_partition(tb, cfg)
    subs, full, tot = C.build_subsets(20, j["k"], j["K"], j["seed"])
    t0 = time.time()
    preds, kept = C.member_predictions(cfg, t, subs)
    secs = time.time() - t0
    votes = C.votes_from_member_preds(preds)
    # reproduction check against the canonical rows this ensemble produced
    rows = [r for r in C.load_rows(j["canon"])
            if r["partition_seed"] == j["seed"] and r["k"] == j["k"]
            and (r.get("dirichlet_alpha") == j["alpha"])
            and tuple(r.get("devices_per_household") or ()) == tuple(j["dph"])
            and r["N"] == 20 and not r.get("pairing")
            and (r["K"] == len(kept))]
    if j["k"] == 3:   # e2 (K=500) and e2k3full (K=1140) share seeds; keep the right one
        rows = [r for r in rows if (r["full_enumeration"] == (j["K"] == 1140))]
    betas = sorted({round(r["beta"], 4) for r in rows}) or BF
    cert = C.XC.certify_exact(votes, t["yte_np"], kept, 20, j["k"], betas, t["tau"])
    by = {round(g["beta"], 4): g for g in cert["grid"]}
    maxdiff, n_cmp = 0.0, 0
    for r in rows:
        g = by[round(r["beta"], 4)]
        for a in ("CA", "CTR_mal", "CTR_ben", "coverage"):
            maxdiff = max(maxdiff, abs(g[a] - r[a])); n_cmp += 1
        maxdiff = max(maxdiff, abs(cert["mean_margin"] - r["mean_vote_margin"]))
        maxdiff = max(maxdiff, abs(t["pmeta"]["S_JS"] - r["S_JS"]))
    check = dict(n_rows=len(rows), n_compared=n_cmp, max_abs_diff=maxdiff,
                 reproduced=bool(rows) and maxdiff <= 1e-6)
    os.makedirs(BANKDIR, exist_ok=True)
    np.savez_compressed(out_npz, packed=np.packbits(preds.astype(bool), axis=1),
                        n_test=len(t["yte_np"]), subsets=np.array(kept, np.int16))
    meta = dict(job=j, id=jid, K=len(kept), full_enumeration=bool(len(kept) == math.comb(20, j["k"])),
                train_secs=round(secs, 2), pmeta={k: v for k, v in t["pmeta"].items()
                                                  if not isinstance(v, (list, dict))},
                client_sizes=[int(len(t["parts_np"][i])) for i in range(20)],
                client_mal_frac=[float(np.mean(t["ytr_np"][t["parts_np"][i]]))
                                 if len(t["parts_np"][i]) else None for i in range(20)],
                client_devices=[sorted(set(int(d) for d in t["dtr"][t["parts_np"][i]]))
                                for i in range(20)],
                beta_star=cert["beta_star"], mean_margin=cert["mean_margin"],
                check=check)
    json.dump(meta, open(out_js, "w"), indent=1)
    return jid, round(secs, 1), check


def load_bank(jid):
    z = np.load(os.path.join(BANKDIR, jid + ".npz"))
    n = int(z["n_test"])
    preds = np.unpackbits(z["packed"], axis=1)[:, :n].astype(np.int8)
    meta = json.load(open(os.path.join(BANKDIR, jid + ".json")))
    return preds, [tuple(int(x) for x in s) for s in z["subsets"]], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true", help="list jobs and how many are cached; run nothing")
    a = ap.parse_args()
    J = [j for b in a.bank for j in jobs(b)]
    J = list({job_id(j): j for j in J}.values())     # banks B/D and A/D share some draws
    if a.dry_run:
        done = [j for j in J if os.path.exists(os.path.join(BANKDIR, job_id(j) + ".npz"))
                and os.path.exists(os.path.join(BANKDIR, job_id(j) + ".json"))]
        mem = sum(min(math.comb(20, j["k"]), j["K"]) for j in J if j not in done)
        print(f"{len(J)} jobs in banks {a.bank}; {len(done)} cached; {len(J)-len(done)} to run "
              f"({mem} member trainings)")
        return
    # heaviest first so the pool drains evenly
    J.sort(key=lambda j: -(math.comb(20, j["k"]) if math.comb(20, j["k"]) <= j["K"] else j["K"]) * j["k"])
    t0 = time.time()
    ctx = mp.get_context("spawn")
    bad = 0
    with ctx.Pool(a.workers) as pool:
        for jid, secs, chk in pool.imap_unordered(run_job, J):
            bad += (not chk["reproduced"])
            print(f"{jid}  train={secs}s  rows={chk['n_rows']} maxdiff={chk['max_abs_diff']:.2e}"
                  f"  {'OK' if chk['reproduced'] else 'NOT REPRODUCED'}", flush=True)
    print(f"DONE {len(J)} jobs in {(time.time()-t0)/60:.1f} min; not reproduced: {bad}")


if __name__ == "__main__":
    main()
