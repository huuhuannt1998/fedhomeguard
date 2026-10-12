# Predeclaration PB04: One-factor-at-a-time controlled partitions (new training runs)

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

All arms use every IoT-23 training row (total data fixed), N = 20, the repo's member training, k = 1
full enumeration; k = 2 (full, K = 190) on 5 draws per cell where stated. beta grid 0 to 0.50 step 0.05.

- **PB04a. Coverage-repaired device-derived.** For each e5f device-derived seed (10-39) build a
  partition with the same construction (1-3 capture types per household, each type's rows split evenly
  among its owners) but resample any household whose malicious share falls outside [0.05, 0.95]
  (iterating to a fixed point, <= 500 passes, seeded by the draw seed); report the realised types per
  household, S_JS, S_dev, fracDegen. Compare with the paper's device-derived draws of the same seeds.
  *Prediction (coverage reading).* median k=1 beta* >= 0.35 and collapse at beta = 0.20 <= 0.20, with
  S_JS still >= 0.6. *Falsifier.* median k=1 beta* <= 0.15 despite fracDegen = 0.
- **PB04b. Coverage dial at fixed volume and device mix.** From the IID partition (seeds 0-9), make j
  clients one-class by exchanging rows within class (client sizes equal to +-1 row; within-class device
  mix preserved in expectation). Variants: symmetric (j/2 MAL-only, j/2 BEN-only; j in {0,2,4,6,8}) and
  MAL-only (j in {2,4,6,8}). CVM predictions (K = 20, k = 1): symmetric beta* = (9 - j/2)/20 =
  0.45, 0.40, 0.35, 0.30, 0.25; MAL-only beta* = (9 - j)/20 = 0.35, 0.25, 0.15, 0.05. fracDegen is the
  same for both variants at equal j. *Falsifier (CVM).* observed median beta* differs from the
  prediction by more than one grid step in >= 2 of the 9 cells. *Falsifier (coverage reading).* MAL-only
  j = 8 median beta* >= 0.35. k = 2 on 5 draws per cell, descriptive.
- **PB04c. Volume dial at full coverage.** IID composition; 4 "small" clients of s rows each (random
  rows, so both classes in expectation), the other 16 share the rest equally; s in {equal, 1000, 300,
  100, 50, 20, 10}; 10 draws each. s = 10 is below the 16-row training minimum, so those members are
  dropped (K = 16). *Prediction (paper's claim that very small clients lower beta*).* median beta*
  falls as s shrinks among trainable s. *Alternative (member-drop mechanics).* beta* stays at 0.45 for
  every trainable s and drops to 0.35 only at s = 10, where K = 16 forces m < 8 even for unanimous
  votes. *Falsifier (paper's reading).* median beta* = 0.45 at every s >= 20.
- **Runtime.** a: ~60 k=1 ensembles; b: 90 k=1 + 45 k=2; c: 70 k=1. Estimated <= 1.5 h wall on 6
  workers under the current machine load.
