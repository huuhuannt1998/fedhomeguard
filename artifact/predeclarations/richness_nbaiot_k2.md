# Predeclaration: device-richness sweep on N-BaIoT at k = 2

Written and committed BEFORE the runs. Completes the 2x2 (corpus x subsample size).

## What is already established

  IoT-23,  k=1   beta* spans 0.000 -> 0.450 across the richness grid
  IoT-23,  k=2   spans 0.000 -> 0.250 (its own ceiling), boundary moved left
  N-BaIoT, k=1   flat at 0.450, span 0.000 -- richness does nothing

The mechanism is that a member fails when it sees essentially one class. On
N-BaIoT device identity carries no label information, so no household is
single-class regardless of how few devices it holds.

## Prediction, fixed before running

  P1  N-BaIoT at k=2 is FLAT across the richness grid: span <= 0.05.
  P2  It sits at beta_geo(20,2) = 0.250 at every level, i.e. at its ceiling.
  P3  No cell exceeds 0.250.  [bug check, not a finding]

Note the asymmetry this tests. On IoT-23, k=2 CHANGED the picture: it moved the
boundary left, because pooling supplied classes a poor household lacked. If the
mechanism is right, k should do nothing on N-BaIoT, because there was nothing
missing to supply. A flat-at-ceiling result at both k on one corpus and a
k-dependent boundary on the other is the whole claim in one table.

## What each outcome means

- **P1 and P2 hold.** k matters only where class coverage is the binding
  constraint. The 2x2 is complete and the mechanism explains every cell.
- **P1 fails (k=2 varies with richness on N-BaIoT).** Something other than class
  coverage is driving the k dependence, and the explanation in Section 7 must be
  weakened to cover only IoT-23.
- **P2 fails but P1 holds (flat, below ceiling).** k=2 is leaving headroom on the
  table for a reason the mechanism does not predict; report the gap and do not
  claim the ceiling is reached.

## Protocol, fixed in advance

Same as predeclarations/richness_nbaiot.md: scripts/bstar.py, 30 draws per level,
k=2 with full enumeration (K = 190), beta grid 0 to 0.50 in 0.05 steps,
--clean-only, dph grid (1,1), (1,3), (2,5), (3,8), (5,9). No level dropped after
seeing its result.
