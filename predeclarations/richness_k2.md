# Predeclaration: device-richness sweep at k = 2

Written and committed BEFORE the runs.

## Why

The richness boundary is measured at k = 1 only, where a member trains on a
single household. A reviewer can reasonably ask whether the boundary is a
property of the federation or an artifact of single-household members. k = 2 is
the cheapest test that separates those.

## What the mechanism predicts

The paper's mechanism is that a member fails when it sees essentially one class.
A k = 2 member trains on the union of two households, so it sees the union of
their device types. Pooling should therefore supply exactly what a device-poor
household lacks, and the boundary should move LEFT -- certification should become
available at a lower richness than it does at k = 1.

Against that, Corollary 1 lowers the ceiling: beta_geo(20,1) = 0.450 but
beta_geo(20,2) = 0.250. So raising k buys agreement and spends headroom, and the
two must be compared on the normalised quantity beta* / beta_geo(20,k), not on
raw beta*.

**Predictions (fixed before running).**

  P1  At 1-3 device types, normalised beta* is HIGHER at k = 2 than at k = 1.
      (Pooling supplies classes a poor household lacks.)
  P2  At 2-5 types and above, both k reach at least 0.8 of their own ceiling.
      (Above the boundary, k stops mattering.)
  P3  Raw beta* at k = 2 never exceeds beta_geo(20,2) = 0.250 at any richness
      level. (A violation would indicate a bug in the certificate, not a finding.)

## What each outcome means

- **P1 and P2 hold.** The boundary is a property of how many classes a MEMBER
  sees, not of how many a household holds, and a deployer facing device-poor
  homes has a lever: raise k, and pay for it in ceiling. That is a deployment
  recommendation the paper does not currently make.
- **P1 fails (k = 2 no better at 1-3 types).** Pooling does not supply the missing
  classes, so the mechanism is about household composition in a way the current
  statement does not capture, and the "one class per member" explanation needs
  narrowing.
- **P3 fails.** Treat as a defect in the certificate or the estimator and
  investigate before reporting anything else.

## Protocol, fixed in advance

- Same code path and estimator (scripts/bstar.py), 30 partition draws per level,
  beta grid 0 to 0.50 in 0.05 steps, --clean-only, full enumeration at k = 2
  (K = 190 of 190).
- Same richness grid as k = 1: dph = (1,1), (1,3), (2,5), (3,8), (5,10) on IoT-23.
- No level dropped after seeing its result.
