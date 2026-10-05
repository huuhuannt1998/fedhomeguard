#!/usr/bin/env python3
"""Backfill c_max_mode into rows written before the field existed.

The value is deterministic, not a guess: c_max_bounded enumerates every B when
C(N,m) <= 200,000 and falls back to the degree-sum upper bound otherwise. Every
pre-existing row has N=20, where the largest m is 8 and C(20,8)=125,970, so all of
them took the exact path. Rows that already carry the field are left untouched.
"""
import glob, json, math, os, sys

CAP = 200_000


def main():
    touched = total = 0
    for p in sorted(glob.glob("results/canonical/*.jsonl")):
        out, changed = [], 0
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            total += 1
            if "c_max_mode" not in r and "c_max" in r:
                N, m = r["N"], r["m"]
                mode = ("exact" if m <= 0 or m >= N or math.comb(N, m) <= CAP
                        else "degree_upper_bound")
                # order the key next to c_max so the file stays readable
                r = {k: v for k, v in r.items()}
                r["c_max_mode"] = mode
                changed += 1
            out.append(json.dumps(r))
        if changed:
            open(p, "w").write("\n".join(out) + "\n")
            touched += changed
            print(f"  {os.path.basename(p):38s} +{changed}")
    print(f"backfilled {touched} of {total} rows")


if __name__ == "__main__":
    sys.exit(main())
