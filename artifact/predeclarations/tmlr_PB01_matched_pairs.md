# Predeclaration PB01: Matched device-skew vs label-skew pairs: dependence, uncertainty, matching sensitivity

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Question.** The paper (b) reports, over 16 skew-matched draw pairs, a k=1 vote-margin advantage of
  device-support skew over label skew of +0.1509 (cluster-bootstrap 95% CI [+0.0439, +0.3136]) and a
  non-significant beta* advantage. P0 found (c) that 9 of the 16 pairs have label concentration
  alpha >= 3 (both families near IID, |margin difference| <= 0.0043) and 7 have alpha <= 1. Is the
  effect robust to draw-level dependence and to the matching rule, and does it survive conditioning on
  class coverage?
- **Data.** `results/canonical/e7_devskew.jsonl`, `e7_labelskew.jsonl`, k=1, K=20 draws only (the
  paper's rule; 21 device, 16 label draws), plus fracDegen / minClassSup recomputed by rebuilding each
  partition with `partition.measure_skew` (no training).
- **Analyses.** (a) Stratify the paper's 16 pairs: informative (label alpha <= 1) vs near-IID
  (label alpha >= 3); n, mean and sign of each difference. (b) Two-way draw-level bootstrap: resample
  label draws and device draws independently with replacement (10,000 reps), re-apply the paper's
  nearest-S_JS matching with tolerance 0.10 inside each replicate, recompute the mean margin and beta*
  differences; percentile 95% CI. (c) Matching sensitivity: tolerance 0.05 / 0.10 / 0.20;
  one-to-one matching without replacement (optimal assignment on |dS_JS|, pairs above tolerance
  dropped); matching on S_dev instead of S_JS. (d) Coverage conditioning: match on fracDegen
  (tolerance 0.05) and, separately, on minClassSup (tolerance 0.05) instead of S_JS.
  (e) Descriptive ANCOVA over all 37 eligible draws: margin ~ family + S_JS, with a draw bootstrap CI
  for the family coefficient.
- **Control.** Near-IID pairs (alpha >= 3) are the built-in null.
- **Expected.** (a) all 7 informative differences positive, near-IID ~0; (b) margin CI excludes 0,
  beta* CI may include 0; (c) sign stable; (d) family difference shrinks toward 0 when matched on
  coverage.
- **Falsifier (paper's margin claim).** Two-way bootstrap CI for the mean margin difference includes 0,
  or one-to-one matching reverses its sign. **Falsifier (coverage reading, feeds PB05).** Matched on
  fracDegen or minClassSup, the family margin difference stays >= the S_JS-matched value (+0.1509).
- **Runtime.** < 5 min, no training.
