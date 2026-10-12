#!/usr/bin/env python3
"""PB11b (post hoc extension of the predeclared PB11 audit; 2026-10-12; no training): CIC IoT-IDAD 2024, packet-based
features, the sample on disk (the first CSV of each of the 28 traffic types).

The predeclared script (pb11_idad_audit.py) needs a per-row label column; the release has none (README: rows are
unlabelled, the label is the folder or file name). This extension takes the label from the file name, as the README
prescribes, and reads only the identity columns (src_mac, dst_mac, src_ip, dst_ip, device_mac, eth_src_oui,
eth_dst_oui). Outputs results/pb11b_idad_extended.json.

  python3 pb11b_idad_extended.py ROOT OUT_JSON
"""
import collections, json, math, os, re, sys
import pandas as pd

ROOT, OUT = sys.argv[1], sys.argv[2]
COLS = ["src_mac", "dst_mac", "src_ip", "dst_ip", "device_mac", "eth_src_oui", "eth_dst_oui"]
MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$", re.I)
FAMILY = {"BenignTraffic": "Benign", "DictionaryBruteForce": "BruteForce", "Mirai-greip_flood": "Mirai",
          "Backdoor_Malware": "Web-Based", "BrowserHijacking": "Web-Based", "CommandInjection": "Web-Based",
          "SqlInjection": "Web-Based", "Uploading_Attack": "Web-Based", "XSS": "Web-Based",
          "DNS_Spoofing": "Spoofing", "MITM-ArpSpoofing": "Spoofing", "VulnerabilityScan": "Recon"}


def family(t):
    if t in FAMILY:
        return FAMILY[t]
    return t.split("-")[0]  # DDoS-*, DoS-*, Recon-*


def entropy(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


def mutual_info(joint):
    """joint: Counter over (x, y). Returns I(X;Y), H(Y)."""
    cx, cy = collections.Counter(), collections.Counter()
    for (x, y), v in joint.items():
        cx[x] += v; cy[y] += v
    hy = entropy(cy)
    hy_x = sum(cx[x] / sum(cx.values()) * entropy(collections.Counter({y: v for (xx, y), v in joint.items() if xx == x}))
               for x in cx)
    return hy - hy_x, hy


files = sorted(f for f in os.listdir(ROOT) if f.endswith(".csv"))
per = {}
dev_by_type = collections.Counter()      # (device_mac, type) -> rows
src_oui = collections.Counter(); dst_oui = collections.Counter()
name_oui = collections.defaultdict(collections.Counter)   # named device -> OUI vendor seen beside it
mac_oui = {}
for f in files:
    t = f[:-4].rstrip("-")
    c = dict(rows=0, devmac=collections.Counter(), src=collections.Counter(), dst=collections.Counter(),
             src_oui=collections.Counter(), dst_oui=collections.Counter(), side=collections.Counter(),
             pair_oui=collections.Counter(), touches_rpi=0, touches_vmware=0)
    for ch in pd.read_csv(os.path.join(ROOT, f), usecols=COLS, dtype=str, chunksize=1_000_000):
        ch = ch.fillna("nan")
        c["rows"] += len(ch)
        c["devmac"].update(ch["device_mac"].values)
        c["src"].update(ch["src_mac"].values); c["dst"].update(ch["dst_mac"].values)
        c["src_oui"].update(ch["eth_src_oui"].values); c["dst_oui"].update(ch["eth_dst_oui"].values)
        side = (ch["device_mac"] == ch["src_mac"]).map({True: "src", False: ""}) + \
               (ch["device_mac"] == ch["dst_mac"]).map({True: "dst", False: ""})
        c["side"].update(side.values)
        c["pair_oui"].update(zip(ch["eth_src_oui"].values, ch["eth_dst_oui"].values))
        rpi = (ch["eth_src_oui"] == "Raspberry Pi Trading Ltd") | (ch["eth_dst_oui"] == "Raspberry Pi Trading Ltd")
        vmw = (ch["eth_src_oui"] == "VMware, Inc.") | (ch["eth_dst_oui"] == "VMware, Inc.")
        c["touches_rpi"] += int(rpi.sum()); c["touches_vmware"] += int(vmw.sum())
        for s, o in zip(ch["src_mac"].values, ch["eth_src_oui"].values):
            if not MAC.match(s):
                name_oui[s][o] += 1
            elif s not in mac_oui:
                mac_oui[s] = o
        for s, o in zip(ch["dst_mac"].values, ch["eth_dst_oui"].values):
            if not MAC.match(s):
                name_oui[s][o] += 1
            elif s not in mac_oui:
                mac_oui[s] = o
    for d, v in c["devmac"].items():
        dev_by_type[(d, t)] += v
    per[t] = c
    print(f, c["rows"], flush=True)


def is_named(d):
    return not MAC.match(d) and d not in ("nan",)


def vendor(d):
    if is_named(d):
        return name_oui[d].most_common(1)[0][0] if name_oui[d] else "?"
    return mac_oui.get(d, "?")


types = sorted(per)
out = dict(root=ROOT, files=len(files), types=types, rows={t: per[t]["rows"] for t in types},
           total_rows=sum(per[t]["rows"] for t in types))
# Q1 identity
side = collections.Counter(); named_rows = 0; tot = 0
for t in types:
    side.update(per[t]["side"])
    for d, v in per[t]["devmac"].items():
        tot += v; named_rows += v if is_named(d) else 0
devices = collections.Counter()
for (d, t), v in dev_by_type.items():
    devices[d] += v
out["q1"] = dict(device_mac_equals=dict(side), rows=tot, named_share=named_rows / tot,
                 distinct_device_mac=len(devices), distinct_named=sum(1 for d in devices if is_named(d)),
                 distinct_raw_mac=sum(1 for d in devices if MAC.match(d)),
                 raw_mac_vendors=collections.Counter(vendor(d) for d in devices if MAC.match(d)).most_common(25),
                 top_device_mac=[(d, v, vendor(d)) for d, v in devices.most_common(40)])
# Q2 attackers and victims per attack type
q2 = {}
for t in types:
    if t == "BenignTraffic":
        continue
    c = per[t]; n = c["rows"]
    q2[t] = dict(rows=n, top_src=[(s, round(v / n, 4), vendor(s)) for s, v in c["src"].most_common(5)],
                 top_dst=[(s, round(v / n, 4), vendor(s)) for s, v in c["dst"].most_common(5)],
                 src_oui=[(o, round(v / n, 4)) for o, v in c["src_oui"].most_common(5)],
                 touches_rpi=round(c["touches_rpi"] / n, 4), touches_vmware=round(c["touches_vmware"] / n, 4),
                 top_pair=[(a, b, round(v / n, 4)) for (a, b), v in c["pair_oui"].most_common(3)])
out["q2"] = q2
att_src = collections.Counter(); att_dst = collections.Counter()
for t in types:
    if t == "BenignTraffic":
        continue
    for s, v in per[t]["src"].most_common(3):
        if v / per[t]["rows"] >= 0.05:
            att_src[(s, vendor(s))] += 1
    for s, v in per[t]["dst"].most_common(3):
        if v / per[t]["rows"] >= 0.05:
            att_dst[(s, vendor(s))] += 1
out["q2_summary"] = dict(main_sources=[(a, b, n) for (a, b), n in att_src.most_common()],
                         main_destinations=[(a, b, n) for (a, b), n in att_dst.most_common()])
# Q3 coupling with device = device_mac, label = file type or benign/attack
j_type = collections.Counter(); j_bin = collections.Counter()
for (d, t), v in dev_by_type.items():
    j_type[(d, t)] += v; j_bin[(d, int(t != "BenignTraffic"))] += v
i_t, h_t = mutual_info(j_type); i_b, h_b = mutual_info(j_bin)
j_type_n = collections.Counter({k: v for k, v in j_type.items() if is_named(k[0])})
j_bin_n = collections.Counter({k: v for k, v in j_bin.items() if is_named(k[0])})
i_tn, h_tn = mutual_info(j_type_n); i_bn, h_bn = mutual_info(j_bin_n)
out["q3"] = dict(per_type=dict(I=i_t, H=h_t, ratio=i_t / h_t), binary=dict(I=i_b, H=h_b, ratio=i_b / h_b),
                 named_only_per_type=dict(I=i_tn, H=h_tn, ratio=i_tn / h_tn),
                 named_only_binary=dict(I=i_bn, H=h_bn, ratio=i_bn / h_bn),
                 attack_share=sum(per[t]["rows"] for t in types if t != "BenignTraffic") / out["total_rows"],
                 note="sample: the first CSV of each type, not the release's proportions")
# Q4 partitions: devices with benign and attack rows
ben = collections.Counter(); att = collections.Counter(); att_types = collections.defaultdict(set)
for (d, t), v in dev_by_type.items():
    if t == "BenignTraffic":
        ben[d] += v
    else:
        att[d] += v; att_types[d].add(t)
both = [d for d in devices if ben[d] >= 16 and att[d] >= 16]
attacker_vendors = {"Raspberry Pi Trading Ltd", "VMware, Inc."}
both_real = [d for d in both if vendor(d) not in attacker_vendors]
out["q4"] = dict(devices_with_benign_ge16=sum(1 for d in devices if ben[d] >= 16),
                 devices_with_attack_ge16=sum(1 for d in devices if att[d] >= 16),
                 devices_with_both_ge16=len(both), real_devices_with_both_ge16=len(both_real),
                 named_with_both_ge16=sum(1 for d in both_real if is_named(d)),
                 per_device=sorted([(d, vendor(d), ben[d], att[d], round(att[d] / (ben[d] + att[d]), 4),
                                     len(att_types[d])) for d in devices if ben[d] + att[d] >= 1000],
                                   key=lambda r: -(r[2] + r[3]))[:60],
                 benign_devices_in_attack_files=sum(1 for d in devices if ben[d] >= 16 and att[d] > 0),
                 attack_rows_by_named_device_share=sum(v for d, v in att.items() if is_named(d)) / sum(att.values()))
json.dump(out, open(OUT, "w"), indent=1, default=list)
print(json.dumps({k: out[k] for k in ("total_rows", "q1", "q3", "q4")}, indent=1, default=list)[:6000])
