"""Stage orchestration + CLI.

Stages (design 11.1):
  0 substrate       build + measure partitions, no training
  1 baseline        centralized / FedAvg competence at beta=0; fixes tau_triv
  2 empirical       attack suite x defense suite x beta grid  -> EA_min
  3 certification   Algorithm 2 (+3)                          -> CA          [GATE G1]
  4 gap             Algorithm 7                               -> Gamma, R_lit\\R_hon
  5 skew            skew sweep + matched-Dirichlet control (Alg 4) + LODO (Alg 5)

Usage:
  python -m fedhomeguard.runner --stage 0 --config configs/stage0_substrate.yaml
  python -m fedhomeguard.runner --stage 3 --config configs/stage3_certification.yaml
  python -m fedhomeguard.runner --stage 3 --config ... --smoke   # tiny, for wiring checks
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np, torch

from . import certify as C, config as CFG, data as DATA, fl as FL, metrics as M
from . import partition as P, capability as CAP, attacks as A
from .models import build_model, n_params, resolve_device


# ------------------------------------------------------------------------- plumbing
def prepare(cfg, verbose=True):
    dev = resolve_device(cfg.device)
    if verbose: print(f"device={dev}  dataset={cfg.data.dataset}")
    bundle = DATA.load_dataset(cfg, verbose=verbose)
    X, y, device = bundle["X"], bundle["y"], bundle["device"]
    lodo = getattr(cfg.data, "lodo_device", None)
    if lodo:
        # W7/E5: hold one device out of training entirely and test only on it.
        tr, te = DATA.leave_one_device_out(device, lodo)
    else:
        tr, te = DATA.time_split_within_device(y, device, cfg.data.train_frac,
                                               block=bundle.get("block"))
    Xtr, Xte, _, _ = DATA.standardize(X[tr], X[te])
    ytr, yte, dtr = y[tr], y[te], device[tr]
    parts, pmeta = P.build(cfg, ytr, dtr)
    t = dict(
        Xtr=torch.tensor(Xtr, device=dev), ytr=torch.tensor(ytr, device=dev),
        Xte=torch.tensor(Xte, device=dev), yte_np=yte, ytr_np=ytr, dtr=dtr,
        parts={i: torch.tensor(v, device=dev) for i, v in parts.items()},
        parts_np=parts, pmeta=pmeta, dev=dev, tau=M.tau_triv(yte),
        bal=M.balanced_index(yte, cfg.partition.seed),
        fam_te=(bundle["family"][te] if bundle.get("family") is not None else None),
        n_class=int(getattr(cfg.model, "n_class", 2) or 2),
        class_names=bundle.get("class_names"),
        device_names=bundle["device_names"], feature_names=bundle["feature_names"])
    if verbose:
        print(f"train={len(ytr)} test={len(yte)} dim={Xtr.shape[1]} tau_triv={t['tau']:.4f}")
        print(f"partition={pmeta}")
    return t


def apply_smoke(cfg):
    """Shrink everything so wiring can be verified in seconds."""
    cfg.data.max_rows_per_device = 2_000
    cfg.partition.N = 8
    cfg.fl.rounds_T = 2
    cfg.cert.k = min(cfg.cert.k, 3)
    cfg.cert.K = 12
    cfg.seeds = (cfg.seeds[0],)
    cfg.betas = (0.0, 0.10, 0.25)
    return cfg


def _save(cfg, name, payload):
    os.makedirs(cfg.out_dir, exist_ok=True)
    path = os.path.join(cfg.out_dir, f"{name}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"wrote {path}")
    return path


# --------------------------------------------------------------------------- stages
def stage0_substrate(cfg):
    t = prepare(cfg)
    out = dict(stage=0, dataset=cfg.data.dataset, partition=t["pmeta"],
               n_train=int(len(t["ytr_np"])), n_test=int(len(t["yte_np"])),
               dim=int(t["Xtr"].shape[1]), tau_triv=round(t["tau"], 6),
               device_names=t["device_names"],
               per_client_sizes={str(i): int(len(v)) for i, v in t["parts_np"].items()})
    return _save(cfg, f"stage0_{cfg.name}", out)


def stage1_baseline(cfg):
    t = prepare(cfg)
    t0 = time.time()
    g = FL.fl_run(cfg, list(range(cfg.partition.N)), t["Xtr"], t["ytr"], t["parts"])
    acc = FL.accuracy(g, t["Xte"], t["yte_np"])
    accb = FL.accuracy(g, t["Xte"][t["bal"]], t["yte_np"][t["bal"]])
    out = dict(stage=1, partition=t["pmeta"], tau_triv=round(t["tau"], 6),
               fedavg_acc=round(acc, 6), fedavg_acc_balanced=round(accb, 6),
               beats_trivial=bool(acc > t["tau"]), secs=round(time.time() - t0, 1))
    print(f"FedAvg acc={acc:.4f} (tau_triv={t['tau']:.4f}) balanced={accb:.4f}")
    return _save(cfg, f"stage1_{cfg.name}", out)


def stage2_empirical(cfg, attacks=None, defenses=None):
    t = prepare(cfg)
    attacks = attacks or ["label_flip", "sign_flip", "gaussian", "ipm", "alie"]
    defenses = defenses or ["fedavg", "krum", "trimmed_mean", "median", "norm_clip"]
    recs = []
    for defn in defenses:
        cfg.defense.name = defn
        cfg.defense.observability = __import__(
            "fedhomeguard.defenses", fromlist=["LEVEL"]).LEVEL[defn]
        for b in cfg.betas:
            mal = A.select_malicious(cfg.partition.N, b, cfg.adversary.seed)
            for atk in (["none"] if b == 0 else attacks):
                if atk != "none":
                    try:
                        A.check_capability(atk, cfg.adversary.F3_knowledge)
                    except ValueError as e:
                        print(f"  skip {atk}: {e}"); continue
                cfg.adversary.beta = b
                g = FL.fl_run(cfg, list(range(cfg.partition.N)), t["Xtr"], t["ytr"],
                              t["parts"], malicious_ids=mal,
                              attack=None if atk == "none" else atk)
                acc = FL.accuracy(g, t["Xte"], t["yte_np"])
                recs.append(dict(defense=defn, attack=atk, beta=b, m=len(mal),
                                 EA=round(acc, 6)))
                print(f"  {defn:14s} {atk:11s} beta={b:.2f} EA={acc:.4f}")
    out = dict(stage=2, partition=t["pmeta"], tau_triv=round(t["tau"], 6), records=recs)
    return _save(cfg, f"stage2_{cfg.name}", out)


def stage3_certification(cfg, verbose=True):
    """GATE G1 IS EVALUATED HERE. Build nothing below this until it resolves."""
    t = prepare(cfg)
    N, k = cfg.partition.N, cfg.cert.k
    subsets, exact, total = C.choose_subsets(N, k, cfg.cert.K, cfg.partition.seed,
                                             cfg.cert.prefer_exact)
    if verbose:
        print(f"C({N},{k})={total}  K={len(subsets)}  exact={exact}  "
              f"beta_geo={C.beta_geo(N,k):.3f} (ceiling 1-2^(-1/k)="
              f"{C.beta_geo_asymptotic(k):.3f})")
    votes = np.zeros((len(t["yte_np"]), 2), np.int32)
    t0, steps = time.time(), 0
    for j, S in enumerate(subsets):
        g = FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"])
        pred = FL.predict(g, t["Xte"])
        votes[np.arange(len(pred)), pred] += 1
        steps += cfg.fl.rounds_T * sum(len(t["parts_np"][i]) for i in S)
        if verbose and (j + 1) % max(1, len(subsets) // 10) == 0:
            print(f"  ensemble {j+1}/{len(subsets)}  [{time.time()-t0:.0f}s]")
    cert = C.certify_from_votes(votes, t["yte_np"], N, k, cfg.betas, exact,
                                cfg.cert.confidence, t["tau"])
    certb = C.certify_from_votes(votes[t["bal"]], t["yte_np"][t["bal"]], N, k,
                                 cfg.betas, exact, cfg.cert.confidence, 0.5)
    cert["balanced"] = dict(tau_triv=0.5, beta_star=certb["beta_star"],
                            grid=[{kk: g[kk] for kk in ("beta", "CA", "severity")}
                                  for g in certb["grid"]])
    cert["S_JS"] = t["pmeta"]["S_JS"]
    gate = gate_verdict(cert, t["tau"])
    rec = CAP.build_record(cfg, run_id=f"stage3_{cfg.name}", partition_meta=t["pmeta"],
                           n_params=n_params(build_model(cfg, t["Xtr"].shape[1])),
                           metrics={kk: cert[kk] for kk in
                                    ("beta_star", "beta_geo", "ensemble_acc", "MC_het",
                                     "tau_triv")},
                           budget=dict(total_gradient_steps=int(steps),
                                       wall_clock_s=round(time.time() - t0, 1)))
    CAP.save(rec, cfg.out_dir, f"stage3_{cfg.name}")
    out = dict(stage=3, partition=t["pmeta"], certification=cert, gate=gate,
               secs=round(time.time() - t0, 1))
    if verbose:
        for g in cert["grid"]:
            print(f"  beta={g['beta']:4.2f} CA={g['CA']:.4f} (tau={g['tau_triv']:.3f}) "
                  f"{g['severity']:20s} possible={g['combinatorially_possible']}")
        print(f"  GATE G1 -> {gate['exit']}: {gate['reason']}")
    return _save(cfg, f"stage3_{cfg.name}", out)


def gate_verdict(cert: dict, tau: float, target_beta: float = 0.10) -> dict:
    """Design 13: the three named exits, decided in advance."""
    row = next((g for g in cert["grid"] if abs(g["beta"] - target_beta) < 1e-9), None)
    ca0 = next((g["CA"] for g in cert["grid"] if g["beta"] == 0.0), 0.0)
    if ca0 <= tau:
        return dict(exit="EXIT_3_PIVOT", reason=(
            "S3 collapse: CA at beta=0 is already at or below tau_triv -- heterogeneity "
            "alone killed the certificate, before any adversary. Negative-result paper (D2)."))
    if row is None:
        return dict(exit="UNDETERMINED", reason=f"beta={target_beta} not in the grid")
    if row["CA"] > tau + 0.10:
        return dict(exit="EXIT_1_GO", reason=(
            f"CA({target_beta})={row['CA']:.4f} > tau_triv+0.10={tau+0.10:.4f} (S0). "
            "Full paper; Act II is live."))
    if row["CA"] > tau:
        return dict(exit="EXIT_2_NARROW", reason=(
            f"CA({target_beta})={row['CA']:.4f} is above tau_triv={tau:.4f} but not by 0.10 "
            "(S1). Frontier paper: certification works below where the field publishes."))
    return dict(exit="EXIT_3_PIVOT", reason=(
        f"CA({target_beta})={row['CA']:.4f} <= tau_triv={tau:.4f} (S2 vacuous). "
        "Negative-result paper (D2). Do not manufacture a positive result."))


def stage4_gap(cfg, stage2_path=None, stage3_path=None):
    s2 = json.load(open(stage2_path or os.path.join(cfg.out_dir, f"stage2_{cfg.name}.json")))
    s3 = json.load(open(stage3_path or os.path.join(cfg.out_dir, f"stage3_{cfg.name}.json")))
    summ = M.summarize(s3["certification"], s2["records"])
    if summ["any_bug"]:
        print("!! Gamma < 0 detected -- BUG SIGNAL, not a finding (design C8). Audit "
              "certificate soundness and whether an attack left the declared threat class.")
    for r in summ["rows"]:
        print(f"  beta={r['beta']:4.2f} CA={r['CA']:.4f} EA_min={r.get('emp_EA_min')} "
              f"Gamma={r.get('Gamma')}")
    return _save(cfg, f"stage4_{cfg.name}", dict(stage=4, summary=summ))


def stage5_skew(cfg, alphas=(100.0, 10.0, 1.0, 0.5, 0.1)):
    """Skew sweep + Algorithm 4 matched control + Algorithm 5 leave-one-device-out."""
    base = prepare(cfg, verbose=True)
    target = base["pmeta"]["S_JS"]
    print(f"device-derived S_JS={target:.4f}; matching Dirichlet control to it (Alg 4)")
    rows = []

    def run_for(kind, tag=None, **over):
        c = CFG.from_dict(json.loads(json.dumps(cfg.to_dict(), default=str)))
        c.partition.kind = kind
        for kk, vv in over.items():
            setattr(c.partition, kk, vv)
        c.name = f"{cfg.name}_{kind}" + ("" if not over else "_" + "_".join(map(str, over.values())))
        t = prepare(c, verbose=False)
        subsets, exact, _ = C.choose_subsets(c.partition.N, c.cert.k, c.cert.K,
                                             c.partition.seed, c.cert.prefer_exact)
        votes = np.zeros((len(t["yte_np"]), 2), np.int32)
        for S in subsets:
            pred = FL.predict(FL.fl_run(c, list(S), t["Xtr"], t["ytr"], t["parts"]), t["Xte"])
            votes[np.arange(len(pred)), pred] += 1
        cert = C.certify_from_votes(votes, t["yte_np"], c.partition.N, c.cert.k,
                                    c.betas, exact, c.cert.confidence, t["tau"])
        r = dict(kind=kind, tag=tag or kind,
                 **{kk: t["pmeta"][kk] for kk in ("S_JS", "S_dev")},
                 beta_star=cert["beta_star"], beta_geo=cert["beta_geo"],
                 ensemble_acc=cert["ensemble_acc"], MC_het=cert["MC_het"],
                 meta={kk: vv for kk, vv in t["pmeta"].items() if kk.startswith(("alpha", "matched", "drop"))})
        rows.append(r)
        print(f"  {r['tag']:26s} S_JS={r['S_JS']:.4f} beta*={r['beta_star']:.2f} "
              f"ens_acc={r['ensemble_acc']:.4f} MC_het={r['MC_het']:.3f}")
        return r

    run_for("device_derived", tag="device_derived")
    run_for("iid", tag="iid")
    run_for("dirichlet_matched", tag="matched_control", match_target_S_JS=target)
    for a in alphas:
        run_for("dirichlet", tag=f"dirichlet_label_a{a:g}", dirichlet_alpha=a)
        run_for("dirichlet_device", tag=f"dirichlet_device_a{a:g}", dirichlet_alpha=a)
    for d, nm in enumerate(base["device_names"]):
        run_for("device_derived", tag=f"LODO_drop_{nm}", drop_device=d)

    dev_row = next(r for r in rows if r["tag"] == "device_derived")
    mat_row = next((r for r in rows if r["tag"] == "matched_control"), None)
    necessity = None
    if mat_row:
        delta = dev_row["beta_star"] - mat_row["beta_star"]
        necessity = dict(
            delta_beta_star=round(delta, 6),
            matched_S_JS=mat_row["S_JS"], device_S_JS=dev_row["S_JS"],
            skew_residual=round(dev_row["S_JS"] - mat_row["S_JS"], 6),
            control_valid=bool(abs(dev_row["S_JS"] - mat_row["S_JS"]) <= 0.05),
            necessity_supported=bool(delta < 0),
            note=("Device STRUCTURE hurts beyond matched skew MAGNITUDE."
                  if delta < 0 else
                  "NOT supported: skew magnitude, not device structure, drives the effect. "
                  "Design Algorithm 4 line 8 -- report this and downgrade the D1 claim. "
                  "Single seed here; the confirmatory version needs paired seeds + 99% CI. "
                  "If control_valid is False the two partitions differ in skew MAGNITUDE "
                  "and the comparison is confounded -- do not report necessity from it."))
        print(f"  NECESSITY: delta beta* = {delta:+.3f} -> {necessity['note']}")
    lodo = [r for r in rows if r["tag"].startswith("LODO_")]
    structural = None
    if lodo:
        base_bs = dev_row["beta_star"]
        contrib = {r["tag"]: round(base_bs - r["beta_star"], 6) for r in lodo}
        tot = sum(abs(v) for v in contrib.values()) or 1.0
        worst = max(contrib, key=lambda kk: abs(contrib[kk]))
        structural = dict(contributions=contrib, dominant=worst,
                          dominant_share=round(abs(contrib[worst]) / tot, 4),
                          collapse_is_structural=bool(abs(contrib[worst]) / tot <= 0.5),
                          note="ALGORITHM 5: if one device accounts for >50% of the "
                               "effect the collapse is that device's artifact, not a "
                               "structural property, and must be reported as such.")
        print(f"  LODO: dominant={worst} share={structural['dominant_share']:.2f} "
              f"structural={structural['collapse_is_structural']}")
    return _save(cfg, f"stage5_{cfg.name}",
                 dict(stage=5, rows=rows, necessity=necessity, structural=structural))


STAGES = {0: stage0_substrate, 1: stage1_baseline, 2: stage2_empirical,
          3: stage3_certification, 4: stage4_gap, 5: stage5_skew}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fedhomeguard.runner")
    ap.add_argument("--stage", type=int, required=True, choices=sorted(STAGES))
    ap.add_argument("--config", required=True)
    ap.add_argument("--name", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--smoke", action="store_true", help="tiny run to verify wiring")
    a = ap.parse_args(argv)
    cfg = CFG.load(a.config)
    if a.name: cfg.name = a.name
    if a.out_dir: cfg.out_dir = a.out_dir
    if a.smoke:
        cfg = apply_smoke(cfg); cfg.name += "_smoke"
    cfg.save(os.path.join(cfg.out_dir, f"config_{cfg.name}.json"))
    return STAGES[a.stage](cfg)


if __name__ == "__main__":
    main()
