#!/usr/bin/env python3
"""JS01 descriptive report, before any training (predeclarations/jisa_JS01_cic_victim_replication.md): the kept
devices with rows and malicious shares, the test split's malicious share tau_triv, and I(device; label)/H(label)
over the kept rows. Builds (and caches) the dataset through the project loader. Writes results/jisa/js01_describe.json.
"""
import collections, json, math, os, sys
import numpy as np
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
os.chdir(REPO)
from fedhomeguard import config as CFG, data as DATA  # noqa: E402

cfg = CFG.load("configs/jisa_cic_victim.yaml")
b = DATA.load_dataset(cfg, verbose=True)
y, dev = b["y"], b["device"]
names = b["device_names"]
tr, te = DATA.time_split_within_device(y, dev, cfg.data.train_frac, block=b.get("block"))


def H(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


hy = H(collections.Counter(y.tolist()))
cond = sum((dev == d).sum() / len(y) * H(collections.Counter(y[dev == d].tolist())) for d in np.unique(dev))
devices = [dict(device=names[d], rows=int((dev == d).sum()), malicious_share=float(y[dev == d].mean()))
           for d in np.unique(dev)]
devices.sort(key=lambda r: -r["rows"])
out = dict(rows=int(len(y)), devices=len(devices), features=len(b["feature_names"]),
           feature_names=b["feature_names"], train_rows=int(tr.sum()), test_rows=int(te.sum()),
           tau_triv=float(max(y[te].mean(), 1 - y[te].mean())), test_malicious_share=float(y[te].mean()),
           coupling_bits=hy - cond, label_entropy_bits=hy, coupling_share=(hy - cond) / hy,
           one_class_devices_95=sum(1 for r in devices if r["malicious_share"] > 0.95 or r["malicious_share"] < 0.05),
           device_table=devices)
os.makedirs("results/jisa", exist_ok=True)
json.dump(out, open("results/jisa/js01_describe.json", "w"), indent=1)
print({k: v for k, v in out.items() if k not in ("device_table", "feature_names")})
