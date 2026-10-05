#!/usr/bin/env python3
"""Review r7: do the "finite" collapses of Section 6.3 have finite members?

Section 6.3 counts, over the void draws on which the drawn malicious set touches more
than half the members, the draws where some attack other than the x100 sign flip drives
the attacked ensemble to the minority-class rate. The result rows record accuracy, not
whether any member's weights went non-finite. This script reruns ONLY those collapsed
draws, and only their winning attack, on the default (corrected) code path, and records
per touched member whether any round's update (honest or malicious), any round's
aggregate, or the final weights are non-finite. It also rebuilds the draw's final-round
attacked accuracy from the probed members and checks it against the recorded value, so
the probe is shown to rerun the same computation.

The probe wraps the FedAvg aggregator (defenses.REGISTRY["fedavg"]), which sees every
client's update and produces every round's aggregate; nothing in the training path is
changed.

    python3 scripts/probe_r7_finite.py --workers 4
Writes results/r7_finite_probe/probe.jsonl (one row per collapsed draw).
"""
from __future__ import annotations
import argparse, glob, json, os, sys
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("OMP_NUM_THREADS", "1")

PUB = ("label_flip", "sign_flip", "gaussian", "ipm", "alie")
OUT = os.path.join(ROOT, "results", "r7_finite_probe")


def key(r):
    return (r["partition_type"], r["partition_seed"], r["k"], round(r["beta"], 4), r["mal_seed"])


def rows(pat):
    o = {}
    for f in glob.glob(os.path.join(ROOT, pat)):
        for l in open(f):
            if l.startswith("{"):
                r = json.loads(l); o[key(r)] = r
    return o


def collapsed_draws():
    """The draws Section 6.3 counts as finite-attack collapses, with the winning attack
    (the argmin over the five published attacks, as corrected, and replace_invert)."""
    corr = rows("results/r6_nan_fix/corrected/e2_*.jsonl")
    ns = rows("results/r4_normscaled/e2ns_*.jsonl")
    out = []
    for kk, r in corr.items():
        if r["m"] == 0 or r["combinatorially_possible"] or r["members_touched"] <= r["K"] / 2:
            continue
        ea = {a: r["EA_final_round"][a] for a in PUB}
        ea["replace_invert"] = ns[kk]["EA_final_round"]["replace_invert"]
        minority = 1 - r["tau_triv"]
        best = min(ea.values())
        if best > minority + 1e-3:
            continue
        # ties (sign_flip and ipm are the same update at scale 1): record all of them,
        # probe the first in a fixed order
        winners = [a for a in ("replace_invert",) + PUB if abs(ea[a] - best) < 1e-12]
        out.append(dict(key=list(kk), attack=winners[0], tied_with=winners[1:],
                        EA_recorded=best, tau=r["tau_triv"]))
    return out


def probe_group(job):
    import numpy as np, torch
    torch.set_num_threads(1)
    from fedhomeguard import config as CFG, runner as R, fl as FL, defenses as D
    from exp_e2 import build_subsets, malicious_set
    part, pseed, k, draws = job
    cfg = CFG.load(os.path.join(ROOT, "configs/stage3_certification.yaml"))
    cfg.device = "cpu"; cfg.partition.kind = part; cfg.partition.seed = pseed; cfg.fl.seed = 0
    cfg.defense.name = "fedavg"; cfg.defense.observability = D.LEVEL["fedavg"]
    cfg.adversary.F3_knowledge = "white_box"
    cwd = os.getcwd(); os.chdir(ROOT)
    try:
        t = R.prepare(cfg, verbose=False)
    finally:
        os.chdir(cwd)
    y = t["yte_np"]
    subsets, _, _ = build_subsets(20, k, {2: 190, 3: 500}[k], pseed)

    rec = {}
    orig = D.REGISTRY["fedavg"]
    fin = lambda v: bool(torch.isfinite(v).all())

    def probed(updates, **kw):
        mal = set(kw.get("malicious_ids") or ())
        for i, u in updates.items():
            if not fin(u):
                rec["update"] = True
                rec["mal_update" if i in mal else "honest_update"] = True
        a = orig(updates, **kw)
        if not fin(a):
            rec["aggregate"] = True
        return a
    D.REGISTRY["fedavg"] = probed

    def member(S, mal_in_S, attack):
        rec.clear()
        try:
            g, snaps = FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"],
                                 malicious_ids=tuple(mal_in_S),
                                 attack=attack if mal_in_S else None, snapshot_last=1)
        except ValueError as e:
            if "enough rows" not in str(e):
                raise
            return None, None
        FL.set_flat(g, snaps[-1])
        final_ok = fin(snaps[-1])
        return FL.predict(g, t["Xte"]), dict(rec, final_nonfinite=not final_ok)

    clean = {}
    for S in subsets:
        p, _ = member(S, (), None)
        clean[tuple(S)] = p
    out = []
    for d in draws:
        kk = d["key"]; m = int(round(kk[3] * 20))
        B = set(malicious_set("random", 20, m, 1000 + kk[4], t))
        cfg.adversary.scale = 1.0          # published scale (replace_invert ignores it)
        votes = np.zeros((len(y), 2), np.int32); ar = np.arange(len(y))
        n_touched = n_nf = n_nf_final = n_nf_mal = n_nf_honest = n_nf_agg = 0
        for S in subsets:
            if clean[tuple(S)] is None:
                continue                  # untrainable member, dropped as in exp_e2
            inter = sorted(B.intersection(S))
            if inter:
                p, info = member(S, inter, d["attack"])
                n_touched += 1
                any_nf = any(info.values())
                n_nf += any_nf; n_nf_final += info["final_nonfinite"]
                n_nf_mal += bool(info.get("mal_update")); n_nf_honest += bool(info.get("honest_update"))
                n_nf_agg += bool(info.get("aggregate"))
            else:
                p = clean[tuple(S)]
            votes[ar, p] += 1
        ea = float((votes.argmax(1) == y).mean())
        out.append(dict(d, partition=part, k=k, touched=n_touched,
                        members_nonfinite_any=n_nf, members_nonfinite_final=n_nf_final,
                        members_nonfinite_mal_update=n_nf_mal,
                        members_nonfinite_honest_update=n_nf_honest,
                        members_nonfinite_aggregate=n_nf_agg,
                        EA_probe=round(ea, 6), EA_match=abs(ea - d["EA_recorded"]) < 1e-6))
        print(f"{part} ps{pseed} k{k} b{kk[3]} ms{kk[4]} {d['attack']}: touched {n_touched} "
              f"nonfinite {n_nf} EA {ea:.6f} vs {d['EA_recorded']:.6f}", flush=True)
    D.REGISTRY["fedavg"] = orig
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    draws = collapsed_draws()
    groups = {}
    for d in draws:
        kk = d["key"]; groups.setdefault((kk[0], kk[1], kk[2]), []).append(d)
    jobs = [(p, s, k, ds) for (p, s, k), ds in sorted(groups.items())]
    print(f"{len(draws)} collapsed draws in {len(jobs)} (partition, draw, k) groups")
    os.makedirs(OUT, exist_ok=True)
    with Pool(a.workers) as pool:
        res = [r for chunk in pool.map(probe_group, jobs) for r in chunk]
    with open(os.path.join(OUT, "probe.jsonl"), "w") as fh:
        for r in res:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(res)} rows to {OUT}/probe.jsonl")


if __name__ == "__main__":
    main()
