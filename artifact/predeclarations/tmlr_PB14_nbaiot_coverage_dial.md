# Predeclaration PB14: Coverage dial on N-BaIoT (a class-coverage test that needs no device identity)

Written 2026-10-10T14:56:23-0400 BEFORE the runs, for the TMLR revision (round tmlr4; mock review item N3; coordinator item 7). Not committed; dated by its RKA journal entry and SHA-256.

## Why
The N-BaIoT result supplies only the null side of the mechanism. The count of one-class members needs only labels, so it can be tested positively on N-BaIoT by making clients one-class.

## Protocol, fixed in advance
- N-BaIoT (nine devices, the paper's split and preprocessing, tau = 0.9001), N = 20, k = 1, the repository's members, beta grid 0 to 0.50 in steps of 0.05.
- From the IID partition (seeds 0-4), make j clients one-class by exchanging rows within class, client sizes fixed (the PB04b construction, `scripts/pb04_partitions.py:coverage_dial`). Cells: MAL-only j in {0, 2, 4, 6, 8}; symmetric j = 2 (one MAL-only, one BEN-only client). 30 runs. A cell that the benign rows cannot supply is reported as infeasible, not replaced.
- *Prediction (count of one-class members).* beta* = (9 - max(n_mal, n_ben))/20: 0.45, 0.35, 0.25, 0.15, 0.05 for MAL-only j = 0, 2, 4, 6, 8; 0.40 for symmetric j = 2.
- *Falsifier.* The median observed beta* differs from the prediction by more than one grid step in >= 2 of the 6 cells. Per-draw exact and within-one-step shares are reported.
- **Runtime.** 30 x 20 member trainings on N-BaIoT; under 45 min on 3 workers.
