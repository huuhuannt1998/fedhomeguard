# Predeclaration PB03: Coverage-vote model (CVM): an a-priori predictor of beta* from per-client label composition

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Question.** If one-class members are what breaks small-k certification, then beta* at k = 1 (and
  k = 2) should be predictable, before any training, from how many members are one-class of each class.
- **Model, fixed now.** Client i is trainable iff it holds >= 16 rows (the repo's `min_rows`); untrainable
  clients produce no member. A member's training data (union of its trainable clients) with malicious
  share q is MAL if q > 0.95, BEN if q < 0.05, else MIX. Assume MIX members vote correctly on every
  flow and one-class members vote their class on every flow. With K kept members, n_M MAL and n_B BEN
  members: benign flows are certified-correct at budget m iff K - 2 n_M > 2 c_max(m); malicious flows iff
  K - 2 n_B > 2 c_max(m) (c_max from the actual kept subsets). Predicted CA(m) = tau 1[mal ok] +
  (1 - tau) 1[ben ok]; predicted beta* = largest grid beta with predicted CA > tau. For k = 2 the same
  rule with pooled member composition and exact c_max.
- **Data.** Rebuilt partitions (no training) for every draw with observed beta*: IoT-23 e5f IID and
  device-derived (60), e11b device types per household (150), e7f/e7 label- and device-Dirichlet (42),
  e7 volume (15); N-BaIoT nb9 (60) and e21 (150); k = 2 from e5f, e22, e7f, e7 volume, nb9, e23.
  Each prediction uses the grid of the file it is compared with.
- **Metrics.** Exact-match rate, within-one-grid-step rate, MAE in grid steps, Spearman rho; per
  construction family; confusion of predicted vs observed collapse at beta = 0.20.
- **Expected.** Near-perfect on IID and N-BaIoT (all MIX -> ceiling); high on device-derived and label
  skew; misses on volume skew and on draws with confidently wrong mixed members.
- **Falsifier.** On IoT-23 device-derived draws at k = 1 (e5f + e11b, 180 draws), within-one-step rate
  < 0.70 or Spearman rho < 0.80.
- **Counterexample harvest (pre-stated classes).** CX1 high divergence, useful certificate
  (S_JS >= 0.8 and normalised beta* >= 0.8); CX2 modest divergence, failure (S_JS <= pooled median and
  normalised beta* <= 0.34); CX3 every client holds both classes (fracDegen = 0, minClassSup = 1) yet
  normalised beta* <= 0.67; CX4 high clean agreement on the wrong class (clean coverage >= 0.9 and
  CA <= tau at some budget), searched over all clean canonical rows.
- **Runtime.** < 10 min.
