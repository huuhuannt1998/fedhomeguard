#!/usr/bin/env python3
"""PB09 (preregistered, predeclarations/tmlr_PB09_compute_cost.md): compute cost of k = 1, 2, 3
(sampled 500 / full 1,140), 5, 8 against one FedAvg run over the 20 households.

  --counts   analytic counts only (client-rounds, member trainings, parameters stored); no timing
  --timing   wall-clock: median single-process training time per member over 10 members per k
             (IID draw 0), one FedAvg run, and K-member vote latency on 33,310 flows (median of 5).
             RUN ONLY ON A QUIET MACHINE (coordinator instruction); records the load average.
Writes results/pb09_cost.json."""
import argparse, json, math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

N, T, PARAMS = 20, 15, 1586
ARMS = [(1, 20), (2, 190), (3, 500), (3, 1140), (5, 200), (8, 200)]


def counts():
    out = {"fedavg": dict(K=1, client_rounds=N * T, member_trainings=1, params_stored=PARAMS)}
    for k, K in ARMS:
        out[f"k{k}_K{K}"] = dict(K=K, full_enumeration=(K == math.comb(N, k)), client_rounds=K * k * T,
                                 x_fedavg=K * k * T / (N * T), member_trainings=K,
                                 params_stored=K * PARAMS, bytes_float32=K * PARAMS * 4,
                                 forward_passes_per_flow=K)
    return out


def timing():
    import torch
    import common as C
    from fedhomeguard import fl as FL
    tb = C.prepare_base("iot-23")
    cfg = C.base_cfg("iot-23", "iid", 0)
    t = C.with_partition(tb, cfg)
    res = dict(loadavg=os.getloadavg())
    t0 = time.perf_counter(); FL.fl_run(cfg, list(range(N)), t["Xtr"], t["ytr"], t["parts"])
    res["fedavg_secs"] = time.perf_counter() - t0
    for k, K in ARMS:
        subs, _, _ = C.build_subsets(N, k, K, 0)
        secs = []
        for S in subs[:10]:
            t0 = time.perf_counter(); FL.fl_run(cfg, list(S), t["Xtr"], t["ytr"], t["parts"])
            secs.append(time.perf_counter() - t0)
        m = float(np.median(secs))
        res[f"k{k}_K{K}"] = dict(member_secs_median=m, ensemble_secs_est=m * K)
    # vote latency: K identical-architecture members, batched over the test flows
    models = [FL.fl_run(cfg, [0], t["Xtr"], t["ytr"], t["parts"]) for _ in range(1)]
    for k, K in ARMS:
        lat = []
        for _ in range(5):
            t0 = time.perf_counter()
            with torch.no_grad():
                for _ in range(K):
                    models[0](t["Xte"]).argmax(1)
            lat.append(time.perf_counter() - t0)
        res[f"k{k}_K{K}"]["vote_secs_all_flows"] = float(np.median(lat))
        res[f"k{k}_K{K}"]["vote_us_per_flow"] = float(np.median(lat)) / len(tb["yte_np"]) * 1e6
    res["loadavg_after"] = os.getloadavg()
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts", action="store_true"); ap.add_argument("--timing", action="store_true")
    a = ap.parse_args()
    import common as C
    out = dict(counts=counts())
    if a.timing:
        out["timing"] = timing()
    else:
        out["timing"] = "BLOCKED until the coordinator reports a quiet machine"
    C.dump("pb09_cost.json", out)
    print(json.dumps(out, indent=1))
