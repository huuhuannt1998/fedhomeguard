# N-BaIoT outcome prediction, 2026-08-25 (exported project-log record)

Exported on 2026-10-03 from the project's internal research log, where it was written as a note.
The log stores a creation time and a last-update time for every record; for this record both are
2026-08-25T11:34:45Z, so it has not been edited since it was written. The log is internal to the
project: no external registry timestamped this prediction.

The first N-BaIoT results recorded in the same log came later the same day: the five-device arm,
and the nine-device certified arm in a record created 2026-08-25T14:59:41Z (five draws at k = 1 and
k = 2). The 30-draw nine-device results the paper reports were produced afterwards and re-run after
the determinism fix (Section 4).

Scope notes added on export (not part of the record): predictions P2-P4 are stated against IoT-23's
k = 1 figures (vote margin 0.4456, median beta* 0.050, collapse 0.26 at beta = 0 and 1.00 at
beta >= 0.30); the record makes no separate prediction for k = 2. The prediction was written on five
devices; P1 failed once all nine were used.

The record's text follows verbatim.

---

PREDECLARATION. Recorded BEFORE running any N-BaIoT federated experiment, so the prediction cannot be fitted to the outcome.

BACKGROUND. E7 retracted the paper's device-diversity mechanism. The corrected claim is that device-derived partitioning is damaging in IoT-23 because DEVICE IDENTITY PREDICTS THE LABEL there: per-device malicious rates run 0.000-0.971 and the mutual information between device and label is 0.3189 bits, 37.4% of the label entropy. Assigning whole devices to households therefore induces severe label skew, and label skew is what costs ensemble agreement.

THE NATURAL EXPERIMENT. N-BaIoT is constructed differently: the same Gafgyt/Mirai attack suite was executed against every device, so every device carries a similar mix of benign and attack traffic. Measured on the five devices we recovered intact (Danmini_Doorbell, Ecobee_Thermostat, Ennio_Doorbell, Philips_B120N10_Baby_Monitor, Provision_PT_737E_Security_Camera; 150,000 rows, 115 features):
  per-device P(malicious): 0.9091, 0.9091, 0.8333, 0.9091, 0.9091
  I(label; device) = 0.0042 bits of a 0.4690-bit label entropy = 0.9%
  tau_triv = 0.9000 (against IoT-23's 0.7300)
Device identity is therefore almost uninformative about the label here, where in IoT-23 it carries over a third of it.

PREDICTION. If the corrected mechanism is right, then on N-BaIoT:
  P1. The device-derived partition should reach a much LOWER S_JS than IoT-23's 0.845, because the label component of the joint device-by-label divergence is nearly absent.
  P2. The device-derived mean vote margin at k=1 should stay HIGH -- near the IID value -- rather than falling to IoT-23's 0.4456.
  P3. beta* under device-derived partitioning should approach the geometric ceiling, rather than collapsing as it does on IoT-23 (median 0.050 at k=1).
  P4. The collapse rate under device-derived skew should be far below IoT-23's 0.26 at beta=0 and 1.00 at beta>=0.30.

FALSIFICATION. If instead N-BaIoT's device-derived partition collapses certification to a similar degree despite the near-zero device-label coupling, the corrected mechanism is WRONG and something else about device-derived partitioning is responsible. That outcome must be reported as a refutation, not explained away.

CAVEAT TO CARRY EITHER WAY: tau_triv = 0.9000 on N-BaIoT is a much higher trivial floor than IoT-23's 0.7300, so a certified accuracy has to clear a harder bar to carry information at all. beta* is defined against tau_triv, so this makes P3 HARDER to satisfy, not easier -- the prediction is not being graded on a curve.

SCOPE: five devices, not the published nine. Provision_PT_838 lacks its Mirai partition and Samsung and both SimpleHome cameras lack their attack partitions; UCI's endpoint streams a ~2 GB archive without Content-Length or range support and drops between 500 MB and 1.2 GB, and the missing devices are alphabetically last. Recovery continues; the device catalogue will be extended if the tail arrives.
