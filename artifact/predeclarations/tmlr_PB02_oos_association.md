# Predeclaration PB02: Out-of-sample association of beta* with coverage, volume, margin and divergence

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Question.** How much of the variation in normalised beta* is associated with member-level class
  coverage, volume skew, vote margin and generic divergence, when evaluated out of sample with draws
  as groups? No causal claim.
- **Data.** `results/analysis/instruments.jsonl` (318 cells = 159 draws x k in {1,2}; 7 families over
  IoT-23 and N-BaIoT) joined to each cell's clean mean vote margin from the canonical rows (join keyed
  on dataset, family, seed, alpha, k and checked by equality of S_JS).
- **Predictors, one at a time.** Coverage: minClassSup, fracDegen. Volume: minSizeShare. Divergence:
  S_JS, S_dev, S_lab. Post-training reference (not a pre-training signal): mean vote margin.
  Also two-statistic: minClassSup + minSizeShare.
- **Model.** Per-k isotonic regression of normalised beta* on the statistic (direction fixed by the sign
  of its pooled Spearman rho in the paper's Table 11); the two-statistic model is a monotone-constrained
  `HistGradientBoostingRegressor` (max_depth 2, 100 iterations).
- **Evaluation.** (i) GroupKFold, 10 folds, group = draw (k=1 and k=2 cells of one draw never split);
  (ii) leave-one-family-out (7 folds). Metrics: out-of-fold R^2, MAE (normalised units) and Spearman
  rho of prediction vs truth; 1,000-replicate draw-level bootstrap CIs on the OOF metrics.
- **Expected.** Coverage statistics > divergence statistics under both schemes; margin best; S_JS
  transfers worst across families.
- **Falsifier.** Under GroupKFold, the best divergence statistic's OOF R^2 is within 0.05 of, or above,
  the best coverage statistic's.
- **Runtime.** < 5 min.
