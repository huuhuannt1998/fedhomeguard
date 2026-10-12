# Predeclaration PB05: Falsifier for "class coverage per member explains the small-k decline"

Written 2026-10-08T15:24:18-04:00 BEFORE the runs, for the TMLR revision of the paper (executor, task plan `TMLR_Executor_Improvement_Plan.md`, Paper 2). Not committed: the task forbids commits, so this file is dated by its RKA journal entry and its SHA-256, recorded in `TMLR_Revision/paper2/reproduction_log.md`. Master copy: `TMLR_Revision/paper2/experiment_matrix.md`.

## Conventions

tau = majority-class share of the evaluated test split (IoT-23 0.7300,
N-BaIoT 0.9001). beta* = largest beta on the run's own grid with certified accuracy CA > tau (0 if
none). Normalised beta* = beta* / beta_geo(20,k). "Draw" = one partition seed of one construction.
Grid step = 0.05 (= 1/N at N = 20). Members are the repository's 1,586-parameter MLPs trained by
`fl_run` (15 rounds, seed 0), exactly as in `scripts/exp_e2.py`.

## Protocol, fixed in advance

Pre-stated triggers; the claim is reported as **falsified** if any fires, **not falsified** otherwise:
(i) PB04a median k=1 beta* <= 0.15 with fracDegen = 0; (ii) PB03 fails its accuracy criterion on
IoT-23 device-derived draws; (iii) PB01d family margin difference after coverage matching >= +0.1509;
(iv) PB04b MAL-only j = 8 median beta* >= 0.35. Volume skew is a known separate route (b) and does not
count against the claim unless it also fires (i)-(iv). No new runs.
