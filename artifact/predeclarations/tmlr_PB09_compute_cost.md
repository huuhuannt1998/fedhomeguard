# Predeclaration PB09: Compute cost

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- k in {1, 2, 3 (sampled 500 and full 1,140), 5, 8} vs one FedAvg run over the 20 households:
  client-rounds (analytic, K x k x 15), measured median single-process training time per member on 10
  members per k on IID draw 0 (and the one FedAvg run), inference latency of the K-member vote on the
  33,310 test flows (batched, median of 5), parameters stored (K x 1,586 x 4 bytes). Timings are taken
  while other jobs share the machine; the load average is recorded with them. No falsifier.
- **Runtime.** < 20 min.
