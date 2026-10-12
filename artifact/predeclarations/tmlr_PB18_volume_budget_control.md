# Predeclaration PB18: volume dial with a budget-scaled step count

Written 2026-10-10T16:34:24-0400 BEFORE the runs, for the TMLR revision (round tmlr5; mock review round 2, M5; coordinator priority 4). Not committed; dated by its RKA journal entry and SHA-256.

## Why
In the volume dial (PB04 arm c) four clients of s rows (s in {1000, 300, 100, 50, 20, 10}) lower median beta* from 0.450 to 0.250-0.300. Each member trains 15 rounds of one local epoch at batch 512, so a 20-row member takes 15 SGD steps while an equal-size member (about 6,661 rows) takes 210. The effect may be data scarcity or the fixed optimization budget.

## Protocol, fixed in advance
- The same 70 partitions as PB04 arm c (levels equal, 1000, 300, 100, 50, 20, 10; seeds 0-9; volume_dial in scripts/pb04_partitions.py), k = 1, K = 20 less clients under 16 rows, exact certification, beta grid 0-0.50, tau_triv = 0.7300.
- Budget-scaled members: client i trains E_i = ceil(14 / b_i) local epochs per round, where b_i = ceil(n_i / 512) is its number of batches per epoch and 14 is that of an equal-size client; everything else as in the paper (15 rounds, SGD lr 0.05, momentum 0.9, batch 512, seed 0). Clients of at least 6,657 rows keep E = 1, so the 'equal' level reproduces PB04 exactly (control).
- Per level: median beta*, median vote margin, the small members' clean accuracy.
- **Prediction (undertraining reading):** at levels 20-300 the budget-scaled median beta* is at least 0.40. **Falsifier (data-scarcity reading):** median beta* at most 0.30 at two or more of those three levels. Either outcome is reported.
- Runtime: 70 ensembles of 20 members, under 10 min.
