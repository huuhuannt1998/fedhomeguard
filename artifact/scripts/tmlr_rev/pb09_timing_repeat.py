#!/usr/bin/env python3
"""PB09 wall-clock timings, repeated (coordinator, 2026-10-10: at least 3 repeats, median and range, mark approximate
if the variation exceeds 10%). Each repeat is one full pass of pb09_cost.timing() (protocol fixed in
predeclarations/tmlr_PB09_compute_cost.md: one FedAvg run; median single-process training time per member over 10
members per k on IID draw 0, times K; K-member vote latency on the 33,310 test flows, median of 5), on one core
(common.py sets torch.set_num_threads(1), as the paper's runs did).

The load average and the busiest background processes (and docker containers, if the CLI answers) are recorded
before and after the whole run and with every repeat.

  python3 pb09_timing_repeat.py --repeats 5
Writes results/pb09_timing.json and merges the summary into results/pb09_cost.json ("timing")."""
import argparse, json, os, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C          # noqa: E402  (sets torch threads to 1)
import pb09_cost as P       # noqa: E402


def background():
    snap = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S%z"), loadavg=os.getloadavg())
    try:
        ps = subprocess.run(["ps", "-Ao", "pcpu,comm", "-r"], capture_output=True, text=True, timeout=20).stdout
        rows = []
        for line in ps.splitlines()[1:9]:
            pc, _, comm = line.strip().partition(" ")
            rows.append([float(pc), os.path.basename(comm.strip())[:60]])
        snap["top_processes_pcpu"] = rows
    except Exception as e:  # noqa: BLE001
        snap["top_processes_pcpu"] = f"unavailable: {e}"
    try:
        ds = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}} {{.MemUsage}}"],
                            capture_output=True, text=True, timeout=30)
        snap["docker"] = ds.stdout.strip().splitlines() if ds.returncode == 0 else f"unavailable: {ds.stderr.strip()[:200]}"
    except Exception as e:  # noqa: BLE001
        snap["docker"] = f"unavailable: {e}"
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=5)
    a = ap.parse_args()
    out = dict(protocol="predeclarations/tmlr_PB09_compute_cost.md; repeated per coordinator 2026-10-10",
               threads=1, before=background(), repeats=[])
    for i in range(a.repeats):
        t0 = time.time()
        r = P.timing()
        r["repeat"] = i + 1
        r["wall_secs"] = round(time.time() - t0, 1)
        r["background_after"] = background()
        out["repeats"].append(r)
        print(f"repeat {i + 1}: fedavg {r['fedavg_secs']:.2f}s, loadavg {r['loadavg']} -> {r['loadavg_after']}", flush=True)
    out["after"] = background()
    # summary: median and range over repeats; approximate if (max - min) / median > 10%
    keys = [("fedavg_secs", None)] + [(f"k{k}_K{K}", f) for k, K in P.ARMS
                                       for f in ("member_secs_median", "ensemble_secs_est", "vote_secs_all_flows",
                                                 "vote_us_per_flow")]
    summ = {}
    for arm, f in keys:
        vals = [r[arm] if f is None else r[arm][f] for r in out["repeats"]]
        med = float(np.median(vals))
        spread = (max(vals) - min(vals)) / med if med else 0.0
        summ[arm if f is None else f"{arm}.{f}"] = dict(median=med, min=float(min(vals)), max=float(max(vals)),
                                                        rel_range=spread, approximate=bool(spread > 0.10),
                                                        n=len(vals))
    out["summary"] = summ
    C.dump("pb09_timing.json", out)
    cost = json.load(open(os.path.join(C.OUTDIR, "pb09_cost.json")))
    cost["timing"] = dict(source="pb09_timing.json", repeats=a.repeats, summary=summ,
                          loadavg_before=out["before"]["loadavg"], loadavg_after=out["after"]["loadavg"])
    C.dump("pb09_cost.json", cost)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
