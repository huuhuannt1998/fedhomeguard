#!/usr/bin/env python3
"""Dataset and result manifest with checksums (review sec 48).

  python scripts/manifest.py            write results/MANIFEST.json
  python scripts/manifest.py --verify   re-hash and report drift

Covers the raw dataset files and every canonical result file, so an evaluator can
tell whether a rebuilt artifact used the same inputs we did.
"""
import argparse, glob, hashlib, json, os, sys

OUT = "results/MANIFEST.json"


def sha256(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def collect():
    files = sorted(glob.glob("data/raw/**/*", recursive=True)) + \
            sorted(glob.glob("results/canonical/*.json*"))
    out = {}
    for p in files:
        if os.path.isfile(p):
            out[p] = dict(sha256=sha256(p), bytes=os.path.getsize(p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    cur = collect()
    if not a.verify:
        os.makedirs("results", exist_ok=True)
        json.dump(dict(schema="fedhomeguard.manifest/v1", files=cur),
                  open(OUT, "w"), indent=1)
        print(f"wrote {OUT}: {len(cur)} files")
        return 0
    if not os.path.exists(OUT):
        print(f"no {OUT}; run without --verify first"); return 1
    old = json.load(open(OUT))["files"]
    missing = [p for p in old if p not in cur]
    added = [p for p in cur if p not in old]
    changed = [p for p in cur if p in old and cur[p]["sha256"] != old[p]["sha256"]]
    for tag, lst in (("MISSING", missing), ("CHANGED", changed), ("added", added)):
        for p in lst:
            print(f"  {tag:8s} {p}")
    bad = bool(missing or changed)
    print(f"manifest: {len(cur)} files, {len(missing)} missing, {len(changed)} changed, "
          f"{len(added)} added -> {'DRIFT' if bad else 'OK'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
