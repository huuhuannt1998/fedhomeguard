#!/usr/bin/env python3
"""Light N-BaIoT loader: training labels and device codes only (no features), reproducing exactly
what runner.prepare hands to partition.build for N-BaIoT, at a fraction of the memory.

runner.prepare -> data.load_dataset reads the parquet cache written by data.load_nbaiot
(max_rows_per_device = 60,000 and the COMPLETE_DEVICES.txt list), sets
  y      = (label == "malicious"),
  device = pd.Categorical(df["device"]).codes,
  block  = df["traffic_type"],
and splits with data.time_split_within_device(y, device, 0.8, block). Partitions need only
y[train] and device[train]. Reading three parquet columns keeps resident memory well under 1 GB.

    python3 nbaiot_light.py --check     # prints sizes and label/device summaries, no partitioning
"""
import argparse, hashlib, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = "<artifact-root>"
ROOT = os.path.join(REPO, "data", "raw", "nbaiot")


def cache_path(max_rows_per_device=60_000):
    """Same key as data.load_nbaiot."""
    manifest = os.path.join(ROOT, "COMPLETE_DEVICES.txt")
    keep = {l.strip() for l in open(manifest) if l.strip()}
    ckey = f"{max_rows_per_device}_{'-'.join(sorted(keep))}"
    return os.path.join(ROOT, f".cache_{hashlib.sha1(ckey.encode()).hexdigest()[:12]}.parquet")


def load_labels_devices(max_rows_per_device=60_000):
    path = cache_path(max_rows_per_device)
    if not os.path.exists(path):
        raise FileNotFoundError(f"N-BaIoT parquet cache missing: {path}")
    df = pd.read_parquet(path, columns=["label", "device", "traffic_type"])
    y = (df["label"] == "malicious").to_numpy().astype(np.int64)
    cat = pd.Categorical(df["device"])
    device = cat.codes.astype(int)
    block = df["traffic_type"].astype(str).to_numpy(dtype=object)
    # data.time_split_within_device with block (copied logic, identical result)
    keys = np.array([f"{d}|{b}" for d, b in zip(device, block)])
    tr = np.zeros(len(y), bool)
    for kk in np.unique(keys):
        ix = np.where(keys == kk)[0]
        tr[ix[: int(0.8 * len(ix))]] = True
    te = ~tr
    tau = float(max(y[te].mean(), 1 - y[te].mean()))
    return dict(ytr_np=y[tr], dtr=device[tr], yte_np=y[te], tau=tau,
                device_names=list(cat.categories), n_rows=int(len(y)), path=path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only report the cache file and its size")
    a = ap.parse_args()
    p = cache_path()
    print(p, os.path.getsize(p) if os.path.exists(p) else "MISSING")
