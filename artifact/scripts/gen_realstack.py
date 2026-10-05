#!/usr/bin/env python3
"""Analyse the real-stack arm: cross-validation against the simulation, and what an
L1 server can actually observe about a compromised household.

Two questions, kept separate. (1) Does delivering the attack over a real federated
stack reproduce the simulation? If not, the sweeps the paper rests on are suspect.
(2) Would a server that sees individual updates notice? That is the observability
lattice of Section IX, measured rather than assumed.
"""
from __future__ import annotations
import collections, glob, json, os, statistics as st

RS = "results/realstack"
ATTACKS = ["none", "label_flip", "sign_flip", "gaussian", "ipm", "alie"]


def load():
    sim = {(r["partition"], r["attack"], r["m"]): r["accuracy"]
           for r in json.load(open(f"{RS}/sim_counterpart.json"))}
    real, contrib = {}, {}
    for f in sorted(glob.glob(f"{RS}/*.json")):
        b = os.path.basename(f)[:-5]
        if b == "sim_counterpart":
            continue
        d = json.load(open(f))
        part = "device_derived" if b.startswith("device_derived") else "iid"
        rest = b[len(part) + 1:]
        attack, m = rest.rsplit("_m", 1)
        key = (part, attack, int(m))
        accs = d.get("accuracy_by_round") or {}
        real[key] = accs.get(str(d["rounds"])) or (max(accs.values()) if accs else None)
        contrib[key] = d["contributions"]
    return sim, real, contrib


def main() -> None:
    sim, real, contrib = load()
    keys = sorted(set(real) & set(sim))

    print("=" * 74)
    print("CROSS-VALIDATION: real federated stack vs single-process simulation")
    print("=" * 74)
    print(f"{'partition':15s} {'attack':11s} {'m':>2s} {'real':>8s} {'sim':>8s} {'delta':>8s}")
    deltas = []
    for k in keys:
        d = real[k] - sim[k]
        deltas.append(abs(d))
        print(f"{k[0]:15s} {k[1]:11s} {k[2]:>2d} {real[k]:8.4f} {sim[k]:8.4f} {d:+8.4f}")
    print(f"\n  n={len(deltas)}  mean |delta| {st.mean(deltas):.4f}  "
          f"median {st.median(deltas):.4f}  max {max(deltas):.4f}")
    within = sum(1 for d in deltas if d <= 0.01)
    print(f"  within 0.01: {within}/{len(deltas)}   within 0.03: "
          f"{sum(1 for d in deltas if d <= 0.03)}/{len(deltas)}")

    print()
    print("=" * 74)
    print("PROTOCOL CONFORMANCE (every contribution, both partitions)")
    print("=" * 74)
    allc = [r for v in contrib.values() for r in v]
    print(f"  contributions           : {len(allc)}")
    print(f"  shapes match the model  : {set(r['shapes_ok'] for r in allc)}")
    print(f"  all values finite       : {set(r['finite'] for r in allc)}")
    print(f"  dtypes                  : {set(tuple(r['dtypes']) for r in allc)}")
    print(f"  distinct message sizes  : {sorted(set(r['bytes'] for r in allc))} bytes")

    print()
    print("=" * 74)
    print("L1 DETECTABILITY: is a compromised household separable by update norm?")
    print("=" * 74)
    print(f"{'partition':15s} {'attack':11s} {'m':>2s} {'honest l2 range':>22s} "
          f"{'malicious l2 range':>22s}  {'separable':>9s}")
    sep = collections.Counter()
    for k in sorted(contrib):
        if k[1] == "none":
            continue
        rows = [r for r in contrib[k] if r["round"] == 15]
        h = [r["update_l2"] for r in rows if not r["malicious"]]
        m_ = [r["update_l2"] for r in rows if r["malicious"]]
        if not h or not m_:
            continue
        ok = min(m_) > max(h) or max(m_) < min(h)
        sep[(k[0], ok)] += 1
        print(f"{k[0]:15s} {k[1]:11s} {k[2]:>2d} "
              f"{min(h):10.4f}..{max(h):<10.4f} {min(m_):10.4f}..{max(m_):<10.4f}  "
              f"{'YES' if ok else 'no':>9s}")
    print()
    for part in ("iid", "device_derived"):
        y, n = sep[(part, True)], sep[(part, False)]
        if y + n:
            print(f"  {part:15s} separable by norm alone in {y}/{y+n} attacked cells")


if __name__ == "__main__":
    main()
