#!/usr/bin/env python3
"""P0: recompute every table and headline number of the submitted paper from the raw result rows,
with code written independently of the repository's generators.

Sources (all read-only): results/canonical/*.jsonl, results/r6_nan_fix/corrected/*.jsonl (the
attacked-arm rows the paper prints), results/analysis/{instruments,richness_instruments}.jsonl,
and the raw IoT-23 / N-BaIoT captures for the information-theoretic figures.

Writes results/p0_recompute.json.
"""
import collections, glob, json, math, os, sys
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

REPO = C.REPO
CORR = os.path.join(REPO, "results", "r6_nan_fix", "corrected")


def rows(pattern, base=C.CANON):
    out = []
    for f in sorted(glob.glob(os.path.join(base, pattern))):
        out += C.load_rows(f)
    return out


def bstar_by_draw(rs, k):
    by = collections.defaultdict(list)
    for r in rs:
        if r["k"] == k:
            by[r["partition_seed"]].append(r)
    out = {}
    for s, v in by.items():
        good = [r["beta"] for r in v if r["CA"] > r["tau_triv"]]
        out[s] = max(good) if good else 0.0
    return out


def first(rs, **kw):
    return [r for r in rs if all((round(r[k], 4) if isinstance(r[k], float) else r[k]) == v
                                 for k, v in kw.items())]


def med(x):
    return float(np.median(x)) if len(x) else float("nan")


def table1_9(res):
    """Tables 1 and 9: medians over 3 draws x 3 malicious sets (corrected e2 rows)."""
    rs = rows("e2_*.jsonl", CORR)
    t1 = {}
    for p in ("iid", "device_derived"):
        for k in (1, 2, 3):
            for b in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4):
                v = [r for r in rs if r["partition_type"] == p and r["k"] == k
                     and abs(r["beta"] - b) < 1e-9]
                t1[f"{p}|k{k}|b{b:g}"] = dict(
                    n_rows=len(v), n_draws=len({r["partition_seed"] for r in v}),
                    K=sorted({r["K"] for r in v}),
                    CA=med([r["CA"] for r in v]), CTR_mal=med([r["CTR_mal"] for r in v]),
                    CTR_ben=med([r["CTR_ben"] for r in v]),
                    EA_window=med([r["EA_ensemble"] for r in v if r["EA_ensemble"] is not None]),
                    G=med([r["G_cert"] for r in v if r["G_cert"] is not None]),
                    void=all(not r["combinatorially_possible"] for r in v),
                    G_max=max([r["G_cert"] for r in v if r["G_cert"] is not None], default=None))
    res["table1_9"] = t1
    # decomposition check CA = tau*CTRmal + (1-tau)*CTRben over every canonical + corrected row
    allr = rows("*.jsonl") + rows("*.jsonl", CORR)
    bad = [r for r in allr if r.get("CTR_mal") is not None and r.get("n_class", 2) == 2 and
           abs(r["CA"] - (r["tau_triv"] * r["CTR_mal"] + (1 - r["tau_triv"]) * r["CTR_ben"])) > 1e-6]
    res["decomposition"] = dict(n_rows=len([r for r in allr if r.get("CTR_mal") is not None
                                            and r.get("n_class", 2) == 2]),
                                n_violations_1e6=len(bad),
                                max_dev=max([abs(r["CA"] - (r["tau_triv"] * r["CTR_mal"] + (1 - r["tau_triv"]) * r["CTR_ben"]))
                                             for r in allr if r.get("CTR_mal") is not None and r.get("n_class", 2) == 2]))
    # 1% prior re-weighting over the 36 (partition, k, beta) cells
    cells = collections.defaultdict(list)
    for r in rs:
        cells[(r["partition_type"], r["k"], round(r["beta"], 4))].append(r)
    pri = {}
    for pi in (0.5, 0.1, 0.01, 0.001):
        ca = {c: med([pi * r["CTR_mal"] + (1 - pi) * r["CTR_ben"] for r in v]) for c, v in cells.items()}
        nonvoid = {c: v for c, v in ca.items() if any(r["combinatorially_possible"] for r in cells[c])}
        pri[str(pi)] = dict(n_cells=len(ca), n_nonvoid=len(nonvoid),
                            n_above_floor=sum(v > max(pi, 1 - pi) + 1e-12 for v in ca.values()),
                            best=max(ca.values()), iid_k1_b04=ca[("iid", 1, 0.4)])
    res["prior_reweight_e2"] = pri


def slack30(res):
    rs = rows("e24_slack30_iid.jsonl")
    poss = [r for r in rs if r["combinatorially_possible"] and r["G_cert"] is not None]
    res["slack30_iid_k1"] = dict(n_rows=len(rs), n_draws=len({r["partition_seed"] for r in rs}),
                                 n_possible=len(poss), max_G=max(r["G_cert"] for r in poss),
                                 max_G_window=max(r["G_cert_windowmin"] for r in poss),
                                 min_G=min(r["G_cert"] for r in poss))


def fig1_table4(res):
    out = {}
    for p in ("iid", "device_derived"):
        e5 = rows(f"e5f_{p}.jsonl")
        for k in (1, 2):
            b = bstar_by_draw(e5, k)
            out[f"{p}|k{k}"] = dict(n=len(b), median=med(list(b.values())),
                                    at_ceiling=sum(v == {1: 0.45, 2: 0.25}[k] for v in b.values()),
                                    values=sorted(b.values()))
        k3 = rows(f"e2k3full_{p}_s*.jsonl")
        b = bstar_by_draw(k3, 3)
        out[f"{p}|k3full"] = dict(n=len(b), median=med(list(b.values())), values=sorted(b.values()))
        k58 = rows(f"e2k58_cert_{p}_s*.jsonl")
        for k in (5, 8):
            b = bstar_by_draw(k58, k)
            out[f"{p}|k{k}"] = dict(n=len(b), median=med(list(b.values())), values=sorted(b.values()))
    res["fig1_bstar"] = out
    # Table 4: collapse over 30 draws
    t4 = {}
    for p in ("iid", "device_derived"):
        e5 = rows(f"e5f_{p}.jsonl")
        for k in (1, 2):
            for b in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4):
                v = [r for r in e5 if r["k"] == k and abs(r["beta"] - b) < 1e-9]
                x = sum(r["collapsed"] for r in v)
                # collapsed flag vs CA <= tau recomputed
                x2 = sum(r["CA"] <= r["tau_triv"] for r in v)
                t4[f"{p}|k{k}|b{b:g}"] = dict(x=x, x_recomputed=x2, n=len(v),
                                              wilson=[round(z, 2) for z in C.wilson(x2, len(v))])
    res["table4"] = t4


def table2(res):
    instr = [json.loads(l) for l in open(os.path.join(REPO, "results/analysis/instruments.jsonl"))]
    fam_map = {"device": ("e7f_devskew.jsonl", "dirichlet_device"),
               "label": ("e7f_labelskew.jsonl", "dirichlet"),
               "volume": ("e7_volskew.jsonl", "volume")}
    t2 = {}
    for fam, (f, ifam) in fam_map.items():
        rs = [r for r in rows(f) if r["k"] == 1]
        for a in sorted({r["dirichlet_alpha"] for r in rs}, reverse=True):
            v = [r for r in rs if r["dirichlet_alpha"] == a]
            bs = bstar_by_draw(v, 1)
            per_seed = {}
            for r in v:
                per_seed.setdefault(r["partition_seed"], r)
            fd = [x["frac_degenerate"] for x in instr if x["dataset"] == "iot23" and x["family"] == ifam
                  and x["k"] == 1 and x["alpha"] == a]
            t2[f"{fam}|{a:g}"] = dict(
                n_draws=len(per_seed), K=sorted({r["K"] for r in v}),
                S_JS_mean=float(np.mean([r["S_JS"] for r in per_seed.values()])),
                S_dev_mean=float(np.mean([r["S_dev"] for r in per_seed.values()])),
                fracDegen_median=med(fd), n_fracdegen=len(fd),
                margin_median=med([r["mean_vote_margin"] for r in per_seed.values()]),
                bstar_median=med(list(bs.values())), bstar_values=sorted(bs.values()))
    res["table2"] = t2


def table3_5(res):
    instr = [json.loads(l) for l in open(os.path.join(REPO, "results/analysis/instruments.jsonl"))]
    t3 = {}
    for ds, files in (("iot23", ("e5f_iid.jsonl", "e5f_device_derived.jsonl")),
                      ("nbaiot", ("nb9_cert_iid.jsonl", "nb9_cert_device_derived.jsonl"))):
        for f in files:
            rs = [r for r in rows(f) if r["k"] == 1]
            p = rs[0]["partition_type"]
            per = {}
            for r in rs:
                per.setdefault(r["partition_seed"], r)
            bs = bstar_by_draw(rs, 1)
            col = [r for r in rs if abs(r["beta"] - 0.2) < 1e-9]
            x = sum(r["CA"] <= r["tau_triv"] for r in col)
            fd = [z["frac_degenerate"] for z in instr if z["dataset"] == ds and z["family"] == p and z["k"] == 1]
            t3[f"{ds}|{p}"] = dict(n=len(per), S_JS_mean=float(np.mean([r["S_JS"] for r in per.values()])),
                                   fracDegen_mean=float(np.mean(fd)) if fd else None, n_fd=len(fd),
                                   margin_mean=float(np.mean([r["mean_vote_margin"] for r in per.values()])),
                                   bstar_mean=float(np.mean(list(bs.values()))),
                                   at_ceiling=sum(v == 0.45 for v in bs.values()),
                                   collapse_b02=f"{x}/{len(col)}",
                                   wilson=[round(z, 2) for z in C.wilson(x, len(col))])
            # k = 2 at-ceiling count
            b2 = bstar_by_draw(rows(f), 2)
            t3[f"{ds}|{p}"]["k2_at_ceiling"] = f"{sum(v == 0.25 for v in b2.values())}/{len(b2)}"
    res["table3"] = t3
    rich = [json.loads(l) for l in open(os.path.join(REPO, "results/analysis/richness_instruments.jsonl"))]
    t5 = {}
    for lo, hi in ((1, 1), (1, 3), (2, 5), (3, 8), (5, 10)):
        rs = rows(f"e11b_dph{lo}_{hi}.jsonl")
        per = {}
        for r in rs:
            per.setdefault(r["partition_seed"], r)
        bs = bstar_by_draw(rs, 1)
        col = [r for r in rs if abs(r["beta"] - 0.2) < 1e-9]
        b2 = bstar_by_draw(rows(f"e22_k2rich_{lo}_{hi}.jsonl"), 2)
        nbhi = 9 if hi == 10 else hi
        nb = rows(f"e21_nbrich_{lo}_{nbhi}.jsonl")
        nbb = bstar_by_draw(nb, 1)
        fd = [z["frac_degenerate"] for z in rich if z["dataset"] == "iot23" and z["level"] == f"{lo}_{hi}"]
        fdn = [z["frac_degenerate"] for z in rich if z["dataset"] == "nbaiot" and z["level"] == f"{lo}_{nbhi}"]
        t5[f"{lo}-{hi}"] = dict(n=len(per), S_JS_median=med([r["S_JS"] for r in per.values()]),
                                fracDegen_median=med(fd), n_fd=len(fd),
                                margin_median=med([r["mean_vote_margin"] for r in per.values()]),
                                bstar_median=med(list(bs.values())),
                                collapse_b02=sum(r["CA"] <= r["tau_triv"] for r in col) / len(col),
                                k2_bstar_median=med(list(b2.values())), n_k2=len(b2),
                                nb_fracDegen_median=med(fdn), nb_bstar_median=med(list(nbb.values())),
                                nb_n=len(nbb), nb_collapse_b02=sum(r["CA"] <= r["tau_triv"] for r in nb
                                                                   if abs(r["beta"] - 0.2) < 1e-9))
    # overlap of the 1-3 level with the main grid
    s13 = {r["partition_seed"] for r in rows("e11b_dph1_3.jsonl")}
    s5f = {r["partition_seed"] for r in rows("e5f_device_derived.jsonl")}
    t5["overlap_1_3_with_main"] = len(s13 & s5f)
    res["table5"] = t5


def table11(res):
    instr = [json.loads(l) for l in open(os.path.join(REPO, "results/analysis/instruments.jsonl"))]
    stats = ["min_class_support", "frac_degenerate", "min_size_share", "S_lab", "min_minority", "S_JS", "S_dev"]
    y = np.array([r["beta_star"] / r["beta_geo"] for r in instr])
    pooled = {s: float(spearmanr([r[s] for r in instr], y).statistic) for s in stats}
    fam = [r for r in instr if r["dataset"] == "iot23" and r["family"] == "device_derived" and r["k"] == 1]
    yf = np.array([r["beta_star"] / r["beta_geo"] for r in fam])
    within = {s: float(spearmanr([r[s] for r in fam], yf).statistic) for s in stats}
    rank = sorted(stats, key=lambda s: -abs(pooled[s]))
    res["table11"] = dict(n_cells=len(instr), n_within=len(fam), pooled=pooled, within=within,
                          rank_pooled=rank, sjs_rank=rank.index("S_JS") + 1,
                          n_unique_draws=len({(r["dataset"], r["family"], r["pseed"], r["alpha"]) for r in instr}))


def ablation_pairs(res):
    """The 16-pair statistic as printed (coarse e7 grid, nearest S_JS with replacement, TOL 0.10)."""
    def cells(f):
        by = collections.defaultdict(list)
        for r in rows(f):
            if r["k"] == 1 and r["K"] == 20:
                by[(r["dirichlet_alpha"], r["partition_seed"])].append(r)
        out = []
        for (a, s), v in by.items():
            good = [x["beta"] for x in v if x["CA"] > x["tau_triv"]]
            out.append(dict(alpha=a, seed=s, S=float(np.mean([x["S_JS"] for x in v])),
                            margin=float(np.mean([x["mean_vote_margin"] for x in v])),
                            bstar=max(good) if good else 0.0))
        return out
    dev, lab = cells("e7_devskew.jsonl"), cells("e7_labelskew.jsonl")
    pairs = []
    for l in lab:
        j = min(range(len(dev)), key=lambda i: abs(dev[i]["S"] - l["S"]))
        if abs(dev[j]["S"] - l["S"]) <= 0.10:
            pairs.append(dict(dev=dev[j], lab=l))
    dm = [p["dev"]["margin"] - p["lab"]["margin"] for p in pairs]
    db = [p["dev"]["bstar"] - p["lab"]["bstar"] for p in pairs]
    res["ablation_pairs"] = dict(
        n_pairs=len(pairs), n_dev_draws_used=len({(p["dev"]["alpha"], p["dev"]["seed"]) for p in pairs}),
        n_lab_draws_used=len({(p["lab"]["alpha"], p["lab"]["seed"]) for p in pairs}),
        n_dev_cells=len(dev), n_lab_cells=len(lab),
        mean_skew_mismatch=float(np.mean([abs(p["dev"]["S"] - p["lab"]["S"]) for p in pairs])),
        margin_mean_diff=float(np.mean(dm)), bstar_mean_diff=float(np.mean(db)),
        lab_alphas=sorted({p["lab"]["alpha"] for p in pairs}),
        dev_alphas=sorted({p["dev"]["alpha"] for p in pairs}),
        pairs=[dict(dev=(p["dev"]["alpha"], p["dev"]["seed"]), lab=(p["lab"]["alpha"], p["lab"]["seed"]),
                    dS=round(p["dev"]["S"] - p["lab"]["S"], 4), dm=round(p["dev"]["margin"] - p["lab"]["margin"], 4),
                    db=round(p["dev"]["bstar"] - p["lab"]["bstar"], 4)) for p in pairs])


def coupling(res):
    """I(device; label) and per-device malicious rates, on all rows and on the training rows."""
    def mi(dev, y):
        H = lambda p: -sum(q * math.log2(q) for q in p if q > 0)
        py = np.bincount(y) / len(y)
        Hy = H(py)
        Hyd = 0.0
        for d in np.unique(dev):
            m = dev == d
            Hyd += m.mean() * H(np.bincount(y[m], minlength=2) / m.sum())
        return Hy - Hyd, Hy
    out = {}
    for ds in ("iot-23", "n-baiot"):
        tb = C.prepare_base(ds)
        cwd = os.getcwd(); os.chdir(REPO)
        cfg = C.base_cfg(ds, "iid", 0)
        b = C.DATA.load_dataset(cfg, verbose=False)
        os.chdir(cwd)
        y, dev = b["y"], b["device"]
        I_all, H_all = mi(dev, y)
        I_tr, H_tr = mi(tb["dtr"], tb["ytr_np"])
        rates = {b["device_names"][d]: float(y[dev == d].mean()) for d in np.unique(dev)}
        counts = {b["device_names"][d]: int((dev == d).sum()) for d in np.unique(dev)}
        out[ds] = dict(n_rows=int(len(y)), n_devices=int(len(np.unique(dev))),
                       I_all=I_all, H_all=H_all, frac_all=I_all / H_all,
                       I_train=I_tr, H_train=H_tr, mal_rate_overall=float(y.mean()),
                       test_mal_share=float(tb["yte_np"].mean()),
                       per_device_mal_rate=rates, per_device_rows=counts,
                       n_features=int(tb["Xtr"].shape[1]), n_train=int(len(tb["ytr_np"])),
                       n_test=int(len(tb["yte_np"])))
    res["coupling"] = out


def screen(res):
    """Coverage screen (Section 8) re-implemented from e5f rows."""
    rs = rows("e5f_*.jsonl")
    tau = rs[0]["tau_triv"]
    idx = collections.defaultdict(dict)
    for r in rs:
        idx[(r["partition_type"], r["partition_seed"], round(r["beta"], 4))][r["k"]] = r
    out = {}
    for sf in (1.0, 1.02, 1.05):
        n = unsafe = refuse_ok = refuse_bad = commit = 0
        reg, unsafe_cells = [], []
        for (p, s, b), byk in idx.items():
            n += 1
            feas = [k for k, r in byk.items() if r["combinatorially_possible"] and r["coverage"] > sf * tau]
            pick = max(feas) if feas else None
            good = {k: r["CA"] for k, r in byk.items() if r["CA"] > tau}
            orc = max(good, key=good.get) if good else None
            ca_p = byk[pick]["CA"] if pick else 0.0
            ca_o = good[orc] if orc else 0.0
            if pick is None:
                refuse_ok += orc is None; refuse_bad += orc is not None
            else:
                commit += 1
                if ca_p <= tau:
                    unsafe += 1
                    unsafe_cells.append(dict(partition=p, seed=s, beta=b, k=pick,
                                             coverage=byk[pick]["coverage"], CA=ca_p,
                                             cert_wrong=byk[pick]["cert_wrong"]))
            reg.append(ca_o - ca_p)
        out[str(sf)] = dict(n_cells=n, commitments=commit, unsafe=unsafe, refuse_correct=refuse_ok,
                            refuse_missed=refuse_bad, max_regret=max(reg), mean_regret=float(np.mean(reg)),
                            unsafe_cells=unsafe_cells)
    res["screen"] = out


def main():
    res = {}
    table1_9(res); slack30(res); fig1_table4(res); table2(res); table3_5(res); table11(res)
    ablation_pairs(res); screen(res); coupling(res)
    C.dump("p0_recompute.json", res)
    print(json.dumps({k: (v if k not in ("table1_9", "table4", "table2") else "...") for k, v in res.items()},
                     indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
