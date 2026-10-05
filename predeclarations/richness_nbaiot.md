# Predeclaration: device-richness sweep on N-BaIoT

Written and committed BEFORE the runs. Recorded so the result cannot be
reinterpreted after the fact.

## Why

The paper's headline is now a conditional positive: client-count certification
holds once households own more than a couple of device types. That rests on one
corpus (IoT-23), with synthetically assigned households, at k=1. Replicating the
sweep on a second corpus would add a data point. Predicting its OUTCOME from the
paper's own mechanism, and being wrong if the mechanism is wrong, tests it.

## The mechanism, and what it predicts

The paper attributes the device-derived collapse to device identity predicting
the label: a household holding one device type holds one class, its member
learns a near-constant predictor, and a plurality certificate has no
disagreement to measure. Mutual information between device and label is
I = 0.32 bits on IoT-23 and I = 0.005 bits on N-BaIoT.

If that mechanism is correct, then on N-BaIoT device richness is IRRELEVANT:
assigning a household one device type or ten changes which devices it holds but
not which classes, so competence and beta* should not move with richness.

**Prediction (stated before running).** On N-BaIoT, sweeping devices-per-household
over the same grid as IoT-23 (1, 1-3, 2-5, 3-8, 5-10) leaves beta* flat, at or
near the geometric ceiling beta_geo(20,1) = 0.450, at every level. Concretely:

  P1. max beta* - min beta* across richness levels <= 0.05 (one grid step).
  P2. no richness level collapses on a majority of draws at beta = 0.20.
  P3. by contrast, the IoT-23 sweep spans 0.000 to 0.450 across the same grid.

## What each outcome means

- **Prediction holds.** Richness is not a general property of federated IoT IDS;
  it is the visible face of device->label coupling. The conditional claim
  generalises as a mechanism rather than as a curve fitted to one corpus, and
  the deployer's question becomes "does device identity predict the label in my
  traffic?", which is measurable before training.
- **Prediction fails (beta* moves with richness on N-BaIoT too).** The mechanism
  is wrong or incomplete: richness would then matter for a reason other than
  label coupling, and the paper's explanation must be withdrawn and the
  conditional claim restated as an empirical regularity on IoT-23 only.
- **Partial (moves, but far less than on IoT-23).** Report both spans and state
  that coupling explains most but not all of the effect.

## Protocol, fixed in advance

- Same code path, same estimator (scripts/bstar.py), 30 partition draws per
  level, k=1, beta grid 0 to 0.50 in steps of 0.05, --clean-only.
- Same richness grid as IoT-23: dph = (1,1), (1,3), (2,5), (3,8), (5,10).
- N-BaIoT has 9 devices, so (5,10) is capped at 9; recorded as such.
- No level is dropped after seeing its result. If a level cannot be built
  (too few devices), that is reported, not silently omitted.
