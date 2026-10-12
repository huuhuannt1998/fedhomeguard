# Predeclaration PB15: Label-aware pairing at k = 2 (the CARVY-FL contrast with class coverage as the grouping target)

Written 2026-10-10T14:56:23-0400 BEFORE the runs, for the TMLR revision (round tmlr4; mock review item N4; coordinator item 8). Not committed; dated by its RKA journal entry and SHA-256.

## Why
The paper's grouping contrast (e26) pairs households to span device types; the coverage reading predicts that pairing to span classes is what helps.

## Protocol, fixed in advance
- IoT-23 device-derived draws of the main grid (1-3 device types per household, seeds 10-39, the e26 draws), N = 20, k = 2 with K = 20 pairs forming one cycle (2-regular, as e26), exact c_max on the realised pairs, beta grid 0 to 0.50 in steps of 0.05.
- Arms: *label-aware*: the cyclic order maximising the sum over adjacent pairs of the smaller class share of the pair's pooled rows (multi-start greedy, 12 restarts, then 2-opt, seeded by the draw seed; ties broken by device-type span); *random*: `grouping.random_cycle` re-run through the same script (a check against e26).
- *Prediction (coverage reading).* Label-aware median beta* >= 0.15 and fewer draws collapsing at beta = 0.20 than random. *Falsifier.* Label-aware median beta* <= 0.100 (random's e26 value).
- Threat-model cost, stated with the result: the rule needs each client's class shares, which a malicious client can misreport to steer the draw; the certificate assumes no adversarial influence on the subsets.
- **Runtime.** 60 runs x 20 two-client members; under 15 min.
