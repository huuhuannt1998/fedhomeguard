#!/usr/bin/env bash
# Predeclared in predeclarations/richness_nbaiot_k2.md (commit 7f41a65), BEFORE
# this ran. Completes the corpus x subsample 2x2:
#
#            k=1                        k=2
#   IoT-23   0.000 -> 0.450 (varies)    0.000 -> 0.250 (varies, boundary moves left)
#   N-BaIoT  flat 0.450 (null)          <- this run; mechanism predicts flat 0.250
#
# The exact intersection of run_richness_nbaiot.sh (corpus, config, grid) and
# run_richness_k2.sh (k=2, K=190 full enumeration). Nothing else differs.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/richness_nbaiot_k2.log; : > $L
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
S=$(seq 0 29 | tr '\n' ' ')
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
run(){ local D="$1" T="$2"
  $PY scripts/exp_e2.py --config configs/stage3_nbaiot.yaml --partition device_derived \
      --dph $D --tag NBK2R_$T --pseed $S --k 2 --betas $B --clean-only --k-caps "2:190" \
      --out results/canonical/e23_nbk2rich_$T.jsonl >>$L 2>&1 \
    && log "  ok dph=$D ($(grep -c '^{' results/canonical/e23_nbk2rich_$T.jsonl) rows)" \
    || log "  FAILED dph=$D"; }
log "=== N-BaIoT k=2 device-richness sweep (predeclared: flat at 0.250) ==="
run "1 1" 1_1 & run "1 3" 1_3 & run "2 5" 2_5 & wait
run "3 8" 3_8 & run "5 9" 5_9 & wait
log "=== complete ==="
