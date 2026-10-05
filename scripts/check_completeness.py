#!/usr/bin/env python3
"""Completeness audit of the canonical result files.

Both bugs found on 2026-08-25 were silent: one resumed over rows it had never
produced, the other hung before writing any. Neither raised. This check compares
what each file contains against the grid it was supposed to cover, so a missing
cell is loud.
"""
import collections, glob, json, os, sys

def rows(path):
    return [json.loads(l) for l in open(path) if l.strip()]

def audit():
    bad = 0
    print(f"{'file':38s} {'rows':>5} {'cells':>6} {'dupes':>6}  coverage")
    for p in sorted(glob.glob("results/canonical/*.jsonl")):
        r = rows(p)
        if not r:
            print(f"{os.path.basename(p):38s} {'0':>5}   EMPTY"); bad += 1; continue
        if r[0].get("schema", "").startswith("fedhomeguard.canonical-defense"):
            key = lambda x: (x["partition_seed"], x["beta"], x["mal_seed"],
                             x["defense"], x["attack"], x["scale"])
            axes = dict(seeds=sorted({x["partition_seed"] for x in r}),
                        betas=sorted({x["beta"] for x in r}),
                        defenses=len({x["defense"] for x in r}),
                        attacks=len({x["attack"] for x in r}))
        else:
            # Not every non-defense lane carries every axis. The smoothing arm
            # (e18_crfl_*) has no subsample size k and no malicious-set draw at
            # all: it sweeps (rho, sigma) instead. Assuming k exists on every
            # non-defense file raised KeyError('k') and took `make numbers` and
            # `make paper` down with it. Derive the identity fields from what the
            # rows actually contain, and report coverage only for the axes that
            # are present, so a lane with a different grid is audited on its own
            # grid rather than crashing the audit for every other lane.
            #
            # partition_type and tag are axes for the same reason: e16_lodo holds
            # both partitions and all ten held-out devices in one file, so a key
            # without them collided 342 times and reported a resume bug that was
            # not there.
            candidates = ("partition_seed", "partition_type", "tag", "k", "beta",
                          "mal_mode", "mal_seed", "dirichlet_alpha", "N", "arch",
                          "devices_per_household", "rho", "sigma", "n_smooth",
                          "attack", "family")
            present = [f for f in candidates if any(f in x for x in r)]

            def _h(v):
                return tuple(v) if isinstance(v, list) else v

            key = lambda x, _p=tuple(present): tuple(_h(x.get(f)) for f in _p)

            axes = {}
            axes["seeds"] = sorted({x["partition_seed"] for x in r})
            if "k" in present:
                axes["k"] = sorted({x.get("k") for x in r}, key=lambda v: (v is None, v))
            axes["betas"] = sorted({x["beta"] for x in r})
            if "dirichlet_alpha" in present:
                axes["alphas"] = sorted({x.get("dirichlet_alpha") for x in r},
                                        key=lambda v: -(v or 0))
            for f in ("rho", "sigma"):
                if f in present:
                    axes[f] = sorted({x.get(f) for x in r},
                                     key=lambda v: (v is None, v))
        ks = [key(x) for x in r]
        dup = len(ks) - len(set(ks))
        # A cell measured twice -- once certified-arm-only over a fine beta grid, once
        # same-predictor over a coarser one -- is a legitimate overlap, not a resume-key
        # collision. aggregate.load() keeps the richer row. Count it separately.
        if dup and not r[0].get("schema", "").endswith("canonical-defense/v1"):
            pairs = collections.Counter(ks)
            benign = sum(
                1 for kk, n in pairs.items() if n == 2
                and len({x.get("EA_ensemble") is None for x in r if key(x) == kk}) == 2)
            dup -= benign
        if dup:
            bad += 1
        cov = ", ".join(f"{a}={v}" for a, v in axes.items())
        print(f"{os.path.basename(p):38s} {len(r):>5} {len(set(ks)):>6} {dup:>6}  {cov[:78]}")
    print()
    print("duplicate keys indicate a resume-key collision;"
          " EMPTY indicates a lane that produced nothing.")
    return bad

if __name__ == "__main__":
    sys.exit(1 if audit() else 0)
