#!/usr/bin/env python3
"""E2/E3/E4/E6 driver -- the canonical same-predictor experiment.

Emits one JSONL row per (partition_type, partition_seed, k, beta, malicious_set)
into a single canonical result file. Every table, figure and prose number in the
paper is generated from that file, which is the review's fix for the numerical
contradictions (review sec 5).

  python scripts/exp_e2.py --partition device_derived --pseed 0 --k 1 2 3 \
      --betas 0 0.05 0.1 0.2 0.3 0.4 --mal-seeds 0 1 2 --out results/canonical/e2.jsonl

Resumable: rows already present in --out are skipped.
"""
from __future__ import annotations
import argparse, json, math, os, sys, time
from itertools import combinations
import numpy as np
import torch

# Tiny MLPs are ~5x FASTER single-threaded on CPU than on MPS (kernel-launch
# overhead dominates at this model size), and CPU shards across cores, which MPS
# does not. Measured 0.52 s/member on CPU against 2.81 s on MPS.
torch.set_num_threads(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import config as CFG, runner as R, exactcert as XC, ensemble as EN
from fedhomeguard import grouping as GR
from fedhomeguard import defenses as D

ATTACKS = ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]


def build_subsets(N, k, K_cap, seed):
    """Full enumeration when C(N,k) <= K_cap, else a uniform sample without
    replacement. Either way the realised subsets ARE the deployed ensemble and the
    certificate over them is exact."""
    tot = math.comb(N, k)
    allc = list(combinations(range(N), k))
    if tot <= K_cap:
        return allc, True, tot
    rng = np.random.default_rng(10_000 + seed * 97 + k)
    sel = rng.choice(tot, size=K_cap, replace=False)
    return [allc[j] for j in sorted(sel)], False, tot


def malicious_set(mode, N, m, seed, t):
    if m == 0:
        return []
    if mode == "random":
        return sorted(np.random.default_rng(seed).choice(N, size=m, replace=False).tolist())
    sizes = np.array([len(t["parts_np"][i]) for i in range(N)])
    if mode == "high_volume":
        return sorted(np.argsort(-sizes)[:m].tolist())
    if mode == "rare_device":
        # clients holding the rarest device types: removing them removes coverage
        dev = t["dtr"]
        counts = np.bincount(dev, minlength=int(dev.max()) + 1)
        score = np.zeros(N)
        for i in range(N):
            idx = t["parts_np"][i]
            if len(idx) == 0:
                continue
            ds = np.unique(dev[idx])
            score[i] = float(np.sum(1.0 / np.maximum(counts[ds], 1)))
        return sorted(np.argsort(-score)[:m].tolist())
    raise ValueError(mode)


def load_done(path):
    done = set()
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            # the key must include every knob that distinguishes a run, or a later
            # sweep silently resumes over rows it never produced
            kk = (r["partition_type"], r["partition_seed"], r["k"],
                  round(r["beta"], 4), r["mal_mode"], r["mal_seed"],
                  r.get("dirichlet_alpha"), r.get("N"), r.get("arch"),
                  tuple(r.get("devices_per_household") or ()))
            if r.get("pairing"):
                kk = kk + (r["pairing"],)
            done.add(kk)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage3_certification.yaml")
    ap.add_argument("--partition", default="device_derived")
    ap.add_argument("--lodo", default=None,
                    help="W7/E5: hold this device out of training and "
                         "test only on it (leave-one-device-out fold)")
    ap.add_argument("--pseed", type=int, nargs="+", default=[0])
    ap.add_argument("--k", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--betas", type=float, nargs="+",
                    default=[0.0, 0.05, 0.10, 0.20, 0.30, 0.40])
    ap.add_argument("--mal-seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--mal-mode", nargs="+", default=["random"])
    ap.add_argument("--attacks", nargs="+", default=ATTACKS)
    ap.add_argument("--class-balanced", action="store_true",
                    help="inverse-frequency local loss (review E2)")
    ap.add_argument("--pop-std", action="store_true",
                    help="review r5: population std in alie/gaussian, so one honest "
                         "update gives sd 0 instead of NaN (default: committed "
                         "unbiased std, unchanged)")
    ap.add_argument("--single-honest-zero-sd", action="store_true",
                    help="review r6: the minimal fix (sd 0 in alie/gaussian only when a "
                         "member has exactly one honest update). Now the DEFAULT; the "
                         "flag is kept so earlier run scripts still parse")
    ap.add_argument("--legacy-nan-std", action="store_true",
                    help="opt out of the r6 correction: reproduce the frozen "
                         "pre-correction results (unbiased std, NaN for one honest "
                         "update) in results/canonical/e2_*")
    ap.add_argument("--scale", type=float, default=None,
                    help="adversary update scale; default keeps the config value")
    ap.add_argument("--K-cap", type=int, default=200)
    ap.add_argument("--k-caps", default=None,
                    help="per-k ensemble size, e.g. '1:20,2:190,3:500,5:200,8:200'")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--N", type=int, default=None, help="federation size (E10)")
    ap.add_argument("--dph", type=int, nargs=2, default=None,
                    help="devices per household, min max (E11)")
    ap.add_argument("--arch", default=None, help="model arch (E9), e.g. logreg")
    ap.add_argument("--multiclass", action="store_true",
                    help="E2 multi-class control: relabel IoT-23 to benign + one "
                         "class per attack family, which drops tau_triv from 0.72 "
                         "to 0.53 and tests whether the IID tightness result is a "
                         "property of the certificate or of a saturated binary task")
    ap.add_argument("--tag", default=None, help="label written into every row")
    ap.add_argument("--pairing", default=None, choices=["random", "anticluster"],
                    help="E3/F11: at k=2, build the ensemble from a 2-regular "
                         "pairing rather than from all C(N,2) subsets. Both modes "
                         "give K=N pairs with every household in exactly two, so "
                         "the degree sequence c_max reads is fixed and only WHICH "
                         "households are paired differs.")
    ap.add_argument("--clean-only", action="store_true",
                    help="certified arm only (E5/E7/E8): skip the attacked ensembles")
    ap.add_argument("--out", default="results/canonical/e2.jsonl")
    ap.add_argument("--alpha", type=float, default=None,
                    help="dirichlet concentration when --partition is dirichlet*")
    a = ap.parse_args()

    kcaps = {}
    if a.k_caps:
        for piece in a.k_caps.split(","):
            kk, vv = piece.split(":"); kcaps[int(kk)] = int(vv)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = load_done(a.out)
    fh = open(a.out, "a")
    t_start = time.time()

    for pseed in a.pseed:
        cfg = CFG.load(a.config)
        cfg.device = a.device
        cfg.partition.kind = a.partition
        cfg.partition.seed = pseed
        if a.lodo:
            cfg.data.lodo_device = a.lodo   # W7/E5 fold

        cfg.fl.seed = 0
        if a.alpha is not None:
            cfg.partition.dirichlet_alpha = a.alpha
        if a.N is not None:
            cfg.partition.N = a.N
        if a.dph is not None:
            cfg.partition.devices_per_household = list(a.dph)
        if a.arch is not None:
            cfg.model.arch = a.arch
        if a.multiclass:
            cfg.data.binary = False   # load_dataset sets cfg.model.n_class to match
        cfg.defense.name = "fedavg"          # members aggregate plainly, by construction
        cfg.defense.observability = D.LEVEL["fedavg"]
        cfg.adversary.F3_knowledge = "white_box"   # so ipm/alie are in class
        if a.scale is not None:
            cfg.adversary.scale = a.scale
        if a.legacy_nan_std and (a.pop_std or a.single_honest_zero_sd):
            raise SystemExit("--legacy-nan-std cannot be combined with a correction")
        if a.pop_std:
            cfg.adversary.pop_std = True
        if a.legacy_nan_std:
            cfg.adversary.legacy_nan_std = True
        if a.class_balanced:
            cfg.fl.class_balanced = True
        t = R.prepare(cfg, verbose=False)
        N = cfg.partition.N
        print(f"[{a.partition} pseed={pseed}] S_JS={t['pmeta']['S_JS']:.4f} "
              f"S_dev={t['pmeta'].get('S_dev')} tau={t['tau']:.4f}", flush=True)

        for k in a.k:
            pair_meta = None
            if a.pairing:
                if k != 2:
                    print(f"  k={k} SKIPPED: --pairing is a k=2 construction", flush=True)
                    continue
                subsets = GR.build_pairs(a.pairing, t["parts_np"], t["dtr"], N, pseed)
                pair_meta = GR.pairing_report(subsets, t["parts_np"], t["dtr"])
                # The realised pairs ARE the deployed ensemble, so Proposition 1
                # certifies them exactly; full_enumeration is False because these are
                # N of the C(N,2) pairs, not all of them, and the flag records which.
                exact_pop, tot = False, math.comb(N, 2)
                print(f"  k=2 pairing={a.pairing} {pair_meta}", flush=True)
            else:
                subsets, exact_pop, tot = build_subsets(N, k, kcaps.get(k, a.K_cap), pseed)
            cache = EN.MemberCache()
            t0 = time.time()
            clean_votes, _, subsets = EN.ensemble_votes(cfg, t, subsets, (), None, cache)
            # The guard exists to catch a sweep whose members mostly failed to train.
            # Under --pairing the ensemble size is N by construction, not K_cap, so
            # the K_cap-derived floor would reject a complete run.
            floor = (max(2, int(0.5 * N)) if a.pairing
                     else max(2, int(0.5 * kcaps.get(k, a.K_cap))))
            if len(subsets) < floor:
                print(f"  k={k} SKIPPED: only {len(subsets)} trainable members "
                      f"under this partition", flush=True)
                continue
            cert = XC.certify_exact(clean_votes, t["yte_np"], subsets, N, k,
                                    a.betas, t["tau"],
                                    family=t.get("fam_te"),
                                    class_names=t.get("class_names"))
            clean_secs = time.time() - t0
            print(f"  k={k} K={len(subsets)}/{tot} full_enum={exact_pop} "
                  f"ens_acc={cert['ensemble_acc']:.4f} mean_margin={cert['mean_margin']:.4f} "
                  f"beta*={cert['beta_star']:.3f}  [{clean_secs:.0f}s]", flush=True)

            by_beta = {round(g["beta"], 4): g for g in cert["grid"]}
            for b in a.betas:
                m = int(round(b * N))
                g = by_beta[round(b, 4)]
                modes = ["random"] if m == 0 else a.mal_mode
                for mode in modes:
                    seeds = [0] if (m == 0 or mode != "random") else a.mal_seeds
                    for ms in seeds:
                        key = (a.partition, pseed, k, round(b, 4), mode, ms,
                               a.alpha, N, cfg.model.arch,
                               tuple(cfg.partition.devices_per_household))
                        if a.pairing:
                            key = key + (a.pairing,)
                        if key in done:
                            continue
                        B = malicious_set(mode, N, m, 1000 + ms, t)
                        ta = time.time()
                        if m == 0 or a.clean_only:
                            ea = dict(per_attack={}, worst_attack=None,
                                      EA_ensemble=(cert["ensemble_acc"] if m == 0 else None),
                                      members_touched=0)
                        else:
                            ea = EN.attacked_ensemble_accuracy(cfg, t, subsets, B,
                                                               a.attacks, cache)
                        row = dict(
                            schema="fedhomeguard.canonical/v1",
                            partition_type=a.partition, partition_seed=pseed,
                            dirichlet_alpha=a.alpha, arch=cfg.model.arch,
                            devices_per_household=list(cfg.partition.devices_per_household),
                            tag=a.tag,
                            S_JS=t["pmeta"]["S_JS"], S_dev=t["pmeta"].get("S_dev"),
                            # The label space is part of the identity of a result:
                            # a CA of 0.90 means one thing against tau_triv 0.72 and
                            # another against 0.53.
                            pairing=a.pairing, pairing_meta=pair_meta,
                            n_class=int(t.get("n_class", 2) or 2),
                            class_names=t.get("class_names"),
                            per_class_certified=g.get("per_class_certified"),
                            N=N, k=k, K=len(subsets), n_subsets_total=tot,
                            full_enumeration=bool(exact_pop),
                            beta=float(b), m=m,
                            mal_mode=mode, mal_seed=ms, mal_members=B,
                            tau_triv=cert["tau_triv"],
                            # --- certified side (clean ensemble, exact certificate)
                            c_max=g["c_max"], c_max_mode=g["c_max_mode"],
                            corrupt_frac=g["corrupt_frac"],
                            cert_threshold=g["threshold"],
                            combinatorially_possible=g["combinatorially_possible"],
                            mean_vote_margin=cert["mean_margin"],
                            median_vote_margin=cert["median_margin"],
                            clean_ensemble_acc=cert["ensemble_acc"],
                            CA=g["CA"], CA_minus_tau=g["CA_minus_tau"],
                            coverage=g["coverage"], cert_wrong=g["cert_wrong"],
                            frac_correct_certified=g["frac_correct_certified"],
                            frac_certified_wrong=g["frac_certified_wrong"],
                            frac_geometric_impossible=g["frac_geometric_impossible"],
                            frac_margin_limited=g["frac_margin_limited"],
                            TPR=g["TPR"], FNR=g["FNR"], FPR=g["FPR"],
                            precision=g["precision"], balanced_acc=g["balanced_acc"],
                            macro_F1=g["macro_F1"],
                            CTR_mal=g["CTR_mal"], CTR_ben=g["CTR_ben"],
                            CTR_mal_by_family=g.get("CTR_mal_by_family"),
                            n_mal_by_family=g.get("n_mal_by_family"),
                            n_mal_test=g["n_mal_test"], n_ben_test=g["n_ben_test"],
                            # --- empirical side, SAME ensemble
                            EA_ensemble=ea["EA_ensemble"],
                            worst_attack=ea["worst_attack"],
                            EA_per_attack={kk: v["EA"] for kk, v in ea["per_attack"].items()},
                            # CA is the final-round predictor; EA is a window MINIMUM.
                            # Persist the final-round EA so the two can be compared on
                            # equal terms -- G_cert mixes estimators and can go negative.
                            EA_final_round={kk: v["EA_final_round"] for kk, v in ea["per_attack"].items()},
                            EA_window_spread={kk: v["EA_window_spread"] for kk, v in ea["per_attack"].items()},
                            members_touched=ea["members_touched"],
                            # --- the same-predictor gap
                            # C1 fix. CA is the FINAL-ROUND predictor -- the one actually
                            # deployed, which is what Prop. 1 is a statement about. EA_ensemble
                            # is a MINIMUM over an 8-round window, a deliberately conservative
                            # robustness statistic. Subtracting one from the other mixed two
                            # estimators and let the slack go negative (37/288 rows) next to a
                            # proof that it cannot. The slack now compares like with like; the
                            # window minimum is retained under its own name for the breakdown
                            # -point analysis, where conservatism is the right choice.
                            # With no adversary (m == 0) there is no attacked run: EA_ensemble
                            # is the clean ensemble accuracy and the slack is exactly 0. Keep
                            # that row rather than blanking it -- tab_gap prints beta = 0.
                            G_cert=(round(min(v["EA_final_round"] for v in ea["per_attack"].values())
                                          - g["CA"], 6)
                                    if ea["per_attack"] else
                                    (round(ea["EA_ensemble"] - g["CA"], 6)
                                     if ea["EA_ensemble"] is not None else None)),
                            G_cert_windowmin=(round(ea["EA_ensemble"] - g["CA"], 6)
                                              if ea["EA_ensemble"] is not None else None),
                            collapsed=bool(g["CA"] <= cert["tau_triv"]),
                            std_estimator=("population" if a.pop_std else
                                           "unbiased_legacy_nan" if a.legacy_nan_std
                                           else "single_honest_zero"),
                            secs=round(time.time() - ta, 2),
                            cache=cache.stats(),
                        )
                        fh.write(json.dumps(row) + "\n"); fh.flush()
                        print(f"    b={b:.2f} m={m} {mode}/{ms} CA={g['CA']:.4f} "
                              f"EA_ens={row['EA_ensemble']} G={row['G_cert']} "
                              f"[{row['secs']:.0f}s trainings={cache.stats()['trainings']}]",
                              flush=True)
    fh.close()
    print(f"DONE in {(time.time()-t_start)/60:.1f} min -> {a.out}")


if __name__ == "__main__":
    main()
