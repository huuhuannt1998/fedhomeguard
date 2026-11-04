# Predeclaration: the aggregator-agnostic competence ceiling

Written 2026-11-03, before the ceiling code was written or any ceiling was computed. PI: "Go" (2026-11-03), on the
proposal to turn FedHomeGuard into a theorem-plus-evidence paper on competence redundancy, after the failed gates of
the abstention, anomaly-vote and certified-anomaly tests (RKA jrn_01M6H1020SSWY0R5C1DKSXXTHY,
jrn_01M6H7F647WA77DFTM04ARBQPV, jrn_01M6HBW7DBCVJ32V38JR7WR7E7).

## Statement under test (k = 1, binary)
For a realised ensemble of K members, each input x has a member-output vector v(x) in {0,1}^K. Corrupting m clients
lets the adversary rewrite any c = c_max(m) coordinates. An aggregator g (ANY function of the output vector) certifies
x at m iff g(v') = y(x) for every v' within Hamming distance c of v(x). Lemma: two inputs with different labels can
both be certified only if their vectors differ in more than 2c coordinates. Ceiling: the largest number of test
inputs any aggregator can certify correctly equals the maximum-weight independent set of the bipartite conflict graph
on distinct output vectors (benign-labelled groups vs malicious-labelled groups, edge iff Hamming distance <= 2c,
weights = label counts), computed exactly as total weight minus a max-flow; an oracle aggregator attains it.
Corollary: if 2c >= K - n_const (n_const = members whose output is the same on every test input), no aggregator's
certified accuracy exceeds the constant predictor's.

## Data (no new training except CIC)
- IoT-23 main grid: the member bank's device-derived 1-3, k = 1 draws (40), and IID k = 1 (33) as control.
- CIC IoT-IDAD 2024 victim side, device-derived 1-3, k = 1, partition seeds 10-39 (the paper's JS01 arm B):
  members rebuilt with the paper's code path (common.member_predictions, JS01 config); plurality beta* must match the
  stored JS01 rows (results/jisa/js01_cic_victim_dd13.jsonl) on every draw before any ceiling is read.
- For each draw and m in {0, 1, 2, 3, 4, 6, 8}: ceiling certified accuracy CA_max(m) on the test split, its beta*_max
  (largest beta with CA_max > tau_triv), and plurality's and abstention's beta* (abstention as in
  abstain_feasibility_2026-11-03.md).

## Predictions
- T1 (sanity, every draw, every m): CA_max(m) >= plurality CA(m) and >= abstention CA(m); CA_max is non-increasing in m.
  A violation is a bug, not a finding.
- T2 (aggregation is not the bottleneck, IoT-23 main): among draws where plurality collapses at beta = 0.20, the
  ceiling also collapses (CA_max(4) <= tau_triv) on at least half.
- T3 (CIC IoT-IDAD): median beta*_max <= 0.30, i.e. even the oracle aggregator stays well below the 0.45 ceiling of
  members a single client controls, where the one-class count predicted the ceiling.
- T4 (control, IID k = 1): beta*_max = 0.45 on every draw.
- T5 (corollary check, IoT-23 main): on every draw with 2c >= K - n_const at m = 4, CA_max(4) <= tau_triv.

## Decision
T1 and T5 check the mathematics and the code. If T2 and T3 hold, the paper's thesis is "the limit is member
competence, provably, not the aggregation rule". If T2 fails (the ceiling is well above plurality and abstention), the
paper's thesis becomes the gap itself: a provable target for aggregators that current rules miss. Either outcome is
reported as found; nothing is re-tuned after any result is read.
