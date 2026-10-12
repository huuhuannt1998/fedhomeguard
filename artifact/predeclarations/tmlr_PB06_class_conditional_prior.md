# Predeclaration PB06: Class-conditional certified detection, certified benign rate, prior re-weighting (post hoc)

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Data.** e5f (30 draws per partition, k in {1,2}, 11 budgets); corrected e2 rows (3 draws x 3
  malicious sets, k in {1,2,3}).
- **Outputs.** Median and IQR over draws of CTR_mal and CTR_ben per (partition, k, beta); re-weighted
  CA_pi = pi CTR_mal + (1 - pi) CTR_ben for pi in {0.5, 0.1, 0.01, 0.001} against the floor
  max(pi, 1 - pi); void cells (threshold >= 1) counted separately from the denominator.
  Prior-free breakdown points per draw: beta*_bal = largest beta with 0.5 (CTR_mal + CTR_ben) > 0.5,
  and beta*_pi = largest beta with CA_pi > max(pi, 1 - pi) for pi = 0.01 and 0.1.
- **Labelling.** All re-weighted numbers are marked post hoc; they assume class-conditional certified
  rates do not change with the prior.
- **Expected.** IID beta*_bal = beta*; beta*_{0.01} = 0 on every draw. No falsifier (descriptive).
- **Runtime.** < 1 min.
