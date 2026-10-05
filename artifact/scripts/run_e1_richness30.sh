#!/usr/bin/env bash
# E1' (review W5/W9 fallout): the 3-draw richness sweep is under-powered -- over 30
# draws the device-derived beta* at k=1 spans 0.00-0.20 with 13/30 at exactly zero,
# so a 3-draw median carries sampling error as large as the effect it reports.
# Re-run every richness level on the SAME 30 seeds, k=1, fine grid to 0.50 (the
# coarse grid stopping at 0.40 right-censors the device-rich levels).
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/e1_richness30.log; : > $L
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
S=$(seq 0 29 | tr '\n' ' ')
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
run(){ local D="$1" T="$2"
  $PY scripts/exp_e2.py --partition device_derived --dph $D --tag E1b_dph${T} \
    --pseed $S --k 1 --betas $B --clean-only --k-caps "1:20" \
    --out results/canonical/e11b_dph$T.jsonl >>$L 2>&1 \
    && log "  ok dph=$D ($(grep -c '^{' results/canonical/e11b_dph$T.jsonl) rows)" \
    || log "  FAILED dph=$D"; }
log "=== E1' 30-draw richness sweep start ==="
run "1 1" 1_1 &  run "1 3" 1_3 &  run "2 5" 2_5 &  run "3 8" 3_8 &  run "5 10" 5_10 &
wait
log "=== E1' complete ==="
