# Predeclaration PB10: Member-level worst-case attack (limited adaptive attack)

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **Question.** The paper's slack G is an upper bound because attacked accuracy uses five published
  attacks. The certificate's own threat model lets every touched member output anything. How far is
  certified accuracy from the exact worst case of that model?
- **Adversary models.** M1 (worst case of the certificate's model): every touched member outputs the
  wrong class on every flow; ties resolve as the repository's argmax does (class 0). M2 (realisable at
  k = 1): each touched member outputs the negation of its clean twin (a malicious household can train
  honestly on its own data and flip the output layer).
- **Computation.** From banked clean member predictions: for each budget m, accuracy under M1/M2 for
  (i) the paper's three random malicious sets (seed 1000 + s) and (ii) the adversary's best malicious
  set, by exhaustive enumeration of all C(20, m) sets where C(20,m) x K x (distinct flow patterns)
  <= 5e10, otherwise by greedy + 2,000 random sets (reported as a search, i.e. an upper bound on the
  worst-case accuracy). Also the per-flow exact certificate n1 - n2 > 2 a1* (a1* from P0) vs Eq. (1).
- **Ensembles.** Bank A (IoT-23 draws 0-2, IID and device-derived, k = 1, 2, 3 sampled and full) and
  bank B (e5f, 30 + 30 draws, k = 1; k = 2 where enumerable).
- **Expected.** Soundness: worst-case accuracy >= CA everywhere. IID k <= 2 within the ceiling:
  worst-case minus CA small (<= 0.005); device-derived larger; beyond the ceiling worst-case accuracy
  near or below tau.
- **Falsifier (paper's "nearly exact under IID partitions").** Median over draws of (best-B M1
  accuracy - CA) > 0.01 in any IID cell within the ceiling at k <= 2. **Stop condition.** Any M1
  accuracy below CA (a soundness violation).
- **Runtime.** < 1 h.
