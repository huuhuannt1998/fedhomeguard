#!/usr/bin/env python3
"""PB11c (post hoc, 2026-10-12; no training): roles of the endpoints in the CIC IoT-IDAD 2024 packet-based sample.

Complements pb11b_idad_extended.py, which counted device_mac per file-name label. Here the question is who is attacked
and by whom, since the attack files also carry background traffic. Reads src_mac, dst_mac, device_mac, eth_src_oui,
eth_dst_oui only. A row "touches a Raspberry Pi" when either Ethernet OUI is Raspberry Pi Trading Ltd. Outputs JSON.

  python3 -I pb11c_idad_roles.py ROOT OUT_JSON
"""
import collections, json, math, os, re, sys
import pandas as pd

ROOT, OUT = sys.argv[1], sys.argv[2]
COLS = ["src_mac", "dst_mac", "device_mac", "eth_src_oui", "eth_dst_oui"]
MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$", re.I)
RPI, VMW = "Raspberry Pi Trading Ltd", "VMware, Inc."
NOT_A_DEVICE = {"Broadcast", "none", "nan", "IPv4 Multicast", "IPv6 Multicast"}


def entropy(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


def mutual_info(joint):
    cx, cy = collections.Counter(), collections.Counter()
    for (x, y), v in joint.items():
        cx[x] += v; cy[y] += v
    n = sum(cx.values()); by_x = collections.defaultdict(collections.Counter)
    for (x, y), v in joint.items():
        by_x[x][y] += v
    hy = entropy(cy)
    return hy - sum(cx[x] / n * entropy(by_x[x]) for x in cx), hy


files = sorted(f for f in os.listdir(ROOT) if f.endswith(".csv"))
vendor = {}                                     # identity -> OUI vendor
dev_type = collections.Counter()                # (device_mac, type) -> rows
per = {}
side_when_dst = collections.Counter()           # vendor of src when device_mac == dst only
both_named = 0; tot = 0
for f in files:
    t = f[:-4].rstrip("-")
    c = dict(rows=0, rpi_rows=0, rpi_src_rows=0, victim=collections.Counter(), rpi_host=collections.Counter(),
             devmac_rpi=0, devmac_vmw=0)
    for ch in pd.read_csv(os.path.join(ROOT, f), usecols=COLS, dtype=str, chunksize=1_000_000):
        ch = ch.fillna("nan")
        n = len(ch); c["rows"] += n; tot += n
        for col, oc in (("src_mac", "eth_src_oui"), ("dst_mac", "eth_dst_oui")):
            for k, o in zip(ch[col].values, ch[oc].values):
                if k not in vendor:
                    vendor[k] = o
        dev_type.update(zip(ch["device_mac"].values, [t] * n))
        sr = ch["eth_src_oui"] == RPI; dr = ch["eth_dst_oui"] == RPI
        one = sr ^ dr
        c["rpi_rows"] += int((sr | dr).sum()); c["rpi_src_rows"] += int(sr.sum())
        # counterpart of a Raspberry Pi (rows with exactly one Raspberry Pi end)
        other = ch["dst_mac"].where(sr, ch["src_mac"])[one]
        host = ch["src_mac"].where(sr, ch["dst_mac"])[one]
        c["victim"].update(other.values); c["rpi_host"].update(host.values)
        dv = ch["device_mac"].map(lambda k: vendor.get(k, "?"))
        c["devmac_rpi"] += int((dv == RPI).sum()); c["devmac_vmw"] += int((dv == VMW).sum())
        only_dst = (ch["device_mac"] == ch["dst_mac"]) & (ch["device_mac"] != ch["src_mac"])
        side_when_dst.update(ch["eth_src_oui"][only_dst].values)
        both_named += int((~ch["src_mac"].str.match(MAC.pattern) & ~ch["dst_mac"].str.match(MAC.pattern)).sum())
    per[t] = c
    print(f, c["rows"], flush=True)

types = sorted(per)
attack = [t for t in types if t != "BenignTraffic"]
v = lambda k: vendor.get(k, "?")
real = lambda k: v(k) not in (RPI, VMW) and v(k) not in NOT_A_DEVICE and k not in NOT_A_DEVICE
out = dict(files=len(files), total_rows=tot)
out["q1_extra"] = dict(rows_both_endpoints_named=both_named, share_both_named=both_named / tot,
                       src_vendor_when_device_mac_is_dst=side_when_dst.most_common(8))
att_rows = sum(per[t]["rows"] for t in attack)
out["attack_rows"] = att_rows
out["attack_rows_device_mac_rpi"] = sum(per[t]["devmac_rpi"] for t in attack) / att_rows
out["attack_rows_device_mac_vmware"] = sum(per[t]["devmac_vmw"] for t in attack) / att_rows
out["benign_rows_touching_rpi"] = per["BenignTraffic"]["rpi_rows"] / per["BenignTraffic"]["rows"]
rows = {}
victims_all = collections.Counter(); hosts_all = collections.Counter()
for t in attack:
    c = per[t]; n = c["rows"]; r1 = sum(c["victim"].values())
    vic = [(k, v(k), cnt, round(cnt / r1, 4)) for k, cnt in c["victim"].most_common(3)] if r1 else []
    rows[t] = dict(rows=n, touches_rpi=round(c["rpi_rows"] / n, 4), rpi_is_source=round(c["rpi_src_rows"] / n, 4),
                   rpi_hosts=sum(1 for k, cnt in c["rpi_host"].items() if cnt >= 16),
                   top_counterparts=vic)
    for k, cnt in c["victim"].items():
        victims_all[k] += cnt
    for k, cnt in c["rpi_host"].items():
        hosts_all[k] += cnt
out["per_attack_type"] = rows
main_victims = sorted({(r["top_counterparts"][0][0], r["top_counterparts"][0][1]) for t, r in rows.items()
                       if r["touches_rpi"] >= 0.5 and r["top_counterparts"] and r["top_counterparts"][0][3] >= 0.5})
out["rpi_dominated_types"] = sorted(t for t, r in rows.items() if r["touches_rpi"] >= 0.5)
out["rpi_dominated_types_ge90"] = sorted(t for t, r in rows.items() if r["touches_rpi"] >= 0.9)
out["main_victims_of_rpi_dominated_types"] = main_victims
out["rpi_hosts_ge16"] = sorted(k for k, cnt in hosts_all.items() if cnt >= 16)
out["real_counterparts_ge16"] = sum(1 for k, cnt in victims_all.items() if cnt >= 16 and real(k))
out["real_counterparts_ge1pct_of_some_type"] = sorted({k for t in attack for k, cnt in per[t]["victim"].items()
                                                       if real(k) and sum(per[t]["victim"].values())
                                                       and cnt / sum(per[t]["victim"].values()) >= 0.01})
# Q3 restricted to real devices (device_mac whose vendor is neither Raspberry Pi nor VMware nor a non-device)
jt = collections.Counter({(d, t): n for (d, t), n in dev_type.items() if real(d)})
jb = collections.Counter()
for (d, t), n in jt.items():
    jb[(d, int(t != "BenignTraffic"))] += n
it, ht = mutual_info(jt); ib, hb = mutual_info(jb)
out["q3_real_devices_only"] = dict(per_type=dict(I=it, H=ht, ratio=it / ht), binary=dict(I=ib, H=hb, ratio=ib / hb),
                                   rows=sum(jt.values()))
# Q4 with an attack role instead of file membership: real devices with >=16 benign rows (device_mac) and >=16 rows
# as the counterpart of a Raspberry Pi in an attack file
ben = collections.Counter({d: n for (d, t), n in dev_type.items() if t == "BenignTraffic"})
both = sorted(k for k in victims_all if real(k) and victims_all[k] >= 16 and ben.get(k, 0) >= 16)
out["q4_real_devices_benign_and_rpi_counterpart_ge16"] = len(both)
out["q4_real_devices_benign_and_rpi_counterpart_ge1000"] = sorted(
    (k, v(k), ben.get(k, 0), victims_all[k]) for k in victims_all
    if real(k) and victims_all[k] >= 1000 and ben.get(k, 0) >= 16)
json.dump(out, open(OUT, "w"), indent=1, default=list)
print(json.dumps({k: out[k] for k in out if k != "per_attack_type"}, indent=1, default=list)[:5000])
