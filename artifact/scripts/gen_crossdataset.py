#!/usr/bin/env python3
"""Cross-dataset natural experiment (N-BaIoT) and the S_JS instrument audit.

Emits the matched-contrast table, the instrument-ranking table, and the macros the
prose in Section~\\ref{sec:skew} and Section~\\ref{sec:discussion} reads. Nothing here
is hand-maintained: every value is computed from results/canonical and
results/analysis.
"""
import collections, json, glob, math, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, "src")
import numpy as np

OUT = os.environ.get("FHG_GENERATED",
                     "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated")
BETA_GEO = {1: 0.450, 2: 0.250, 3: 0.150, 5: 0.100, 8: 0.050}


def cert_cells(pattern):
    """(partition, k, seed) -> (beta*, mean margin, S_JS, tau, collapsed at 0.20)."""
    cell, meta, tau = collections.defaultdict(dict), collections.defaultdict(list), {}
    for f in glob.glob(pattern):
        for line in open(f):
            if not line.startswith("{"):
                continue
            r = json.loads(line)
            key = (r["partition_type"], int(r["k"]), int(r["partition_seed"]))
            b, ca = round(float(r["beta"]), 4), float(r["CA"])
            cell[key][b] = min(cell[key].get(b, ca), ca)
            meta[key].append(r); tau[key] = float(r["tau_triv"])
    out = {}
    for key, d in cell.items():
        ok = [b for b, ca in d.items() if ca > tau[key] + 1e-9]
        out[key] = dict(bstar=max(ok) if ok else 0.0,
                        margin=float(np.mean([x["mean_vote_margin"] for x in meta[key]])),
                        S_JS=float(meta[key][0]["S_JS"]), tau=tau[key],
                        collapse20=(0.0 if d.get(0.20, -1) > tau[key] + 1e-9 else 1.0))
    return out


def wilson(k_, n_, z=1.96):
    """Wilson score interval, clamped to [0,1]. Sec. V promises one for every
    collapse figure; the cross-dataset arm was the one place that omitted it."""
    if n_ == 0:
        return (0.0, 1.0)
    p = k_ / n_
    d = 1 + z * z / n_
    c = p + z * z / (2 * n_)
    m_ = z * ((p * (1 - p) + z * z / (4 * n_)) / n_) ** 0.5
    return (max(0.0, (c - m_) / d), min(1.0, (c + m_) / d))


def agg(cells, part, k):
    v = [c for key, c in cells.items() if key[0] == part and key[1] == k]
    if not v:
        return None
    return dict(n=len(v), bstar=float(np.mean([x["bstar"] for x in v])),
                margin=float(np.mean([x["margin"] for x in v])),
                S_JS=float(np.mean([x["S_JS"] for x in v])),
                collapse20=float(np.mean([x["collapse20"] for x in v])),
                tau=v[0]["tau"],
                at_ceiling=sum(1 for x in v if abs(x["bstar"] - BETA_GEO[k]) < 1e-9),
                coll_ci=wilson(sum(1 for x in v if x["collapse20"] > 0.5), len(v)))


def mutual_information():
    """I(label; device) on both datasets, in bits, with the label entropy."""
    from fedhomeguard import data as D
    out = {}
    for name, loader in (("iot23", D.load_iot23), ("nbaiot", D.load_nbaiot)):
        df = loader(verbose=False)
        # Both loaders emit an Arrow-backed string column, so a dtype==object test
        # silently falls through to a numeric branch that casts every non-empty
        # string to True and drives the label entropy to zero.
        y = (df["label"].astype(str) == "malicious").to_numpy()
        dev = df["device"].to_numpy()
        p = float(y.mean()); h = -sum(q * math.log2(q) for q in (p, 1 - p) if q > 0)
        mi = 0.0
        for dv in np.unique(dev):
            m = dev == dv; pdv = m.mean()
            for lv in (True, False):
                pj = ((y == lv) & m).mean()
                if pj > 0:
                    mi += pj * math.log2(pj / (pdv * (y == lv).mean()))
        rates = [float(y[dev == dv].mean()) for dv in np.unique(dev)]
        out[name] = dict(mi=mi, h=h, pct=100 * mi / h, lo=min(rates), hi=max(rates),
                         ndev=len(np.unique(dev)), nrows=len(df),
                         tau=float(max(p, 1 - p)))
    return out


def spearman(a, b):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); rk = [0.0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for t in range(i, j + 1):
                rk[o[t]] = (i + j) / 2.0
            i = j + 1
        return rk
    ra, rb = rank(a), rank(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")


LABELS = {"S_JS": "$S_{\\mathrm{JS}}$", "S_dev": "$S_{\\mathrm{dev}}$",
          "S_lab": "$S_{\\mathrm{lab}}$", "min_minority": "$\\mathrm{minMinority}$",
          "frac_degenerate": "$\\mathrm{fracDegen}$",
          "min_class_support": "$\\mathrm{minClassSup}$",
          "min_size_share": "$\\mathrm{minSizeShare}$"}


def main():
    nb = cert_cells("results/canonical/nb9_cert_*.jsonl")
    io = cert_cells("results/canonical/e5f_*.jsonl")
    if not nb or not io:
        print("cross-dataset incomplete"); return
    mi = mutual_information()

    m, idx = {}, {}
    for k in (1, 2):
        for tag, cells, part in (("NbDev", nb, "device_derived"), ("NbIid", nb, "iid"),
                                 ("IoDev", io, "device_derived"), ("IoIid", io, "iid")):
            a = agg(cells, part, k)
            if not a:
                continue
            # k-indexed values go in `idx`, not `m`: a LaTeX control sequence
            # cannot contain a digit, so \newcommand{\xdNbDevSJS1} is invalid.
            # These are stored under \csname keys and reached through a
            # one-argument wrapper, matching gen_paper_numbers.py.
            idx[(f"xd{tag}SJS", k)] = f"{a['S_JS']:.4f}"
            idx[(f"xd{tag}Margin", k)] = f"{a['margin']:.4f}"
            idx[(f"xd{tag}Bstar", k)] = f"{a['bstar']:.3f}"
            idx[(f"xd{tag}Coll", k)] = f"{a['collapse20']:.2f}"
            idx[(f"xd{tag}N", k)] = str(a["n"])
            idx[(f"xd{tag}Ceil", k)] = f"{a['at_ceiling']}/{a['n']}"
    for nm, key in (("Nb", "nbaiot"), ("Io", "iot23")):
        d = mi[key]
        m[f"xd{nm}MI"] = f"{d['mi']:.4f}"
        m[f"xd{nm}MIpct"] = f"{d['pct']:.1f}"
        m[f"xd{nm}Hlab"] = f"{d['h']:.4f}"
        m[f"xd{nm}RateLo"] = f"{d['lo']:.3f}"
        m[f"xd{nm}RateHi"] = f"{d['hi']:.3f}"
        m[f"xd{nm}Ndev"] = str(d["ndev"])
        m[f"xd{nm}Rows"] = f"{d['nrows']:,}".replace(",", "{,}")
        m[f"xd{nm}Tau"] = f"{d['tau']:.4f}"
    d1, d2 = agg(nb, "device_derived", 1), agg(io, "device_derived", 1)
    m["xdSJSGap"] = f"{abs(d1['S_JS'] - d2['S_JS']):.4f}"
    m["xdBstarRatio"] = f"{d1['bstar'] / d2['bstar']:.0f}" if d2["bstar"] else "--"

    # ---- matched-contrast table ----------------------------------------------
    # review D1 (F-09): mean share of nearly one-class clients over the same draws, read
    # from the instrument audit (which rebuilt these partitions; seeds as in the rows).
    _audit = [json.loads(l) for l in open("results/analysis/instruments.jsonl")]
    def _fd(ds_, part_):
        v = [r["frac_degenerate"] for r in _audit if r["dataset"] == ds_
             and r["family"] == part_ and r["k"] == 1]
        return float(np.mean(v)) if v else float("nan")
    rows = ["% GENERATED -- do not edit", "\\begin{tabular}{llcccccc}", "\\toprule",
            "Dataset & Partition & $n$ & $S_{\\mathrm{JS}}$ & $\\mathrm{fracDegen}$ & margin & "
            "$\\beta^{*}$ & collapse (95\\% CI) \\\\", "\\midrule"]
    for ds, cells in (("IoT-23", io), ("N-BaIoT", nb)):
        for part, nm in (("iid", "IID"), ("device_derived", "device-derived")):
            a = agg(cells, part, 1)
            if a:
                lo, hi = a["coll_ci"]
                rows.append(f"{ds} & {nm} & {a['n']} & {a['S_JS']:.4f} & "
                            f"{_fd('iot23' if ds == 'IoT-23' else 'nbaiot', part):.3f} & {a['margin']:.4f} & "
                            f"{a['bstar']:.3f} & {a['collapse20']:.2f} "
                            f"[{lo:.2f}, {hi:.2f}] \\\\")
        rows.append("\\midrule")
    rows = rows[:-1] + ["\\bottomrule", "\\end{tabular}"]
    open(os.path.join(OUT, "tab_crossdataset.tex"), "w").write("\n".join(rows) + "\n")

    # ---- instrument ranking table --------------------------------------------
    ipath = "results/analysis/instruments.jsonl"
    if os.path.exists(ipath):
        recs = [json.loads(l) for l in open(ipath)]
        for r in recs:
            r["cf"] = r["beta_star"] / r["beta_geo"] if r.get("beta_geo") else None
        us = [r for r in recs if r["cf"] is not None]
        y = [r["cf"] for r in us]
        dev1 = [r for r in us if r["dataset"] == "iot23"
                and r["family"] == "device_derived" and r["k"] == 1]
        y1 = [r["cf"] for r in dev1]
        ranked = []
        for s in LABELS:
            if any(r.get(s) is None for r in us):
                continue
            rho = spearman([r[s] for r in us], y)
            rw = (spearman([r[s] for r in dev1], y1)
                  if len(set(r[s] for r in dev1)) > 1 else float("nan"))
            ranked.append((abs(rho), rho, rw, s))
        ranked.sort(reverse=True)
        tr = ["% GENERATED -- do not edit", "\\begin{tabular}{lcc}", "\\toprule",
              "Instrument & pooled $\\rho$ & within-family $\\rho$ \\\\",
              "\\midrule"]
        for _, rho, rw, s in ranked:
            w = "--" if rw != rw else f"{rw:+.3f}"
            tr.append(f"{LABELS[s]} & {rho:+.3f} & {w} \\\\")
        tr += ["\\bottomrule", "\\end{tabular}"]
        open(os.path.join(OUT, "tab_instruments.tex"), "w").write("\n".join(tr) + "\n")
        m["xdNinstCells"] = str(len(us))
        m["xdSJSrho"] = f"{[r for r in ranked if r[3]=='S_JS'][0][1]:+.3f}"
        m["xdMCSrho"] = f"{[r for r in ranked if r[3]=='min_class_support'][0][1]:+.3f}"
        m["xdSJSrhoW"] = f"{[r for r in ranked if r[3]=='S_JS'][0][2]:+.3f}"
        m["xdMCSrhoW"] = f"{[r for r in ranked if r[3]=='min_class_support'][0][2]:+.3f}"
        m["xdSJSrank"] = str([i for i, r in enumerate(ranked, 1) if r[3] == "S_JS"][0])
        # the instrument S_JS now sits beside (review r6 item 13), printed so the rank
        # can be read against it rather than taken on trust
        m["xdSdevrho"] = f"{[r for r in ranked if r[3]=='S_dev'][0][1]:+.3f}"
        m["xdNinst"] = str(len(ranked))

    mac = ["% GENERATED -- do not edit"] + \
          [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(m.items())]
    # k-indexed values: \csname storage plus a wrapper, since a control sequence
    # name cannot contain a digit.
    for (base, kk), vv in sorted(idx.items()):
        mac.append("\\expandafter\\newcommand\\csname %sk%d\\endcsname{%s}" % (base, kk, vv))
    for base in sorted({b for b, _ in idx}):
        mac.append("\\newcommand{\\%s}[1]{\\ifcsname %sk#1\\endcsname"
                   "\\csname %sk#1\\endcsname\\else\\textbf{??}\\fi}"
                   % (base, base, base))
    open(os.path.join(OUT, "crossdataset_macros.tex"), "w").write("\n".join(mac) + "\n")
    print(f"wrote tab_crossdataset.tex, tab_instruments.tex, crossdataset_macros.tex "
          f"({len(m)} macros)")
    print(f"  matched contrast: IoT-23 S_JS={idx[('xdIoDevSJS', 1)]} "
          f"beta*={idx[('xdIoDevBstar', 1)]} | N-BaIoT S_JS={idx[('xdNbDevSJS', 1)]} "
          f"beta*={idx[('xdNbDevBstar', 1)]} (gap {m['xdSJSGap']})")


if __name__ == "__main__":
    main()
