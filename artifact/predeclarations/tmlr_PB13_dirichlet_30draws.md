# Predeclaration PB13: Device- vs label-Dirichlet contrast on 30 independent draws per concentration

Written 2026-10-10T14:56:23-0400 BEFORE the runs, for the TMLR revision (round tmlr4; mock review item M2; coordinator item 2). Not committed (commits are forbidden); dated by its RKA journal entry and SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`.

## Why
The paper's device-vs-label contrast rests on 3 draws per concentration (Table 2) and 16 matched pairs that reuse 10 device-family draws; its primary test changed after an exact signed-rank p of 0.0625. This run replaces it with one test fixed in advance on independent draws.

## Protocol, fixed in advance
- IoT-23, N = 20, k = 1 (full enumeration, K = 20 less any client below 16 rows), the repository's members (`fl_run`, 15 rounds, seed 0), beta grid 0 to 0.50 in steps of 0.05, tau_triv = 0.7300. Partitions built by `partition.build` exactly as in `scripts/exp_e2.py`.
- Families: label-Dirichlet (`dirichlet`) and device-Dirichlet (`dirichlet_device`); alpha in {1, 0.5, 0.2, 0.1}; partition seeds 100-129 (30 new draws per family and alpha, disjoint from seeds 0-2 of Table 2). 240 runs.
- Per draw: mean k=1 vote margin over test flows, beta*, S_JS, S_dev, fracDegen, minClassSup, K.
- **Primary test.** The matched levels of Table 2: device-Dirichlet alpha = 0.5 against label-Dirichlet alpha = 0.2 (closest mean S_JS in Table 2). Statistic: difference in mean k=1 vote margin (device minus label) over the 30 + 30 independent draws. Two-sided permutation test (100,000 random relabelings, seed 0), alpha = 0.05. *Prediction (paper).* Difference > 0 with p < 0.05. *Falsifier.* Difference <= 0, or p >= 0.05; either is reported as weakening the claim.
- **Secondary, fixed in advance.** (S1) the same test on beta*. (S2) device alpha = 0.1 (the largest device-support divergence) against label alpha = 0.2, margin, same test. (S3) Coverage adjustment over all 240 draws: OLS of margin on a family indicator, fracDegen and S_JS; the family coefficient with a 95% bootstrap CI (10,000 resamples of draws, seed 0). *Coverage reading predicts* a family coefficient much smaller than the raw primary difference; *falsifier for the coverage reading:* family coefficient >= 0.10 with a CI excluding 0.
- Sensitivity only: the paper's 16-pair rule is not re-run here; it stays as reported, labelled as superseded by this test.
- **Runtime.** About 240 x 20 member trainings; under 20 min on 6 workers.
