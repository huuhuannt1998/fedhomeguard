# Predeclaration: feasibility of coverage-gated (abstaining) partition aggregation

Written 2026-11-03, before any abstention result was computed. PI go: "Go" (2026-11-03), after the JISA desk
reject and the ARC novelty search (AutoResearchClaw/runs/fedhomeguard-novelty, direction H2 as corrected).

## Question
Does letting one-class members abstain, with a certificate that stays sound, raise the certified breakdown point
beta* enough to carry a new paper? This is a go/no-go check, not a paper result.

## Data (no training, no new runs)
The existing member bank, results/tmlr_rev/member_bank/ (IoT-23 only; each file passed a reproduction check against
the published rows when built). Test labels from runner.prepare (the same function the bank was built with).
- Main: device_derived, 1-3 device types per household, k = 1, K = 20 (all draws in the bank).
- Control: iid, k = 1, K = 20.
- Descriptive only: device_derived device-type sweep (1-1, 2-5, 3-8, 5-10) at k = 1; device_derived and iid at
  k = 2, K = 190.

## Rule (fixed here)
A member abstains on every input if the minority-class share of its training data is below 0.05 (the paper's
"more than 95% malicious or benign"). For k >= 2 its training data is the union of its clients, so the share is the
size-weighted malicious fraction over its clients (client_sizes, client_mal_frac in each bank JSON).

## Certificate (fixed here)
Votes are counted over non-abstaining members only; margin = top count minus runner-up count. A test point is
certified at m malicious clients iff margin > 2 * c_max(m), with c_max over ALL K members (exactcert.c_max_table,
unchanged). Soundness: a corrupted member can change its contribution from any state (abstain, or a vote) to any
other, which moves any top-minus-other difference by at most 2; honest members' abstention depends only on their own
clients' data, so the adversary cannot change it except through members it already corrupts (counted in c_max).
Prediction = argmax over voters (ties to class 0, as now). No voters = not certified. beta* = largest beta in
{0, 0.05, ..., 0.5} with certified accuracy CA > tau_triv (the constant majority-class predictor), as in the paper.
Plurality is recomputed from the same bank with exactcert.certify_exact and must match each file's stored beta_star.

## Predictions
- P1 (main): median per-draw gain in beta* (abstention minus plurality) >= 0.10.
- P2 (main): draws collapsing at beta = 0.20 (CA <= tau_triv) fall to at most half the plurality count.
- P3 (control, iid k = 1): beta* changes on at most 10% of draws.
- P4 (no harm, main): beta* falls on at most 10% of draws, and median clean ensemble accuracy (beta = 0, no
  adversary) drops by at most 0.01.
- P5 (idealized model, main, reported either way): if two-class members vote correctly and one-class members
  abstain, beta*_abst = (ceil((20 - n1)/2) - 1)/20 with n1 the number of one-class clients; within one grid step on
  >= 80% of draws.

## Decision
Build the paper around coverage-gated aggregation only if P1, P2 and P4 hold. If P1 fails, abstention alone is not
a paper and the next candidate is H1 (certified federated anomaly detection). Every outcome is reported as found.
