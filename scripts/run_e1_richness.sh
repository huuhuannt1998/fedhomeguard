#!/usr/bin/env bash
# E1 (review W2): the headline collapse may be a property of the 1-3 device household
# model rather than of federated IoT IDS. The paper already has dph=(1,1) and (2,5),
# which differ by 6x in beta*. Fill in the sweep so the finding can be stated as a
# function of household device richness rather than asserted at one arbitrary point.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/e1_richness.log; : > $L
B="0 0.05 0.1 0.2 0.3 0.4"; KC12="1:20,2:190"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
run(){ local D="$1" T="$2"
  $PY scripts/exp_e2.py --partition device_derived --dph $D --tag E1_dph${T} \
    --pseed 0 1 2 --k 1 2 --betas $B --clean-only --k-caps "$KC12" \
    --out results/canonical/e11_dph$T.jsonl >>$L 2>&1 \
    && log "  ok dph=$D ($(grep -c '^{' results/canonical/e11_dph$T.jsonl) rows)" \
    || log "  FAILED dph=$D"; }
log "=== E1 device-richness sweep start ==="
run "3 8" 3_8 & run "5 10" 5_10 & wait
log "=== E1 complete ==="
