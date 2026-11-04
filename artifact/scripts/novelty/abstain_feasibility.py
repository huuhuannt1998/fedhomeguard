#!/usr/bin/env python3
"""Feasibility of coverage-gated (abstaining) partition aggregation on the existing member bank.

Predeclaration: predeclarations/abstain_feasibility_2026-11-03.md (SHA-256 4f937a82..., RKA
jrn_01M6H0MV19ZD5X1H5RM477YPJ4). No training: reads results/tmlr_rev/member_bank/, the test labels from
runner.prepare (via scripts/tmlr_rev/common.py) and exactcert's c_max table. Writes results/novelty/.

    python3 scripts/novelty/abstain_feasibility.py
"""
import glob, json, math, os, sys
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the artifact root
sys.path.insert(0, os.path.join(REPO, "scripts", "tmlr_rev"))
import common as C  # noqa: E402

BANK = os.path.join(REPO, "results", "tmlr_rev", "member_bank")
OUT = os.path.join(REPO, "results", "novelty")
BETAS = [round(0.05 * i, 2) for i in range(11)]
N = 20
ONE_CLASS = 0.05
GROUPS = {
    "main_dd_1-3_k1": "iot-23_device_derived_dph1-3_na_s*_k1_K20",
    "control_iid_k1": "iot-23_iid_dph1-3_na_s*_k1_K20",
    "dd_1-1_k1": "iot-23_device_derived_dph1-1_na_s*_k1_K20",
    "dd_2-5_k1": "iot-23_device_derived_dph2-5_na_s*_k1_K20",
    "dd_3-8_k1": "iot-23_device_derived_dph3-8_na_s*_k1_K20",
    "dd_5-10_k1": "iot-23_device_derived_dph5-10_na_s*_k1_K20",
    "dd_1-3_k2": "iot-23_device_derived_dph1-3_na_s*_k2_K190",
    "iid_k2": "iot-23_iid_dph1-3_na_s*_k2_K190",
}


def member_minority(meta, S):
    sz = np.array([meta["client_sizes"][i] for i in S], float)
    fr = np.array([meta["client_mal_frac"][i] or 0.0 for i in S], float)
    p = float((sz * fr).sum() / sz.sum()) if sz.sum() > 0 else 0.0
    return min(p, 1.0 - p)


def certify(preds, y, voting, ctab, tau):
    """preds (K, n) in {0,1}; voting (K,) bool. Returns per-beta CA, coverage, CTR_mal, and clean acc."""
    v1 = (preds[voting] == 1).sum(0)
    v0 = int(voting.sum()) - v1
    top = (v1 > v0).astype(int)                     # ties -> class 0, as argmax does
    margin = np.abs(v1 - v0)
    correct = top == y
    out = []
    for b in BETAS:
        m = int(round(b * N))
        c = ctab[m]["c_max"]
        cert = margin > 2 * c
        out.append(dict(beta=b, m=m, c_max=c, CA=float((cert & correct).mean()),
                        coverage=float(cert.mean()),
                        CTR_mal=float((cert & correct & (y == 1)).sum() / max((y == 1).sum(), 1)),
                        CTR_ben=float((cert & correct & (y == 0)).sum() / max((y == 0).sum(), 1))))
    bstar = max([g["beta"] for g in out if g["CA"] > tau], default=0.0)
    return dict(grid=out, beta_star=bstar, clean_acc=float(correct.mean()),
                CA20=next(g["CA"] for g in out if g["beta"] == 0.2))


def main():
    os.makedirs(OUT, exist_ok=True)
    t = C.prepare_base("iot-23")
    y = np.asarray(t["yte_np"]).astype(int)
    tau = float(max(y.mean(), 1 - y.mean()))
    rows, mismatch = [], []
    for g, pat in GROUPS.items():
        for f in sorted(glob.glob(os.path.join(BANK, pat + ".npz"))):
            z = np.load(f)
            meta = json.load(open(f[:-4] + ".json"))
            n = int(z["n_test"]); assert n == len(y)
            preds = np.unpackbits(z["packed"], axis=1)[:, :n].astype(int)
            subs = [tuple(int(i) for i in s) for s in z["subsets"]]
            K = len(subs)
            ctab = C.XC.c_max_table(subs, N, [int(round(b * N)) for b in BETAS])
            plur = certify(preds, y, np.ones(K, bool), ctab, tau)
            # plurality must reproduce the stored certificate
            if abs(plur["beta_star"] - meta["beta_star"]) > 1e-9:
                mismatch.append((meta["id"], plur["beta_star"], meta["beta_star"]))
            mino = np.array([member_minority(meta, S) for S in subs])
            voting = mino >= ONE_CLASS
            absn = certify(preds, y, voting, ctab, tau)
            n1 = sum(1 for i in range(N) if meta["client_sizes"][i] > 0 and
                     min(meta["client_mal_frac"][i] or 0.0, 1 - (meta["client_mal_frac"][i] or 0.0)) < ONE_CLASS)
            ideal = (math.ceil((N - n1) / 2) - 1) / N
            rows.append(dict(group=g, id=meta["id"], K=K, n_abstain=int((~voting).sum()), n1_clients=n1,
                             plur_beta_star=plur["beta_star"], abst_beta_star=absn["beta_star"],
                             ideal_beta_star=round(max(ideal, 0.0), 4),
                             plur_CA20=plur["CA20"], abst_CA20=absn["CA20"], tau=tau,
                             plur_clean_acc=plur["clean_acc"], abst_clean_acc=absn["clean_acc"],
                             plur_CTRmal20=plur["grid"][4]["CTR_mal"], abst_CTRmal20=absn["grid"][4]["CTR_mal"]))
    json.dump(dict(rows=rows, mismatch=mismatch, tau=tau), open(os.path.join(OUT, "abstain_feasibility.json"), "w"),
              indent=1)
    print("plurality reproduction mismatches:", len(mismatch), mismatch[:3])
    for g in GROUPS:
        R = [r for r in rows if r["group"] == g]
        if not R:
            continue
        gain = np.array([r["abst_beta_star"] - r["plur_beta_star"] for r in R])
        col_p = sum(r["plur_CA20"] <= r["tau"] for r in R); col_a = sum(r["abst_CA20"] <= r["tau"] for r in R)
        dacc = np.array([r["abst_clean_acc"] - r["plur_clean_acc"] for r in R])
        ideal_ok = sum(abs(r["abst_beta_star"] - r["ideal_beta_star"]) <= 0.05 + 1e-9 for r in R)
        print(f"{g:16s} n={len(R):2d} beta* plur med {np.median([r['plur_beta_star'] for r in R]):.3f} "
              f"abst med {np.median([r['abst_beta_star'] for r in R]):.3f} | gain med {np.median(gain):+.3f} "
              f"mean {gain.mean():+.3f} | up {int((gain > 0).sum())} same {int((gain == 0).sum())} down {int((gain < 0).sum())} "
              f"| collapse@0.20 {col_p}->{col_a} | clean acc d med {np.median(dacc):+.4f} | ideal+-1 {ideal_ok}/{len(R)} "
              f"| CTRmal@0.2 med {np.median([r['plur_CTRmal20'] for r in R]):.3f}->{np.median([r['abst_CTRmal20'] for r in R]):.3f}")


if __name__ == "__main__":
    main()
