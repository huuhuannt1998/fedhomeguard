#!/usr/bin/env python3
"""Resilient N-BaIoT fetcher.

UCI streams this archive without Content-Length or range support, so a dropped
connection cannot be resumed and `zipfile` refuses the result: the central directory
lives at the END of a zip, and a truncated file has none.

But the entries themselves are stored front-to-back, each behind its own local file
header, so every entry that finished transferring is intact and recoverable. And
successive attempts truncate at different byte offsets. So: download repeatedly,
salvage whatever entries are complete in each attempt by walking the local headers
directly, and union them across attempts until the expected inventory is present.

  python scripts/fetch_nbaiot_robust.py --attempts 12
"""
from __future__ import annotations
import argparse, os, struct, subprocess, sys, zlib

URL = ("https://archive.ics.uci.edu/static/public/442/"
       "detection+of+iot+botnet+attacks+n+baiot.zip")
ROOT = "data/raw/nbaiot"
SIG_LOCAL = b"PK\x03\x04"


def salvage(zip_path: str, dest: str) -> tuple[int, int]:
    """Walk local file headers and write out every entry that is complete.

    Returns (recovered, already_present). Never raises on truncation: it stops at
    the first entry whose data runs past the end of the file.
    """
    data = open(zip_path, "rb").read()
    pos, new, have = 0, 0, 0
    while True:
        i = data.find(SIG_LOCAL, pos)
        if i < 0:
            break
        try:
            (_, _, flags, method, _, _, crc, csize, usize,
             nlen, elen) = struct.unpack("<IHHHHHIIIHH", data[i:i + 30])
        except struct.error:
            break
        start = i + 30 + nlen + elen
        name = data[i + 30:i + 30 + nlen].decode("utf-8", "replace")
        if csize == 0 and (flags & 0x08):
            pos = i + 4               # size in a trailing descriptor; skip this entry
            continue
        end = start + csize
        if end > len(data):
            break                     # this entry did not finish transferring
        if name.endswith("/") or not name:
            pos = end
            continue
        out = os.path.join(dest, name)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            have += 1
            pos = end
            continue
        blob = data[start:end]
        try:
            raw = zlib.decompress(blob, -15) if method == 8 else blob
            if crc and zlib.crc32(raw) & 0xFFFFFFFF != crc:
                pos = end
                continue              # corrupt entry, skip rather than write garbage
        except zlib.error:
            pos = end
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(raw)
        new += 1
        pos = end
    return new, have


def unpack_rars(root: str) -> int:
    """The attack partitions ship as nested .rar archives inside the zip, which is why
    a plain unzip yields only the benign CSVs. 7z lists them but cannot decode this RAR
    variant; unar can. Only fully-transferred archives are unpacked, checked by
    comparing each extracted file against the size the archive header declares."""
    import shutil
    n = 0
    for dirpath, _, fnames in os.walk(root):
        for fn in fnames:
            if not fn.endswith(".rar"):
                continue
            rar = os.path.join(dirpath, fn)
            dest = os.path.join(dirpath, fn[:-4])
            if os.path.isdir(dest) and any(
                    x.endswith(".csv") and os.path.getsize(os.path.join(dest, x)) > 0
                    for x in os.listdir(dest)):
                continue
            os.makedirs(dest, exist_ok=True)
            subprocess.run(["unar", "-q", "-f", "-o", dest, rar],
                           check=False, capture_output=True)
            # unar nests a directory named after the archive; flatten it
            inner = os.path.join(dest, fn[:-4])
            if os.path.isdir(inner):
                for x in os.listdir(inner):
                    shutil.move(os.path.join(inner, x), os.path.join(dest, x))
                os.rmdir(inner)
            got = [x for x in os.listdir(dest) if x.endswith(".csv")
                   and os.path.getsize(os.path.join(dest, x)) > 0]
            if got:
                n += 1
            else:
                shutil.rmtree(dest, ignore_errors=True)
    return n


def inventory(root: str) -> dict:
    devs = sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)))
    out = {}
    for d in devs:
        files = []
        for dirpath, _, fnames in os.walk(os.path.join(root, d)):
            for fn in fnames:
                if fn.endswith(".csv"):
                    files.append(os.path.relpath(os.path.join(dirpath, fn),
                                                 os.path.join(root, d)))
        out[d] = sorted(files)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempts", type=int, default=12)
    a = ap.parse_args()
    os.makedirs(ROOT, exist_ok=True)
    tmp = os.path.join(ROOT, "_partial.zip")
    total_new = 0
    for i in range(1, a.attempts + 1):
        subprocess.run(
            ["curl", "-sL", "--speed-limit", "20000", "--speed-time", "120",
             "--max-time", "5400", "-o", tmp, URL], check=False)
        size = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        new, have = salvage(tmp, ROOT)
        total_new += new
        unpacked = unpack_rars(ROOT)
        inv = inventory(ROOT)
        n = sum(len(v) for v in inv.values())
        rars = sum(1 for dp, _, fs in os.walk(ROOT) for f in fs if f.endswith(".rar"))
        print(f"  attempt {i:2d}: {size/1e6:7.1f} MB -> +{new} salvaged, "
              f"{rars} rars held, {unpacked} unpacked; {n} CSVs / {len(inv)} devices",
              flush=True)
        if n >= 89:
            print("  full inventory recovered"); break
        if new == 0 and i >= 6:
            print("  no further progress from this endpoint")
            break
    if os.path.exists(tmp):
        os.remove(tmp)
    inv = inventory(ROOT)
    print(f"\nrecovered {total_new} new files this run")
    for d, files in inv.items():
        kinds = sorted({f.split("/")[0] if "/" in f else "benign" for f in files})
        print(f"  {d:44s} {len(files):3d} files  {kinds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
