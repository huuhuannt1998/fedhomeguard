# Predeclaration: a max-flow certified decoder learned from a small labelled server set

Written 2026-11-03, before the decoder code was written or run. PI: "Go. Change the title if needed also"
(2026-11-03). Follows the competence-ceiling test (predeclarations/competence_ceiling_2026-11-03.md; result RKA
jrn_01M6HETF5NC3G448F8KCZMHE24: T2 failed, so the oracle ceiling is well above plurality and abstention, median
beta* 0.05 / 0.15 / 0.20 on the IoT-23 main grid). Theory: notes/competence_theorem.md.

## Method (fixed here)
- Members: the paper's k = 1 MLP members (common.member_predictions), N = K = 20, unchanged.
- Server set: the first 10% (in time order) of every device's test rows, with labels; the assumption is a small
  labelled clean sample at the server, as in FLTrust. Evaluation set: the remaining 90%. Nothing from the evaluation
  set is used to build the decoder.
- Decoder at m (c = c_max(m)): solve Theorem 1's max-flow on the server set's distinct output vectors; take the
  independent set from the min cut (left nodes reachable from the source in the residual graph, right nodes not
  reachable). g(v) = the label of a chosen vector within Hamming distance c of v, and 0 (benign) if there is none.
- Exact certification of g on an evaluation input x with label y: if y = 0, certified iff g(v(x)) = 0 and no chosen
  malicious vector lies within 2c of v(x); if y = 1, certified iff every vector within c of v(x) lies within c of some
  chosen malicious vector (ball enumeration).
- Arms on the same evaluation set: P (plurality), A (abstention, as before), D (decoder), MAX (Theorem 1's ceiling
  computed on the evaluation set itself; an oracle, upper bound only).
- m in {0, 1, 2, 3, 4}; beta* read on {0, ..., 0.20} (capped at 0.20 because ball enumeration grows quickly with c).

## Data (fresh draws, never used before)
- Primary: IoT-23 device-derived, 1-3 device types per household, partition seeds 70-99 (30 draws).
- Secondary: CIC IoT-IDAD 2024 victim side, device-derived 1-3, seeds 40-69 (30 draws).
- Descriptive: the same primary draws with a 2% server set instead of 10%.

## Predictions (primary, per-draw medians)
- D1: among draws where P collapses at m = 4 (CA <= tau_triv), D collapses on at most half.
- D2: CA(D) - max(CA(P), CA(A)) at m = 4 >= 0.03.
- D3: clean accuracy (m = 0) of D >= that of P - 0.02.
- D4 (sanity, every draw and m): CA(D) <= CA(MAX). A violation is a bug.
- Secondary (CIC): median CA(D) - max(CA(P), CA(A)) at m = 4 >= 0, reported in full.

## Decision
Build the method paper (theorem + max-flow decoder + evaluation) only if D1, D2 and D3 hold on the primary set. If
D1 or D2 fails, the paper is the theorem and the measured gap, with the decoder reported as a negative result.
Nothing is re-tuned after any evaluation result is read.
