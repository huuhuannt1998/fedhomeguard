#!/usr/bin/env bash
# Predeclared test: predeclarations/richness_nbaiot.md
#
# The paper attributes the device-derived collapse to device identity predicting
# the label (I = 0.32 bits on IoT-23, 0.005 on N-BaIoT). If that is the mechanism,
# device richness is IRRELEVANT on N-BaIoT: beta* should stay flat at the ceiling
# across the whole grid, while the same grid on IoT-23 spans 0.000 to 0.450.
#
# Same estimator, same 30 draws, same beta grid, same k as the IoT-23 sweep.
# N-BaIoT has 9 devices, so the top level is (5,9) rather than (5,10).
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/richness_nbaiot.log; : > $L
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
S=$(seq 0 29 | tr '\n' ' ')
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
run(){ local D="$1" T="$2"
  $PY scripts/exp_e2.py --config configs/stage3_nbaiot.yaml --partition device_derived \
      --dph $D --tag NBR_$T --pseed $S --k 1 --betas $B --clean-only --k-caps "1:20" \
      --out results/canonical/e21_nbrich_$T.jsonl >>$L 2>&1 \
    && log "  ok dph=$D ($(grep -c '^{' results/canonical/e21_nbrich_$T.jsonl) rows)" \
    || log "  FAILED dph=$D"; }
log "=== N-BaIoT device-richness sweep (predeclared null) ==="
run "1 1" 1_1 & run "1 3" 1_3 & run "2 5" 2_5 & wait
run "3 8" 3_8 & run "5 9" 5_9 & wait
log "=== complete ==="
