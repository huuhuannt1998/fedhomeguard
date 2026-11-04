# Predeclaration: feasibility of certified anomaly-based federated intrusion detection

Written 2026-11-03, before any code for this test was written or run. PI: "Sounds good to me" (2026-11-03), on the
proposal to move FedHomeGuard from supervised partition-and-vote to anomaly detectors trained on each household's
benign traffic, with a threshold-vote certificate and a certified operating curve. Follows the failed gates of
predeclarations/abstain_feasibility_2026-11-03.md and anomaly_vote_2026-11-03.md.

## Construction (fixed here)
- Households: the paper's device-derived partitions, N = 20 (P.build via scripts/tmlr_rev/common.py), partition
  seeds 100-129 (30 draws, never used before). N-BaIoT with 1-2 device types per household (the paper's setting),
  CIC IoT-IDAD 2024 victim side and IoT-23 with 1-3.
- Members (k = 1): one autoencoder per household, trained only on that household's BENIGN training rows (the
  deployment assumption: a household trains on traffic it believes benign; poisoning is what the certificate covers).
  At most 5,000 rows per household (uniform sample, numpy seed 7 + 1000*draw + household). Layers d-32-8-32-d, ReLU,
  Adam lr 1e-3, batch 256, 20 epochs, torch seed 1000*draw + household. A household with fewer than 20 benign rows
  trains no member. Each member's threshold: the 0.99 quantile of its own training reconstruction errors.
- Vote: a(x) = number of members whose error on x exceeds their own threshold. Alarm iff a(x) >= t.
- Certificate at m malicious clients, c = c_max(m) over the realised members (exactcert.c_max_table; at k = 1,
  c = m): certified alarm iff a(x) - c >= t; certified no-alarm iff a(x) + c < t. Sound because a corrupted member can
  change only its own alarm bit and honest members' bits and thresholds depend only on their own households.
- Choosing t without attack labels: on a benign validation set (the last 10% of every household's benign training
  rows, in time order, held out from training), take the smallest t whose certified false-alarm rate (share of
  validation rows NOT certified no-alarm) is <= 0.01 at the given m.
- Reported on the test split: certified TPR (malicious test rows certified alarm) and certified FPR (benign test rows
  not certified no-alarm), plus clean TPR/FPR at the same t with m = 0.

## Predictions (medians over the 30 draws)
- F1 (N-BaIoT, m = 2, beta = 0.10): certified TPR >= 0.50 with certified FPR <= 0.02.
- F2 (N-BaIoT, m = 4, beta = 0.20): certified TPR >= 0.30 with certified FPR <= 0.02.
- F3 (CIC IoT-IDAD 2024, m = 2): certified TPR >= 0.30 with certified FPR <= 0.02.
- F4 (IoT-23, m = 2): certified TPR < 0.10 (flow features too weak for benign-only autoencoders; reported either way).
Also reported: the full certified operating curve (all t) at m in {0, 1, 2, 4}, and how many draws have an empty
curve (no t meets the false-alarm budget).

## Decision
Build the redirected paper on certified anomaly-based federated IDS only if F1, F2 and F3 hold (two corpora). If F1
or F2 fails, the direction stops. If only N-BaIoT works, the PI decides whether one corpus is enough. Nothing is
re-tuned after any test result is read.

## Deviation recorded 2026-11-03T18:15Z, before any of seeds 100-129 was run
A smoke test on seed 99 (outside the predeclared set) showed the members barely flag attacks (alarm rate 0-15% on
attack rows of their own devices). Cause: the members were fed the paper's globally standardized features, whose mean
and standard deviation are computed over the whole training split, attack traffic included -- statistics a household
that trains only on its own benign traffic could not compute. Change: each member standardizes its inputs with the
mean and standard deviation of its own benign training rows, on the raw features (DATA.load_dataset, same
train/test split as runner.prepare). With this change on seed 99, five members flag 73-100% of attack rows at about 1%
false alarms on their own devices and 5-39% on other households' devices. Nothing else changes: architecture,
epochs, thresholds, vote, certificate, t selection, seeds and predictions F1-F4 stay as written above.
