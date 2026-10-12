# Predeclaration PB07: Leakage, capture-identity shortcut, train/test capture overlap

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

- **PB07a. Exact duplicates.** P0 found (c) that 73.7% of IoT-23 test flows (84.8% malicious, 43.7%
  benign) have a byte-identical feature vector in the training rows. For the banked e5f ensembles
  (30 IID + 30 device-derived draws, k = 1 and 2) and the e2 ensembles, recompute CA, CTR_mal,
  CTR_ben, coverage and beta* on the deduplicated test subset (flows with no training duplicate),
  with tau recomputed on that subset. *Falsifier (IID tightness/positive case relies on memorised
  duplicates).* IID median k=1 beta* on the dedup subset < 0.45 or IID dedup CA <= tau_dedup at
  beta = 0.40. Also report the device-derived collapse rates on the dedup subset.
- **PB07b. Capture-identity shortcut.** (i) Capture-prior classifier: each test flow gets its capture's
  majority training label; accuracy vs tau and vs the IID ensemble. (ii) Capture identifiability:
  multinomial logistic regression and a centralised (32,16) MLP predicting the capture from the 31
  features (train rows -> test rows), test accuracy. Interpretation is descriptive: a high capture-prior
  accuracy means the IoT-23 binary label is largely predictable from capture identity.
- **PB07c. Capture overlap.** Record that every test capture is a training capture (by construction)
  and cite the existing leave-one-capture-out arm; no new LOCO runs.
- **Runtime.** < 15 min.
