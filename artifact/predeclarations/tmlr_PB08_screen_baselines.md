# Predeclaration PB08: Coverage screen against simple alternatives, with draw-level splits

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Data.** e5f rows (660 decision cells = 30 draws x {IID, device-derived} x 11 budgets; choices
  k in {1,2}) and per-draw partition statistics rebuilt from the partitions.
- **Screens** (each commits to the largest feasible k it accepts, else refuses): S-cov, the paper's
  label-free coverage rule (factor 1.05 fixed, and the factor selected on development draws from
  {1.00,1.02,1.05,1.08,1.10,1.15,1.20}); S-cov1.00 (no safety factor); S-geo (ceiling only);
  S-refuse; S-div (accept iff S_JS <= t); S-vol (accept iff minSizeShare >= t); S-lab-sup
  (minClassSup >= t) and S-lab-deg (fracDegen <= t), which need labels and are not label-free.
- **Fitting.** Thresholds and factors are chosen on even seeds only (development) with the paper's
  lexicographic rule (no unsafe commitment, then most agreements, then least mean regret, ties to the
  more conservative value); evaluated on odd seeds (held out); full-set numbers reported separately and
  labelled.
- **Metrics.** Commitments; unsafe commitments (committed k has CA <= tau); correct refusals; missed
  opportunities (refusal although some k has CA > tau); max and mean regret against hindsight;
  draws with >= 1 unsafe commitment; Clopper-Pearson 95% upper bounds per commitment and per draw.
  Prior dependence: re-run S-cov with the floor of a 1% attack prior (0.99) as tau.
- **Expected.** S-geo many unsafe commitments on device-derived draws; S-cov about 1; S-lab few;
  S-div/S-vol in between; S-refuse 0 unsafe and all opportunities lost; at the 1% prior S-cov refuses
  everything.
- **Falsifier (the screen adds information over simple label-free rules).** On held-out draws, S-div or
  S-vol has no more unsafe commitments and no more missed opportunities than S-cov.
- **Runtime.** < 1 min.
