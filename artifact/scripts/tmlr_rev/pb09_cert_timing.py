#!/usr/bin/env python3
"""PB09 addendum (post hoc, not in the predeclared protocol; added 2026-10-10 to compare the paper's 'clean pass'
times, which include certification, with PB09's training-only times): wall-clock of exact certification
(exactcert.certify_exact: c_max by enumeration of malicious sets, margins, the IDS panel) on the banked votes of
IID draw 0, beta grid 0 to 0.50 in steps of 0.05, one core, 3 repeats per arm (median and range).

  python3 pb09_cert_timing.py --repeats 3
Writes results/pb09_cert_timing.json."""
import argparse, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                      # noqa: E402  (one torch thread)
from build_member_bank import load_bank  # noqa: E402

ARMS = [(1, 20), (2, 190), (3, 500), (3, 1140), (5, 200), (8, 200)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    tb = C.prepare_base("iot-23")
    y = tb["yte_np"]
    BF = [round(0.05 * i, 2) for i in range(11)]
    out = dict(loadavg_before=os.getloadavg(), grid=BF, arms={})
    for k, K in ARMS:
        preds, subs, _ = load_bank(f"iot-23_iid_dph1-3_na_s0_k{k}_K{K}")
        votes = C.votes_from_member_preds(preds)
        secs = []
        for _ in range(a.repeats):
            t0 = time.perf_counter()
            C.XC.certify_exact(votes, y, subs, 20, k, BF, tb["tau"])
            secs.append(time.perf_counter() - t0)
        med = float(np.median(secs))
        out["arms"][f"k{k}_K{K}"] = dict(secs=secs, median=med, min=min(secs), max=max(secs),
                                         rel_range=(max(secs) - min(secs)) / med if med else 0.0)
        print(f"k={k} K={K}: certify median {med:.2f}s range [{min(secs):.2f}, {max(secs):.2f}]", flush=True)
    out["loadavg_after"] = os.getloadavg()
    C.dump("pb09_cert_timing.json", out)


if __name__ == "__main__":
    main()
