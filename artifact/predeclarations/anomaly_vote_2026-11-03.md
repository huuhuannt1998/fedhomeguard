# Predeclaration: one-sided anomaly votes for benign-only members (coverage-gated aggregation, round 2)

Written 2026-11-03, before any code for this test was run. PI: "Go ahead" (2026-11-03). Follows the abstention
feasibility check (predeclarations/abstain_feasibility_2026-11-03.md; result RKA jrn_01M6H1020SSWY0R5C1DKSXXTHY:
P1 held, P2 failed) and the H1 theory check (RKA jrn_01M6H1J99Z299GV8WWY2VZJW27). The certified-detection gain
seen there (median certified malicious detection at beta = 0.20 from 0.000 to 0.791) was post hoc; this test is
the predeclared check of it, on partition draws never used before.

## Rule under test (three aggregation arms on the same members)
- P (plurality): every member votes its predicted class. The paper's current construction.
- A (abstention): members whose training data has minority-class share < 0.05 abstain on every input; the rest vote.
- V (anomaly votes): as A, except each benign-only member (minority share < 0.05, majority benign) votes
  "malicious" on an input whose reconstruction error under its own autoencoder exceeds its own threshold, and
  abstains otherwise. Malicious-only members abstain, as in A.

Two-class members are the paper's MLP members, built with the paper's own code path (scripts/tmlr_rev/common.py:
member_predictions, unchanged). Each benign-only member's autoencoder is trained only on that household's own rows,
without labels: layers d-32-8-32-d with ReLU, Adam lr 1e-3, batch 256, 30 epochs, torch seed 1000*draw_seed +
client index, on the paper's standardized features; threshold = 99th percentile of its own training reconstruction
errors. Nothing about the AE is tuned after this file is hashed.

## Certificate (unchanged from the abstention check)
Votes counted over non-abstaining members; margin = top count minus runner-up count; certified at m malicious
clients iff margin > 2 * c_max(m), c_max over all K members (exactcert.c_max_table). Sound because a corrupted member
moves any top-minus-other difference by at most 2 whatever it does, and an honest member's vote or abstention
depends only on its own household's data. Ties to class 0; no voters = not certified. k = 1, N = 20, K = 20.

## Data
- Primary (held out): IoT-23, device-derived households with 1-3 device types, partition seeds 40-69 (30 draws, never
  used in any earlier run or analysis).
- Secondary: IoT-23 1 device type per household, seeds 0-29 (existing bank); CIC IoT-IDAD 2024 victim side,
  device-derived, 1-3 device types, seeds 0-29 (the paper's JS01 construction); N-BaIoT device-derived, seeds
  0-29 (control: no one-class households expected).

## Metrics (at beta = 0.20, m = 4, unless stated)
CTR_mal (malicious test flows predicted malicious and certified, over all malicious flows); CTR_ben (same for benign);
CA and collapse (CA <= tau_triv, the constant majority-class predictor); beta* on the 0.05 grid; clean TPR and FPR
(no adversary, beta = 0).

## Predictions (primary set, per-draw medians over 30 draws)
- V1: CTR_mal(V) - CTR_mal(P) >= 0.50.
- V2: collapse count at beta = 0.20 under V <= half of P's.
- V3: beta*(V) - beta*(P) >= 0.10.
- V4 (cost): CTR_ben(V) >= CTR_ben(P) - 0.10, and clean FPR(V) <= clean FPR(P) + 0.02.
- V5 (V beats A): CTR_mal(V) >= CTR_mal(A), and V's collapse count <= A's.
Secondary: N-BaIoT, V changes beta* on <= 10% of draws; IoT-23 1-type and CIC IoT-IDAD reported in full, with the
prediction that V's collapse count is below P's on each.

## Decision
Build the next paper around anomaly-vote aggregation only if V1-V4 hold on the primary set. If V1 or V3 fails, the
FedHomeGuard line stops producing a new method and the PI decides between a workshop version and shelving.
Every outcome is reported as found; nothing is re-tuned after the primary results are read.
