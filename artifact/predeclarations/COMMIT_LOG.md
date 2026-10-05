# Commit log of the predeclarations (anonymized)

Extracted on 2026-10-03 from the project's local git repository. Only the commit hash, the
commit time (local clock, as recorded by git) and the files each commit added are kept; author
identities are removed, and the repository itself is not shipped. Each predeclaration file was
committed once and never changed afterwards (`git log -- <file>` lists one commit; the working copy
equals it). The sha256 of each file below equals the copy in this folder.

| predeclaration | sha256 | commit that added it | commit that added its results |
|---|---|---|---|
| `richness_nbaiot.md` (N-BaIoT device-type sweep, k = 1) | `3e116f0c929b9a0cab56889dfd9d098ad39e87fe8416bef3070d03d326e2f75a` | `bafca461c13dd4ce9fa6a4c4d913ec3bc96d0470` 2026-09-03 19:05:26 | `1debbdc6282d7f84bd5c6a135f40ae192a0ea19e` 2026-09-03 20:05:23 (`results/canonical/e21_nbrich_*.jsonl`, all five levels) |
| `richness_k2.md` (IoT-23 device-type sweep, k = 2) | `ff4f9f1730ff5a67e6dc2d6373208292752e83123831d6f2e7a1bfc13e8e1123` | `98895d7da3abc9982edf79f1536884e75516d5aa` 2026-09-03 20:12:15 | `ae9bae1323272aa59f5f35b6493b877ca98d2620` 2026-09-03 20:50:47 (`results/canonical/e22_k2rich_*.jsonl`, all five levels) |
| `richness_nbaiot_k2.md` (N-BaIoT device-type sweep, k = 2) | `77b540e53e75185af5d78ecacce4cd928b8378edc7b0f3a2c6788d98d2dcaff7` | `7f41a65f2b59848ad5632e9e3e7690320f64fd41` 2026-09-03 21:28:47 | `9c6f146e963f0c1a7806b8a2cec46512cf690377` 2026-09-04 17:32:53 (first draw of three levels) and `483a0dc5983d829ab9cc55d55712ffb9589c81cd` 2026-09-04 23:01:36 (the rest of `results/canonical/e23_nbk2rich_*.jsonl`) |

What this shows: each predeclaration was committed before any commit that contains its results.
What it does not show: commit order is a local record. No external registry or third party
timestamped these files, and git does not prove that no run preceded a commit.

The earlier N-BaIoT prediction (2026-08-25) was not a file in this repository; it is exported in
`nbaiot_2026-08-25_record.md`.
