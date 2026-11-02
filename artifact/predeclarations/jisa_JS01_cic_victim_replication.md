# JS01: does the class-coverage mechanism replicate on CIC IoT-IDAD 2024, read on the victim side?

Predeclared 2026-10-16 (UTC), before the loader below exists and before any member is trained on this corpus.
Round: JISA preparation (feedback `feedback/JISA_Reviewer_Feedback_and_Revision_Plan.md`, item M2 and the §6
"strongly recommended" list; triage `feedback/JISA_triage_and_plan.md`, F13).

## Why

The paper's positive case rests on IoT-23, whose ten device types are two real devices plus eight malware captures
run on one Raspberry Pi. The PB11 audit (2026-10-12) found that CIC IoT-IDAD 2024 is not an independent positive
case in the release's own device column, because its attack hosts are also Raspberry Pis. The audit named, but did
not run, a victim-side reading, in which the device is the real device that the attack reaches. In that reading the
devices carry both their own benign traffic and the attacks they receive. Their labels are therefore not set by
how malware was captured, which is the independence the feedback asks for. This is a test of the mechanism and of
its count rule (the coverage-vote model, CVM, of PB03), not a second positive case by construction.

## What was looked at before this predeclaration (disclosed)

- The PB11 audit and its two post hoc extensions (identity columns only; no features, no training).
- One exploratory count, 2026-10-15: per-device benign and attack row counts under a draft of the victim rule
  (scratchpad `cicprobe/victim_counts.py`; no features, no training). It found 70 real identities with at least 200
  rows, most holding both classes, and about a dozen over 95% attack. No certificate, member or partition was
  computed.

## Data and rules (fixed here)

- **Corpus:** the sample on disk, `data/raw/cic-iot-idad-2024/`, the first CSV of each of the 28 packet-based
  traffic types (the PB11 sample).
- **Raspberry Pi end:** a packet end whose Ethernet OUI column is `Raspberry Pi Trading Ltd`, or whose
  `device_mac` name is `Raspberry Pi 4-2 GB`.
- **Attack rows:** packets in the 27 attack files with exactly one Raspberry Pi end. The device is the other end.
  Excluded: an other end that is a VMware host, a multicast or broadcast address (first octet odd, or
  ff:ff:ff:ff:ff:ff), or an address with no registered vendor (empty OUI).
- **Benign rows:** packets in `BenignTraffic.csv`, assigned to the `device_mac` identity, with the same exclusions
  plus the Raspberry Pi hosts.
- **Dropped as unlabelable:** attack-file packets with no Raspberry Pi end (background traffic, or attacks whose
  attacker the addresses do not reveal), and packets between two Raspberry Pis.
- **Identity resolution:** a device named in `device_mac` keeps its name. A raw MAC is mapped to a name when, in a
  single-Raspberry-Pi-end attack packet, `device_mac` carries that name and the non-Raspberry-Pi end has that MAC
  (the first mapping seen, in file order, wins). Other raw MACs stay raw identities.
- **Devices kept:** identities with at least 500 rows after these rules.
- **Thinning and split:**
  - Each device is thinned evenly to at most 20,000 rows, in file-then-row order, preserving each file's share.
  - `traffic_type` is the source file. The split takes the last 20% of each (device, file) block, as for N-BaIoT
    (`time_split_within_device` with `block`).
- **Features:** every column that parses as numeric on at least 99% of kept rows, except the identity and
  addressing columns (stream, src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, device_mac, eth_src_oui,
  eth_dst_oui). Non-numeric cells become 0, and the transform is log1p(|x|), as for N-BaIoT.
- **Everything else** is unchanged from the IoT-23 runs:
  - N = 20 households; member MLP 32-16; FedAvg, 15 rounds; certification as in `exp_e2.py --clean-only`;
  - beta grid 0, 0.05, ..., 0.50;
  - k in {1, 2} with K caps 1:20 and 2:190; partition seeds 10 to 39.

## Arms

| arm | partition | devices per household | draws | k |
|---|---|---|---|---|
| A | IID | n/a | 30 | 1, 2 |
| B | device-derived | 1-3 (the IoT-23 main grid) | 30 | 1, 2 |
| C | device-derived | 1-1 (one device per household; more one-class members) | 30 | 1, 2 |

## Reported first, descriptively

- The kept devices, their rows and malicious shares.
- The test split's malicious share tau_triv.
- I(device; label)/H(label) over the kept rows, against IoT-23's 0.374 and N-BaIoT's ~0.
- Per draw, from the partition alone (before any training): the share of one-class clients (fracDegen) and the CVM
  prediction of beta* and of collapse at beta = 0.20.

## Predictions (tested on arms B and C pooled, k = 1 and k = 2 scored separately)

- **P1.** The CVM's beta* is within one 0.05 grid step of the observed beta* on at least 80% of device-derived
  draws, at each k. Its mean signed error in steps is >= 0 (errs high or exact, as on IoT-23).
- **P2.** IID (arm A) certifies at the ceiling, beta* = 0.45 at k = 1 and 0.25 at k = 2, on at least 28 of 30
  draws at each k.
- **P3.** At k = 1 the CVM's collapse prediction at beta = 0.20 agrees with the observed collapse on at least 80%
  of device-derived draws.
- **P4 (direction).** Across device-derived draws at k = 1, Spearman rho between fracDegen and the observed beta*
  is negative. For the joint device-by-label divergence S_JS, the rank correlation is reported for comparison, with
  no prediction.

**Outcome rule:**
- P1 and P3 both hold: the count rule transfers to an independent corpus.
- Either fails: it does not, and the paper says so.
- P2 fails: the pipeline or the corpus is suspect, and the result is reported as a failure of the setup, not of the
  mechanism.

No threshold, rule or arm will change after the first training run. If a rule above cannot be applied as written,
the deviation is recorded here with its date, before results are read.

## Outputs

- `results/jisa/js01_cic_victim_{iid,dd13,dd11}.jsonl`;
- `results/jisa/js01_cvm.json`;
- `results/jisa/js01_summary.md`.
- Script: `scripts/jisa_js01_cvm.py` (scoring); loader `cic-idad-victim` in `src/fedhomeguard/data.py`.

## Clarification recorded 2026-10-20, after the identity-column index pass and before any training

- The release writes the OUI column as `none` for an address with no registered vendor (also used as a name by the
  PB11 audit). It is read as "no registered vendor (empty OUI)" and excluded, as the rule above says. One identity
  (56:4f:8a:e1:f3:2d, 1,383 rows) is affected.
- A raw-MAC mapping is never made to the Raspberry Pi name or to a broadcast/multicast name, since the mapped end is
  by construction the non-Raspberry-Pi end.
- The benign file's device_mac identities are resolved with the same raw-MAC-to-name mapping, so one device keeps
  one identity across benign and attack rows.
- Seen in the index pass (identity columns only; descriptive, as this file allows): 66 identities with at least 500
  rows before this clarification, 65 after; malicious shares per identity range from 0.000 to 1.000.
