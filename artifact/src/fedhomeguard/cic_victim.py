"""CIC IoT-IDAD 2024, read on the victim side (JISA JS01).

Rules fixed in predeclarations/jisa_JS01_cic_victim_replication.md (2026-10-16), before this loader existed:

- A packet end is a Raspberry Pi end when its Ethernet OUI column is "Raspberry Pi Trading Ltd" or its address
  column carries the device name "Raspberry Pi 4-2 GB".
- Attack rows: packets of the 27 attack files with exactly one Raspberry Pi end; the device is the other end.
  Excluded: an other end that is a VMware host, a multicast or broadcast address (first octet odd, or
  ff:ff:ff:ff:ff:ff, or one of the release's broadcast/multicast names), or an address with no registered vendor
  (empty OUI).
- Benign rows: packets of BenignTraffic.csv, assigned to the device_mac identity, with the same exclusions plus the
  Raspberry Pi hosts.
- Dropped as unlabelable: attack-file packets with no Raspberry Pi end, and packets between two Raspberry Pis.
- Identity resolution: a device named in device_mac keeps its name; a raw MAC is mapped to a name when, in a
  single-Raspberry-Pi-end attack packet, device_mac carries that name and the non-Raspberry-Pi end has that MAC (the
  first mapping seen, in file order, wins); other raw MACs stay raw identities.
- Devices kept: identities with at least 500 rows; each thinned evenly to at most 20,000 rows in file-then-row
  order, preserving each file's share; traffic_type is the source file (the split blocks on it).
- Features: every column numeric on at least 99% of kept rows, except the identity and addressing columns;
  non-numeric cells become 0; log1p(|x|), as for N-BaIoT.

Two passes over the CSVs: pass 1 reads the five identity columns only and builds a row index; pass 2 reads the
selected rows in full. Both are cached next to the data.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import numpy as np
import pandas as pd

ID_COLS = ["src_mac", "dst_mac", "device_mac", "eth_src_oui", "eth_dst_oui"]
DROP_COLS = {"stream", "src_mac", "dst_mac", "src_ip", "dst_ip", "src_port", "dst_port", "device_mac",
             "eth_src_oui", "eth_dst_oui"}
RPI_OUI, RPI_NAME, VMW_OUI = "Raspberry Pi Trading Ltd", "Raspberry Pi 4-2 GB", "VMware, Inc."
BENIGN_FILE = "BenignTraffic.csv"
NOT_A_DEVICE = {"Broadcast", "IPv4 Multicast", "IPv6 Multicast", "none", "nan", ""}
MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$", re.I)
MIN_ROWS, MAX_ROWS, NUMERIC_SHARE = 500, 20_000, 0.99
CHUNK = 1_000_000


def _is_mac(v: str) -> bool:
    return bool(MAC.match(v))


def _multicast(v: str) -> bool:
    """Multicast or broadcast: a raw MAC whose first octet is odd (this includes ff:ff:ff:ff:ff:ff), or one of the
    release's broadcast/multicast names."""
    if v in NOT_A_DEVICE:
        return True
    return _is_mac(v) and int(v[:2], 16) & 1 == 1


def _files(root):
    return sorted(f for f in os.listdir(root) if f.endswith(".csv"))


def _read_ids(path):
    for ch in pd.read_csv(path, usecols=ID_COLS, dtype=str, chunksize=CHUNK):
        yield ch.fillna("")


def build_index(root: str, verbose: bool = True) -> dict:
    """Pass 1: (file, row) -> (identity, label) for every kept packet, plus diagnostics. Vectorized over unique
    address values (a few hundred) rather than rows (tens of millions)."""
    files = _files(root)
    vendor, name_of = {}, {}
    # 1a: vendor of every address value, and the raw-MAC -> name mapping from attack files, in file order
    for f in files:
        attack = f != BENIGN_FILE
        for ch in _read_ids(os.path.join(root, f)):
            for col, oc in (("src_mac", "eth_src_oui"), ("dst_mac", "eth_dst_oui")):
                first = ch[[col, oc]].drop_duplicates(subset=[col], keep="first")
                for v, o in zip(first[col].values, first[oc].values):
                    if v not in vendor:
                        vendor[v] = o
            if not attack:
                continue
            s_rpi = ((ch["eth_src_oui"] == RPI_OUI) | (ch["src_mac"] == RPI_NAME)).values
            d_rpi = ((ch["eth_dst_oui"] == RPI_OUI) | (ch["dst_mac"] == RPI_NAME)).values
            one = s_rpi ^ d_rpi
            pairs = pd.DataFrame({"v": np.where(s_rpi, ch["dst_mac"].values, ch["src_mac"].values)[one],
                                  "d": ch["device_mac"].values[one]}).drop_duplicates(keep="first")
            for v, d in zip(pairs["v"].values, pairs["d"].values):
                if _is_mac(v) and v not in name_of and d and not _is_mac(d) and d != RPI_NAME \
                        and d not in NOT_A_DEVICE:
                    name_of[v] = d
        if verbose:
            print(f"  pass 1a {f}", flush=True)

    def excluded(v, oui):
        # "none" is the release's OUI value for an address with no registered vendor (clarification, 2026-10-20)
        return oui == VMW_OUI or oui in ("", "none") or _multicast(v)

    rec_file, rec_row, rec_id, rec_lab = [], [], [], []
    diag = {}
    for fi, f in enumerate(files):
        attack = f != BENIGN_FILE
        base, d = 0, dict(rows=0, kept=0, no_rpi=0, two_rpi=0, excluded=0)
        for ch in _read_ids(os.path.join(root, f)):
            n = len(ch)
            d["rows"] += n
            if attack:
                s_rpi = ((ch["eth_src_oui"] == RPI_OUI) | (ch["src_mac"] == RPI_NAME)).values
                d_rpi = ((ch["eth_dst_oui"] == RPI_OUI) | (ch["dst_mac"] == RPI_NAME)).values
                d["no_rpi"] += int((~s_rpi & ~d_rpi).sum())
                d["two_rpi"] += int((s_rpi & d_rpi).sum())
                one = s_rpi ^ d_rpi
                v = pd.Series(np.where(s_rpi, ch["dst_mac"].values, ch["src_mac"].values)[one])
                o = pd.Series(np.where(s_rpi, ch["eth_dst_oui"].values, ch["eth_src_oui"].values)[one])
                rows = np.where(one)[0]
                lab = 1
            else:
                v = pd.Series(ch["device_mac"].values)
                o = v.map(lambda x: vendor.get(x, ""))
                rows = np.arange(n)
                lab = 0
            key = v + "\x00" + o
            u = key.unique()
            bad = {}
            for kk in u:
                vv, oo = kk.split("\x00")
                bad[kk] = excluded(vv, oo) or (not attack and (vv == RPI_NAME or oo == RPI_OUI))
            drop = key.map(bad).to_numpy(bool)
            d["excluded"] += int(drop.sum())
            keep = ~drop
            ident = v[keep].map(lambda x: name_of.get(x, x)).to_numpy(object)
            rec_file.append(np.full(len(ident), fi, np.int16)); rec_row.append(base + rows[keep])
            rec_id.append(ident); rec_lab.append(np.full(len(ident), lab, np.int8))
            d["kept"] += int(keep.sum())
            base += n
        diag[f] = d
        if verbose:
            print(f"  pass 1b {f}: {d}", flush=True)
    return dict(files=files, file=np.concatenate(rec_file), row=np.concatenate(rec_row).astype(np.int64),
                identity=np.concatenate(rec_id), label=np.concatenate(rec_lab), diag=diag, name_of=name_of,
                vendor=vendor)


def select_rows(idx: dict) -> dict:
    """Devices with >= MIN_ROWS kept rows, each thinned evenly to <= MAX_ROWS in file-then-row order, preserving
    each file's share. Returns per-file sorted row positions with their identity and label."""
    ids, counts = np.unique(idx["identity"], return_counts=True)
    keep = set(ids[counts >= MIN_ROWS])
    sel = {fi: [] for fi in range(len(idx["files"]))}
    for dev in sorted(keep):
        m = np.where(idx["identity"] == dev)[0]
        order = np.lexsort((idx["row"][m], idx["file"][m]))
        m = m[order]
        n = len(m)
        if n > MAX_ROWS:
            parts = []
            for fi in np.unique(idx["file"][m]):
                blk = m[idx["file"][m] == fi]
                q = int(np.floor(MAX_ROWS * len(blk) / n))
                if q > 0:
                    parts.append(blk[np.linspace(0, len(blk) - 1, q).astype(int)])
            m = np.concatenate(parts)
        for i in m:
            sel[int(idx["file"][i])].append((int(idx["row"][i]), dev, int(idx["label"][i])))
    return {fi: sorted(v) for fi, v in sel.items() if v}


def load_cic_victim(root: str = "data/raw/cic-iot-idad-2024", max_rows_per_device: int | None = None,
                    verbose: bool = True, cache: bool = True) -> pd.DataFrame:
    """The kept, thinned rows with all columns plus label/device/device_name/traffic_type. max_rows_per_device is
    fixed by the predeclaration (20,000) and the argument is ignored."""
    files = _files(root)
    sig = hashlib.sha1(json.dumps([files, MIN_ROWS, MAX_ROWS, "v2-none-excluded"]).encode()).hexdigest()[:12]
    cpath = os.path.join(root, f".cache_victim_{sig}.parquet")
    if cache and os.path.exists(cpath):
        df = pd.read_parquet(cpath)
        if verbose:
            print(f"  cic-idad-victim rows={len(df)} devices={df.device.nunique()} (cached)")
        return df
    idx = build_index(root, verbose)
    sel = select_rows(idx)
    frames = []
    for fi, rows in sel.items():
        f = files[fi]
        want = {r: (dev, lab) for r, dev, lab in rows}
        wpos = np.array(sorted(want), np.int64)
        base, got = 0, []
        for ch in pd.read_csv(os.path.join(root, f), dtype=str, chunksize=CHUNK // 5):
            pos = np.arange(base, base + len(ch))
            hit = np.isin(pos, wpos, assume_unique=True)
            sub = ch[hit]
            if len(sub):
                meta = [want[p] for p in pos[hit]]
                sub = sub.assign(device=[m[0] for m in meta], device_name=[m[0] for m in meta],
                                 label=["malicious" if m[1] else "benign" for m in meta],
                                 traffic_type=f[:-4])
                got.append(sub)
            base += len(ch)
        frames.append(pd.concat(got, ignore_index=True))
        if verbose:
            print(f"  pass 2 {f}: {sum(len(g) for g in got)} rows", flush=True)
    df = pd.concat(frames, ignore_index=True)
    # file-then-row order within each device is kept by construction (files sorted, rows sorted)
    if verbose:
        print(f"  cic-idad-victim rows={len(df)} devices={df.device.nunique()}")
    if cache:
        try:
            df.to_parquet(cpath, index=False)
        except Exception as e:  # a missing parquet engine must not fail the load
            if verbose:
                print(f"  cic-idad-victim cache skipped: {e}")
    return df


def featurize_cic_victim(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    meta = {"label", "device", "device_name", "traffic_type"}
    cand = [c for c in df.columns if c not in meta and c not in DROP_COLS]
    names, cols = [], []
    for c in cand:
        x = pd.to_numeric(df[c], errors="coerce")
        if x.notna().mean() >= NUMERIC_SHARE:
            names.append(c)
            cols.append(x.fillna(0).to_numpy(float))
    X = np.log1p(np.abs(np.stack(cols, 1))).astype(np.float32)
    y = (df["label"] == "malicious").to_numpy().astype(np.int64)
    return X, y, names
