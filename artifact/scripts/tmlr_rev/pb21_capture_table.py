#!/usr/bin/env python3
"""PB21a (round tmlr6, post hoc data description; no training): the ten IoT-23 captures as the paper uses them.

For each capture: labelled rows read (benign or malicious, within the loader's first 400,000 lines), rows kept
after even thinning to at most 60,000 in time order, benign and malicious rows kept, train and test rows (the
paper's 80/20 time split within each capture), and the full capture's labelled rows and malicious share (the
whole file, read the same way). Uses the repository loader's own reading rules (src/fedhomeguard/data.py).

  python3 pb21_capture_table.py REPO OUT_JSON
"""
import json, os, sys
import numpy as np, pandas as pd

REPO, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(REPO, "src"))
from fedhomeguard import data as D  # noqa: E402

root = os.path.join(REPO, "data", "raw", "iot23")
rows = []
for name in sorted(os.listdir(root)):
    if not name.endswith(".conn.log.labeled"):
        continue
    dev = name.split(".conn")[0]
    path = os.path.join(root, name)
    def read(nrows):
        df = pd.read_csv(path, sep=r"\s+", comment="#", names=D.IOT23_COLS, header=None, engine="python",
                         on_bad_lines="skip", dtype=str, nrows=nrows, usecols=["label", "detailed"])
        df = df[df["label"].notna()]
        lab = df["label"].str.lower()
        return df[lab.isin(["benign", "malicious"])].assign(label=lab[lab.isin(["benign", "malicious"])])
    full = read(None)
    read_ = read(400_000)
    kept = read_
    if len(kept) > 60_000:
        kept = kept.iloc[np.linspace(0, len(kept) - 1, 60_000).astype(int)]
    y = (kept["label"] == "malicious").to_numpy()
    ntr = int(0.8 * len(kept))
    det = kept.loc[kept["label"] == "malicious", "detailed"].astype(str).str.strip().value_counts()
    rows.append(dict(
        capture=dev, device=D.IOT23_DEVICE_NAME.get(dev, "malware capture"),
        full_rows=int(len(full)), full_mal_share=float((full["label"] == "malicious").mean()),
        read_rows=int(len(read_)), read_mal_share=float((read_["label"] == "malicious").mean()),
        kept_rows=int(len(kept)), kept_benign=int((~y).sum()), kept_malicious=int(y.sum()),
        kept_mal_share=float(y.mean()), train_rows=ntr, test_rows=int(len(kept) - ntr),
        test_malicious=int(y[ntr:].sum()), truncated=bool(len(full) > len(read_)),
        main_detailed_label=(det.index[0] if len(det) else None)))
    print(rows[-1], flush=True)
tot = dict(kept=sum(r["kept_rows"] for r in rows), test=sum(r["test_rows"] for r in rows),
           test_mal=sum(r["test_malicious"] for r in rows))
tot["test_mal_share"] = tot["test_mal"] / tot["test"]
json.dump(dict(captures=rows, totals=tot,
               note="post hoc data description (round tmlr6); no training; loader rules of src/fedhomeguard/data.py"),
          open(OUT, "w"), indent=1)
print(tot)
