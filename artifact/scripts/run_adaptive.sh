#!/usr/bin/env bash
# Objection #13: EA_ens minimises over five PUBLISHED attacks, none designed against a
# plurality-vote ensemble. This adds an adaptive, white-box attack that solves for the
# FedAvg aggregate instead of perturbing its own contribution, and re-measures the
# cells where EA still has headroom.
set -u; cd "$(dirname "$0")/.."
PY=${PY:-python3}; L=logs/adaptive.log; : > $L
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }
ATT="label_flip sign_flip gaussian ipm alie adaptive"
run_p(){ local P=$1
  $PY scripts/exp_e2.py --partition $P --pseed 0 1 2 --k 1 2 --betas 0.05 0.1 0.2 \
    --mal-seeds 0 1 2 --k-caps "1:20,2:190" --attacks $ATT --tag ADAPTIVE \
    --out results/scratch/adaptive/adaptive_$P.jsonl >>$L 2>&1 \
    && log "  ok adaptive_$P ($(grep -c '^{' results/scratch/adaptive/adaptive_$P.jsonl) rows)" \
    || log "  FAILED adaptive_$P"; }
log "=== adaptive attack sweep start ==="
run_p iid & run_p device_derived & wait
log "=== adaptive sweep complete ==="
