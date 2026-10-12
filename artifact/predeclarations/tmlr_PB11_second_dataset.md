# Predeclaration PB11: Second dataset with device identity and device-label coupling (desk audit)

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Criteria, fixed now.** C1 per-record device identity (column, per-device capture files, or a
  published MAC/IP-to-device map); C2 per-record benign/attack labels; C3 at least 5 devices and either
  attacks on several devices or I(device; label)/H(label) >= 0.10 when computable; C4 public with no
  paid access and <= 5 GB for a usable subset; C5 a licence that permits research use; C6 network-flow
  or packet-feature records comparable to IoT-23/N-BaIoT.
- **Candidates.** CICIoT2023 (exclusion re-checked, not assumed), TON_IoT, Edge-IIoTset,
  CIC IoT-DIAD 2024, CIC IoT Dataset 2022, MedBIoT, IoT Network Intrusion Dataset (Kang et al.),
  Bot-IoT, X-IIoTID, WUSTL-IIoT, ACI-IoT-2023, UNSW IoT traffic traces, Kitsune.
- **Output.** One row per candidate with C1-C6 verdicts and sources; a negative result is recorded as
  such. No federated runs on a new corpus in Phase B; if one passes C1-C6 and is small, compute only
  I(device; label) and per-device label rates.
