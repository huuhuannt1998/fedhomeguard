#!/usr/bin/env python3
"""Which partition statistic actually predicts certifiability?

The paper introduces S_JS and leans on it. Two measured counterexamples say it is
not sufficient and not necessary:
  * volume-skewed partitions certify poorly at S_JS < 0.01;
  * N-BaIoT device-derived partitions certify at the geometric ceiling at S_JS 0.73.
So this script rebuilds every partition the experiments used -- through the same
runner path, so the instrument values cannot drift from what the runs saw -- and
ranks candidate instruments by how well they predict the measured beta*.

No training happens here. Partitioning and the certificate are already on disk;
this only joins them.
"""
from __future__ import annotations
import sys, os, json, glob, math, collections
sys.path.insert(0, "src"); sys.path.insert(0, "scripts")
import numpy as np
from fedhomeguard import runner as R
from fedhomeguard import config as CFG

INSTRUMENTS = ["S_JS", "S_dev", "S_lab", "min_minority", "frac_degenerate",
               "min_class_support", "min_size_share"]
BETA_GEO = {1: 0.450, 2: 0.250, 3: 0.150, 5: 0.100, 8: 0.050}

# file glob -> (config, how the partition kind is named in the row)
SOURCES = [
    ("results/canonical/e5f_*.jsonl",       "configs/stage3_certification.yaml"),
    ("results/canonical/e7f_*.jsonl",       "configs/stage3_certification.yaml"),
    ("results/canonical/e7_volskew.jsonl",  "configs/stage3_certification.yaml"),
    ("results/canonical/nb_cert_*.jsonl",   "configs/stage0_nbaiot.yaml"),
    ("results/canonical/nb9_cert_*.jsonl",  "configs/stage0_nbaiot.yaml"),
]


def rows_for(pattern):
    for path in sorted(glob.glob(pattern)):
        for line in open(path):
            line = line.strip()
            if line.startswith("{"):
                r = json.loads(line); r["_src"] = os.path.basename(path); yield r


def beta_star(cells, tau):
    """Largest grid beta whose certified accuracy still beats the trivial
    certificate. Taken over the WORST malicious seed, so it is not optimistic."""
    ok = [b for b, ca in cells.items() if ca > tau + 1e-9]
    return max(ok) if ok else 0.0


def main():
    # ---- collect measured beta* per partition draw -------------------------------
    draws = {}   # (cfgpath, kind, pseed, alpha, N, dph) -> {k: {beta: CA}}, tau
    for pattern, cfgpath in SOURCES:
        for r in rows_for(pattern):
            key = (cfgpath, r["partition_type"], int(r["partition_seed"]),
                   r.get("dirichlet_alpha"), int(r["N"]),
                   tuple(r.get("devices_per_household") or ()))
            d = draws.setdefault(key, {"tau": float(r["tau_triv"]), "k": {}})
            cell = d["k"].setdefault(int(r["k"]), {})
            b = round(float(r["beta"]), 4); ca = float(r["CA"])
            cell[b] = min(cell.get(b, ca), ca)

    print(f"{len(draws)} distinct partition draws across "
          f"{len({(k[0], k[1]) for k in draws})} (dataset, family) cells\n")

    # ---- rebuild each partition and read its instruments -------------------------
    out, cache, pcache = [], {}, {}
    for i, (key, d) in enumerate(sorted(draws.items(), key=lambda kv: str(kv[0])), 1):
        cfgpath, kind, pseed, alpha, N, dph = key
        if key in cache:
            pm = cache[key]
        else:
            cfg = CFG.load(cfgpath)
            cfg.device = "cpu"; cfg.partition.kind = kind; cfg.partition.seed = pseed
            cfg.partition.N = N
            if alpha is not None:
                cfg.partition.dirichlet_alpha = alpha
            if dph:
                cfg.partition.devices_per_household = list(dph)
            t = R.prepare(cfg, verbose=False)
            pm = t["pmeta"]
            cache[key] = pm
            from fedhomeguard import partition as _P
            pcache[key] = {q: _P.min_class_support(t["parts_np"], t["ytr_np"], q)
                           for q in (0.01, 0.02, 0.05, 0.10, 0.20)}
        for k, cells in sorted(d["k"].items()):
            out.append(dict(dataset=("nbaiot" if "nbaiot" in cfgpath else "iot23"),
                            family=kind, pseed=pseed, alpha=alpha, N=N, k=k,
                            beta_star=beta_star(cells, d["tau"]),
                            beta_geo=BETA_GEO.get(k),
                            _pkey=key,
                            **{s: pm.get(s) for s in INSTRUMENTS}))
        if i % 10 == 0:
            print(f"  rebuilt {i}/{len(draws)}", flush=True)

    with open("results/analysis/instruments.jsonl", "w") as fh:
        for r in out:
            fh.write(json.dumps({k: v for k, v in r.items() if k != "_pkey"}) + "\n")

    # ---- rank the instruments ----------------------------------------------------
    def spearman(a, b):
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i]); rk = [0.0] * len(v); i = 0
            while i < len(order):                      # average ties
                j = i
                while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                    j += 1
                for t in range(i, j + 1):
                    rk[order[t]] = (i + j) / 2.0
                i = j + 1
            return rk
        ra, rb = rank(a), rank(b); n = len(a)
        ma, mb = sum(ra) / n, sum(rb) / n
        num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
        den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
        return num / den if den else float("nan")

    # beta* is only comparable across k after normalising by the ceiling k imposes.
    for r in out:
        r["cert_frac"] = (r["beta_star"] / r["beta_geo"]) if r["beta_geo"] else None
    usable = [r for r in out if r["cert_frac"] is not None]
    print(f"\nSpearman rho against beta*/beta_geo  (n={len(usable)} draw-k cells, "
          f"{len({r['family'] for r in usable})} partition families, 2 datasets)")
    print(f"  {'instrument':16s} {'rho':>7s}   {'|rho|':>6s}")
    y = [r["cert_frac"] for r in usable]
    ranked = []
    for s in INSTRUMENTS:
        x = [r[s] for r in usable]
        if any(v is None for v in x):
            continue
        ranked.append((abs(spearman(x, y)), spearman(x, y), s))
    for a, rho, s in sorted(ranked, reverse=True):
        print(f"  {s:16s} {rho:7.3f}   {a:6.3f}")

    # A pooled rho over 7 (dataset, family) groups can be produced entirely by
    # between-family variation, with the cells inside a family neither independent
    # nor informative. So repeat it WITHIN each family that has variation in
    # cert_frac -- an instrument that only works between families is a description
    # of the families, not a predictor.
    # Group by (dataset, family, k), NOT (dataset, family). beta*/beta_geo does not
    # fully remove the k dependence -- at k=1 the observed range is 0.000-0.556 and
    # at k=2 it is 0.200-0.800 -- while every instrument here is a property of the
    # partition and so is constant across k for a given draw. Pooling two k values
    # therefore drives the rank correlation toward zero no matter how good the
    # instrument is. Grouping at the wrong level produced a spurious "nothing
    # predicts inside iot23 device_derived" that split-by-k refutes outright.
    print("\nwithin-(family, k) Spearman rho (cells with variation in cert_frac)")
    fam = collections.defaultdict(list)
    for r in usable:
        fam[(r["dataset"], r["family"], r["k"])].append(r)
    hdr2 = f"  {'dataset':8s} {'family':17s} {'k':>2s} {'n':>3s} " + " ".join(f"{s:>15s}" for s in INSTRUMENTS)
    print(hdr2)
    wins = collections.Counter(); seen = 0
    for key in sorted(fam):
        rr = fam[key]
        yy = [r["cert_frac"] for r in rr]
        if len(set(yy)) < 2:
            print(f"  {key[0]:8s} {key[1]:17s} {key[2]:2d} {len(rr):3d} " + " ".join(f"{'(constant)':>15s}" for _ in INSTRUMENTS))
            continue
        seen += 1
        cells, best, bestv = [], None, -1.0
        for s in INSTRUMENTS:
            xx = [r[s] for r in rr]
            if len(set(xx)) < 2:
                cells.append(f"{'(constant)':>15s}"); continue
            rho = spearman(xx, yy); cells.append(f"{rho:15.3f}")
            if abs(rho) > bestv:
                bestv, best = abs(rho), s
        if best:
            wins[best] += 1
        print(f"  {key[0]:8s} {key[1]:17s} {key[2]:2d} {len(rr):3d} " + " ".join(cells))
    if seen:
        print(f"  best instrument per cell, over {seen} (family, k) cells with variation: "
              + ", ".join(f"{k} x{v}" for k, v in wins.most_common()))

    # The single cleanest contrast in the whole study: same construction, same
    # measured S_JS, opposite outcome.
    a = [r for r in usable if r["dataset"] == "iot23" and r["family"] == "device_derived"]
    b = [r for r in usable if r["dataset"] == "nbaiot" and r["family"] == "device_derived"]
    if a and b:
        print("\nmatched contrast, device_derived on both datasets")
        print(f"  {'':10s} {'n':>3s} " + " ".join(f"{s:>15s}" for s in INSTRUMENTS) + f" {'cert_frac':>10s}")
        for nm, rr in (("iot23", a), ("nbaiot", b)):
            print(f"  {nm:10s} {len(rr):3d} "
                  + " ".join(f"{np.mean([r[s] for r in rr]):15.4f}" for s in INSTRUMENTS)
                  + f" {np.mean([r['cert_frac'] for r in rr]):10.3f}")

    # min_class_support was derived AFTER seeing the other six fail, so its
    # threshold q is a free parameter and must be swept in public. q=0.05 happens
    # to be the peak; quoting it alone would be a fit. What survives the sweep is
    # the qualitative claim -- any q <= 0.05 beats S_JS -- not the peak value.
    print("\nmin_class_support threshold sweep (q is a free post-hoc parameter)")
    print(f"  {'q':>6s} {'pooled rho':>11s} {'iot23 device_derived k=1 rho':>30s}")
    sub = [r for r in usable if r["dataset"] == "iot23"
           and r["family"] == "device_derived" and r["k"] == 1]
    ysub = [r["cert_frac"] for r in sub]
    for q in (0.01, 0.02, 0.05, 0.10, 0.20):
        xs = [pcache[r["_pkey"]][q] for r in usable]
        xr = [pcache[r["_pkey"]][q] for r in sub]
        a = spearman(xs, y)
        b = spearman(xr, ysub) if len(set(xr)) > 1 else float("nan")
        print(f"  {q:6.2f} {a:11.3f} {b:30.3f}")

    print("\nper (dataset, family) means")
    g = collections.defaultdict(list)
    for r in usable:
        g[(r["dataset"], r["family"])].append(r)
    hdr = "  " + f"{'dataset':8s} {'family':17s} {'n':>3s} " + " ".join(f"{s:>14s}" for s in INSTRUMENTS) + f" {'cert_frac':>9s}"
    print(hdr)
    for key in sorted(g):
        rr = g[key]
        vals = " ".join(f"{np.mean([r[s] for r in rr]):14.4f}" for s in INSTRUMENTS)
        print(f"  {key[0]:8s} {key[1]:17s} {len(rr):3d} {vals} "
              f"{np.mean([r['cert_frac'] for r in rr]):9.3f}")


if __name__ == "__main__":
    main()
