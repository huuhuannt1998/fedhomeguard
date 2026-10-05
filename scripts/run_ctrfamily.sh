#!/usr/bin/env bash
# Technical comment 5: CTR_mal per attack family. The aggregate is the paper's
# headline security number, and IoT-23 labels each malicious flow with its family
# (C&C, DDoS, horizontal port scan, ...). A certificate covering DDoS but not C&C
# beacons is a different security statement from the one the aggregate implies.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/ctrfamily.log; : > $L
B="0 0.05 0.1 0.2 0.3 0.4"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
log "=== CTR_mal by attack family, k=1 ==="
for P in iid device_derived; do
  $PY scripts/exp_e2.py --partition $P --tag CTRFAM --pseed 0 1 2 --k 1 \
      --betas $B --k-caps "1:20" \
      --out results/canonical/e17_ctrfamily_$P.jsonl >>$L 2>&1 \
    && log "  ok $P ($(grep -c '^{' results/canonical/e17_ctrfamily_$P.jsonl) rows)" \
    || log "  FAILED $P"
done
log "=== complete ==="
