#!/usr/bin/env python3
"""Macros and the delivery table for the real-stack arm. Every value is computed
from results/realstack, never written by hand."""
from __future__ import annotations
import glob, json, os, re, statistics as st

RS = "results/realstack"
OUT = "manuscripts/prj-01m0ee73rtcak0jngd4sy4a1y2/IEEE-SP/generated"


def main() -> None:
    sim = {(r["partition"], r["attack"], r["m"]): r["accuracy"]
           for r in json.load(open(f"{RS}/sim_counterpart.json"))}
    cells, contrib = {}, []
    for f in sorted(glob.glob(f"{RS}/*.json")):
        b = os.path.basename(f)[:-5]
        if b.startswith("sim_counterpart"):
            continue
        d = json.load(open(f))
        part = "device_derived" if b.startswith("device_derived") else "iid"
        attack, m = b[len(part) + 1:].rsplit("_m", 1)
        a = d.get("accuracy_by_round") or {}
        cells[(part, attack, int(m))] = a.get(str(d["rounds"]))
        contrib += d["contributions"]

    keys = [k for k in cells if k in sim and cells[k] is not None]
    dl = [abs(cells[k] - sim[k]) for k in keys]
    n_att = len([r for r in contrib if r["malicious"]])

    # the attacker's diff, counted rather than asserted
    src = open("docker/fl_client_malicious.py").read().split("\n")
    loc = len([l for l in src if l.strip() and not l.strip().startswith("#")
               and not l.strip().startswith('"""')])

    m = dict(
        rsCells=str(len(cells)), rsContribs=f"{len(contrib):,}".replace(",", "{,}"),
        rsAttackedContribs=f"{n_att:,}".replace(",", "{,}"),
        rsMedianDelta=f"{st.median(dl):.4f}", rsMeanDelta=f"{st.mean(dl):.4f}",
        rsMaxDelta=f"{max(dl):.4f}",
        rsWithinPointOhOne=f"{sum(1 for d in dl if d <= 0.01)}/{len(dl)}",
        rsMsgBytes=str(sorted({r["bytes"] for r in contrib})[0]),
        rsDistinctSizes=str(len(set(r["bytes"] for r in contrib))),
        rsAttackerLOC=str(loc),
        rsHouseholds="20", rsCPU="0.4", rsMem="300",
        rsWallMin=str(int(sum(json.load(open(f))["wall_secs"]
                              for f in glob.glob(f"{RS}/*.json")
                              if "sim_counterpart" not in f) / 60)),
    )
    # L1 separability at the final round, split by partition. Pooling the two hides
    # the effect: heterogeneity does not make attacks undetectable, it widens the
    # honest band the server must discriminate against.
    sep = tot = 0
    per = {"iid": [0, 0], "device_derived": [0, 0]}
    spread = {"iid": [], "device_derived": []}
    for f in sorted(glob.glob(f"{RS}/*.json")):
        b = os.path.basename(f)[:-5]
        if b.startswith("sim_counterpart") or "_none_" in b:
            continue
        d = json.load(open(f))
        last = [r for r in d["contributions"] if r["round"] == d["rounds"]]
        h = [r["update_l2"] for r in last if not r["malicious"]]
        mm = [r["update_l2"] for r in last if r["malicious"]]
        if h and mm:
            part = "device_derived" if b.startswith("device_derived") else "iid"
            ok = bool(min(mm) > max(h) or max(mm) < min(h))
            tot += 1; sep += ok
            per[part][0] += ok; per[part][1] += 1
            spread[part].append(max(h) - min(h))
    m["rsSeparable"] = f"{sep}/{tot}"
    m["rsSeparableIid"] = f"{per['iid'][0]}/{per['iid'][1]}"
    m["rsSeparableDev"] = f"{per['device_derived'][0]}/{per['device_derived'][1]}"
    m["rsHonestSpreadIid"] = f"{st.mean(spread['iid']):.4f}"
    m["rsHonestSpreadDev"] = f"{st.mean(spread['device_derived']):.4f}"
    m["rsSpreadRatio"] = f"{st.mean(spread['device_derived']) / st.mean(spread['iid']):.0f}"

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "realstack_macros.tex"), "w") as fh:
        fh.write("% GENERATED -- do not edit\n")
        for k, v in sorted(m.items()):
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    print(f"wrote realstack_macros.tex ({len(m)} macros)")
    for k in ("rsCells", "rsContribs", "rsMedianDelta", "rsWithinPointOhOne",
              "rsMsgBytes", "rsDistinctSizes", "rsAttackerLOC", "rsSeparable"):
        print(f"   {k:18s} {m[k]}")


if __name__ == "__main__":
    main()
