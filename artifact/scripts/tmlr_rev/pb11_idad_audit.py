#!/usr/bin/env python3
"""PB11 cheap audit of CIC IoT-IDAD 2024, once the PI's download is in
FedHomeGuard-P10/data/raw/cic-iot-idad-2024/. No training. Reads headers, then label and identity
columns only, in chunks.

Checks (preregistered criteria C1-C6, predeclarations/tmlr_PB11_second_dataset.md):
  C1 per-record device identity: a device/MAC column, or Src IP plus an IP/MAC-to-device map file
  C2 per-record labels; C3 >= 5 devices, attacks on several, I(device;label)/H(label)
  household partitions possible: >= 10 devices each holding >= 16 records (N = 20 households need
  devices to split), and the share of devices holding both classes.
Writes results/pb11_idad_audit.json.
"""
import collections, glob, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = "<artifact-root>/data/raw/cic-iot-idad-2024"
OUT = "<artifact-root>/results/tmlr_rev/pb11_idad_audit.json"
ID_COLS = ["device_mac", "Device", "device", "src_mac", "Src MAC", "eth.src", "Src IP", "src_ip", "Source IP"]
LAB_COLS = ["Label", "label", "Label 2", "attack", "Attack", "Category", "category"]


def entropy(counter):
    n = sum(counter.values())
    return -sum(c / n * math.log2(c / n) for c in counter.values() if c)


def main():
    import pandas as pd
    files = sorted(glob.glob(os.path.join(ROOT, "**", "*"), recursive=True))
    files = [f for f in files if os.path.isfile(f)]
    inv = [dict(path=os.path.relpath(f, ROOT), bytes=os.path.getsize(f)) for f in files]
    res = dict(root=ROOT, n_files=len(files), total_bytes=sum(x["bytes"] for x in inv), files=inv[:500])
    if not files:
        res["verdict"] = "Blocked: folder empty (waiting for the PI's download)"
        json.dump(res, open(OUT, "w"), indent=1); print(res["verdict"]); return
    maps = [f for f in files if re.search(r"(device|mac|ip).*(list|map)|readme|inventory", os.path.basename(f), re.I)]
    res["candidate_map_files"] = [os.path.relpath(f, ROOT) for f in maps]
    csvs = [f for f in files if f.lower().endswith(".csv")]
    heads = {}
    for f in csvs:
        try:
            heads[os.path.relpath(f, ROOT)] = list(pd.read_csv(f, nrows=0).columns)
        except Exception as e:
            heads[os.path.relpath(f, ROOT)] = f"unreadable: {e}"
    res["csv_headers"] = dict(list(heads.items())[:50])
    joint = collections.Counter(); dev_c = collections.Counter(); lab_c = collections.Counter()
    used_id = used_lab = None
    for f in csvs:
        h = heads[os.path.relpath(f, ROOT)]
        if isinstance(h, str):
            continue
        idc = next((c for c in ID_COLS if c in h), None)
        lc = next((c for c in LAB_COLS if c in h), None)
        if idc is None or lc is None:
            continue
        used_id, used_lab = idc, lc
        for ch in pd.read_csv(f, usecols=[idc, lc], chunksize=500_000, dtype=str):
            mal = (~ch[lc].str.lower().isin(["benign", "benigntraffic", "normal", "0"])).astype(int)
            for d, y in zip(ch[idc].values, mal.values):
                joint[(d, y)] += 1
            dev_c.update(ch[idc].values); lab_c.update(mal.values)
    if not joint:
        res["verdict"] = ("C1 FAIL or undetermined: no CSV carries both an identity column "
                          f"{ID_COLS} and a label column {LAB_COLS}; inspect candidate map files")
        json.dump(res, open(OUT, "w"), indent=1); print(res["verdict"]); return
    H = entropy(lab_c)
    Hc = sum(dev_c[d] / sum(dev_c.values()) *
             entropy(collections.Counter({y: joint[(d, y)] for y in (0, 1)})) for d in dev_c)
    per = {d: joint[(d, 1)] / dev_c[d] for d in dev_c}
    big = [d for d in dev_c if dev_c[d] >= 16]
    res.update(identity_column=used_id, label_column=used_lab, n_records=sum(dev_c.values()),
               n_identities=len(dev_c), n_identities_ge16=len(big), H_label=H, I_device_label=H - Hc,
               I_over_H=(H - Hc) / H if H else None,
               n_identities_both_classes=sum(1 for d in big if 0.0 < per[d] < 1.0),
               malicious_share=lab_c[1] / sum(lab_c.values()),
               note="identity = the column named; if it is an IP, it is a device only through a map file")
    ok = res["n_identities_ge16"] >= 10 and res["I_over_H"] is not None and res["I_over_H"] >= 0.10
    res["verdict"] = ("PASSES the cheap audit (propose runs to the coordinator before any training)" if ok else
                      "does not pass the cheap audit")
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("files", "csv_headers")}, indent=1))


if __name__ == "__main__":
    main()
