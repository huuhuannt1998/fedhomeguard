# Predeclaration: max-flow decoder follow-up runs for the ISJ-GP paper

Written 2026-11-03 (~23:00Z), before any of these runs. PI: "I am back at home. Let's resume" (2026-11-03), after the
plan in [READY] (ISJGP) FedHomeGuard - P10/PAPER_PLAN.md ("Evidence still to run"). The decoder, certificate and
server/evaluation split are exactly those of predeclarations/maxflow_decoder_2026-11-03.md (SHA-256 662176bb...,
result RKA jrn_01M6HJ4A84B13NS1RFWTBQTV4Q); nothing about the method changes here.

## Runs (fresh partition seeds, never used before)
- R1 (control): N-BaIoT device-derived, 1-2 device types per household (the paper's setting), seeds 70-99, 10% server
  set.
- R2 (server-set size): IoT-23 device-derived 1-3, the primary seeds 70-99 already used, server sets of 0.5% and 1%
  (descriptive extension of the predeclared 2% and 10% arms).
- R3 (base rate): from the stored rows of the primary IoT-23 run and R1, certified detection rate (malicious rows
  certified alarm) and certified false-alarm bound (benign rows not certified benign) for P, A and D at m = 4,
  re-weighted to a 1% attack prior (precision lower bound = 0.01*cTPR / (0.01*cTPR + 0.99*cFPR), with cTPR the
  share of malicious rows certified alarm and cFPR the share of benign rows not certified benign). This needs
  per-class certified rates, so R3 re-runs the primary seeds with per-class output added (same decoder, same split).
- R4 (runtime): wall time of decoder learning and of certification per evaluation input at m = 0..4, from R2/R3 logs.

## Predictions
- F-R1: on N-BaIoT, D's beta* equals P's on at least 27 of 30 draws (plurality is already at the ceiling there), and
  median CA(D) - CA(P) at m = 4 is within +-0.01.
- F-R2: median CA(D) at m = 4 with a 1% server set is within 0.03 of the 10% result (0.873); at 0.5% it may fall,
  reported either way.
- F-R3: at a 1% prior and m = 4, D's certified precision lower bound exceeds P's on at least 20 of 30 IoT-23 draws.
  The paper's existing negative result (no certified configuration beats always-benign at a 1% prior) is restated
  for D in whatever direction this comes out.
- F-R4: median certification time per evaluation input at m = 4 below 10 ms.

## Decision
These runs complete the evaluation section; none can stop the paper. Each result is reported as found; nothing about
the decoder is re-tuned after any result is read.
