#!/usr/bin/env bash
# Predeclared test: predeclarations/richness_k2.md
#
# Is the richness boundary a property of the federation, or of single-household
# members? A k=2 member trains on the union of two households, so pooling should
# supply the classes a device-poor household lacks and move the boundary left --
# while Corollary 1 lowers the ceiling from 0.450 to 0.250, so the comparison is
# on beta*/beta_geo(20,k), not raw beta*.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/richness_k2.log; : > $L
B="0 0.05 0.1 0.15 0.2 0.25 0.3 0.35 0.4 0.45 0.5"
S=$(seq 0 29 | tr '\n' ' ')
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
run(){ local D="$1" T="$2"
  $PY scripts/exp_e2.py --partition device_derived --dph $D --tag K2R_$T \
      --pseed $S --k 2 --betas $B --clean-only --k-caps "2:190" \
      --out results/canonical/e22_k2rich_$T.jsonl >>$L 2>&1 \
    && log "  ok dph=$D ($(grep -c '^{' results/canonical/e22_k2rich_$T.jsonl) rows)" \
    || log "  FAILED dph=$D"; }
log "=== k=2 device-richness sweep, IoT-23, full enumeration K=190 ==="
run "1 1" 1_1 & run "1 3" 1_3 & wait
run "2 5" 2_5 & run "3 8" 3_8 & wait
run "5 10" 5_10
log "=== complete ==="
