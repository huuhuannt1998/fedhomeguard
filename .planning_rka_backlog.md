# RKA backlog — queued while the MCP transport was down (2026-08-31)

Six records to write once `/mcp` reconnects. Each is stated so it can be pasted
into `record_note` / `record_decision` without rework.

## 1. finding — real federated stack (threat model)
tags: threat-model, flower, docker, launchability, protocol-conformance
The paper defined the adversary abstractly and implemented attacks as tensor
arithmetic in one process, so it could not answer how an adversary launches one.
docker/ now holds a real Flower 1.23 deployment: stock server, one container per
household over gRPC, 0.4 CPU / 300 MB each. Households are exported through
runner.prepare(), the same code path and seeds as the simulation, so both arms
train on identical partitions.
Measured, 32 matched cells, 9600 contributions:
  * arms agree: median |delta| 0.0010, 26/32 within 0.01
  * every contribution, honest or compromised, is protocol-identical: same
    shapes, float32, all finite, one message size (7112 bytes)
  * the attacker's whole diff is 72 lines subclassing the honest client; server
    untouched, no protocol rule broken
  * an L1 server cannot separate them by update norm: malicious update_l2 sits
    inside the honest range, and that range is wide BECAUSE of device skew
    (IID households 6661 records each; device-derived 31 to 19515)
Heterogeneity is therefore doubly harmful: it breaks certification and
simultaneously destroys norm-based anomaly detection.

## 2. finding — the simulation over-granted attacker knowledge
tags: threat-model, white-box, F3, correction
malicious_update() is HANDED the other clients' updates. A single compromised
household never sees those; Flower delivers only the global model. So IPM and
ALIE as implemented were not launchable as written. The container client instead
solves the previous round's FedAvg for the honest mean, which a client genuinely
has. This converts "assume white-box" into a stated mechanism.

## 3. finding — EA was read at the final round of an oscillating process
tags: methodology, EA, correction
Under label-flip the global model oscillates with a ~2-round period, swinging
0.27 to 0.98 between adjacent rounds. Final-round accuracy samples an arbitrary
phase; two faithful implementations of the same experiment differed by 0.16 for
that reason alone. EA is now the worst round in an 8-round window. K was chosen
by stopping-round sensitivity, NOT by preference: final 0.0234, K=3 0.0051,
K=5 0.0231, K=8 0.0010, and every round in the K=8 window is past convergence
(reached by round 4). My initial K=5 recommendation was wrong and the data
overruled it. The certified arm is insulated: ensemble_votes defaults to
window=False and is bit-identical, verified by test.

## 4. finding — fl_run was not reproducible (pre-existing, more serious)
tags: reproducibility, rng, artifact-claim, correction
fl_run seeded its own generator but build_model drew initial weights from the
GLOBAL torch RNG, so two identical calls disagreed. Measured run-to-run spread:
mean 0.1127, max 0.6951. Worst cell (device_derived, beta=0.40, alie):
[0.27, 0.9651, 0.27, 0.27, 0.27]. Since 0.27 = 1 - tau_triv the ensemble
collapsed to INVERTED prediction in four of five draws.
This is not noise. It is the same bimodality Section VII already documents. The
paper correctly refuses point estimates for certified accuracy and reports
collapse rates with intervals, then reports the empirical arm as a point
estimate. The unseeded init disguised that inconsistency.
The artifact claims it "regenerates every number, table and figure"; before this
fix it could not. Weights now come from fl.seed with the caller's RNG stream
restored.

## 5. correction to my own earlier report
tags: self-correction
I told the PI the certified arm was unaffected. That is true of the windowing
change (verified bit-identical) and FALSE of the determinism fix, which moves
initial weights and therefore every trained model, certified and empirical
alike. Scope was corrected before any compute was spent, and the PI approved the
full re-run on the corrected scope.

## 6. decision — full re-run under the corrected substrate  (decided_by: pi)
question: Re-run everything under the seeded initialisation and windowed EA, or
  keep the windowing change alone?
chosen: full re-run
rationale: PI approved after being shown that the determinism fix moves the
  certified arm too. Beyond reproducibility it removes initialisation as a
  confound, so member disagreement is attributable to the partition alone --
  which is the mechanism the paper argues for. Pre-change results preserved in
  results/pre_determinism_fix/ (59 files) so the correction is reported as a
  measured delta via scripts/compare_rerun.py, not a silent replacement.
