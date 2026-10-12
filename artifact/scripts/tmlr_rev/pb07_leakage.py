#!/usr/bin/env python3
"""PB07 (preregistered, predeclarations/tmlr_PB07_leakage_shortcut.md).

  --part a   certified metrics on the deduplicated IoT-23 test subset (flows whose feature vector
             never occurs in training), from the member bank (needs banks A and B complete)
  --part b   capture-identity shortcut: capture-prior classifier, multinomial logistic regression and a
             centralised (32,16) MLP predicting the capture from the 31 features
Writes results/pb07a_dedup.json, results/pb07b_shortcut.json."""
import argparse, collections, glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from build_member_bank import load_bank, BANKDIR

BF = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]


def dedup_mask(tb):
    Xtr = np.ascontiguousarray(tb["Xtr"].numpy()); Xte = np.ascontiguousarray(tb["Xte"].numpy())
    v = lambda A: A.view(np.dtype((np.void, A.dtype.itemsize * A.shape[1]))).ravel()
    trset = set(v(Xtr).tolist())
    return np.array([k not in trset for k in v(Xte).tolist()])     # True = unseen vector


def part_a():
    tb = C.prepare_base("iot-23")
    keep = dedup_mask(tb)
    y = tb["yte_np"][keep]
    tau_d = float(max(y.mean(), 1 - y.mean()))
    res = dict(n_test=int(len(keep)), n_dedup=int(keep.sum()), dedup_mal_share=float(y.mean()), tau_dedup=tau_d,
               ensembles=[])
    metas = sorted(glob.glob(os.path.join(BANKDIR, "iot-23_*_dph1-3_na_*.json")))
    for mf in metas:
        m = json.load(open(mf))
        j = m["job"]
        if j["kind"] not in ("iid", "device_derived") or not m["check"]["reproduced"]:
            continue
        if not (j["seed"] in (0, 1, 2) or 10 <= j["seed"] <= 39):   # banks A and B only (preregistered)
            continue
        preds, subs, _ = load_bank(m["id"])
        v_all = C.votes_from_member_preds(preds)
        v_d = C.votes_from_member_preds(preds[:, keep])
        full = C.XC.certify_exact(v_all, tb["yte_np"], subs, 20, j["k"], BF, tb["tau"])
        ded = C.XC.certify_exact(v_d, y, subs, 20, j["k"], BF, tau_d)
        res["ensembles"].append(dict(
            id=m["id"], kind=j["kind"], seed=j["seed"], k=j["k"], K=len(subs),
            beta_star_full=full["beta_star"], beta_star_dedup=ded["beta_star"],
            mean_margin_full=full["mean_margin"], mean_margin_dedup=ded["mean_margin"],
            grid=[dict(beta=g["beta"], CA_full=gf["CA"], CA_dedup=g["CA"], CTR_mal_dedup=g["CTR_mal"],
                       CTR_ben_dedup=g["CTR_ben"], coverage_dedup=g["coverage"],
                       collapsed_dedup=bool(g["CA"] <= tau_d))
                  for g, gf in zip(ded["grid"], full["grid"])]))
    summ = {}
    for kind in ("iid", "device_derived"):
        for k in (1, 2, 3, 5, 8):
            e = [x for x in res["ensembles"] if x["kind"] == kind and x["k"] == k]
            if not e:
                continue
            ca04 = [g["CA_dedup"] for x in e for g in x["grid"] if abs(g["beta"] - 0.4) < 1e-9]
            col02 = [g["collapsed_dedup"] for x in e for g in x["grid"] if abs(g["beta"] - 0.2) < 1e-9]
            summ[f"{kind}|k{k}"] = dict(n=len(e), median_bstar_full=float(np.median([x["beta_star_full"] for x in e])),
                                        median_bstar_dedup=float(np.median([x["beta_star_dedup"] for x in e])),
                                        median_CA_dedup_b04=(float(np.median(ca04)) if ca04 else None),
                                        collapse_b02_dedup=(f"{sum(col02)}/{len(col02)}" if col02 else None))
    res["summary"] = summ
    iid1 = summ.get("iid|k1", {})
    res["falsifier"] = dict(iid_k1_median_bstar_dedup=iid1.get("median_bstar_dedup"),
                            iid_k1_median_CA_dedup_b04=iid1.get("median_CA_dedup_b04"), tau_dedup=tau_d,
                            fired=bool(iid1 and (iid1["median_bstar_dedup"] < 0.45 or
                                                 (iid1["median_CA_dedup_b04"] or 0) <= tau_d)))
    C.dump("pb07a_dedup.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "ensembles"}, indent=1))


def part_b():
    import torch, torch.nn as nn
    from sklearn.linear_model import LogisticRegression
    tb = C.prepare_base("iot-23")
    Xtr, Xte = tb["Xtr"].numpy(), tb["Xte"].numpy()
    dtr = tb["dtr"]
    # test capture codes: rebuild the split (same as runner.prepare)
    cwd = os.getcwd(); os.chdir(C.REPO)
    b = C.DATA.load_dataset(C.base_cfg("iot-23", "iid", 0), verbose=False)
    os.chdir(cwd)
    tr, te = C.DATA.time_split_within_device(b["y"], b["device"], 0.8, block=b.get("block"))
    dte = b["device"][te]
    assert (b["device"][tr] == dtr).all()
    ytr, yte = tb["ytr_np"], tb["yte_np"]
    maj = {d: int(ytr[dtr == d].mean() > 0.5) for d in np.unique(dtr)}
    prior_acc = float(np.mean([maj[d] == yy for d, yy in zip(dte, yte)]))
    lr = LogisticRegression(max_iter=2000).fit(Xtr, dtr)
    lr_acc = float((lr.predict(Xte) == dte).mean())
    # capture predicted from features, then the capture's majority label
    via = float(np.mean([maj[d] == yy for d, yy in zip(lr.predict(Xte), yte)]))
    torch.manual_seed(0)
    nd = int(dtr.max()) + 1
    net = nn.Sequential(nn.Linear(Xtr.shape[1], 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, nd))
    opt = torch.optim.SGD(net.parameters(), lr=0.05, momentum=0.9)
    X = torch.tensor(Xtr); Y = torch.tensor(dtr, dtype=torch.long)
    g = torch.Generator().manual_seed(0)
    for _ in range(15):
        perm = torch.randperm(len(Y), generator=g)
        for s in range(0, len(Y), 512):
            ix = perm[s:s + 512]
            opt.zero_grad(); nn.functional.cross_entropy(net(X[ix]), Y[ix]).backward(); opt.step()
    with torch.no_grad():
        mlp_pred = net(torch.tensor(Xte)).argmax(1).numpy()
    res = dict(n_captures=nd, tau=tb["tau"], capture_prior_label_accuracy=prior_acc,
               capture_majority_labels={b["device_names"][d]: v for d, v in maj.items()},
               logreg_capture_accuracy=lr_acc, logreg_capture_then_prior_label_accuracy=via,
               mlp_capture_accuracy=float((mlp_pred == dte).mean()),
               mlp_capture_then_prior_label_accuracy=float(np.mean([maj[d] == yy for d, yy in zip(mlp_pred, yte)])),
               test_captures_all_in_train=bool(set(np.unique(dte)) <= set(np.unique(dtr))),
               note="descriptive; a high capture-prior accuracy means the binary label is largely "
                    "predictable from capture identity")
    C.dump("pb07b_shortcut.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["a", "b"], required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        n = len(glob.glob(os.path.join(BANKDIR, "iot-23_*_dph1-3_na_*.json")))
        print(f"PB07{a.part}: " + ("bank ensembles available now: %d (needs banks A+B: 156 IID/device "
                                   "ensembles)" % n if a.part == "a" else "capture shortcut, rows + one small MLP"))
    else:
        part_a() if a.part == "a" else part_b()
